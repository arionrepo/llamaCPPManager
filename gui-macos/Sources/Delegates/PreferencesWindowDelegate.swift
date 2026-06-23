//
//  PreferencesWindowDelegate.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Delegates/PreferencesWindowDelegate.swift
//  Description: NSWindowDelegate that notifies StatusViewModel when the preferences window closes.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import AppKit

class PreferencesWindowDelegate: NSObject, NSWindowDelegate {
    private let onClose: () -> Void

    init(onClose: @escaping () -> Void) {
        self.onClose = onClose
        super.init()
    }

    func windowWillClose(_ notification: Notification) {
        // Deferred to windowDidClose — see ChatWindowDelegate for the reason.
    }

    func windowDidClose(_ notification: Notification) {
        onClose()
    }
}
