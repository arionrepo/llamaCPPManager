//
//  CLIService.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Services/CLIService.swift
//  Description: Subprocess orchestrator for the llamacpp-manager Python CLI. Runs every command on a background queue so the calling Task is never blocked. Surfaces both exit-code-only (`run`) and stdout-capturing (`runAndCapture`) variants.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

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
            if FileManager.default.isExecutableFile(atPath: url.path) {
                AppLogger.log("Using CLI: \(name)", level: .info)
                return url
            }
        }
        // Fallback to PATH lookup
        if let path = ProcessInfo.processInfo.environment["PATH"] {
            for dir in path.split(separator: ":") {
                let url = URL(fileURLWithPath: String(dir)).appendingPathComponent("llamacpp-manager")
                if FileManager.default.isExecutableFile(atPath: url.path) {
                    AppLogger.log("Using CLI from PATH: \(url.path)", level: .info)
                    return url
                }
            }
        }
        AppLogger.log("ERROR: No llamacpp-manager CLI found!", level: .error)
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

    func fetchDockerStatus() async throws -> StatusResponse {
        AppLogger.log("Fetching Docker status from CLI", level: .debug)
        do {
            let jsonString = try await runAndCapture(["docker", "status", "--json"])

            // Log the actual JSON response for debugging
            AppLogger.log("Docker status JSON response: \(jsonString.prefix(200))...", level: .debug)

            guard let data = jsonString.data(using: .utf8), !data.isEmpty else {
                AppLogger.log("Empty Docker status response", level: .warning)
                // Return empty response instead of throwing
                return StatusResponse(models: [], infrastructure: [], logging: LoggingConfig(enabled: false, max_bytes: 0, backups: 0, timestamps: false))
            }

            let response = try JSONDecoder().decode(StatusResponse.self, from: data)
            AppLogger.log("Docker status fetched successfully: \(response.models.count) containers", level: .debug)

            // Log first model details
            if let first = response.models.first {
                AppLogger.log("First Docker model: \(first.name), up=\(first.up), health=\(first.health_state ?? "nil")", level: .debug)
            }

            return response
        } catch {
            AppLogger.log("Failed to fetch Docker status: \(error.localizedDescription)", level: .error)
            // Return empty response if Docker not available
            return StatusResponse(models: [], infrastructure: [], logging: LoggingConfig(enabled: false, max_bytes: 0, backups: 0, timestamps: false))
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

    // Non-blocking CLI runner.
    // Previously used Process.waitUntilExit() on the caller's thread, which froze the
    // UI when called from MainActor Tasks (every model start/stop/chat goes through
    // here). Now runs the subprocess on a global background queue and resumes via
    // terminationHandler so the calling Task is never blocked.
    func run(_ args: [String]) async -> Int32 {
        AppLogger.log("Executing CLI command: \(args.joined(separator: " "))", level: .debug)
        let url: URL
        do {
            url = try requireExec()
        } catch {
            AppLogger.log("CLI Execution Error: \(args.joined(separator: " ")) - \(error.localizedDescription)", level: .error)
            return -1
        }
        return await withCheckedContinuation { (continuation: CheckedContinuation<Int32, Never>) in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = url
                process.arguments = args
                let outputPipe = Pipe()
                let errorPipe = Pipe()
                process.standardOutput = outputPipe
                process.standardError = errorPipe

                var didResume = false
                let resumeOnce: (Int32) -> Void = { status in
                    guard !didResume else { return }
                    didResume = true
                    continuation.resume(returning: status)
                }

                process.terminationHandler = { proc in
                    let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
                    let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                    if let outputString = String(data: outputData, encoding: .utf8), !outputString.isEmpty {
                        AppLogger.log("CLI Command Output: \(outputString)", level: .debug)
                    }
                    if let errorString = String(data: errorData, encoding: .utf8), !errorString.isEmpty {
                        AppLogger.log("CLI Command Error: \(args.joined(separator: " ")) - \(errorString)", level: .warning)
                    }
                    let status = proc.terminationStatus
                    if status != 0 {
                        AppLogger.log("CLI Command Failed: \(args.joined(separator: " ")) - Exit Status: \(status)", level: .error)
                    }
                    resumeOnce(status)
                }

                do {
                    try process.run()
                } catch {
                    AppLogger.log("CLI Execution Error: \(args.joined(separator: " ")) - \(error.localizedDescription)", level: .error)
                    resumeOnce(-1)
                }
            }
        }
    }

    // Non-blocking variant of runAndCapture (formerly used synchronous
    // waitUntilExit on the caller's thread). Output buffering / error semantics
    // are preserved.
    func runAndCapture(_ args: [String]) async throws -> String {
        let cmd = args.joined(separator: " ")
        AppLogger.log("runAndCapture: \(cmd)", level: .debug)
        let url = try requireExec()
        return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = url
                process.arguments = args
                let stdoutPipe = Pipe()
                let stderrPipe = Pipe()
                process.standardOutput = stdoutPipe
                process.standardError = stderrPipe

                var didResume = false
                let resumeOnce: (Result<String, Error>) -> Void = { result in
                    guard !didResume else { return }
                    didResume = true
                    switch result {
                    case .success(let s): continuation.resume(returning: s)
                    case .failure(let e): continuation.resume(throwing: e)
                    }
                }

                process.terminationHandler = { proc in
                    let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
                    let stderrData = stderrPipe.fileHandleForReading.readDataToEndOfFile()
                    let stdout = String(data: stdoutData, encoding: .utf8) ?? ""
                    let stderr = String(data: stderrData, encoding: .utf8) ?? ""
                    let exitCode = proc.terminationStatus
                    if !stderr.isEmpty {
                        AppLogger.log("runAndCapture stderr [\(cmd)]: \(stderr)", level: .warning)
                    }
                    if exitCode != 0 {
                        AppLogger.log("runAndCapture failed [\(cmd)] exit=\(exitCode): \(stderr)", level: .error)
                        resumeOnce(.failure(CLIError.commandFailed(cmd: cmd, exitCode: exitCode, stderr: stderr)))
                    } else {
                        AppLogger.log("runAndCapture success [\(cmd)]", level: .debug)
                        resumeOnce(.success(stdout))
                    }
                }

                do {
                    try process.run()
                } catch {
                    resumeOnce(.failure(error))
                }
            }
        }
    }

    private func requireExec() throws -> URL {
        if let url = execURL() { return url }
        AppLogger.log("requireExec: CLI not found in any search path", level: .error)
        throw CLIError.notFound
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

    func dockerLogs(name: String) async throws -> String {
        let args = ["docker", "logs", name]
        return try await runAndCapture(args)
    }
}
