//
//  InfrastructureRow.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Models/InfrastructureRow.swift
//  Description: Data model for an infrastructure component (cloudflared, llm_controller, etc.) decoded from the CLI status payload.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

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
