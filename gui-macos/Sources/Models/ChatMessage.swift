//
//  ChatMessage.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Models/ChatMessage.swift
//  Description: One chat-window message (role, content, timestamp). Identity via UUID assigned per instance.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation

struct ChatMessage: Identifiable, Equatable {
    let id = UUID()
    let role: String // "system", "user", "assistant"
    let content: String
    let timestamp: Date = Date()
}
