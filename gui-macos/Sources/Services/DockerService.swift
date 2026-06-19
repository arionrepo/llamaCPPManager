// File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/DockerService.swift
// Description: Service layer for Docker and Colima management commands
// Author: Libor Ballaty <libor@arionetworks.com>
// Created: 2026-03-25

import Foundation

struct ColimaProfile: Identifiable {
    let id: String
    let name: String
    let status: String
    let arch: String
    let cpus: Int
    let memory: String
    let disk: String
    let runtime: String

    var isRunning: Bool {
        status.lowercased() == "running"
    }
}

struct DockerContainer: Identifiable {
    let id: String
    let name: String
    let status: String
    let image: String
    let ports: String
    let cpuPercent: Double?
    let memoryUsage: String?
    let colimaProfile: String  // Track which Colima profile this container belongs to

    var isRunning: Bool {
        status.lowercased().contains("up")
    }
}

final class DockerService {

    // MARK: - Colima Profile Management

    func getColimaProfiles() async -> [ColimaProfile] {
        do {
            let output = try await runCommand("colima", args: ["list"])
            return parseColimaList(output)
        } catch {
            AppLogger.log("Failed to get Colima profiles: \(error)", level: .error)
            return []
        }
    }

    func startColimaProfile(_ profile: String) async -> Bool {
        do {
            _ = try await runCommand("colima", args: ["start", profile])
            AppLogger.log("Started Colima profile: \(profile)", level: .info)
            return true
        } catch {
            AppLogger.log("Failed to start Colima profile \(profile): \(error)", level: .error)
            return false
        }
    }

    func stopColimaProfile(_ profile: String) async -> Bool {
        do {
            _ = try await runCommand("colima", args: ["stop", profile])
            AppLogger.log("Stopped Colima profile: \(profile)", level: .info)
            return true
        } catch {
            AppLogger.log("Failed to stop Colima profile \(profile): \(error)", level: .error)
            return false
        }
    }

    func restartColima() async -> Bool {
        do {
            _ = try await runCommand("colima", args: ["restart"])
            AppLogger.log("Restarted Colima", level: .info)
            return true
        } catch {
            AppLogger.log("Failed to restart Colima: \(error)", level: .error)
            return false
        }
    }

    // Returns nil on success, or a human-readable error message on failure.
    // Colima has no `create` subcommand; `colima start <profile>` both creates
    // (if missing) and starts the VM. Memory/disk are GiB integers; the form
    // strips any trailing unit suffix before calling. `onLine` is called on
    // the main queue for each line of colima's stdout/stderr so the UI can
    // show live progress (VM creation takes 30-60s).
    func createColimaProfile(
        name: String,
        cpus: Int? = nil,
        memory: String? = nil,
        disk: String? = nil,
        runtime: String? = nil,
        arch: String? = nil,
        onLine: ((String) -> Void)? = nil
    ) async -> String? {
        var args = ["start", name]

        if let cpus = cpus {
            args.append("--cpus")
            args.append(String(cpus))
        }
        if let memory = memory, !memory.isEmpty {
            args.append("--memory")
            args.append(memory)
        }
        if let disk = disk, !disk.isEmpty {
            args.append("--disk")
            args.append(disk)
        }
        if let runtime = runtime, !runtime.isEmpty {
            args.append("--runtime")
            args.append(runtime)
        }
        if let arch = arch, !arch.isEmpty {
            args.append("--arch")
            args.append(arch)
        }

        do {
            _ = try await runCommandStreaming("colima", args: args, onLine: onLine)
            AppLogger.log("Created Colima profile: \(name)", level: .info)
            return nil
        } catch {
            let msg = (error as NSError).localizedDescription
            AppLogger.log("Failed to create Colima profile \(name): \(msg)", level: .error)
            let trimmed = msg.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? "colima start \(name) failed (exit code \((error as NSError).code))" : trimmed
        }
    }

    func deleteColimaProfile(_ profile: String) async -> Bool {
        do {
            _ = try await runCommand("colima", args: ["delete", profile, "-f"])
            AppLogger.log("Deleted Colima profile: \(profile)", level: .info)
            return true
        } catch {
            AppLogger.log("Failed to delete Colima profile \(profile): \(error)", level: .error)
            return false
        }
    }

    // MARK: - Docker Container Management

