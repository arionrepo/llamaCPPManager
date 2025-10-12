# GUI Preferences Panel - Requirements Document

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/GUI_PREFERENCES_REQUIREMENTS.md
**Description:** Requirements specification for the GUI Preferences panel feature
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-12

## 1. Overview

The GUI Preferences panel provides user-configurable settings for the llamaCPP Manager menu bar application, allowing users to customize behavior, performance, and display options without editing configuration files directly.

## 2. Business Requirements

### BR-1: User Configuration Access
Users must be able to access and modify application preferences through a dedicated UI panel.

**Acceptance Criteria:**
- Preferences accessible via menu bar (Help → Preferences or ⌘,)
- Changes persist between app restarts
- Changes take effect immediately or after confirmation

### BR-2: Status Refresh Control
Users must be able to control how frequently the GUI polls for status updates.

**Acceptance Criteria:**
- Configurable refresh interval (5s, 10s, 30s, 60s, manual)
- Current interval displayed in preferences
- Changes apply immediately without restart

### BR-3: Display Preferences
Users must be able to customize the GUI display and information density.

**Acceptance Criteria:**
- Show/hide stopped models option
- Show/hide infrastructure section option
- Compact/detailed view mode

### BR-4: Path Configuration
Users should be able to view (and optionally modify) key system paths.

**Acceptance Criteria:**
- Display CLI executable path
- Display config file location
- Display log directory location
- Option to reveal in Finder

## 3. Functional Requirements

### FR-1: Preferences Window
**Priority:** HIGH

The application must provide a dedicated Preferences window.

**Specifications:**
- Window title: "llamaCPP Manager Preferences"
- Size: 600x400 pixels (resizable)
- Layout: Tabbed interface or single panel with sections
- Tabs/Sections:
  - General
  - Display
  - Advanced

**Dependencies:** None

### FR-2: General Tab
**Priority:** HIGH

**Settings:**
1. **Refresh Interval**
   - Type: Dropdown/Picker
   - Options: 5s, 10s, 30s, 60s, Manual
   - Default: 10s
   - Validation: Must be positive integer

2. **Auto-start Models on Launch**
   - Type: Toggle
   - Default: OFF
   - Description: "Start autostart-enabled models when app launches"

3. **Show Notifications**
   - Type: Toggle
   - Default: ON
   - Description: "Show system notifications for model status changes"

### FR-3: Display Tab
**Priority:** MEDIUM

**Settings:**
1. **Show Stopped Models**
   - Type: Toggle
   - Default: ON
   - Effect: Filter model list to only show running models

2. **Show Infrastructure Section**
   - Type: Toggle
   - Default: ON
   - Effect: Hide/show infrastructure components section

3. **View Mode**
   - Type: Segmented control
   - Options: Compact, Detailed
   - Default: Detailed
   - Compact: Single line per model
   - Detailed: Multi-line with health indicators

4. **Status Indicators**
   - Type: Checkbox group
   - Options:
     - Show uptime
     - Show port numbers
     - Show health status
     - Show version info
   - Default: All ON

### FR-4: Advanced Tab
**Priority:** LOW

**Settings:**
1. **Paths (Read-only display with reveal buttons)**
   - CLI Executable: `/path/to/llamacpp-manager` [Reveal]
   - Config File: `~/.config/llamacpp/config.yaml` [Reveal]
   - Log Directory: `~/Library/Logs/llamaCPPManager/` [Reveal]

2. **Debug Mode**
   - Type: Toggle
   - Default: OFF
   - Effect: Enable verbose logging to console

3. **Check for Updates**
   - Type: Button
   - Action: Check GitHub for new releases

### FR-5: Data Persistence
**Priority:** HIGH

Preferences must be stored persistently using macOS UserDefaults.

**Storage Keys:**
- `refreshInterval` - Int (seconds)
- `autoStartModels` - Bool
- `showNotifications` - Bool
- `showStoppedModels` - Bool
- `showInfrastructure` - Bool
- `viewMode` - String ("compact" | "detailed")
- `debugMode` - Bool

**Default Values:**
```swift
refreshInterval: 10
autoStartModels: false
showNotifications: true
showStoppedModels: true
showInfrastructure: true
viewMode: "detailed"
debugMode: false
```

### FR-6: Apply/Reset Functionality
**Priority:** MEDIUM

**Buttons:**
- **Reset to Defaults** - Restore all settings to default values
- **Close** - Save and close preferences window

**Validation:**
- Warn user before resetting to defaults
- Auto-save on change (no explicit "Apply" needed)

## 4. Non-Functional Requirements

### NFR-1: Performance
- Preferences window must open in < 500ms
- Setting changes must apply in < 100ms
- No UI freeze when saving preferences

### NFR-2: Usability
- All settings must have clear labels and descriptions
- Tooltips for advanced settings
- Visual feedback when settings change
- Follow macOS Human Interface Guidelines

### NFR-3: Reliability
- Invalid settings must be rejected with error message
- Corrupted preferences must fall back to defaults
- No data loss on crash or force quit

### NFR-4: Compatibility
- Support macOS 13.0+ (same as main app)
- Preferences portable between machines
- Forward/backward compatible preference format

## 5. User Workflows

### Workflow 1: Change Refresh Interval
1. User clicks Help → Preferences (or ⌘,)
2. Preferences window opens on General tab
3. User selects new interval from dropdown
4. Setting auto-saves
5. Status refresh immediately uses new interval

### Workflow 2: Enable Compact View
1. User opens Preferences
2. Switches to Display tab
3. Toggles "View Mode" to Compact
4. UI immediately updates to compact layout
5. User closes Preferences

### Workflow 3: Reset All Settings
1. User opens Preferences
2. Clicks "Reset to Defaults" button
3. Warning dialog appears
4. User confirms reset
5. All settings revert to defaults
6. UI updates immediately

## 6. Technical Constraints

1. **Storage:** Must use UserDefaults (no external config files)
2. **UI Framework:** SwiftUI only (no AppKit)
3. **Dependencies:** No new external dependencies
4. **Size:** Preferences window < 1MB memory footprint

## 7. Future Enhancements (Out of Scope)

- Custom keyboard shortcuts
- Theme/appearance customization
- Model-specific preferences
- Import/export preferences
- Cloud sync of preferences
- Multi-profile support

## 8. Success Metrics

- 90% of users can find and change a setting without help
- Zero crashes related to preferences
- < 5% support requests about preferences
- Settings persist correctly 100% of the time

## 9. Dependencies

- Main app must read preferences on startup
- StatusViewModel must respect display preferences
- Refresh timer must update when interval changes

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| UserDefaults corruption | HIGH | Implement validation and fallback to defaults |
| Performance degradation with frequent saves | MEDIUM | Debounce save operations |
| Breaking changes in future | MEDIUM | Version preference format |
| User confusion with too many options | LOW | Use progressive disclosure, hide advanced settings |

## 11. Open Questions

1. Should refresh interval affect CLI polling or just GUI updates?
2. Do we need per-model notification preferences?
3. Should we support keyboard shortcuts customization in v1?

## 12. References

- [macOS Human Interface Guidelines - Preferences](https://developer.apple.com/design/human-interface-guidelines/preferences)
- [SwiftUI UserDefaults Best Practices](https://developer.apple.com/documentation/foundation/userdefaults)
- Main app requirements: `docs/requirements.md`
