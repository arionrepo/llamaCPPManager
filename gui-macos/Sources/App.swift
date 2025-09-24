import SwiftUI
import AppKit

@main
struct LlamaCPPManagerApp: App {
    @StateObject private var vm = StatusViewModel()

    var body: some Scene {
        MenuBarExtra("llamaCPP", systemImage: "brain.head.profile") {
            VStack(alignment: .leading, spacing: 6) {
                if vm.rows.isEmpty {
                    Text("No models configured")
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
                Button("Ensure Running") { vm.ensureRunning() }
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
}

final class StatusViewModel: ObservableObject {
    @Published var rows: [StatusRow] = []
    private let service = CLIService()
    private var timer: Timer?
    private var chatWindows: [String: NSWindow] = [:]
    private var windowDelegates: [String: ChatWindowDelegate] = [:]
    private var monitoredModels: Set<String> = []

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
                self.rows = try await service.fetchStatus()
            } catch {
                // Keep prior rows; optionally surface an error row
            }
        }
    }

    func start(name: String) { Task { _ = try? await service.run(["start", name]) ; refresh() } }
    func stop(name: String) { Task { _ = try? await service.run(["stop", name]) ; refresh() } }
    func restart(name: String) { Task { _ = try? await service.run(["restart", name]) ; refresh() } }
    func ensureRunning() { Task { _ = try? await service.run(["ensure-running"]) ; refresh() } }

    func tailLogs(name: String) {
        // Open in Console or tail -F in Terminal
        guard let row = rows.first(where: { $0.name == name }), let path = row.log_path else { return }
        let url = URL(fileURLWithPath: path)
        NSWorkspace.shared.open(url)
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
        if monitoredModels.contains(name) {
            // Untrack model
            Task {
                _ = try? await service.run(["monitor", "untrack", name])
                await MainActor.run {
                    monitoredModels.remove(name)
                }
            }
        } else {
            // Track model
            Task {
                _ = try? await service.run(["monitor", "track", name])
                await MainActor.run {
                    monitoredModels.insert(name)
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
        // Open help documentation
        let helpText = """
        llamaCPP Manager - Quick Help

        🧠 GUI Controls:
        • Red Circle = Model stopped
        • Green Circle = Model running
        • Start/Stop = Control individual models
        • Chat = Open chat window (when model running)
        • Tail Logs = View model logs
        • Refresh = Update status

        📋 Model Management:
        • Open Config = Add models manually
        • Open CLI = Access full command line
        • Ensure Running = Start configured models

        💡 Quick Start:
        1. Add models via 'Open Config' or 'Open CLI'
        2. Click 'Start' to run a model
        3. Click 'Chat' to open chat window
        4. Visit http://127.0.0.1:[port] in browser

        🔧 CLI Commands:
        llamacpp-manager config add [name] [path] --port [port]
        llamacpp-manager start [name]
        llamacpp-manager status
        llamacpp-manager --help

        📖 Full Documentation:
        Run 'Open CLI' and type: llamacpp-manager --help
        """

        showAlert(title: "llamaCPP Manager Help", message: helpText)
    }

    func openAbout() {
        let aboutText = """
        llamaCPP Manager v1.0.0

        A toolkit for managing local llama.cpp server instances on macOS.

        Features:
        • Multiple model management
        • Menu bar integration
        • Built-in chat interface
        • CLI automation
        • Container & Kubernetes support

        GitHub: https://github.com/your-username/llamacpp-manager
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
    private let executableNames = ["llamacpp-manager", "/usr/local/bin/llamacpp-manager", "/opt/homebrew/bin/llamacpp-manager"]

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

    func fetchStatus() async throws -> [StatusRow] {
        let data = try await runAndCapture(["status", "--json"]).data(using: .utf8) ?? Data()
        let rows = try JSONDecoder().decode([StatusRow].self, from: data)
        return rows
    }

    func run(_ args: [String]) async throws -> Int32 {
        let url = try requireExec()
        let process = Process()
        process.executableURL = url
        process.arguments = args
        try process.run()
        process.waitUntilExit()
        return process.terminationStatus
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
