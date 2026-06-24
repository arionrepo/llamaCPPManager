//
//  ChatViewModel.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/ViewModels/ChatViewModel.swift
//  Description: Chat-window view model — message list, input buffer, loading/error state. Calls CLIService.queryChat for assistant responses.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation
import Combine

@MainActor
final class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var currentInput: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String? = nil

    let modelName: String
    private let cliService: CLIService

    init(modelName: String, cliService: CLIService) {
        self.modelName = modelName
        self.cliService = cliService

        // Add system message
        messages.append(ChatMessage(
            role: "system",
            content: "You are a helpful AI assistant running on llama.cpp via llamaCPPManager."
        ))
    }

    func sendMessage() {
        guard !currentInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        guard !isLoading else { return }

        let userMessage = ChatMessage(role: "user", content: currentInput)
        messages.append(userMessage)

        let inputText = currentInput
        currentInput = ""
        isLoading = true
        errorMessage = nil

        Task { @MainActor in
            do {
                let response = try await cliService.queryChat(modelName: modelName, messages: messages)
                let assistantMessage = ChatMessage(role: "assistant", content: response.trimmingCharacters(in: .whitespacesAndNewlines))
                messages.append(assistantMessage)
            } catch {
                errorMessage = "Failed to send message: \(error.localizedDescription)"
                // Remove the user message if the API call failed
                if let lastIndex = messages.lastIndex(where: { $0.content == inputText && $0.role == "user" }) {
                    messages.remove(at: lastIndex)
                }
            }
            isLoading = false
        }
    }

    func clearChat() {
        messages.removeAll()
        messages.append(ChatMessage(
            role: "system",
            content: "You are a helpful AI assistant running on llama.cpp via llamaCPPManager."
        ))
        errorMessage = nil
    }
}
