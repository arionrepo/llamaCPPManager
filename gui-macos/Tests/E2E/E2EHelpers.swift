//
//  E2EHelpers.swift
//  llamacpp-gui — E2E slice helpers
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Tests/E2E/E2EHelpers.swift
//  Description: Real-stack helpers for vertical-slice E2E tests. Launches the installed app via Process, drives via osascript/System Events, and inspects ~/Library/Logs/llamaCPPManager/lifecycle.jsonl. No mocks, no fakes. See docs/E2E-SLICES.md for the contract.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-24
//

import Foundation

enum E2EError: Error, CustomStringConvertible {
    case appBundleNotInstalled(path: String)
    case launchFailed(String)
    case logTimeout(event: String, after: TimeInterval)
    case osascriptFailed(script: String, status: Int32, stderr: String)
    case quitFailed(String)

    var description: String {
        switch self {
        case .appBundleNotInstalled(let p): return "App bundle not at \(p). Run `llamacpp-manager install-gui` first."
        case .launchFailed(let s): return "Launch failed: \(s)"
        case .logTimeout(let e, let t): return "Timed out waiting for event '\(e)' after \(t)s"
        case .osascriptFailed(let s, let st, let err): return "osascript failed (\(st)): \(s) → \(err)"
        case .quitFailed(let s): return "Quit failed: \(s)"
        }
    }
}

/// Whether the developer has opted in to interactive slices that require
/// Accessibility permission for the test runner. Set `RUN_E2E_INTERACTIVE=1`
/// in the environment to enable. See docs/E2E-SLICES.md for one-time setup.
var interactiveSlicesEnabled: Bool {
    ProcessInfo.processInfo.environment["RUN_E2E_INTERACTIVE"] != nil
}

/// Reason text printed when an interactive slice is skipped.
let interactiveSkipMessage = """
SKIPPED: this slice drives the real UI via osascript / System Events and \
requires the test runner (Terminal / IDE) to have Accessibility permission. \
To enable: \
  1) System Settings → Privacy & Security → Accessibility → add your terminal/IDE, \
  2) run with: RUN_E2E_INTERACTIVE=1 swift test
"""

let menuAutomationSkipMessage = """
SKIPPED: System Events can click the llamaCPPManager menu bar item on this machine \
but the MenuBarExtra popover contents are not exposed back as accessible buttons. \
This is a pre-existing local runtime limitation: existing interactive slices (B/C) \
also cannot discover Chat/Start buttons here. The slice implementation is present, \
but local verification requires a machine where the opened popover is visible to \
System Events.
"""

/// Path to the installed app bundle. The test harness expects the app already
/// installed via `llamacpp-manager install-gui` — slices do not build/install
/// themselves so that one test failure can be localized cleanly.
let installedAppPath = "/Applications/llamaCPP Manager.app"
let appExecutablePath = "\(installedAppPath)/Contents/MacOS/llamacpp-gui"

/// Path to the lifecycle.jsonl that slices tail for assertions.
let lifecycleLogPath: String = {
    let home = FileManager.default.homeDirectoryForCurrentUser.path
    return "\(home)/Library/Logs/llamaCPPManager/lifecycle.jsonl"
}()

func lifecycleLogPath(forLogDir logDir: String) -> String {
    URL(fileURLWithPath: logDir).appendingPathComponent("lifecycle.jsonl").path
}

// MARK: - App lifecycle

/// Launch the installed app. Returns the launched Process.
/// Caller must call `quitApp(_:)` to clean up.
func launchApp(environment: [String: String] = [:]) throws -> Process {
    guard FileManager.default.fileExists(atPath: appExecutablePath) else {
        throw E2EError.appBundleNotInstalled(path: installedAppPath)
    }
    let proc = Process()
    proc.executableURL = URL(fileURLWithPath: appExecutablePath)
    if !environment.isEmpty {
        proc.environment = ProcessInfo.processInfo.environment.merging(environment) { _, new in new }
    }
    proc.standardOutput = Pipe()
    proc.standardError = Pipe()
    do {
        try proc.run()
    } catch {
        throw E2EError.launchFailed("\(error)")
    }
    return proc
}

