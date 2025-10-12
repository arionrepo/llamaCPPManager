# GUI Preferences Panel - Low-Level Design

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/GUI_PREFERENCES_DESIGN.md
**Description:** Low-level technical design for GUI Preferences panel implementation
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-12

## 1. Architecture Overview

### 1.1 Component Structure

```
┌─────────────────────────────────────┐
│      PreferencesWindow.swift        │
│  (SwiftUI Window Scene)             │
└──────────────┬──────────────────────┘
               │
               ├── PreferencesView.swift (Main Container)
               │   │
               │   ├── GeneralPreferencesView.swift
               │   ├── DisplayPreferencesView.swift
               │   └── AdvancedPreferencesView.swift
               │
               └── PreferencesManager.swift
                   │
                   ├── UserDefaults (Storage)
                   └── Published Properties (State)
```

### 1.2 Data Flow

```
User Action → PreferencesView → PreferencesManager → UserDefaults
                                         ↓
                                  @Published Property
                                         ↓
                              StatusViewModel.refresh()
```

## 2. Class Definitions

### 2.1 PreferencesManager (ObservableObject)

**Purpose:** Centralized preferences state management and persistence

**File:** `gui-macos/Sources/PreferencesManager.swift`

```swift
import Foundation
import Combine

final class PreferencesManager: ObservableObject {
    static let shared = PreferencesManager()

    private let defaults = UserDefaults.standard
    private let prefix = "com.llamacpp.manager."

    // MARK: - General Settings

    @Published var refreshInterval: Int {
        didSet { save(refreshInterval, forKey: "refreshInterval") }
    }

    @Published var autoStartModels: Bool {
        didSet { save(autoStartModels, forKey: "autoStartModels") }
    }

    @Published var showNotifications: Bool {
        didSet { save(showNotifications, forKey: "showNotifications") }
    }

    // MARK: - Display Settings

    @Published var showStoppedModels: Bool {
        didSet { save(showStoppedModels, forKey: "showStoppedModels") }
    }

    @Published var showInfrastructure: Bool {
        didSet { save(showInfrastructure, forKey: "showInfrastructure") }
    }

    @Published var viewMode: ViewMode {
        didSet { save(viewMode.rawValue, forKey: "viewMode") }
    }

    @Published var showUptime: Bool {
        didSet { save(showUptime, forKey: "showUptime") }
    }

    @Published var showPortNumbers: Bool {
        didSet { save(showPortNumbers, forKey: "showPortNumbers") }
    }

    @Published var showHealthStatus: Bool {
        didSet { save(showHealthStatus, forKey: "showHealthStatus") }
    }

    @Published var showVersionInfo: Bool {
        didSet { save(showVersionInfo, forKey: "showVersionInfo") }
    }

    // MARK: - Advanced Settings

    @Published var debugMode: Bool {
        didSet { save(debugMode, forKey: "debugMode") }
    }

    // MARK: - Computed Properties

    var cliExecutablePath: String {
        // Detected at runtime
        return CLIService.shared.executablePath ?? "Not found"
    }

    var configFilePath: String {
        return "~/.config/llamacpp/config.yaml"
    }

    var logDirectoryPath: String {
        return "~/Library/Logs/llamaCPPManager/"
    }

    // MARK: - Initialization

    private init() {
        // Load from UserDefaults or use defaults
        self.refreshInterval = defaults.integer(forKey: prefKey("refreshInterval"))
        if self.refreshInterval == 0 { self.refreshInterval = 10 }

        self.autoStartModels = defaults.bool(forKey: prefKey("autoStartModels"))
        self.showNotifications = defaults.object(forKey: prefKey("showNotifications")) as? Bool ?? true
        self.showStoppedModels = defaults.object(forKey: prefKey("showStoppedModels")) as? Bool ?? true
        self.showInfrastructure = defaults.object(forKey: prefKey("showInfrastructure")) as? Bool ?? true

        let viewModeString = defaults.string(forKey: prefKey("viewMode")) ?? "detailed"
        self.viewMode = ViewMode(rawValue: viewModeString) ?? .detailed

        self.showUptime = defaults.object(forKey: prefKey("showUptime")) as? Bool ?? true
        self.showPortNumbers = defaults.object(forKey: prefKey("showPortNumbers")) as? Bool ?? true
        self.showHealthStatus = defaults.object(forKey: prefKey("showHealthStatus")) as? Bool ?? true
        self.showVersionInfo = defaults.object(forKey: prefKey("showVersionInfo")) as? Bool ?? true
        self.debugMode = defaults.bool(forKey: prefKey("debugMode"))
    }

    // MARK: - Methods

    func resetToDefaults() {
        refreshInterval = 10
        autoStartModels = false
        showNotifications = true
        showStoppedModels = true
        showInfrastructure = true
        viewMode = .detailed
        showUptime = true
        showPortNumbers = true
        showHealthStatus = true
        showVersionInfo = true
        debugMode = false
    }

    private func prefKey(_ key: String) -> String {
        return prefix + key
    }

    private func save<T>(_ value: T, forKey key: String) {
        defaults.set(value, forKey: prefKey(key))
    }
}

enum ViewMode: String, CaseIterable {
    case compact = "compact"
    case detailed = "detailed"

    var displayName: String {
        rawValue.capitalized
    }
}
```

