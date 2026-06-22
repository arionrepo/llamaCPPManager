//
//  StatusViewModel.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/ViewModels/StatusViewModel.swift
//  Description: Master view model — status polling, model lifecycle control (start/stop/restart/start-all/stop-all), infrastructure control, chat/preferences/downloader window lifecycle, logging toggle, monitor tracking, external server scanner, startup log parser. Single big coordinator (decomposition is a deferred follow-up).
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import SwiftUI
import AppKit
import Combine

@MainActor
final class StatusViewModel: ObservableObject {
    @Published var rows: [StatusRow] = []
    @Published var dockerRows: [StatusRow] = []
    @Published var infrastructureRows: [InfrastructureRow] = []
    @Published var loggingConfig: LoggingConfig?
    @Published var selectedModes: [String: String] = [:]  // Model name -> mode
    @Published var startupProgress: [String: ModelStartupProgress] = [:]
    private var logMonitorTasks: [String: Task<Void, Never>] = [:]

    // Persistent download view model — survives catalog window closes
    let downloadViewModel: DownloadViewModel
    private let service = CLIService()
    private var timer: Timer?
    private var chatWindows: [String: NSWindow] = [:]
    private var windowDelegates: [String: ChatWindowDelegate] = [:]
    private var monitoredModels: Set<String> = []
    private var modelDownloaderWindow: NSWindow?
    private var modelDownloaderDelegate: ModelDownloaderWindowDelegate?
    private var preferencesWindow: NSWindow?
    private let preferences = PreferencesManager.shared
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Computed Status Properties

    var isAnyModelRunning: Bool {
        // Check if any native model is running
        let nativeRunning = rows.contains { $0.up }
        // Check if any Docker model is running
        let dockerRunning = dockerRows.contains { $0.up }
        return nativeRunning || dockerRunning
    }

    var hasAnyErrors: Bool {
        // Check for native model errors (model with PID but not responding)
        let nativeErrors = rows.contains { row in
            row.pid != nil && !row.up
        }
        // Check for Docker errors
        let dockerErrors = dockerRows.contains { $0.health_state == "unhealthy" }
        // Check infrastructure errors - use healthy boolean field
        let infraErrors = infrastructureRows.contains { !$0.healthy }

        return nativeErrors || dockerErrors || infraErrors
    }

    var overallStatusColor: Color {
        if hasAnyErrors {
            return .red  // Something is wrong
        } else if isAnyModelRunning {
            return .green  // Models are running (will blink)
        } else {
            return .gray  // All is quiet but ready
        }
    }

    init() {
        self.downloadViewModel = DownloadViewModel(cliService: service)

        // Forward DownloadViewModel changes so views observing StatusViewModel re-render
        downloadViewModel.objectWillChange
            .sink { [weak self] _ in
                self?.objectWillChange.send()
            }
            .store(in: &cancellables)

        // Observe refresh interval changes
        preferences.$refreshInterval
            .sink { [weak self] _ in
                self?.setupRefreshTimer()
            }
            .store(in: &cancellables)

        // Start scanner for external model server processes (mlx_lm.server, llama-server)
        // that may be lazy-downloading model files.
        startExternalServerScanner()
    }

    // MARK: - External Server Process Scanner

    private var externalServerScanTask: Task<Void, Never>?

    private func startExternalServerScanner() {
        externalServerScanTask?.cancel()
        externalServerScanTask = Task.detached(priority: .background) { [weak self] in
            while !Task.isCancelled {
                guard let self = self else { return }
                let activeNames = await self.scanForActiveServersOffMain()
                await self.applyExternalServerScan(activeNames: activeNames)
                try? await Task.sleep(nanoseconds: 3_000_000_000)
            }
        }
    }

