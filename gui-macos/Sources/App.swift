import SwiftUI
import AppKit

// Version constant to ensure dynamic version
let APP_VERSION: String = {
    return "1.1.12-1-gefc054a"
}()

import os.log

// Centralized logging utility
enum AppLogger {
    private static let logger = Logger(subsystem: "com.llamacpp.manager", category: "GUI")

    enum LogLevel {
        case debug
        case info
        case warning
        case error
    }

    static func log(_ message: String, level: LogLevel = .info, file: String = #file, function: String = #function, line: Int = #line) {
        let filename = (file as NSString).lastPathComponent
        let formattedMessage = "[\(filename):\(line)] \(function) - \(message)"

        switch level {
        case .debug:
            logger.debug("\(formattedMessage)")
        case .info:
            logger.info("\(formattedMessage)")
        case .warning:
            logger.warning("\(formattedMessage)")
        case .error:
            logger.error("\(formattedMessage)")
        }

        // Additional console logging for development
        print("[LlamaCPP Manager] \(formattedMessage)")
    }
}

// Any custom async operation logging can be added here if needed

@main
struct LlamaCPPManagerApp: App {
    @StateObject private var vm = StatusViewModel()

    var body: some Scene {
        MenuBarExtra("llamaCPP", systemImage: "brain.head.profile") {
            VStack(alignment: .leading, spacing: 6) {
                // MARK: - Infrastructure Section
                if !vm.infrastructureRows.isEmpty {
                    Text("Infrastructure")
                        .font(.headline)
                        .padding(.horizontal, 8)

                    ForEach(vm.infrastructureRows, id: \.name) { infra in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Circle()
                                    .fill(vm.healthColorInfra(for: infra))
                                    .frame(width: 10, height: 10)

                                VStack(alignment: .leading) {
                                    Text(infra.name)
                                        .font(.headline)
                                    Text(vm.healthStatusInfra(for: infra))
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }

                                Spacer()

                                VStack(alignment: .trailing) {
                                    Text(infra.type)
                                        .font(.caption)
                                    if infra.latency_ms > 0 {
                                        Text("\(infra.latency_ms) ms")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                    if let uptime = infra.uptime, !uptime.isEmpty {
                                        Text("up \(uptime)")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
                            .padding(.horizontal, 8)

                            HStack {
                                Button("Start") { vm.startInfra(name: infra.name) }
                                    .disabled(infra.running)
                                Button("Stop") { vm.stopInfra(name: infra.name) }
                                    .disabled(!infra.running)
                                Button("Restart") { vm.restartInfra(name: infra.name) }
                                Button("Logs") { vm.infraLogs(name: infra.name) }
                            }
                            .buttonStyle(.borderless)
                            .font(.caption)
                            .padding(.leading, 18)
                        }
                        Divider()
                    }
                }

                // MARK: - Models Section
                Text("Models")
                    .font(.headline)
                    .padding(.horizontal, 8)

                if vm.rows.isEmpty {
                    Text("No models configured")
                        .padding(.horizontal, 8)
                } else {
                    ForEach(vm.rows, id: \.name) { row in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                // Enhanced health indicator
                                Circle()
                                    .fill(vm.healthColor(for: row))
                                    .frame(width: 10, height: 10)

                                VStack(alignment: .leading) {
                                    Text(row.name)
                                        .font(.headline)
                                    Text(vm.healthStatus(for: row))
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }

                                Spacer()

                                VStack(alignment: .trailing) {
                                    Text("\(row.host):\(row.port)")
                                        .font(.caption)
                                    if let ms = row.latency_ms, ms > 0 {
                                        Text("\(ms) ms")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                    if let uptime = row.uptime, !uptime.isEmpty {
                                        Text("up \(uptime)")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
                            .padding(.horizontal, 8)

                            // Control buttons
                            HStack {
                                Button("Start") { vm.start(name: row.name) }
                                    .disabled(row.up)
                                Button("Stop") { vm.stop(name: row.name) }
                                    .disabled(!row.up)
                                Button("Restart") { vm.restart(name: row.name) }

                                if row.up {
                                    Button("Chat") { vm.openChat(name: row.name) }
                                }

                                Button("Monitor") { vm.toggleMonitoring(name: row.name) }
                                    .foregroundColor(vm.isMonitored(name: row.name) ? .orange : .blue)

                                Button("Logs") { vm.tailLogs(name: row.name) }
                            }
                            .buttonStyle(.borderless)
                            .font(.caption)
                            .padding(.leading, 18)
                        }
                        Divider()
                    }
                }
                HStack {
                    Button(action: { vm.startAllModels() }) {
                        Text("Start All Models")
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                    }
                    .buttonStyle(.bordered)
                    .help("Start all models")

                    Button(action: { vm.stopAllModels() }) {
                        Text("Stop All Models")
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                    }
                    .buttonStyle(.bordered)
                    .foregroundColor(.red)
                    .help("Stop all running models (infrastructure components continue running)")
                }
                Divider()

                // MARK: - Logging Section
                if let logging = vm.loggingConfig {
                    HStack {
                        Text("Logging")
                            .font(.headline)
                        Spacer()
                        Text(logging.enabled ? "ON" : "OFF")
                            .font(.caption)
                            .foregroundColor(logging.enabled ? .green : .red)
                    }
                    .padding(.horizontal, 8)

                    HStack {
                        Button(logging.enabled ? "Disable Logs" : "Enable Logs") {
                            vm.toggleLogging()
                        }
                        Button(logging.timestamps ? "Timestamps: ON" : "Timestamps: OFF") {
                            vm.toggleTimestamps()
                        }
                        .foregroundColor(logging.timestamps ? .green : .secondary)
                    }
                    .buttonStyle(.borderless)
                    .font(.caption)
                    .padding(.horizontal, 8)

                    Divider()
                }

                Button("Download Models") { vm.openModelDownloader() }
                Divider()
                Button("Refresh") { vm.refresh() }
                Button("Open Config") { vm.openConfig() }
                Button("Open CLI") { vm.openCLI() }
                Divider()
                Button("Help") { vm.openHelp() }
                Button("About") { vm.openAbout() }
                Divider()
                Button("Quit") { NSApplication.shared.terminate(nil) }
            }
            .task { vm.startPolling() }
            .padding(6)
        }
        .menuBarExtraStyle(.window)
    }
}

struct StatusRow: Codable {
    let name: String
    let pid: Int?
    let host: String
    let port: Int
    let up: Bool
    let latency_ms: Int?
    let http_status: Int?
    let version: String?
    let mode: String?
    let log_path: String?
    let health_state: String?
    let uptime: String?

    enum CodingKeys: String, CodingKey, CaseIterable {
        case name, pid, host, port, up, latency_ms, http_status, version, mode, log_path, health_state, uptime
    }
}

struct InfrastructureRow: Codable {
    let name: String
    let type: String
    let enabled: Bool
    let running: Bool
    let healthy: Bool
    let status: String
    let health_status: String
    let latency_ms: Int
    let details: [String: AnyCodable]?
    let uptime: String?

    enum CodingKeys: String, CodingKey, CaseIterable {
        case name, type, enabled, running, healthy, status, health_status, latency_ms, details, uptime
    }
}

// Helper for decoding arbitrary JSON
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let int = try? container.decode(Int.self) {
            value = int
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let int = value as? Int {
            try container.encode(int)
        } else if let string = value as? String {
            try container.encode(string)
        } else if let bool = value as? Bool {
            try container.encode(bool)
        } else {
            try container.encodeNil()
        }
    }
}

struct LoggingConfig: Codable {
    let enabled: Bool
    let max_bytes: Int
    let backups: Int
    let timestamps: Bool
}

struct StatusResponse: Codable {
    let models: [StatusRow]
    let infrastructure: [InfrastructureRow]
    let logging: LoggingConfig
}

final class StatusViewModel: ObservableObject {
    @Published var rows: [StatusRow] = []
    @Published var infrastructureRows: [InfrastructureRow] = []
    @Published var loggingConfig: LoggingConfig?
    private let service = CLIService()
    private var timer: Timer?
    private var chatWindows: [String: NSWindow] = [:]
    private var windowDelegates: [String: ChatWindowDelegate] = [:]
    private var monitoredModels: Set<String> = []
    private var modelDownloaderWindow: NSWindow?

    func startPolling(interval: TimeInterval = 2.0) {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            self?.refresh()
        }
        refresh()
    }

    func refresh() {
        Task { @MainActor in
            do {
                let response = try await service.fetchStatus()
                self.rows = response.models
                self.infrastructureRows = response.infrastructure
                self.loggingConfig = response.logging
            } catch {
                // Keep prior rows; optionally surface an error row
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

    func stop(name: String) {
        Task { [weak self] in
            guard let self = self else { return }
            let result = await service.run(["stop", name])
            if result == 0 {
                AppLogger.log("Successfully stopped model: \(name)", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to stop model: \(name)", level: .error)
            }
        }
    }

    func restart(name: String) {
        Task { [weak self] in
            guard let self = self else { return }
            let result = await service.run(["restart", name])
            if result == 0 {
                AppLogger.log("Successfully restarted model: \(name)", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to restart model: \(name)", level: .error)
            }
        }
    }

    func startAllModels() {
        Task { [weak self] in
            guard let self = self else { return }
            let result = await service.run(["start", "all"])
            if result == 0 {
                AppLogger.log("Successfully started all models", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to start all models", level: .error)
            }
        }
    }

    func stopAllModels() {
        Task { [weak self] in
            guard let self = self else { return }
            let result = await service.run(["stop", "all"])
            if result == 0 {
                AppLogger.log("Successfully stopped all models", level: .info)
                refresh()
            } else {
                AppLogger.log("Failed to stop all models", level: .error)
            }
        }
    }

    func tailLogs(name: String) {
        // Open log file with system default app (Console.app on macOS)
        guard let row = rows.first(where: { $0.name == name }), let path = row.log_path else { return }
        let url = URL(fileURLWithPath: path)
        NSWorkspace.shared.open(url)
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
            existingWindow.makeKeyAndOrderFront(nil)
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
        window.makeKeyAndOrderFront(nil)

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

        // Create model downloader view
        let downloaderViewModel = DownloadViewModel(cliService: service)
        let downloaderView = ModelDownloaderView(viewModel: downloaderViewModel)
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
        let delegate = ModelDownloaderWindowDelegate { [weak self] in
            self?.modelDownloaderWindow = nil
        }
        window.delegate = delegate
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

final class CLIService {
    // Configure preferred executable lookup or rely on PATH
    private let executableNames = [
        "\(NSHomeDirectory())/.local/bin/llamacpp-manager",
        "/usr/local/bin/llamacpp-manager",
        "/opt/homebrew/bin/llamacpp-manager",
        "llamacpp-manager"
    ]

    func execURL() -> URL? {
        for name in executableNames {
            let url = URL(fileURLWithPath: name)
            if FileManager.default.isExecutableFile(atPath: url.path) { return url }
        }
        // Fallback to PATH lookup
        if let path = ProcessInfo.processInfo.environment["PATH"] {
            for dir in path.split(separator: ":") {
                let url = URL(fileURLWithPath: String(dir)).appendingPathComponent("llamacpp-manager")
                if FileManager.default.isExecutableFile(atPath: url.path) { return url }
            }
        }
        return nil
    }

    func fetchStatus() async throws -> StatusResponse {
        AppLogger.log("Fetching status from CLI", level: .debug)
        do {
            let jsonString = try await runAndCapture(["status", "--json"])
            guard let data = jsonString.data(using: .utf8), !data.isEmpty else {
                AppLogger.log("Empty status response", level: .warning)
                throw NSError(domain: "CLIService", code: 1, userInfo: [NSLocalizedDescriptionKey: "Empty status response"])
            }

            let response = try JSONDecoder().decode(StatusResponse.self, from: data)
            AppLogger.log("Status fetched successfully: \(response.models.count) models", level: .debug)
            return response
        } catch {
            AppLogger.log("Failed to fetch status: \(error.localizedDescription)", level: .error)
            throw error
        }
    }

    func fetchInfrastructureList() async throws -> String {
        return try await runAndCapture(["infra", "list"])
    }

    func startInfrastructure(_ name: String) async throws {
        let result = await run(["infra", "start", name])
        if result != 0 {
            throw NSError(domain: "InfrastructureService", code: Int(result), userInfo: [
                NSLocalizedDescriptionKey: "Failed to start infrastructure: \(name)"
            ])
        }
    }

    func stopInfrastructure(_ name: String) async throws {
        let result = await run(["infra", "stop", name])
        if result != 0 {
            throw NSError(domain: "InfrastructureService", code: Int(result), userInfo: [
                NSLocalizedDescriptionKey: "Failed to stop infrastructure: \(name)"
            ])
        }
    }

    func restartInfrastructure(_ name: String) async throws {
        let result = await run(["infra", "restart", name])
        if result != 0 {
            throw NSError(domain: "InfrastructureService", code: Int(result), userInfo: [
                NSLocalizedDescriptionKey: "Failed to restart infrastructure: \(name)"
            ])
        }
    }

    func infrastructureLogs(_ name: String) async throws -> String {
        return try await runAndCapture(["infra", "logs", name])
    }

    func run(_ args: [String]) async -> Int32 {
        // Log the command being executed
        AppLogger.log("Executing CLI command: \(args.joined(separator: " "))", level: .debug)

        do {
            let url = try requireExec()
            let process = Process()
            process.executableURL = url
            process.arguments = args

            // Capture output and error
            let outputPipe = Pipe()
            let errorPipe = Pipe()
            process.standardOutput = outputPipe
            process.standardError = errorPipe

            // Start the process
            try process.run()
            process.waitUntilExit()

            // Read output and error data
            let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
            let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()

            // Log output if any
            if let outputString = String(data: outputData, encoding: .utf8), !outputString.isEmpty {
                AppLogger.log("CLI Command Output: \(outputString)", level: .debug)
            }

            // Log and handle errors
            if let errorString = String(data: errorData, encoding: .utf8), !errorString.isEmpty {
                AppLogger.log("CLI Command Error: \(args.joined(separator: " ")) - \(errorString)", level: .warning)
            }

            // Log termination status
            let status = process.terminationStatus
            if status != 0 {
                AppLogger.log("CLI Command Failed: \(args.joined(separator: " ")) - Exit Status: \(status)", level: .error)
            }

            return status
        } catch {
            // Log any execution errors
            AppLogger.log("CLI Execution Error: \(args.joined(separator: " ")) - \(error.localizedDescription)", level: .error)
            return -1
        }
    }

    func runAndCapture(_ args: [String]) async throws -> String {
        let url = try requireExec()
        let process = Process()
        process.executableURL = url
        process.arguments = args
        let pipe = Pipe()
        process.standardOutput = pipe
        try process.run()
        process.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        return String(data: data, encoding: .utf8) ?? "[]"
    }

    private func requireExec() throws -> URL {
        if let url = execURL() { return url }
        throw NSError(domain: "CLIService", code: 1, userInfo: [NSLocalizedDescriptionKey: "llamacpp-manager not found in PATH or common locations"])
    }

    func configDirURL() -> URL? {
        if let dir = ProcessInfo.processInfo.environment["LLAMACPP_MANAGER_CONFIG_DIR"] {
            return URL(fileURLWithPath: dir)
        }
        let home = FileManager.default.homeDirectoryForCurrentUser
        return home.appendingPathComponent("Library/Application Support/llamaCPPManager")
    }

    func queryChat(modelName: String, messages: [ChatMessage]) async throws -> String {
        var args = ["query", "chat", modelName]
        for message in messages {
            args.append("--message")
            args.append("\(message.role):\(message.content)")
        }
        return try await runAndCapture(args)
    }

    func queryCompletion(modelName: String, prompt: String, maxTokens: Int = 512, temperature: Double = 0.7) async throws -> String {
        let args = [
            "query", "complete", modelName, prompt,
            "--max-tokens", String(maxTokens),
            "--temperature", String(temperature)
        ]
        return try await runAndCapture(args)
    }
}

// MARK: - Chat Functionality

struct ChatMessage: Identifiable, Equatable {
    let id = UUID()
    let role: String // "system", "user", "assistant"
    let content: String
    let timestamp: Date = Date()
}

final class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var currentInput: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String? = nil

    let modelName: String
    private let cliService: CLIService

    init(modelName: String, cliService: CLIService) {
        self.modelName = modelName
        self.cliService = cliService

        // Add system message
        messages.append(ChatMessage(
            role: "system",
            content: "You are a helpful AI assistant running on llama.cpp via llamaCPPManager."
        ))
    }

    func sendMessage() {
        guard !currentInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        guard !isLoading else { return }

        let userMessage = ChatMessage(role: "user", content: currentInput)
        messages.append(userMessage)

        let inputText = currentInput
        currentInput = ""
        isLoading = true
        errorMessage = nil

        Task { @MainActor in
            do {
                let response = try await cliService.queryChat(modelName: modelName, messages: messages)
                let assistantMessage = ChatMessage(role: "assistant", content: response.trimmingCharacters(in: .whitespacesAndNewlines))
                messages.append(assistantMessage)
            } catch {
                errorMessage = "Failed to send message: \(error.localizedDescription)"
                // Remove the user message if the API call failed
                if let lastIndex = messages.lastIndex(where: { $0.content == inputText && $0.role == "user" }) {
                    messages.remove(at: lastIndex)
                }
            }
            isLoading = false
        }
    }

    func clearChat() {
        messages.removeAll()
        messages.append(ChatMessage(
            role: "system",
            content: "You are a helpful AI assistant running on llama.cpp via llamaCPPManager."
        ))
        errorMessage = nil
    }
}

struct ChatView: View {
    @StateObject var viewModel: ChatViewModel

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Chat with \(viewModel.modelName)")
                    .font(.headline)
                Spacer()
                Button("Clear") {
                    viewModel.clearChat()
                }
                .buttonStyle(.borderless)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))

            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(viewModel.messages.filter { $0.role != "system" }) { message in
                            ChatMessageView(message: message)
                                .id(message.id)
                        }

                        if viewModel.isLoading {
                            HStack {
                                ProgressView()
                                    .scaleEffect(0.8)
                                Text("Thinking...")
                                    .foregroundColor(.secondary)
                                Spacer()
                            }
                            .padding(.horizontal)
                        }
                    }
                    .padding()
                }
                .onChange(of: viewModel.messages.count) { _ in
                    if let lastMessage = viewModel.messages.last {
                        withAnimation(.easeOut(duration: 0.3)) {
                            proxy.scrollTo(lastMessage.id, anchor: .bottom)
                        }
                    }
                }
            }

            // Error message
            if let error = viewModel.errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle")
                        .foregroundColor(.orange)
                    Text(error)
                        .foregroundColor(.orange)
                        .font(.caption)
                    Spacer()
                    Button("Dismiss") {
                        viewModel.errorMessage = nil
                    }
                    .buttonStyle(.borderless)
                    .font(.caption)
                }
                .padding()
                .background(Color.orange.opacity(0.1))
            }

            // Input area
            HStack {
                TextField("Type your message...", text: $viewModel.currentInput, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(1...6)
                    .onSubmit {
                        viewModel.sendMessage()
                    }

                Button("Send") {
                    viewModel.sendMessage()
                }
                .keyboardShortcut(.return, modifiers: [])
                .disabled(viewModel.currentInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
        }
        .frame(minWidth: 400, minHeight: 300)
    }
}

struct ChatMessageView: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            Circle()
                .fill(message.role == "user" ? Color.blue : Color.green)
                .frame(width: 24, height: 24)
                .overlay(
                    Text(message.role == "user" ? "U" : "AI")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                )

            // Message content
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(message.role.capitalized)
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)

                    Spacer()

                    Text(message.timestamp, style: .time)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }

                Text(message.content)
                    .textSelection(.enabled)
                    .padding(8)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(message.role == "user"
                                ? Color.blue.opacity(0.1)
                                : Color.gray.opacity(0.1))
                    )
            }

            Spacer()
        }
    }
}

class ChatWindowDelegate: NSObject, NSWindowDelegate {
    private let onClose: () -> Void

    init(onClose: @escaping () -> Void) {
        self.onClose = onClose
        super.init()
    }

    func windowWillClose(_ notification: Notification) {
        onClose()
    }
}

class ModelDownloaderWindowDelegate: NSObject, NSWindowDelegate {
    private let onClose: () -> Void

    init(onClose: @escaping () -> Void) {
        self.onClose = onClose
        super.init()
    }

    func windowWillClose(_ notification: Notification) {
        onClose()
    }
}
