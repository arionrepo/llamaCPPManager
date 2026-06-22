//
//  StatusRow.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Models/StatusRow.swift
//  Description: Data model for native and Docker model status decoded from the CLI status payload.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

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
    let format: String?  // Model format: gguf, mlx, moe
    let log_path: String?
    let health_state: String?
    let uptime: String?
    // Enriched fields (optional - missing on older CLI versions)
    let model_path: String?
    let model_filename: String?
    let file_size_gb: Double?
    let quantization: String?
    let deployment_type: String?
    let ram_mb: Double?
    let cpu_percent: Double?
    let description: String?

    enum CodingKeys: String, CodingKey, CaseIterable {
        case name, pid, host, port, up, latency_ms, http_status, version, mode, format, log_path, health_state, uptime
        case model_path, model_filename, file_size_gb, quantization, deployment_type, ram_mb, cpu_percent, description
    }
}
