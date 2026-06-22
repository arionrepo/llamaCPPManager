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

class ModelDownloaderWindowDelegate: NSObject, NSWindowDelegate {
    private let onClose: () -> Void

    init(onClose: @escaping () -> Void) {
        self.onClose = onClose
        super.init()
    }

    func windowWillClose(_ notification: Notification) {
        onClose()
    }
}