/// Quit the app cleanly via SIGTERM. Falls back to SIGKILL after 3 seconds.
func quitApp(_ proc: Process) {
    guard proc.isRunning else { return }
    proc.terminate()
    let deadline = Date().addingTimeInterval(3.0)
    while proc.isRunning, Date() < deadline {
        Thread.sleep(forTimeInterval: 0.1)
    }
    if proc.isRunning {
        kill(proc.processIdentifier, SIGKILL)
        proc.waitUntilExit()
    }
}

// MARK: - Lifecycle log tailing

/// Snapshot the current end offset of the lifecycle log so subsequent waits
/// only consider events written AFTER the snapshot. Returns 0 if the log
/// doesn't exist yet (first ever launch on a fresh machine).
func snapshotLogOffset(logPath: String = lifecycleLogPath) -> UInt64 {
    let url = URL(fileURLWithPath: logPath)
    guard let attrs = try? FileManager.default.attributesOfItem(atPath: url.path),
          let size = attrs[.size] as? NSNumber else {
        return 0
    }
    return size.uint64Value
}

/// Wait up to `timeout` seconds for a log entry whose `event` field equals
/// the given event name and that appears AFTER `startOffset`. Returns the
/// parsed entry on success.
@discardableResult
func waitForLogEvent(_ event: String,
                     after startOffset: UInt64,
                     logPath: String = lifecycleLogPath,
                     timeout: TimeInterval = 10.0,
                     pollInterval: TimeInterval = 0.2) throws -> [String: Any] {
    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        if let entry = readLogEntry(matchingEvent: event, after: startOffset, logPath: logPath) {
            return entry
        }
        Thread.sleep(forTimeInterval: pollInterval)
    }
    throw E2EError.logTimeout(event: event, after: timeout)
}

/// Read the lifecycle log starting at `startOffset`, return the first entry
/// whose `event` field matches.
private func readLogEntry(matchingEvent event: String, after startOffset: UInt64, logPath: String) -> [String: Any]? {
    guard let handle = try? FileHandle(forReadingFrom: URL(fileURLWithPath: logPath)) else {
        return nil
    }
    defer { try? handle.close() }
    do {
        try handle.seek(toOffset: startOffset)
    } catch {
        return nil
    }
    guard let data = try? handle.readToEnd(), !data.isEmpty else { return nil }
    guard let text = String(data: data, encoding: .utf8) else { return nil }
    for line in text.split(separator: "\n") {
        guard let lineData = line.data(using: .utf8) else { continue }
        guard let obj = try? JSONSerialization.jsonObject(with: lineData) as? [String: Any] else { continue }
        if obj["event"] as? String == event {
            return obj
        }
    }
    return nil
}

// MARK: - osascript bridge

/// Run an AppleScript fragment via /usr/bin/osascript. Returns trimmed stdout.
/// Throws E2EError.osascriptFailed on non-zero exit.
@discardableResult
func runAppleScript(_ script: String) throws -> String {
    let proc = Process()
    proc.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
    proc.arguments = ["-e", script]
    let outPipe = Pipe()
    let errPipe = Pipe()
    proc.standardOutput = outPipe
    proc.standardError = errPipe
    try proc.run()
    proc.waitUntilExit()
    let stdoutData = outPipe.fileHandleForReading.readDataToEndOfFile()
    let stderrData = errPipe.fileHandleForReading.readDataToEndOfFile()
    let stdout = String(data: stdoutData, encoding: .utf8) ?? ""
    let stderr = String(data: stderrData, encoding: .utf8) ?? ""
    guard proc.terminationStatus == 0 else {
        throw E2EError.osascriptFailed(script: script,
                                       status: proc.terminationStatus,
                                       stderr: stderr.trimmingCharacters(in: .whitespacesAndNewlines))
    }
    return stdout.trimmingCharacters(in: .whitespacesAndNewlines)
}

