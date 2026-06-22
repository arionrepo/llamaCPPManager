//
//  CLIError.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Errors/CLIError.swift
//  Description: Domain errors raised by CLIService when the llamacpp-manager subprocess fails or produces unexpected output.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

// MARK: - CLI Error Types

enum CLIError: Error, LocalizedError {
    case notFound
    case commandFailed(cmd: String, exitCode: Int32, stderr: String)
    case parseError(cmd: String, raw: String)

    var errorDescription: String? {
        switch self {
        case .notFound:
            return "CLI not found. Check that llamacpp-manager is installed: pip install -e ."
        case .commandFailed(let cmd, let exitCode, let stderr):
            let detail = stderr.isEmpty ? "no stderr output" : stderr
            return "Command failed (exit \(exitCode)) [\(cmd)]: \(detail)"
        case .parseError(let cmd, let raw):
            return "Command succeeded but returned unexpected output [\(cmd)]. Raw: \(raw.prefix(200))"
        }
    }
}
