//
//  ModelStartupProgress.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Models/ModelStartupProgress.swift
//  Description: Per-model in-flight startup state (status text, optional percent, detail, start timestamp).
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

// MARK: - Model Startup Progress

struct ModelStartupProgress: Equatable {
    var status: String          // e.g., "Starting...", "Downloading model files...", "Loading model..."
    var progress: Double?       // 0.0 to 1.0, nil if unknown
    var detail: String?         // e.g., "5/11 files", "1.2 GB / 18 GB"
    var startedAt: Date
}
