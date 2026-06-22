//
//  ChatWindowDelegate.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Delegates/ChatWindowDelegate.swift
//  Description: NSWindowDelegate that notifies StatusViewModel when a chat window closes, so the window/delegate refs can be cleaned up.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import AppKit

class ChatWindowDelegate: NSObject, NSWindowDelegate {
    private let onClose: () -> Void

    init(onClose: @escaping () -> Void) {
        self.onClose = onClose
        super.init()
    }

    func windowWillClose(_ notification: Notification) {
        onClose()
    }
}
