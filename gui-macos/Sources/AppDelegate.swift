//
//  AppDelegate.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/AppDelegate.swift
//  Description: NSApplicationDelegate that keeps the menu-bar app alive after the last secondary window (chat, preferences, model downloader, log viewer, help) is closed. Without this, Cocoa's default behavior — once `NSApp.activate(ignoringOtherApps:)` has promoted the LSUIElement menu-bar app to a regular foreground app for window focus — is to terminate the process when the last window closes. The user then has to relaunch from /Applications. Returning `false` from `applicationShouldTerminateAfterLastWindowClosed` is the macOS-idiomatic fix.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        // Menu-bar app — never auto-terminate when secondary windows close.
        // The user quits explicitly via the "Quit" menu item.
        return false
    }
}