### 2.2 PreferencesView (Main Container)

**File:** `gui-macos/Sources/PreferencesView.swift`

```swift
import SwiftUI

struct PreferencesView: View {
    @ObservedObject var preferences = PreferencesManager.shared
    @State private var selectedTab: PreferencesTab = .general

    var body: some View {
        TabView(selection: $selectedTab) {
            GeneralPreferencesView()
                .tabItem {
                    Label("General", systemImage: "gear")
                }
                .tag(PreferencesTab.general)

            DisplayPreferencesView()
                .tabItem {
                    Label("Display", systemImage: "eye")
                }
                .tag(PreferencesTab.display)

            AdvancedPreferencesView()
                .tabItem {
                    Label("Advanced", systemImage: "wrench.and.screwdriver")
                }
                .tag(PreferencesTab.advanced)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

enum PreferencesTab {
    case general
    case display
    case advanced
}
```

### 2.3 GeneralPreferencesView

**File:** `gui-macos/Sources/GeneralPreferencesView.swift`

```swift
import SwiftUI

struct GeneralPreferencesView: View {
    @ObservedObject var preferences = PreferencesManager.shared

    var body: some View {
        Form {
            Section(header: Text("Status Updates")) {
                Picker("Refresh Interval:", selection: $preferences.refreshInterval) {
                    Text("5 seconds").tag(5)
                    Text("10 seconds").tag(10)
                    Text("30 seconds").tag(30)
                    Text("1 minute").tag(60)
                    Text("Manual").tag(0)
                }
                .pickerStyle(.menu)

                Text("Controls how often the app checks model status")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Section(header: Text("Behavior")) {
                Toggle("Auto-start models on launch", isOn: $preferences.autoStartModels)
                    .help("Start models marked as 'autostart' when the app launches")

                Toggle("Show notifications", isOn: $preferences.showNotifications)
                    .help("Display system notifications for status changes")
            }

            Spacer()

            HStack {
                Spacer()
                Button("Reset to Defaults") {
                    confirmReset()
                }
                .buttonStyle(.bordered)
            }
        }
        .formStyle(.grouped)
    }

    private func confirmReset() {
        let alert = NSAlert()
        alert.messageText = "Reset All Preferences?"
        alert.informativeText = "This will restore all settings to their default values."
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Reset")
        alert.addButton(withTitle: "Cancel")

        if alert.runModal() == .alertFirstButtonReturn {
            preferences.resetToDefaults()
        }
    }
}
```

### 2.4 DisplayPreferencesView

**File:** `gui-macos/Sources/DisplayPreferencesView.swift`

