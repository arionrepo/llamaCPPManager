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
    private let modelName: String
    private let onClose: () -> Void

    init(modelName: String, onClose: @escaping () -> Void) {
        self.modelName = modelName
        self.onClose = onClose
        super.init()
    }

    func windowWillClose(_ notification: Notification) {
        let policyBefore = NSApp.activationPolicy().rawValue
        let visibleWindows = NSApp.windows.filter { $0.isVisible }.count
        LifecycleLog.log("ui.chat.window_will_close", model: modelName,
                         ["activation_policy_before": policyBefore,
                          "visible_windows_before_close": visibleWindows])
        onClose()
        DispatchQueue.main.async {
            let policyAfter = NSApp.activationPolicy().rawValue
            let visibleAfter = NSApp.windows.filter { $0.isVisible }.count
            LifecycleLog.log("ui.chat.window_did_close", model: self.modelName,
                             ["activation_policy_after": policyAfter,
                              "visible_windows_after_close": visibleAfter])
        }
    }
}