/// Click the app's status bar item. Requires Accessibility permission for
/// the test runner. Returns true on success.
@discardableResult
func clickStatusBarItem() throws -> String {
    // The app process is named "llamacpp-gui" by the executable.
    let script = """
    tell application "System Events"
        tell process "llamacpp-gui"
            click menu bar item 1 of menu bar 2
        end tell
    end tell
    """
    return try runAppleScript(script)
}

/// Send Cmd-W to the frontmost window of the app.
@discardableResult
func sendCmdW() throws -> String {
    let script = """
    tell application "System Events"
        tell process "llamacpp-gui"
            keystroke "w" using command down
        end tell
    end tell
    """
    return try runAppleScript(script)
}

/// Send a keystroke string to the app.
@discardableResult
func typeString(_ s: String) throws -> String {
    // Escape double quotes inside the string for AppleScript.
    let escaped = s.replacingOccurrences(of: "\"", with: "\\\"")
    let script = """
    tell application "System Events"
        tell process "llamacpp-gui"
            keystroke "\(escaped)"
        end tell
    end tell
    """
    return try runAppleScript(script)
}

/// Click the first SwiftUI Button labeled "Chat" inside the MenuBarExtra
/// popover. Used by slices B and C. The MenuBarExtra popover hosts SwiftUI
/// Button views with the literal title "Chat" which are visible to System
/// Events via accessibility.
@discardableResult
func clickChatButton() throws -> String {
    let script = """
    tell application "System Events"
        tell process "llamacpp-gui"
            set clickedCount to 0
            repeat with w in windows
                try
                    set chatBtns to (every button of w whose name is "Chat")
                    if (count of chatBtns) > 0 then
                        click (item 1 of chatBtns)
                        set clickedCount to clickedCount + 1
                        exit repeat
                    end if
                end try
                try
                    -- Probe one level deeper for buttons inside scroll
                    -- areas / groups, common in SwiftUI layouts.
                    repeat with grp in (every UI element of w)
                        try
                            set chatBtns to (every button of grp whose name is "Chat")
                            if (count of chatBtns) > 0 then
                                click (item 1 of chatBtns)
                                set clickedCount to clickedCount + 1
                                exit repeat
                            end if
                        end try
                    end repeat
                    if clickedCount > 0 then exit repeat
                end try
            end repeat
            if clickedCount = 0 then
                error "Could not find a Chat button in any open window"
            end if
        end tell
    end tell
    """
    return try runAppleScript(script)
}

@discardableResult
func clickTab(named tabName: String) throws -> String {
    let escaped = tabName.replacingOccurrences(of: "\"", with: "\\\"")
    let script = """
    tell application "System Events"
        tell process "llamacpp-gui"
            set clickedCount to 0
            repeat with w in windows
                try
                    set tabBtns to (every radio button of w whose name is "\(escaped)")
                    if (count of tabBtns) > 0 then
                        click (item 1 of tabBtns)
                        set clickedCount to clickedCount + 1
                        exit repeat
                    end if
                end try
                try
                    set tabBtns to (every button of w whose name is "\(escaped)")
                    if (count of tabBtns) > 0 then
                        click (item 1 of tabBtns)
                        set clickedCount to clickedCount + 1
                        exit repeat
                    end if
                end try
                try
                    repeat with grp in (every UI element of w)
                        try
                            set tabBtns to (every radio button of grp whose name is "\(escaped)")
                            if (count of tabBtns) > 0 then
                                click (item 1 of tabBtns)
                                set clickedCount to clickedCount + 1
                                exit repeat
                            end if
                        end try
                        try
                            set tabBtns to (every button of grp whose name is "\(escaped)")
                            if (count of tabBtns) > 0 then
                                click (item 1 of tabBtns)
                                set clickedCount to clickedCount + 1
                                exit repeat
                            end if
                        end try
                        try
                            repeat with grp2 in (every UI element of grp)
                                try
                                    set tabBtns to (every radio button of grp2 whose name is "\(escaped)")
                                    if (count of tabBtns) > 0 then
                                        click (item 1 of tabBtns)
                                        set clickedCount to clickedCount + 1
                                        exit repeat
                                    end if
                                end try
                                try
                                    set tabBtns to (every button of grp2 whose name is "\(escaped)")
                                    if (count of tabBtns) > 0 then
                                        click (item 1 of tabBtns)
                                        set clickedCount to clickedCount + 1
                                        exit repeat
                                    end if
                                end try
                            end repeat
                            if clickedCount > 0 then exit repeat
                        end try
                    end repeat
                    if clickedCount > 0 then exit repeat
                end try
            end repeat
            if clickedCount = 0 then
                error "Could not find tab named \(escaped)"
            end if
        end tell
    end tell
    """
    return try runAppleScript(script)
}

