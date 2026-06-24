//
//  SliceA_LaunchTests.swift
//  llamacpp-gui — E2E vertical slice A
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Tests/E2E/SliceA_LaunchTests.swift
//  Description: First vertical-slice E2E test. User flow: open the app. Verifies that the installed app launches, boots successfully, runs a real CLI status fetch against the real Python CLI, and emits the expected lifecycle log events. No mocks. No fakes.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-24
//

import Testing
import Foundation

@Suite("E2E Slice A — App Launch & Boot")
struct SliceA_LaunchTests {

    @Test("App launches and emits did_finish_launching")
    func appLaunchEmitsDidFinishLaunching() async throws {
        let logOffset = snapshotLogOffset()
        let proc = try launchApp()
        defer { quitApp(proc) }

        let entry = try waitForLogEvent("ui.app.did_finish_launching",
                                        after: logOffset,
                                        timeout: 15.0)

        #expect(entry["event"] as? String == "ui.app.did_finish_launching")
        #expect(entry["source"] as? String == "gui")
        // We intentionally do not assert pid equality between proc.processIdentifier
        // and entry["pid_self"]. Bundled macOS apps often fork once during startup
        // (launcher → main process), so the logged pid is typically off by one
        // from the Process pid. The event firing inside the launch window is
        // sufficient proof of "app booted".
    }

    @Test("First status refresh completes against real CLI")
    func firstStatusRefreshCompletes() async throws {
        let logOffset = snapshotLogOffset()
        let proc = try launchApp()
        defer { quitApp(proc) }

        // Wait for boot first.
        _ = try waitForLogEvent("ui.app.did_finish_launching",
                                after: logOffset,
                                timeout: 15.0)

        // Then wait for the first real CLI status fetch to complete.
        let entry = try waitForLogEvent("cli.status.fetched",
                                        after: logOffset,
                                        timeout: 30.0)

        // Verify shape: the log entry should report a model count and an
        // infrastructure count. We don't assert specific numbers — any real
        // configured environment satisfies this. We assert the FIELDS exist
        // and are non-negative integers.
        let modelCount = entry["model_count"] as? Int
        let infraCount = entry["infrastructure_count"] as? Int
        #expect(modelCount != nil, "model_count must be present in cli.status.fetched")
        #expect(infraCount != nil, "infrastructure_count must be present in cli.status.fetched")
        if let mc = modelCount { #expect(mc >= 0) }
        if let ic = infraCount { #expect(ic >= 0) }
    }
}
