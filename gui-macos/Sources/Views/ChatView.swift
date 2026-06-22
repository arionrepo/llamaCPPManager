//
//  ChatView.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Views/ChatView.swift
//  Description: SwiftUI chat window UI — header, scrollable message list, error banner, input box.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import SwiftUI
import AppKit

struct ChatView: View {
    @StateObject var viewModel: ChatViewModel

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Chat with \(viewModel.modelName)")
                    .font(.headline)
                Spacer()
                Button("Clear") {
                    viewModel.clearChat()
                }
                .buttonStyle(.borderless)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))

            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(viewModel.messages.filter { $0.role != "system" }) { message in
                            ChatMessageView(message: message)
                                .id(message.id)
                        }

                        if viewModel.isLoading {
                            HStack {
                                ProgressView()
                                    .scaleEffect(0.8)
                                Text("Thinking...")
                                    .foregroundColor(.secondary)
                                Spacer()
                            }
                            .padding(.horizontal)
                        }
                    }
                    .padding()
                }
                .onChange(of: viewModel.messages.count) { _ in
                    if let lastMessage = viewModel.messages.last {
                        withAnimation(.easeOut(duration: 0.3)) {
                            proxy.scrollTo(lastMessage.id, anchor: .bottom)
                        }
                    }
                }
            }

            // Error message
            if let error = viewModel.errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle")
                        .foregroundColor(.orange)
                        .accessibilityHidden(true)
                    Text(error)
                        .foregroundColor(.orange)
                        .font(.caption)
                    Spacer()
                    Button("Dismiss") {
                        viewModel.errorMessage = nil
                    }
                    .buttonStyle(.borderless)
                    .font(.caption)
                }
                .padding()
                .background(Color.orange.opacity(0.1))
            }

            // Input area
            HStack {
                TextField("Type your message...", text: $viewModel.currentInput, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(1...6)
                    .onSubmit {
                        viewModel.sendMessage()
                    }

                Button("Send") {
                    viewModel.sendMessage()
                }
                .keyboardShortcut(.return, modifiers: [])
                .disabled(viewModel.currentInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
        }
        .frame(minWidth: 400, minHeight: 300)
    }
}