    func getDockerContainers() async -> [DockerContainer] {
        // Get Colima profiles and query containers from RUNNING profiles only
        // Stopped profiles have no Docker context, so containers cannot be queried
        let profiles = await getColimaProfiles()
        var allContainers: [DockerContainer] = []

        let profilesToQuery = profiles.filter { $0.isRunning }

        for profile in profilesToQuery {
            do {
                // Use colima-specific Docker context
                let output = try await runCommand("docker", args: ["--context", "colima-\(profile.name)", "ps", "-a", "--format", "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}|{{.Ports}}"])
                let containers = parseDockerContainers(output, profileName: profile.name)
                AppLogger.log("Found \(containers.count) containers in profile \(profile.name)", level: .debug)
                allContainers.append(contentsOf: containers)
            } catch {
                AppLogger.log("Failed to get containers for profile \(profile.name): \(error)", level: .error)
            }
        }

        AppLogger.log("Total containers before dedup: \(allContainers.count)", level: .debug)

        // Deduplicate by container ID (same container shouldn't appear twice)
        var seen = Set<String>()
        let uniqueContainers = allContainers.filter { container in
            if seen.contains(container.id) {
                AppLogger.log("Skipping duplicate container: \(container.name) (ID: \(container.id), profile: \(container.colimaProfile))", level: .debug)
                return false
            }
            seen.insert(container.id)
            return true
        }

        AppLogger.log("Total unique containers: \(uniqueContainers.count)", level: .debug)
        for container in uniqueContainers {
            AppLogger.log("  - \(container.name) from profile '\(container.colimaProfile)'", level: .debug)
        }

        return uniqueContainers
    }

    func startDockerContainer(_ containerName: String, profile: String) async -> Bool {
        do {
            _ = try await runCommand("docker", args: ["--context", "colima-\(profile)", "start", containerName])
            AppLogger.log("Started container: \(containerName) (profile: \(profile))", level: .info)
            return true
        } catch {
            AppLogger.log("Failed to start container \(containerName): \(error)", level: .error)
            return false
        }
    }

    func stopDockerContainer(_ containerName: String, profile: String) async -> Bool {
        do {
            _ = try await runCommand("docker", args: ["--context", "colima-\(profile)", "stop", containerName])
            AppLogger.log("Stopped container: \(containerName) (profile: \(profile))", level: .info)
            return true
        } catch {
            AppLogger.log("Failed to stop container \(containerName): \(error)", level: .error)
            return false
        }
    }

    func restartDockerContainer(_ containerName: String, profile: String) async -> Bool {
        do {
            _ = try await runCommand("docker", args: ["--context", "colima-\(profile)", "restart", containerName])
            AppLogger.log("Restarted container: \(containerName) (profile: \(profile))", level: .info)
            return true
        } catch {
            AppLogger.log("Failed to restart container \(containerName): \(error)", level: .error)
            return false
        }
    }