```swift
import SwiftUI

struct DisplayPreferencesView: View {
    @ObservedObject var preferences = PreferencesManager.shared

    var body: some View {
        Form {
            Section(header: Text("Visibility")) {
                Toggle("Show stopped models", isOn: $preferences.showStoppedModels)
                Toggle("Show infrastructure section", isOn: $preferences.showInfrastructure)
            }

            Section(header: Text("View Mode")) {
                Picker("Layout:", selection: $preferences.viewMode) {
                    ForEach(ViewMode.allCases, id: \.self) { mode in
                        Text(mode.displayName).tag(mode)
                    }
                }
                .pickerStyle(.segmented)

                Text(preferences.viewMode == .compact
                    ? "Single line per model"
                    : "Multi-line with health indicators")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Section(header: Text("Status Indicators")) {
                Toggle("Show uptime", isOn: $preferences.showUptime)
                Toggle("Show port numbers", isOn: $preferences.showPortNumbers)
                Toggle("Show health status", isOn: $preferences.showHealthStatus)
                Toggle("Show version info", isOn: $preferences.showVersionInfo)
            }
        }
        .formStyle(.grouped)
    }
}
```

### 2.5 AdvancedPreferencesView

**File:** `gui-macos/Sources/AdvancedPreferencesView.swift`

```swift
import SwiftUI

struct AdvancedPreferencesView: View {
    @ObservedObject var preferences = PreferencesManager.shared

    var body: some View {
        Form {
            Section(header: Text("System Paths")) {
                PathRow(label: "CLI Executable:", path: preferences.cliExecutablePath)
                PathRow(label: "Config File:", path: preferences.configFilePath)
                PathRow(label: "Log Directory:", path: preferences.logDirectoryPath)
            }

            Section(header: Text("Debugging")) {
                Toggle("Debug mode", isOn: $preferences.debugMode)
                    .help("Enable verbose logging to Console.app")
            }

            Section(header: Text("Updates")) {
                Button("Check for Updates") {
                    checkForUpdates()
                }
                .buttonStyle(.bordered)
            }
        }
        .formStyle(.grouped)
    }

    private func checkForUpdates() {
        // Open GitHub releases page
        if let url = URL(string: "https://github.com/arionrepo/llamaCPPManager/releases") {
            NSWorkspace.shared.open(url)
        }
    }
}

struct PathRow: View {
    let label: String
    let path: String

    var body: some View {
        HStack {
            Text(label)
                .frame(width: 120, alignment: .trailing)
            Text(path)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
                .foregroundColor(.secondary)
            Spacer()
            Button("Reveal") {
                revealInFinder()
            }
            .buttonStyle(.borderless)
        }
    }

    private func revealInFinder() {
        let expandedPath = NSString(string: path).expandingTildeInPath
        let url = URL(fileURLWithPath: expandedPath)
        NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: url.deletingLastPathComponent().path)
    }
}
```

## 3. Integration with Main App

### 3.1 Update StatusViewModel

**Changes to `StatusViewModel` in `App.swift`:**

```swift
class StatusViewModel: ObservableObject {
    // ... existing code ...

    private var refreshTimer: Timer?
    @ObservedObject private var preferences = PreferencesManager.shared

    init() {
        // ... existing init code ...

        // Setup timer with preference
        setupRefreshTimer()

        // Observe preference changes
        preferences.$refreshInterval
            .sink { [weak self] _ in
                self?.setupRefreshTimer()
            }
            .store(in: &cancellables)
    }

    private func setupRefreshTimer() {
        refreshTimer?.invalidate()

        guard preferences.refreshInterval > 0 else { return }

        refreshTimer = Timer.scheduledTimer(withTimeInterval: TimeInterval(preferences.refreshInterval), repeats: true) { [weak self] _ in
            self?.refresh()
        }
    }

    // Filter models based on preferences
    var visibleRows: [ModelRow] {
        if preferences.showStoppedModels {
            return rows
        } else {
            return rows.filter { $0.up }
        }
    }
}
```

### 3.2 Add Preferences Menu Item

**Update `MenuBarExtra` in `App.swift`:**

