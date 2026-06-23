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
        // Do NOT call onClose() here. NSWindow does not retain its delegate, so
        // onClose() removing the last strong ref from windowDelegates would free
        // this object while windowWillClose is still on the call stack →
        // use-after-free crash in objc_release during autorelease pool drain.
        // Cleanup is deferred to windowDidClose, which fires after the window
        // and its autorelease pool have fully unwound.
    }

    func windowDidClose(_ notification: Notification) {
        onClose()
        let policyAfter = NSApp.activationPolicy().rawValue
        let visibleAfter = NSApp.windows.filter { $0.isVisible }.count
        LifecycleLog.log("ui.chat.window_did_close", model: modelName,
                         ["activation_policy_after": policyAfter,
                          "visible_windows_after_close": visibleAfter])
    }
}
