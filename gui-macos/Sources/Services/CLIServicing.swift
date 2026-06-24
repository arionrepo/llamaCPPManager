//
//  CLIServicing.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Services/CLIServicing.swift
//  Description: Protocol seam over CLIService so view models can be unit-tested with mocks. Method signatures mirror the public surface of CLIService that view models actually call (Phase 6 inventory). No behavior change.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-24
//

import Foundation

/// Test seam for `CLIService`. View models depend on this protocol so unit
/// tests can substitute a `MockCLIService` without spawning a real CLI
/// subprocess. The concrete `CLIService` satisfies this protocol unchanged
/// via the extension at the bottom of this file.
protocol CLIServicing {
    func fetchStatus() async throws -> StatusResponse
    func fetchDockerStatus() async throws -> StatusResponse
    func startInfrastructure(_ name: String) async throws
    func stopInfrastructure(_ name: String) async throws
    func restartInfrastructure(_ name: String) async throws
    func run(_ args: [String]) async -> Int32
    func runAndCapture(_ args: [String]) async throws -> String
    func configDirURL() -> URL?
    func queryChat(modelName: String, messages: [ChatMessage]) async throws -> String
    func dockerLogs(name: String) async throws -> String
}

extension CLIService: CLIServicing {}
