//
//  LoggingConfig.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Models/LoggingConfig.swift
//  Description: Data model for CLI-side logging configuration (rotation thresholds, timestamp flag).
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

struct LoggingConfig: Codable {
    let enabled: Bool
    let max_bytes: Int
    let backups: Int
    let timestamps: Bool
}
