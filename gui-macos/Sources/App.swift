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
                        HStack {
                            Circle()
                                .fill(row.up ? Color.green : Color.red)
                                .frame(width: 8, height: 8)
                            Text(row.name)
                            Spacer()
                            Text("\(row.host):\(row.port)")
                            if let ms = row.latency_ms { Text("\(ms) ms") }
                        }
                        .padding(.horizontal, 8)
                        HStack {
                            Button("Start") { vm.start(name: row.name) }
                            Button("Stop") { vm.stop(name: row.name) }
                            Button("Restart") { vm.restart(name: row.name) }
                            Button("Tail Logs") { vm.tailLogs(name: row.name) }
                        }
                        .buttonStyle(.borderless)
                        .padding(.leading, 16)
                        Divider()
                    }
                }
                Button("Ensure Running") { vm.ensureRunning() }
                Divider()
                Button("Refresh") { vm.refresh() }
                Button("Open Config") { vm.openConfig() }
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
}

final class StatusViewModel: ObservableObject {
    @Published var rows: [StatusRow] = []
    private let service = CLIService()
    private var timer: Timer?

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

    func openConfig() {
        // Open config dir in Finder
        if let dir = service.configDirURL() { NSWorkspace.shared.activateFileViewerSelecting([dir]) }
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
}
