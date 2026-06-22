//
//  ChatMessageView.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Views/ChatMessageView.swift
//  Description: One chat-message row — avatar, role label, timestamp, selectable content bubble.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import SwiftUI

struct ChatMessageView: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            Circle()
                .fill(message.role == "user" ? Color.blue : Color.green)
                .frame(width: 24, height: 24)
                .overlay(
                    Text(message.role == "user" ? "U" : "AI")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                )

            // Message content
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(message.role.capitalized)
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)

                    Spacer()

                    Text(message.timestamp, style: .time)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }

                Text(message.content)
                    .textSelection(.enabled)
                    .padding(8)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(message.role == "user"
                                ? Color.blue.opacity(0.1)
                                : Color.gray.opacity(0.1))
                    )
            }

            Spacer()
        }
    }
}