@discardableResult
func clickFirstEnabledButton(named buttonName: String) throws -> String {
    let escaped = buttonName.replacingOccurrences(of: "\"", with: "\\\"")
    let script = """
    tell application "System Events"
        tell process "llamacpp-gui"
            set clickedCount to 0
            repeat with w in windows
                try
                    set matchingBtns to (every button of w whose name is "\(escaped)" and enabled is true)
                    if (count of matchingBtns) > 0 then
                        click (item 1 of matchingBtns)
                        set clickedCount to clickedCount + 1
                        exit repeat
                    end if
                end try
                try
                    repeat with grp in (every UI element of w)
                        try
                            set matchingBtns to (every button of grp whose name is "\(escaped)" and enabled is true)
                            if (count of matchingBtns) > 0 then
                                click (item 1 of matchingBtns)
                                set clickedCount to clickedCount + 1
                                exit repeat
                            end if
                        end try
                        try
                            repeat with grp2 in (every UI element of grp)
                                try
                                    set matchingBtns to (every button of grp2 whose name is "\(escaped)" and enabled is true)
                                    if (count of matchingBtns) > 0 then
                                        click (item 1 of matchingBtns)
                                        set clickedCount to clickedCount + 1
                                        exit repeat
                                    end if
                                end try
                            end repeat
                            if clickedCount > 0 then exit repeat
                        end try
                    end repeat
                    if clickedCount > 0 then exit repeat
                end try
            end repeat
            if clickedCount = 0 then
                error "Could not find an enabled button named \(escaped)"
            end if
        end tell
    end tell
    """
    return try runAppleScript(script)
}

func menuHasEnabledButton(named buttonName: String) -> Bool {
    let escaped = buttonName.replacingOccurrences(of: "\"", with: "\\\"")
    let script = """
    tell application "System Events"
        tell process "llamacpp-gui"
            repeat with w in windows
                try
                    set matchingBtns to (every button of w whose name is "\(escaped)" and enabled is true)
                    if (count of matchingBtns) > 0 then
                        return "yes"
                    end if
                end try
                try
                    repeat with grp in (every UI element of w)
                        try
                            set matchingBtns to (every button of grp whose name is "\(escaped)" and enabled is true)
                            if (count of matchingBtns) > 0 then
                                return "yes"
                            end if
                        end try
                        try
                            repeat with grp2 in (every UI element of grp)
                                try
                                    set matchingBtns to (every button of grp2 whose name is "\(escaped)" and enabled is true)
                                    if (count of matchingBtns) > 0 then
                                        return "yes"
                                    end if
                                end try
                            end repeat
                        end try
                    end repeat
                end try
            end repeat
            return "no"
        end tell
    end tell
    """
    return (try? runAppleScript(script)) == "yes"
}

/// Send Return key.
@discardableResult
func sendReturn() throws -> String {
    let script = """
    tell application "System Events"
        tell process "llamacpp-gui"
            key code 36
        end tell
    end tell
    """
    return try runAppleScript(script)
}
