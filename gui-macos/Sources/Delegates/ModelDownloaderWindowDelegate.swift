//
//  ModelDownloaderWindowDelegate.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Delegates/ModelDownloaderWindowDelegate.swift
//  Description: NSWindowDelegate that notifies StatusViewModel when the model-downloader window closes.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import AppKit

@MainActor
final class ModelDownloaderWindowDelegate: NSObject, NSWindowDelegate {
    private let onClose: () -> Void

    init(onClose: @escaping () -> Void) {
        self.onClose = onClose
        super.init()
    }

    func windowWillClose(_ notification: Notification) {
        // Deferred to windowDidClose — see ChatWindowDelegate for the reason.
    }

}

extension ModelDownloaderWindowDelegate {
    func windowDidClose(_ notification: Notification) {
        onClose()
    }
}