    /// Run `ps` on a background queue, look for mlx_lm.server / llama-server
    /// processes, and extract the model name they're running.
    nonisolated private func scanForActiveServersOffMain() async -> Set<String> {
        await withCheckedContinuation { continuation in
            DispatchQueue.global(qos: .background).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/bin/ps")
                process.arguments = ["-eo", "command"]
                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = Pipe()
                do {
                    try process.run()
                    process.waitUntilExit()
                } catch {
                    continuation.resume(returning: [])
                    return
                }
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                guard let output = String(data: data, encoding: .utf8) else {
                    continuation.resume(returning: [])
                    return
                }
                var names = Set<String>()
                for line in output.split(separator: "\n") {
                    let s = String(line)
                    // mlx_lm.server pattern: --model <hf_repo_or_path>
                    if s.contains("mlx_lm.server") || s.contains("mlx_lm/server.py") {
                        if let modelArg = StatusViewModel.argValue(in: s, flag: "--model") {
                            names.insert(modelArg)
                        }
                    }
                    // llama-server pattern: -m <path>
                    if s.contains("llama-server") {
                        if let pathArg = StatusViewModel.argValue(in: s, flag: "-m") {
                            names.insert(pathArg)
                        }
                    }
                }
                continuation.resume(returning: names)
            }
        }
    }

    nonisolated private static func argValue(in command: String, flag: String) -> String? {
        let tokens = command.split(separator: " ", omittingEmptySubsequences: true).map(String.init)
        guard let idx = tokens.firstIndex(of: flag), idx + 1 < tokens.count else { return nil }
        return tokens[idx + 1]
    }

    @MainActor
    private func applyExternalServerScan(activeNames: Set<String>) {
        // For each running server, match to a model in our config and add to startupProgress
        // if the health check says it isn't ready yet.
        for row in rows where !row.up {
            let isMatching = activeNames.contains(row.name) ||
                activeNames.contains(where: { $0.contains(row.name) })
            if isMatching && startupProgress[row.name] == nil {
                startupProgress[row.name] = ModelStartupProgress(
                    status: "Loading (server starting)...",
                    progress: nil,
                    detail: nil,
                    startedAt: Date()
                )
                startLogMonitor(for: row.name)
            }
        }
    }

    func startPolling(interval: TimeInterval = 2.0) {
        setupRefreshTimer()
        refresh()
        loadMonitoredModels()
    }

    private func loadMonitoredModels() {
        Task { [weak self] in
            guard let self = self else { return }

            // Get monitor status to load tracked models
            guard let output = try? await service.runAndCapture(["monitor", "status"]) else {
                AppLogger.log("Failed to load monitored models", level: .error)
                return
            }

            await MainActor.run { [weak self] in
                guard let self = self else { return }

                // Parse output to find tracked models
                // Output format: "  - model-name"
                let lines = output.components(separatedBy: "\n")
                var tracked = Set<String>()
                var inTrackedSection = false

                for line in lines {
                    if line.contains("Tracked Models:") {
                        inTrackedSection = true
                        continue
                    }
                    if inTrackedSection && line.trimmingCharacters(in: .whitespaces).starts(with: "- ") {
                        let modelName = line.trimmingCharacters(in: .whitespaces).dropFirst(2).trimmingCharacters(in: .whitespaces)
                        tracked.insert(String(modelName))
                    } else if inTrackedSection && !line.trimmingCharacters(in: .whitespaces).isEmpty && !line.contains("- ") {
                        break
                    }
                }

                self.monitoredModels = tracked
                AppLogger.log("Loaded \(tracked.count) monitored models", level: .info)
            }
        }
    }

    private func setupRefreshTimer() {
        timer?.invalidate()
        guard preferences.refreshInterval > 0 else { return }

        timer = Timer.scheduledTimer(
            withTimeInterval: TimeInterval(preferences.refreshInterval),
            repeats: true
        ) { [weak self] _ in
            Task { @MainActor in
                self?.refresh()
            }
        }
    }

    func refresh() {
        Task { @MainActor in
            do {
                let response = try await service.fetchStatus()
                self.rows = response.models
                self.infrastructureRows = response.infrastructure
                self.loggingConfig = response.logging

                // Load saved modes for native models
                for model in response.models {
                    if let savedMode = model.mode {
                        self.selectedModes[model.name] = savedMode
                    } else {
                        // Default to basic if not set
                        self.selectedModes[model.name] = "basic"
                    }
                }

                // Fetch Docker status separately
                do {
                    let dockerResponse = try await service.fetchDockerStatus()
                    self.dockerRows = dockerResponse.models

                    // Load saved modes for Docker models
                    for model in dockerResponse.models {
                        if let savedMode = model.mode {
                            self.selectedModes[model.name] = savedMode
                        } else {
                            // Default to basic if not set
                            self.selectedModes[model.name] = "basic"
                        }
                    }
                } catch {
                    // Keep prior Docker rows on error
                    AppLogger.log("Failed to fetch Docker status: \(error.localizedDescription)", level: .warning)
                }
            } catch {
                // Keep prior rows; optionally surface an error row
            }
        }
    }

    // MARK: - Mode Persistence

    func saveMode(for modelName: String, mode: String) {
        Task { [weak self] in
            guard let self = self else { return }

            // Update mode in config using CLI
            let command = ["config", "update", modelName, "--mode", mode]
            let result = await service.run(command)

            if result == 0 {
                AppLogger.log("Successfully saved mode '\(mode)' for model: \(modelName)", level: .info)
                // Mode is already updated in selectedModes by the UI
            } else {
                AppLogger.log("Failed to save mode for model: \(modelName)", level: .error)
                // Refresh to restore actual state
                refresh()
            }
        }
    }

    // MARK: - Logging Control Methods

    func toggleLogging() {
        Task { [weak self] in
            guard let self = self else { return }

            let command = loggingConfig?.enabled == true ? ["logging", "disable"] : ["logging", "enable"]
            let result = await service.run(command)

            if result == 0 {
                AppLogger.log("Logging toggle successful: \(command.joined(separator: " "))", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to toggle logging with command: \(command.joined(separator: " "))", level: .error)
            }
        }
    }

    func toggleTimestamps() {
        Task { [weak self] in
            guard let self = self else { return }

            let command = loggingConfig?.timestamps == true ? ["logging", "timestamps", "off"] : ["logging", "timestamps", "on"]
            let result = await service.run(command)

            if result == 0 {
                AppLogger.log("Timestamps toggle successful: \(command.joined(separator: " "))", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to toggle timestamps with command: \(command.joined(separator: " "))", level: .error)
            }
        }
    }

    func start(name: String) {
        Task { [weak self] in
            guard let self = self else { return }
            let result = await service.run(["start", name])
            if result == 0 {
                AppLogger.log("Successfully started model: \(name)", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to start model: \(name)", level: .error)
            }
        }
    }

    func startWithScript(name: String, mode: String? = nil, isDocker: Bool = false) {
        // Determine deployment type from the configured row, so we can route MLX / MLX-VLM / GGUF correctly
        let row = rows.first(where: { $0.name == name })
        // Prefer the explicit deployment_type field from the CLI status payload when present,
        // fall back to the format field, then default to gguf.
        let deployment = (row?.deployment_type?.lowercased())
                       ?? (row?.format?.lowercased())
                       ?? "gguf"
        let isMlx = deployment == "mlx"
        let isMlxVlm = deployment == "mlx-vlm" || deployment == "diffusion"

        LifecycleLog.log("ui.start.clicked", model: name, [
            "isDocker": isDocker,
            "deployment": deployment,
            "mode": mode ?? selectedModes[name] ?? "default"
        ])

        // Set initial startup progress (visible immediately in UI)
        startupProgress[name] = ModelStartupProgress(
            status: "Starting...",
            progress: nil,
            detail: nil,
            startedAt: Date()
        )
        startLogMonitor(for: name)

        Task { [weak self] in
            guard let self = self else { return }

            let result: Int32
            let command: [String]
            if isDocker {
                let effectiveMode = mode ?? selectedModes[name] ?? "tools"
                command = ["docker", "start", name, "--mode", effectiveMode]
            } else if isMlxVlm {
                // MLX-VLM models (e.g., DiffusionGemma) go through `start` which routes
                // to start_mlx_vlm_process via the Phase 1b CLI branch.
                command = ["start", name]
            } else if isMlx {
                // MLX models MUST go through `start` (which routes to start_mlx_process).
                // `start-script` only supports llama-server / GGUF, so MLX models silently fail there.
                command = ["start", name]
            } else {
                let effectiveMode = mode ?? selectedModes[name] ?? "basic"
                command = ["start-script", name, "--mode", effectiveMode]
            }

            LifecycleLog.log("ui.start.cli_invoke", model: name, [
                "command": command,
                "deployment": deployment
            ])
            result = await service.run(command)
            LifecycleLog.log("ui.start.cli_result", model: name, [
                "exit_code": result,
                "command": command
            ])

            if result == 0 {
                AppLogger.log("Successfully started \(name) (deployment=\(deployment))", level: .info)
                try? await Task.sleep(nanoseconds: 3_000_000_000)
                refresh()
            } else {
                AppLogger.log("Failed to start \(name) (exit=\(result))", level: .error)
                await MainActor.run {
                    self.startupProgress.removeValue(forKey: name)
                    self.stopLogMonitor(for: name)
                }
            }
        }
    }

    // MARK: - Startup Log Monitoring

    private func startLogMonitor(for name: String) {
        stopLogMonitor(for: name)  // ensure no duplicates

        let task = Task { [weak self] in
            // Log path used by both MLX and native models
            let logPath = "\(NSHomeDirectory())/Library/Logs/llamaCPPManager/\(name).log"

            // Poll every 1 second for log changes
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard let self = self else { return }

                // Stop monitoring if the model is up
                let isUp = await MainActor.run { () -> Bool in
                    let nativeUp = self.rows.first(where: { $0.name == name })?.up ?? false
                    let dockerUp = self.dockerRows.first(where: { $0.name == name })?.up ?? false
                    return nativeUp || dockerUp
                }

                if isUp {
                    await MainActor.run {
                        self.startupProgress.removeValue(forKey: name)
                        self.stopLogMonitor(for: name)
                    }
                    return
                }

                // Auto-clear if startup is taking too long (>10 minutes)
                let elapsed = await MainActor.run { () -> TimeInterval in
                    guard let started = self.startupProgress[name]?.startedAt else { return 0 }
                    return Date().timeIntervalSince(started)
                }
                if elapsed > 600 {
                    await MainActor.run {
                        self.startupProgress.removeValue(forKey: name)
                        self.stopLogMonitor(for: name)
                    }
                    return
                }

                // Read tail of log file
                if let progress = self.parseStartupLog(path: logPath, modelName: name) {
                    await MainActor.run {
                        if var existing = self.startupProgress[name] {
                            existing.status = progress.status
                            existing.progress = progress.progress
                            existing.detail = progress.detail
                            self.startupProgress[name] = existing
                        }
                    }
                }
            }
        }
        logMonitorTasks[name] = task
    }

    private func stopLogMonitor(for name: String) {
        logMonitorTasks[name]?.cancel()
        logMonitorTasks.removeValue(forKey: name)
    }

    private func extractNumbers(from text: String) -> [Int] {
        var result: [Int] = []
        var current = ""
        for ch in text {
            if ch.isNumber {
                current.append(ch)
            } else {
                if let n = Int(current) { result.append(n) }
                current = ""
            }
        }
        if let n = Int(current) { result.append(n) }
        return result
    }

    private func parseStartupLog(path: String, modelName: String) -> ModelStartupProgress? {
        // Read up to last ~64KB of the log; for big log files we'd otherwise pull
        // megabytes into memory and parse them on the caller's thread.
        let maxBytes = 64 * 1024
        guard let handle = FileHandle(forReadingAtPath: path) else { return nil }
        defer { try? handle.close() }
        let size = (try? handle.seekToEnd()) ?? 0
        let offset = size > UInt64(maxBytes) ? size - UInt64(maxBytes) : 0
        try? handle.seek(toOffset: offset)
        let data = handle.readDataToEndOfFile()
        guard let text = String(data: data, encoding: .utf8) else { return nil }
        let lines = text.split(separator: "\n").suffix(50).map(String.init)

        var latest = ModelStartupProgress(
            status: "Starting...",
            progress: nil,
            detail: nil,
            startedAt: Date()
        )

        for line in lines {
            // MLX download progress: "Fetching 11 files:   9%|...| 1/11 [...]"
            if line.contains("Fetching") && line.contains("files:") {
                let numbers = extractNumbers(from: line)
                if numbers.count >= 4 {
                    // [totalFiles, percent, currentFile, totalFiles_again]
                    let percent = Double(numbers[1]) / 100.0
                    latest.status = "Downloading model files..."
                    latest.progress = percent
                    latest.detail = "\(numbers[2])/\(numbers[3]) files"
                }
            }
            // MLX server ready: "Starting httpd at..." or similar
            else if line.contains("Starting httpd") || line.contains("Running on http") || line.contains("Uvicorn running") {
                latest.status = "Server ready, performing health check..."
                latest.progress = 0.95
            }
            // Model loading (llama.cpp)
            else if line.contains("llm_load_tensors") || line.contains("loading model") || line.contains("load_tensors:") {
                latest.status = "Loading model into memory..."
                latest.progress = 0.85
            }
            // llama.cpp warmup
            else if line.contains("warming up") || line.contains("system_info:") {
                latest.status = "Warming up..."
                latest.progress = 0.9
            }
            // Downloading from HuggingFace
            else if line.contains("HTTP Request") && line.contains("safetensors") {
                if latest.progress == nil {
                    latest.status = "Downloading from HuggingFace..."
                }
            }
            // Errors
            else if line.lowercased().contains("error") && !line.contains("favicon") {
                latest.status = "Issue detected (see logs)"
            }
        }
        return latest
    }

    func stop(name: String, isDocker: Bool = false) {
        LifecycleLog.log("ui.stop.clicked", model: name, ["isDocker": isDocker])
        Task { [weak self] in
            guard let self = self else { return }
            let command = isDocker ? ["docker", "stop", name] : ["stop", name]
            LifecycleLog.log("ui.stop.cli_invoke", model: name, ["command": command])
            let result = await service.run(command)
            LifecycleLog.log("ui.stop.cli_result", model: name, [
                "exit_code": result, "command": command
            ])
            if result == 0 {
                let systemLabel = isDocker ? "Docker container" : "model"
                AppLogger.log("Successfully stopped \(systemLabel): \(name)", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to stop \(name)", level: .error)
            }
        }
    }

    func restart(name: String, isDocker: Bool = false) {
        Task { [weak self] in
            guard let self = self else { return }
            let command = isDocker ? ["docker", "restart", name] : ["restart", name]
            let result = await service.run(command)
            if result == 0 {
                let systemLabel = isDocker ? "Docker container" : "model"
                AppLogger.log("Successfully restarted \(systemLabel): \(name)", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to restart \(name)", level: .error)
            }
        }
    }

    func startAllModels(isDocker: Bool = false) {
        Task { [weak self] in
            guard let self = self else { return }
            let command = isDocker ? ["docker", "start", "all"] : ["start", "all"]
            let result = await service.run(command)
            if result == 0 {
                let systemLabel = isDocker ? "Docker containers" : "models"
                AppLogger.log("Successfully started all \(systemLabel)", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to start all models", level: .error)
            }
        }
    }

    func stopAllModels(isDocker: Bool = false) {
        Task { [weak self] in
            guard let self = self else { return }
            let command = isDocker ? ["docker", "stop", "all"] : ["stop", "all"]
            let result = await service.run(command)
            if result == 0 {
                let systemLabel = isDocker ? "Docker containers" : "models"
                AppLogger.log("Successfully stopped all \(systemLabel)", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to stop all models", level: .error)
            }
        }
    }

    func tailLogs(name: String, isDocker: Bool = false) {
        if isDocker {
            // For Docker containers, fetch logs via CLI and display in a window
            Task { [weak self] in
                guard let self = self else { return }
                do {
                    let logs = try await service.dockerLogs(name: name)
                    await MainActor.run {
                        self.showLogsWindow(title: "Docker Logs: \(name)", content: logs)
                    }
                } catch {
                    AppLogger.log("Failed to fetch Docker logs for \(name): \(error.localizedDescription)", level: .error)
                }
            }
        } else {
            // Native models: Open log file with system default app (Console.app on macOS)
            guard let row = rows.first(where: { $0.name == name }), let path = row.log_path else { return }
            let url = URL(fileURLWithPath: path)
            NSWorkspace.shared.open(url)
        }
    }

    // MARK: - Infrastructure Control Methods

    func startInfra(name: String) {
        Task {
            try? await service.startInfrastructure(name)
            refresh()
        }
    }

    func stopInfra(name: String) {
        Task {
            try? await service.stopInfrastructure(name)
            refresh()
        }
    }

    func restartInfra(name: String) {
        Task {
            try? await service.restartInfrastructure(name)
            refresh()
        }
    }

    func infraLogs(name: String) {
        // Open infrastructure log file with system default app (Console.app on macOS)
        // Infrastructure logs are in ~/llms/logs/
        let homeDir = FileManager.default.homeDirectoryForCurrentUser
        let logDir = homeDir.appendingPathComponent("llms/logs")

        // Determine log filename based on component
        // cloudflared writes to stderr, most others to stdout
        let filename: String
        if name == "cloudflared" {
            filename = "cloudflared.err.log"  // cloudflared uses stderr
        } else if name.contains("controller") {
            filename = "controller.out.log"
        } else {
            filename = "\(name).out.log"
        }

        let logURL = logDir.appendingPathComponent(filename)
        NSWorkspace.shared.open(logURL)
    }

    func healthColorInfra(for row: InfrastructureRow) -> Color {
        if !row.enabled { return .gray }
        if !row.running { return .red }
        if !row.healthy { return .orange }
        return .green
    }

    func healthStatusInfra(for row: InfrastructureRow) -> String {
        if !row.enabled { return "disabled" }
        if !row.running { return "stopped" }
        if !row.healthy { return "unhealthy" }
        return row.health_status
    }

    private func showLogsWindow(title: String, content: String) {
        let textView = NSTextView()
        textView.string = content
        textView.isEditable = false
        textView.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)

        let scrollView = NSScrollView(frame: NSRect(x: 0, y: 0, width: 800, height: 600))
        scrollView.documentView = textView
        scrollView.hasVerticalScroller = true

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 800, height: 600),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = title
        window.contentView = scrollView
        window.center()
        window.makeKeyAndOrderFront(nil)
    }

    func openChat(name: String) {
        // Check if chat window already exists for this model
        if let existingWindow = chatWindows[name] {
            existingWindow.level = .floating
            existingWindow.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        // Create new chat window
        let chatViewModel = ChatViewModel(modelName: name, cliService: service)
        let chatView = ChatView(viewModel: chatViewModel)
        let hostingController = NSHostingController(rootView: chatView)

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 600, height: 800),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )

        window.title = "Chat with \(name)"
        window.contentViewController = hostingController
        window.center()
        window.level = .floating
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        // Store window reference
        chatWindows[name] = window

        // Set up window delegate to clean up when closed
        let delegate = ChatWindowDelegate { [weak self] in
            self?.chatWindows.removeValue(forKey: name)
            self?.windowDelegates.removeValue(forKey: name)
        }
        windowDelegates[name] = delegate
        window.delegate = delegate
    }

    func openConfig() {
        // Open config dir in Finder
        if let dir = service.configDirURL() { NSWorkspace.shared.activateFileViewerSelecting([dir]) }
    }

    func openModelDownloader() {
        // Check if model downloader window already exists
        if let existingWindow = modelDownloaderWindow {
            existingWindow.level = .floating
            existingWindow.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        // Reuse persistent download view model so downloads survive window close
        let downloaderView = ModelDownloaderView(viewModel: downloadViewModel)
        let hostingController = NSHostingController(rootView: downloaderView)

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 750, height: 650),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )

        window.title = "Model Downloader"
        window.contentViewController = hostingController
        window.center()
        window.level = .floating
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        // Store window reference
        modelDownloaderWindow = window

        // Set up window delegate to clean up when closed
        modelDownloaderDelegate = ModelDownloaderWindowDelegate { [weak self] in
            self?.modelDownloaderWindow = nil
        }
        window.delegate = modelDownloaderDelegate
    }

    // MARK: - Enhanced Health Status Methods

    func healthColor(for row: StatusRow) -> Color {
        let healthState = row.health_state ?? "down"
        switch healthState {
        case "ok":
            return .green
        case "starting":
            return .orange
        case "down":
            return .red
        default:
            return .gray
        }
    }

    func healthStatus(for row: StatusRow) -> String {
        let healthState = row.health_state ?? "down"
        let mode = row.mode ?? "unknown"

        switch healthState {
        case "ok":
            return "Running (\(mode))"
        case "starting":
            return "Starting..."
        case "down":
            return "Stopped"
        default:
            return "Unknown"
        }
    }

    func formatBadgeColor(_ format: String) -> Color {
        switch format.lowercased() {
        case "gguf":
            return .blue
        case "mlx":
            return .purple
        case "moe":
            return .orange
        case "diffusion":
            return .pink
        default:
            return .gray
        }
    }

    func isMonitored(name: String) -> Bool {
        return monitoredModels.contains(name)
    }

    func toggleMonitoring(name: String) {
        AppLogger.log("Toggling monitoring for model: \(name)", level: .debug)

        if monitoredModels.contains(name) {
            // Untrack model
            Task { [weak self] in
                guard let self = self else { return }
                let result = await service.run(["monitor", "untrack", name])

                await MainActor.run { [weak self] in
                    guard let self = self else { return }
                    if result == 0 {
                        monitoredModels.remove(name)
                        AppLogger.log("Successfully untracked model: \(name)", level: .info)
                        refresh()
                    } else {
                        AppLogger.log("Failed to untrack model: \(name)", level: .error)
                    }
                }
            }
        } else {
            // Track model
            Task { [weak self] in
                guard let self = self else { return }
                let result = await service.run(["monitor", "track", name])

                await MainActor.run { [weak self] in
                    guard let self = self else { return }
                    if result == 0 {
                        monitoredModels.insert(name)
                        AppLogger.log("Successfully tracked model: \(name)", level: .info)
                        refresh()
                    } else {
                        AppLogger.log("Failed to track model: \(name)", level: .error)
                    }
                }
            }
        }
    }

    func openCLI() {
        // Open Terminal with llamacpp-manager ready to use
        let script = """
        tell application "Terminal"
            activate
            do script "export PATH=\\"$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH\\"; echo \\"llamaCPP Manager CLI - Ready!\\"; echo \\"Try: llamacpp-manager --help\\"; echo"
        end tell
        """

        if let appleScript = NSAppleScript(source: script) {
            appleScript.executeAndReturnError(nil)
        }
    }

    func openHelp() {
        // Open comprehensive help documentation in a separate window
        let helpContent = loadUserManual()

        // Create text view with proper sizing
        let textView = NSTextView(frame: NSRect(x: 0, y: 0, width: 900, height: 700))
        textView.string = helpContent
        textView.isEditable = false
        textView.font = NSFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        textView.textColor = NSColor.labelColor
        textView.backgroundColor = NSColor.textBackgroundColor
        textView.textContainerInset = NSSize(width: 20, height: 20)
        textView.autoresizingMask = [.width, .height]

        // Ensure text view is properly sized
        textView.minSize = NSSize(width: 0, height: 0)
        textView.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        textView.isVerticallyResizable = true
        textView.isHorizontallyResizable = false
        textView.textContainer?.containerSize = NSSize(width: 860, height: CGFloat.greatestFiniteMagnitude)
        textView.textContainer?.widthTracksTextView = true

        let scrollView = NSScrollView(frame: NSRect(x: 0, y: 0, width: 900, height: 700))
        scrollView.documentView = textView
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 900, height: 700),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "llamaCPP Manager - User Manual"
        window.contentView = scrollView
        window.center()
        window.level = .floating
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        // Keep window reference to prevent deallocation
        window.isReleasedWhenClosed = false
    }

    private func loadUserManual() -> String {
        // Try to load user-manual.md from bundle or fall back to basic help
        if let bundleURL = Bundle.main.url(forResource: "user-manual", withExtension: "md"),
           let content = try? String(contentsOf: bundleURL, encoding: .utf8) {
            return content
        }

        // Fallback to comprehensive built-in help
        return """
        # llamaCPP Manager - User Manual

        A complete guide to managing llama.cpp models on macOS.

        ## Quick Start

        ### 1. GUI Controls

        **Status Indicators:**
        • 🟢 Green Circle = Model running and healthy
        • 🔴 Red Circle = Model stopped
        • 🟠 Orange Circle = Model starting or unhealthy
        • ⚫ Gray Circle = Model disabled

        **Model Controls:**
        • **Start** - Start a stopped model
        • **Stop** - Stop a running model
        • **Restart** - Restart a model (stop + start)
        • **Chat** - Open chat window (only when model is running)
        • **Monitor** - Enable/disable auto-restart monitoring
        • **Logs** - View model logs in Console.app

        **Global Actions:**
        • **Start All Models** - Start all configured models
        • **Stop All Models** - Stop all currently running models
        • **Refresh** - Manually refresh status
        • **Open Config** - Open configuration directory in Finder
        • **Open CLI** - Launch Terminal with llamacpp-manager CLI

        ### 2. Model Management

        **Adding Models:**
        1. Click "Open CLI" to access the command line
        2. Run: `llamacpp-manager config add MODEL_NAME /path/to/model.gguf --port PORT`
        3. Refresh the GUI to see the new model

        **Example:**
        ```bash
        llamacpp-manager config add phi3 ~/llms/phi3/model.gguf --port 8081
        ```

        **Starting Models:**
        1. Find your model in the Models list
        2. Click "Start" button
        3. Wait for green indicator
        4. Click "Chat" to interact or visit http://127.0.0.1:[PORT] in browser

        ### 3. Model Downloader

        **Downloading Pre-Configured Models:**

        The CLI includes a curated library of agentic and coding models optimized for different use cases.

        **List Available Models:**
        ```bash
        llamacpp-manager models list --available
        ```

        **Download a Model:**
        ```bash
        llamacpp-manager models download qwen-coder-7b
        ```

        **Available Agentic Models:**
        • **qwen-coder-7b** (8GB) - Best for tool calling and structured JSON outputs
        • **hermes-3-llama-8b** (9GB) - Multi-agent systems and autonomous workflows
        • **llama-3.1-8b** (9GB) - Strong instruction following for compliance queries
        • **qwen-2.5-14b** (16GB) - Balanced reasoning for document analysis

        **Model Information:**
        ```bash
        llamacpp-manager models info qwen-coder-7b
        ```

        ### 4. Model Groups

        Models can be organized into groups with mutual exclusion to prevent resource exhaustion.

        **Exclusive Groups:**
        When models belong to an exclusive group, starting one model automatically stops other models in the same group.

        **Example Configuration:**
        ```yaml
        model_groups:
          agentic-models:
            exclusive: true
            auto_stop_minutes: 60
            members:
              - qwen-coder-7b
              - hermes-3-llama-8b
              - llama-3.1-8b
        ```

        **Using Groups:**
        ```bash
        # Launch model (auto-stops siblings in exclusive group)
        llamacpp-manager launch qwen-coder-7b
        ```

        ### 5. Infrastructure Management

        The GUI also manages supporting infrastructure components like cloudflared tunnel and LLM controller.

        **Infrastructure Controls:**
        • **Start** - Start an infrastructure component
        • **Stop** - Stop an infrastructure component
        • **Restart** - Restart an infrastructure component
        • **Logs** - View infrastructure logs

        **Status Indicators:**
        • 🟢 Healthy - Component running and responding
        • 🟠 Unhealthy - Component running but not responding
        • 🔴 Stopped - Component not running
        • ⚫ Disabled - Component disabled in configuration

        ### 6. Monitoring & Auto-Restart

        The Monitor button enables automatic crash detection and restart for models.

        **Enable Monitoring:**
        1. Click "Monitor" button next to a model
        2. Button turns orange when monitoring is enabled
        3. Model will auto-restart if it crashes

        **Monitor Daemon:**
        For persistent monitoring across system reboots, install the monitoring daemon:
        ```bash
        llamacpp-manager monitor launchd install
        ```

        ### 7. CLI Commands

        **Core Commands:**
        ```bash
        # Initialize configuration
        llamacpp-manager init

        # Add a model
        llamacpp-manager config add MODEL_NAME /path/to/model.gguf --port PORT

        # Start/stop models
        llamacpp-manager start MODEL_NAME
        llamacpp-manager stop MODEL_NAME
        llamacpp-manager stop all  # Stop all models

        # Check status
        llamacpp-manager status
        llamacpp-manager status --json  # Machine-readable format

        # Query models
        llamacpp-manager query complete MODEL_NAME "Your prompt here"
        llamacpp-manager query chat MODEL_NAME --message "user:Hello!"
        ```

        **Model Downloader Commands:**
        ```bash
        # List available models
        llamacpp-manager models list --available

        # Download model
        llamacpp-manager models download qwen-coder-7b

        # Get model info
        llamacpp-manager models info qwen-coder-7b
        ```

        **Infrastructure Commands:**
        ```bash
        # View infrastructure status
        llamacpp-manager infra status

        # Control infrastructure
        llamacpp-manager infra start cloudflared
        llamacpp-manager infra stop llm_controller
        llamacpp-manager infra restart llm_controller

        # View logs
        llamacpp-manager infra logs llm_controller
        ```

        ### 8. Configuration Files

        **Config Location:**
        `~/Library/Application Support/llamaCPPManager/config.yaml`

        **Log Location:**
        `~/Library/Logs/llamaCPPManager/`

        **Edit Configuration:**
        1. Click "Open Config" in GUI
        2. Edit `config.yaml` in your preferred editor
        3. Click "Refresh" in GUI to reload

        ### 9. Troubleshooting

        **Model Won't Start:**
        1. Check logs by clicking "Logs" button
        2. Verify model file exists at configured path
        3. Check port is not already in use
        4. Try running: `llamacpp-manager status` in terminal

        **GUI Not Updating:**
        1. Click "Refresh" button
        2. Check that llamacpp-manager CLI is in PATH
        3. Run `which llamacpp-manager` in terminal

        **Port Already in Use:**
        ```bash
        # Find what's using the port
        lsof -i :8081

        # Change model port in config
        llamacpp-manager config update MODEL_NAME --port 8082
        ```

        **Model Not Responding:**
        1. Check model is running (green indicator)
        2. Click "Restart" to restart the model
        3. Enable "Monitor" for auto-restart on crashes
        4. Check logs for errors

        ### 10. Advanced Features

        **launchd Integration:**
        Make models start automatically on boot:
        ```bash
        # Install launchd agent
        llamacpp-manager launchd install MODEL_NAME

        # Check status
        llamacpp-manager launchd status MODEL_NAME

        # Uninstall
        llamacpp-manager launchd uninstall MODEL_NAME
        ```

        **Monitoring Daemon:**
        Install persistent monitoring across reboots:
        ```bash
        llamacpp-manager monitor launchd install
        llamacpp-manager monitor launchd status
        ```

        **Logging Control:**
        The GUI includes logging controls to enable/disable model logging and timestamps.

        **MCP Server Integration:**
        llamaCPPManager includes Model Context Protocol (MCP) server for AI assistant integration:
        ```bash
        # Available in Claude Desktop, Continue.dev, etc.
        # See user manual for full MCP setup instructions
        ```

        ### 11. Keyboard Shortcuts

        **In Chat Window:**
        • **Return** - Send message
        • **Cmd+W** - Close window

        ### 12. Tips & Best Practices

        **Resource Management:**
        • Use model groups for large models to prevent memory exhaustion
        • Enable auto_stop_minutes for models you use occasionally
        • Monitor system resources with Activity Monitor

        **Performance:**
        • Apple Silicon (M1/M2/M3/M4): Use -ngl 9999 to offload to GPU
        • Adjust context size (-c flag) based on your needs
        • Use smaller quantized models (Q4, Q5) for faster inference

        **Organization:**
        • Keep models in ~/llms/ directory
        • Use descriptive model names
        • Group related models together

        **Backups:**
        • Configuration: `~/Library/Application Support/llamaCPPManager/config.yaml`
        • Back up before making major changes

        ### 13. Getting Help

        **Documentation:**
        • Run `llamacpp-manager --help` for CLI help
        • Check GitHub issues for known problems
        • Read comprehensive user manual (this document)

        **CLI Help:**
        ```bash
        llamacpp-manager --help
        llamacpp-manager COMMAND --help  # Help for specific command
        ```

        **Support:**
        • GitHub: https://github.com/your-username/llamacpp-manager
        • Issues: Report bugs and request features

        ### 14. What's New

        **Latest Features:**
        • ✅ Model groups with exclusive access
        • ✅ Model downloader with Hugging Face integration
        • ✅ Agentic models (qwen-coder-7b, hermes-3-llama-8b, llama-3.1-8b)
        • ✅ Enhanced infrastructure management
        • ✅ Uptime tracking for models and infrastructure
        • ✅ Logging control UI
        • ✅ Stop All Models button

        ---

        **Version:** 1.0.0
        **Updated:** 2025-10-10

        For complete documentation, run:
        ```bash
        llamacpp-manager --help
        ```
        """
    }

    func openPreferences() {
        if let window = preferencesWindow {
            window.level = .floating
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        let contentView = PreferencesView()
        let hostingController = NSHostingController(rootView: contentView)

        let window = NSWindow(contentViewController: hostingController)
        window.title = "Preferences"
        window.styleMask = [.titled, .closable]
        window.center()
        window.level = .floating
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        // Set up window delegate to clean up when closed
        let delegate = PreferencesWindowDelegate { [weak self] in
            self?.preferencesWindow = nil
        }
        window.delegate = delegate

        preferencesWindow = window
    }

    func openAbout() {
        let aboutText = """
        llamaCPP Manager v\(APP_VERSION)

        A toolkit for managing local llama.cpp server instances on macOS.

        Features:
        • Multiple model management
        • Menu bar integration
        • Built-in chat interface
        • CLI automation
        • Container & Kubernetes support

        GitHub: https://github.com/arionrepo/llamaCPPManager
        Release Notes: https://github.com/arionrepo/llamaCPPManager/blob/main/CHANGELOG.md
        """

        showAlert(title: "About llamaCPP Manager", message: aboutText)
    }

    private func showAlert(title: String, message: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = .informational
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}
