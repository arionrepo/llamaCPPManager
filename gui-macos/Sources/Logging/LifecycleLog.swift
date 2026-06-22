//
//  LifecycleLog.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Logging/LifecycleLog.swift
//  Description: Structured JSON event logger writing to ~/Library/Logs/llamaCPPManager/lifecycle.jsonl alongside the Python CLI's events so GUI actions can be correlated with backend behavior.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

// MARK: - GUI Lifecycle Logger
// Writes structured JSON events to ~/Library/Logs/llamaCPPManager/lifecycle.jsonl
// alongside the Python CLI's events so we can correlate GUI actions with backend behavior.
enum LifecycleLog {
    private static let logPath: URL = {
        let home = FileManager.default.homeDirectoryForCurrentUser
        return home
            .appendingPathComponent("Library")
            .appendingPathComponent("Logs")
            .appendingPathComponent("llamaCPPManager")
            .appendingPathComponent("lifecycle.jsonl")
    }()

    private static let queue = DispatchQueue(label: "com.llamacpp.manager.lifecycle", qos: .utility)

    static func log(_ event: String, model: String? = nil, _ fields: [String: Any] = [:],
                    file: String = #file, function: String = #function) {
        queue.async {
            var entry: [String: Any] = [
                "ts": Self.timestamp(),
                "pid_self": ProcessInfo.processInfo.processIdentifier,
                "event": event,
                "source": "gui",
                "caller": "gui." + ((file as NSString).lastPathComponent as String).replacingOccurrences(of: ".swift", with: "") + "." + function,
            ]
            if let model = model { entry["model"] = model }
            for (k, v) in fields { entry[k] = v }
            AppLogger.log("[lifecycle] \(event) model=\(model ?? "-") \(fields)", level: .debug)
            do {
                try FileManager.default.createDirectory(at: logPath.deletingLastPathComponent(),
                                                         withIntermediateDirectories: true)
                let data = try JSONSerialization.data(withJSONObject: entry, options: [])
                guard let line = String(data: data, encoding: .utf8) else { return }
                let payload = (line + "\n").data(using: .utf8)!
                if FileManager.default.fileExists(atPath: logPath.path) {
                    if let handle = try? FileHandle(forWritingTo: logPath) {
                        try? handle.seekToEnd()
                        try? handle.write(contentsOf: payload)
                        try? handle.close()
                    }
                } else {
                    try? payload.write(to: logPath)
                }
            } catch {
                AppLogger.log("[lifecycle] write failed: \(error)", level: .error)
            }
        }
    }

    private static func timestamp() -> String {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withColonSeparatorInTime]
        return f.string(from: Date())
    }
}
