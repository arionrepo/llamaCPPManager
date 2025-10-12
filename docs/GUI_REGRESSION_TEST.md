# GUI Regression Test Checklist

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/GUI_REGRESSION_TEST.md
**Description:** Comprehensive regression test checklist for GUI application
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-12

## Test Environment
- macOS Version:
- Build: Debug/Release
- Git Branch:
- Git Commit:

## Menu Bar Buttons

### Main Menu
- [ ] **Download Models** - Opens Model Downloader window at floating level
- [ ] **Refresh** - Refreshes status of all models
- [ ] **Open Config** - Opens config directory in Finder
- [ ] **Open CLI** - Opens Terminal with llamacpp-manager ready
- [ ] **Preferences...** (⌘,) - Opens Preferences window at floating level
- [ ] **Help** - Opens User Manual window at floating level
- [ ] **About** - Shows About dialog with version info and links
- [ ] **Quit** - Exits application cleanly

### Model Row Buttons (Per Model)
- [ ] **Start** - Starts the model server
- [ ] **Stop** - Stops the model server
- [ ] **Restart** - Restarts the model server
- [ ] **Chat** - Opens Chat window for model at floating level
- [ ] **Monitor** - Toggles monitoring for model
- [ ] **Logs** - Opens log file in Console.app

### Infrastructure Row Buttons (Per Container)
- [ ] **Start** - Starts infrastructure container
- [ ] **Stop** - Stops infrastructure container
- [ ] **Restart** - Restarts infrastructure container
- [ ] **Logs** - Shows infrastructure logs

### Batch Action Buttons
- [ ] **Start All Models** - Starts all configured models
- [ ] **Stop All Models** - Stops all running models

### Logging Control Buttons
- [ ] **Enable Logs / Disable Logs** - Toggles logging on/off
- [ ] **Timestamps: ON / OFF** - Toggles timestamp logging

## Model Downloader Window

### Window Behavior
- [ ] Window opens at floating level above all windows
- [ ] Window centers on screen
- [ ] Window can be closed
- [ ] Re-opening brings existing window to front

### Model List Buttons (Per Model)
- [ ] **Download** - Downloads model from Hugging Face
- [ ] **Info** - Shows model details in alert dialog

### Filter Controls
- [ ] **Size Filter** - Filters by model size (Small/Medium/Large)
- [ ] **Use Case Filter** - Filters by use case (Agentic/Coding/etc)

### Download Progress
- [ ] Progress bar shows during download
- [ ] Download can be cancelled
- [ ] Error messages display properly

## Chat Window

### Window Behavior
- [ ] Window opens at floating level above all windows
- [ ] Window centers on screen
- [ ] Window can be resized
- [ ] Window can be closed
- [ ] Multiple chat windows can open simultaneously
- [ ] Re-opening same model brings existing window to front

### Chat Buttons
- [ ] **Send** - Sends message to model
- [ ] **Clear** - Clears chat history
- [ ] **Dismiss** (for errors) - Dismisses error messages

### Chat Functionality
- [ ] Text input accepts user messages
- [ ] Messages display in chat area
- [ ] Model responses appear after sending
- [ ] Scroll view works correctly

## Preferences Window

### Window Behavior
- [ ] Window opens at floating level above all windows
- [ ] Window centers on screen
- [ ] Window can be closed
- [ ] Re-opening brings existing window to front
- [ ] Keyboard shortcut ⌘, works

### General Tab
- [ ] Refresh interval picker (values: 5s, 10s, 15s, 30s, 60s)
- [ ] Auto-start models toggle
- [ ] Show notifications toggle
- [ ] Reset to Defaults button

### Display Tab
- [ ] Show stopped models toggle
- [ ] Show infrastructure toggle
- [ ] View mode picker (Compact/Detailed)
- [ ] Show uptime toggle
- [ ] Show port numbers toggle
- [ ] Show health status toggle
- [ ] Show version info toggle

### Advanced Tab
- [ ] Config path display with Reveal button
- [ ] Models path display with Reveal button
- [ ] Logs path display with Reveal button
- [ ] Debug mode toggle
- [ ] Check for Updates button

### Preferences Persistence
- [ ] Settings save automatically
- [ ] Settings persist after app restart
- [ ] Reset to Defaults works correctly

## Help Window

### Window Behavior
- [ ] Window opens at floating level above all windows
- [ ] Window centers on screen
- [ ] Window can be resized
- [ ] Window can be scrolled
- [ ] Content displays properly formatted

## About Dialog

### Dialog Behavior
- [ ] Alert displays centered
- [ ] Shows correct version number
- [ ] Shows all features list
- [ ] Shows GitHub link
- [ ] Shows Release Notes link
- [ ] OK button closes dialog

## Test Results

### Test Date: ___________
### Tester: ___________
### Pass/Fail: ___________

### Issues Found:
1.
2.
3.

### Notes:
