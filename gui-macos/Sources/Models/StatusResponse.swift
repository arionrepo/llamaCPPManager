//
//  StatusResponse.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Models/StatusResponse.swift
//  Description: Top-level JSON response from the CLI status / docker-status commands.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

struct StatusResponse: Codable {
    let models: [StatusRow]
    let infrastructure: [InfrastructureRow]
    let logging: LoggingConfig
}