    func getContainerStats() async -> [String: (cpu: Double, memory: String)] {
        // Query stats from all running Colima profiles
        let profiles = await getColimaProfiles()
        var allStats: [String: (cpu: Double, memory: String)] = [:]

        for profile in profiles where profile.isRunning {
            do {
                let output = try await runCommand("docker", args: ["--context", "colima-\(profile.name)", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}"])
                let stats = parseDockerStats(output)
                allStats.merge(stats) { current, _ in current }
            } catch {
                AppLogger.log("Failed to get stats for profile \(profile.name): \(error)", level: .error)
            }
        }

        return allStats
    }

    // MARK: - Helper Methods

    // Run a subprocess fully off the main thread.
    // The previous version used Process.waitUntilExit() inline; since DockerColimaViewModel
    // is @MainActor, that blocked the UI for the duration of the subprocess. Long-running
    // commands (e.g. `colima delete -f` which takes many seconds) would freeze the menu
    // bar and the confirmation dialog. Using withCheckedThrowingContinuation +
    // terminationHandler keeps the @MainActor caller free while we wait.
    private func runCommand(_ command: String, args: [String]) async throws -> String {
        return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
                process.arguments = [command] + args

                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = pipe

                // Track resume state to avoid double-resume on edge cases.
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
                    let data = pipe.fileHandleForReading.readDataToEndOfFile()
                    let output = String(data: data, encoding: .utf8) ?? ""
                    if proc.terminationStatus == 0 {
                        resumeOnce(.success(output))
                    } else {
                        let err = NSError(
                            domain: "DockerService",
                            code: Int(proc.terminationStatus),
                            userInfo: [NSLocalizedDescriptionKey: output]
                        )
                        resumeOnce(.failure(err))
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

    // Streaming variant: invokes `onLine` (on the main queue) for each
    // newline-terminated chunk of stdout/stderr. Used by long-running commands
    // (e.g. `colima start <new-profile>`) so the UI can show live progress.
    private func runCommandStreaming(
        _ command: String,
        args: [String],
        onLine: ((String) -> Void)?
    ) async throws -> String {
        return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
                process.arguments = [command] + args

                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = pipe

                let bufferLock = NSLock()
                var lineBuffer = ""
                var collected = ""

                pipe.fileHandleForReading.readabilityHandler = { handle in
                    let data = handle.availableData
                    guard !data.isEmpty, let chunk = String(data: data, encoding: .utf8) else { return }
                    bufferLock.lock()
                    lineBuffer += chunk
                    collected += chunk
                    var lines: [String] = []
                    while let nl = lineBuffer.firstIndex(of: "\n") {
                        lines.append(String(lineBuffer[..<nl]))
                        lineBuffer = String(lineBuffer[lineBuffer.index(after: nl)...])
                    }
                    bufferLock.unlock()
                    if let onLine = onLine {
                        for line in lines {
                            let l = line
                            DispatchQueue.main.async { onLine(l) }
                        }
                    }
                }

                var didResume = false
                let resumeOnce: (Result<String, Error>) -> Void = { result in
                    guard !didResume else { return }
                    didResume = true
                    pipe.fileHandleForReading.readabilityHandler = nil
                    switch result {
                    case .success(let s): continuation.resume(returning: s)
                    case .failure(let e): continuation.resume(throwing: e)
                    }
                }

                process.terminationHandler = { proc in
                    bufferLock.lock()
                    let tail = lineBuffer
                    lineBuffer = ""
                    let allOutput = collected
                    bufferLock.unlock()
                    if !tail.isEmpty, let onLine = onLine {
                        DispatchQueue.main.async { onLine(tail) }
                    }
                    if proc.terminationStatus == 0 {
                        resumeOnce(.success(allOutput))
                    } else {
                        let err = NSError(
                            domain: "DockerService",
                            code: Int(proc.terminationStatus),
                            userInfo: [NSLocalizedDescriptionKey: allOutput]
                        )
                        resumeOnce(.failure(err))
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

    private func parseColimaList(_ output: String) -> [ColimaProfile] {
        let lines = output.split(separator: "\n").map(String.init)
        guard lines.count > 1 else { return [] }

        return lines.dropFirst().compactMap { line in
            let parts = line.split(separator: " ", omittingEmptySubsequences: true).map(String.init)
            guard parts.count >= 6 else { return nil }

            return ColimaProfile(
                id: parts[0],
                name: parts[0],
                status: parts[1],
                arch: parts[2],
                cpus: Int(parts[3]) ?? 0,
                memory: parts[4],
                disk: parts[5],
                runtime: parts.count > 6 ? parts[6] : ""
            )
        }
    }

    private func parseDockerContainers(_ output: String, profileName: String) -> [DockerContainer] {
        let lines = output.split(separator: "\n").map(String.init)

        return lines.compactMap { line in
            // Keep empty trailing fields (Ports may be empty for containers with no exposed ports)
            let parts = line.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
            guard parts.count >= 4 else { return nil }

            return DockerContainer(
                id: parts[0],
                name: parts[1],
                status: parts[2],
                image: parts[3],
                ports: parts.count > 4 ? parts[4] : "",
                cpuPercent: nil,
                memoryUsage: nil,
                colimaProfile: profileName
            )
        }
    }

    private func parseDockerStats(_ output: String) -> [String: (cpu: Double, memory: String)] {
        var stats: [String: (cpu: Double, memory: String)] = [:]

        for line in output.split(separator: "\n") {
            let parts = line.split(separator: "|").map(String.init)
            guard parts.count >= 3 else { continue }

            let name = parts[0]
            let cpuStr = parts[1].replacingOccurrences(of: "%", with: "")
            let cpu = Double(cpuStr) ?? 0.0
            let memory = parts[2]

            stats[name] = (cpu: cpu, memory: memory)
        }

        return stats
    }
}