```swift
MenuBarExtra("llamaCPP", systemImage: "brain.head.profile") {
    // ... existing content ...

    Divider()

    Button("Preferences...") {
        openPreferences()
    }
    .keyboardShortcut(",", modifiers: .command)

    // ... rest of menu ...
}

@State private var preferencesWindow: NSWindow?

func openPreferences() {
    if let window = preferencesWindow {
        window.makeKeyAndOrderFront(nil)
        return
    }

    let window = NSWindow(
        contentRect: NSRect(x: 0, y: 0, width: 600, height: 400),
        styleMask: [.titled, .closable],
        backing: .buffered,
        defer: false
    )
    window.title = "llamaCPP Manager Preferences"
    window.contentView = NSHostingView(rootView: PreferencesView())
    window.center()
    window.makeKeyAndOrderFront(nil)

    preferencesWindow = window
}
```

## 4. File Structure

```
gui-macos/Sources/
├── App.swift (updated)
├── PreferencesManager.swift (new)
├── PreferencesView.swift (new)
├── GeneralPreferencesView.swift (new)
├── DisplayPreferencesView.swift (new)
└── AdvancedPreferencesView.swift (new)
```

## 5. Implementation Phases

### Phase 1: Core Infrastructure (30 min)
- [ ] Create PreferencesManager.swift
- [ ] Implement UserDefaults persistence
- [ ] Add unit tests for PreferencesManager

### Phase 2: UI Components (45 min)
- [ ] Create PreferencesView.swift (tab container)
- [ ] Implement GeneralPreferencesView
- [ ] Implement DisplayPreferencesView
- [ ] Implement AdvancedPreferencesView

### Phase 3: Integration (30 min)
- [ ] Add preferences menu item
- [ ] Wire up StatusViewModel to use preferences
- [ ] Update model filtering logic
- [ ] Update refresh timer logic

### Phase 4: Testing (30 min)
- [ ] Test all preference changes
- [ ] Test persistence (quit/relaunch)
- [ ] Test reset to defaults
- [ ] Test path reveal functionality

**Total Estimated Time:** 2-3 hours

## 6. Testing Strategy

### Unit Tests
```swift
func testPreferencesDefaults() {
    let prefs = PreferencesManager()
    XCTAssertEqual(prefs.refreshInterval, 10)
    XCTAssertFalse(prefs.autoStartModels)
    XCTAssertTrue(prefs.showNotifications)
}

func testPreferencesPersistence() {
    let prefs = PreferencesManager.shared
    prefs.refreshInterval = 30

    // Simulate app restart
    let newPrefs = PreferencesManager()
    XCTAssertEqual(newPrefs.refreshInterval, 30)
}
```

### Manual Test Cases
1. Open preferences → Change refresh interval → Verify timer updates
2. Toggle show stopped models → Verify model list filters
3. Reset to defaults → Verify all settings revert
4. Reveal paths → Verify Finder opens correct location
5. Quit app → Relaunch → Verify settings persisted

## 7. Security & Privacy

- UserDefaults stored in app sandbox (secure)
- No sensitive data stored in preferences
- Paths are read-only display (no modification)
- No network access from preferences

## 8. Performance Considerations

- Lazy loading of preference views
- Debounce UserDefaults saves (built into @Published)
- No expensive operations on main thread
- Window reuse (don't create new window each time)

## 9. Accessibility

- All controls keyboard accessible
- VoiceOver labels on all inputs
- Proper tab order
- Color-blind friendly (no color-only indicators)

## 10. Error Handling

```swift
// Handle corrupted preferences
private func loadSafely<T>(_ key: String, default: T) -> T {
    guard let value = defaults.object(forKey: prefKey(key)) as? T else {
        return `default`
    }
    return value
}
```

## 11. Future Enhancements

- [ ] iCloud sync of preferences
- [ ] Import/export preferences as JSON
- [ ] Per-model notification settings
- [ ] Custom keyboard shortcuts
- [ ] Appearance (light/dark/auto)

## 12. References

- Requirements: `docs/GUI_PREFERENCES_REQUIREMENTS.md`
- SwiftUI Forms: https://developer.apple.com/documentation/swiftui/form
- UserDefaults: https://developer.apple.com/documentation/foundation/userdefaults
