//
//  Formatting.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Utils/Formatting.swift
//  Description: Display-formatting helpers shared across views (download ETA, etc.).
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

// Helper: format ETA seconds as a short human-readable string
func formatDownloadETA(_ seconds: Int) -> String {
    if seconds < 60 { return "\(seconds)s" }
    if seconds < 3600 { return "\(seconds / 60)m \(seconds % 60)s" }
    let h = seconds / 3600
    let m = (seconds % 3600) / 60
    return "\(h)h \(m)m"
}
