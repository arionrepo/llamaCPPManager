//
//  SliceB_ChatWindowTests.swift
//  llamacpp-gui — E2E vertical slice B
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Tests/E2E/SliceB_ChatWindowTests.swift
//  Description: Second vertical-slice E2E test. User flow: launch app → click menu bar icon → click Chat on a configured model → verify the chat window opened → send Cmd-W → verify the chat window closed. Regression-tests the v2026.06.23.7 + .8 window-lifecycle fixes. Requires Accessibility permission granted to the test runner (Terminal / IDE) so System Events can click and send keystrokes.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-24
//

import Testing
import Foundation

@Suite("E2E Slice B — Chat Window Open + Cmd-W Close")
struct SliceB_ChatWindowTests {

    @Test("Open chat window via menu and close it with Cmd-W")
    func openChatThenCmdW() async throws {
        guard interactiveSlicesEnabled else {
            print(interactiveSkipMessage)
            return
        }
        let logOffset = snapshotLogOffset()
        let proc = try launchApp()
        defer { quitApp(proc) }

        // Wait for boot + first status refresh so the menu has model rows.
        _ = try waitForLogEvent("ui.app.did_finish_launching", after: logOffset, timeout: 15.0)
        let postBoot = snapshotLogOffset()
        _ = try waitForLogEvent("cli.status.fetched", after: logOffset, timeout: 30.0)

        // Open the menu bar popover.
        try clickStatusBarItem()
        // Brief settle delay for SwiftUI to render the popover content.
        Thread.sleep(forTimeInterval: 0.4)

        // Click the first "Chat" button in the popover. The MenuBarExtra
        // hosts SwiftUI Button views with the literal title "Chat" — these
        // are visible to System Events via accessibility.
        try clickChatButton()

        // Verify a chat window opened.
        let opened = try waitForLogEvent("ui.chat.window_opened",
                                         after: postBoot,
                                         timeout: 10.0)
        #expect(opened["event"] as? String == "ui.chat.window_opened")
        let openedModelName = opened["model"] as? String
        #expect(openedModelName != nil, "ui.chat.window_opened must carry a model name")

        // Give the window a moment to actually become key (the
        // makeKeyAndOrderFront → makeKey path takes a tick under SwiftUI).
        Thread.sleep(forTimeInterval: 0.3)

        // Send Cmd-W and verify the window closes.
        let preClose = snapshotLogOffset()
        try sendCmdW()

        let closed = try waitForLogEvent("ui.chat.window_did_close",
                                         after: preClose,
                                         timeout: 5.0)
        #expect(closed["event"] as? String == "ui.chat.window_did_close")
        // The closed window should be for the same model that was opened.
        #expect(closed["model"] as? String == openedModelName)
    }
}

// clickChatButton() now lives in E2EHelpers.swift so multiple slices can use it.
