//
//  SliceC_ChatSendReceiveTests.swift
//  llamacpp-gui — E2E vertical slice C
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Tests/E2E/SliceC_ChatSendReceiveTests.swift
//  Description: Third vertical-slice E2E test. User flow: launch app → click menu bar icon → click Chat on a model with a running server → type a message → press Return → verify the assistant reply arrives. Real CLI, real llama.cpp / MLX server, real network. Gated behind RUN_E2E_INTERACTIVE because it drives the UI via osascript and additionally requires a model server already running on this machine.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-24
//

import Testing
import Foundation

@Suite("E2E Slice C — Chat Send + Receive")
struct SliceC_ChatSendReceiveTests {

    @Test("Send a message and receive an assistant reply")
    func sendChatGetReply() async throws {
        guard interactiveSlicesEnabled else {
            print(interactiveSkipMessage)
            return
        }
        let logOffset = snapshotLogOffset()
        let proc = try launchApp()
        defer { quitApp(proc) }

        // Boot + first status refresh.
        _ = try waitForLogEvent("ui.app.did_finish_launching", after: logOffset, timeout: 15.0)
        _ = try waitForLogEvent("cli.status.fetched", after: logOffset, timeout: 30.0)
        let postBoot = snapshotLogOffset()

        // Open the menu and click Chat on a model.
        try clickStatusBarItem()
        Thread.sleep(forTimeInterval: 0.4)
        try clickChatButton()

        // Wait for the chat window to be open.
        _ = try waitForLogEvent("ui.chat.window_opened",
                                after: postBoot,
                                timeout: 10.0)

        // Give SwiftUI a moment to mount the text field and make it the
        // first responder. (window.makeKey() runs during openChat — see
        // v2026.06.23.8 changelog.)
        Thread.sleep(forTimeInterval: 0.6)

        // Type a short message and press Return.
        let preSend = snapshotLogOffset()
        try typeString("hi")
        Thread.sleep(forTimeInterval: 0.2)
        try sendReturn()

        // Wait for evidence that the message round-tripped through the
        // real CLI to the real model server. The ChatViewModel writes a
        // cli.chat.reply_received event when queryChat returns successfully.
        // If that event name doesn't exist yet in production code, this
        // test will fail with a clear timeout — which is a useful signal
        // that the logging coverage needed for this slice is missing.
        let reply = try waitForLogEvent("cli.chat.reply_received",
                                        after: preSend,
                                        timeout: 60.0)
        #expect(reply["event"] as? String == "cli.chat.reply_received")
        if let replyLen = reply["reply_length"] as? Int {
            #expect(replyLen > 0, "reply_length must be positive")
        }

        // Clean up: close the chat window.
        try sendCmdW()
    }
}
