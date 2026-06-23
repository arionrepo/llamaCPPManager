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
        let policy = sender.activationPolicy().rawValue
        LifecycleLog.log("ui.app.last_window_closed",
                         ["activation_policy": policy, "returning": false])
        return false
    }

    func applicationWillTerminate(_ notification: Notification) {
        let policy = NSApp.activationPolicy().rawValue
        LifecycleLog.log("ui.app.will_terminate",
                         ["activation_policy": policy,
                          "windows_open": NSApp.windows.filter { $0.isVisible }.count])
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        LifecycleLog.log("ui.app.did_finish_launching",
                         ["activation_policy": NSApp.activationPolicy().rawValue])
        // Install a minimal main menu so standard keyboard shortcuts route correctly
        // for secondary windows (chat, preferences, model downloader, help, log
        // viewer). Without this, MenuBarExtra apps have NSApp.mainMenu == nil, which
        // means Cocoa's standard keyboard routing (Cmd-W -> performClose:,
        // Cmd-Q -> terminate:, Cmd-M -> performMiniaturize:) has no menu item to
        // bind to and silently does nothing.
        installMainMenu()
    }

    private func installMainMenu() {
        let mainMenu = NSMenu()

        // --- Application menu (first menu item; macOS picks up its name from the bundle) ---
        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)

        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About llamaCPP Manager",
                        action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)),
                        keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Hide llamaCPP Manager",
                        action: #selector(NSApplication.hide(_:)),
                        keyEquivalent: "h")
        let hideOthers = appMenu.addItem(withTitle: "Hide Others",
                                          action: #selector(NSApplication.hideOtherApplications(_:)),
                                          keyEquivalent: "h")
        hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(withTitle: "Show All",
                        action: #selector(NSApplication.unhideAllApplications(_:)),
                        keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit llamaCPP Manager",
                        action: #selector(NSApplication.terminate(_:)),
                        keyEquivalent: "q")
        appMenuItem.submenu = appMenu

        // --- File menu (gives Cmd-W its target) ---
        let fileMenuItem = NSMenuItem()
        mainMenu.addItem(fileMenuItem)

        let fileMenu = NSMenu(title: "File")
        // `performClose:` is the standard Cocoa selector that respects
        // window delegates' windowShouldClose / windowWillClose hooks, so our
        // chat/preferences/downloader cleanup still fires when the user hits Cmd-W.
        fileMenu.addItem(withTitle: "Close Window",
                         action: #selector(NSWindow.performClose(_:)),
                         keyEquivalent: "w")
        fileMenuItem.submenu = fileMenu

        // --- Edit menu (Cmd-C / Cmd-V / Cmd-X / Cmd-A on text inputs) ---
        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)

        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(withTitle: "Undo",
                         action: Selector(("undo:")),
                         keyEquivalent: "z")
        let redo = editMenu.addItem(withTitle: "Redo",
                                     action: Selector(("redo:")),
                                     keyEquivalent: "z")
        redo.keyEquivalentModifierMask = [.command, .shift]
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "Cut",
                         action: #selector(NSText.cut(_:)),
                         keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy",
                         action: #selector(NSText.copy(_:)),
                         keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste",
                         action: #selector(NSText.paste(_:)),
                         keyEquivalent: "v")
        editMenu.addItem(withTitle: "Select All",
                         action: #selector(NSText.selectAll(_:)),
                         keyEquivalent: "a")
        editMenuItem.submenu = editMenu

        // --- Window menu (gives Cmd-M its target) ---
        let windowMenuItem = NSMenuItem()
        mainMenu.addItem(windowMenuItem)

        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Minimize",
                           action: #selector(NSWindow.performMiniaturize(_:)),
                           keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Zoom",
                           action: #selector(NSWindow.performZoom(_:)),
                           keyEquivalent: "")
        windowMenuItem.submenu = windowMenu
        NSApplication.shared.windowsMenu = windowMenu

        NSApplication.shared.mainMenu = mainMenu
    }
}
