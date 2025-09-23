# GUI Testing Guide

Complete guide to testing the llamaCPP Manager SwiftUI menu bar GUI.

## Quick Start

### Option 1: Command Line Testing
```bash
# From project root
cd gui-macos

# Set up environment
export PATH="../.venv/bin:$PATH"
export LLAMACPP_MANAGER_CONFIG_DIR=~/Testing/llamacpp-config
export LLAMACPP_MANAGER_LOG_DIR=~/Testing/llamacpp-logs

# Run GUI
swift run llamacpp-gui
```

### Option 2: Xcode Testing (Recommended)
```bash
# Open in Xcode
open gui-macos/Package.swift

# In Xcode:
# 1. Select "llamacpp-gui" scheme
# 2. Click Run button
# 3. Look for "llamaCPP" icon in menu bar
```

## Prerequisites

### 1. Build and Test
```bash
cd gui-macos

# Build (should succeed)
swift build

# Run tests (should pass)
swift test
```
**Expected:** ✅ Build succeeds, ✅ 1 test passes (JSON parsing)

### 2. Set Up CLI Configuration
```bash
# Initialize config (required for GUI)
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs init

# Add a test model
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config \
  config add test-model \
  ~/path/to/your/model.gguf \
  --port 8081
```

### 3. Environment Variables
The GUI needs these to find CLI and config:
```bash
export LLAMACPP_MANAGER_CONFIG_DIR=~/Testing/llamacpp-config
export LLAMACPP_MANAGER_LOG_DIR=~/Testing/llamacpp-logs
export PATH="/path/to/project/.venv/bin:$PATH"
```

## GUI Testing Steps

### Step 1: Launch GUI
```bash
cd gui-macos
export PATH="../.venv/bin:$PATH"
swift run llamacpp-gui
```

**Expected Results:**
- ✅ No build errors
- ✅ App launches silently (no console output after "Build complete")
- ✅ "llamaCPP" icon appears in menu bar (look for brain icon 🧠)

### Step 2: Basic Menu Functionality
1. **Click menu bar icon** (brain icon)
2. **Verify menu opens** with options:
   - Model list (or "No models configured")
   - "Ensure Running" button
   - "Refresh" button
   - "Open Config" button
   - "Quit" button

**Expected Results:**
- ✅ Menu opens when clicked
- ✅ All buttons visible
- ✅ No crash or errors

### Step 3: Test With No Models
If no models configured, menu should show:
```
No models configured
[Ensure Running]
───────────────
[Refresh]
[Open Config]
───────────────
[Quit]
```

**Test Actions:**
- ✅ Click "Refresh" (should work, no errors)
- ✅ Click "Open Config" (should open config directory)
- ✅ Click "Ensure Running" (should work, no models to start)

### Step 4: Test With Configured Models
After adding models with CLI, menu should show:
```
🟢 test-model    127.0.0.1:8081    15 ms
[Start] [Stop] [Restart] [Chat] [Tail Logs]
───────────────────────────────────────────
[Ensure Running]
───────────────
[Refresh]
[Open Config]
───────────────
[Quit]
```

**Status Indicators:**
- 🟢 Green = Model running and responding
- 🔴 Red = Model stopped or not responding
- Port and latency shown if running

### Step 5: Test Model Control Buttons

**With model stopped:**
- ✅ Click "Start" → should start model, dot turns green
- ✅ "Chat" button should appear when running
- ✅ Latency should show (e.g., "15 ms")

**With model running:**
- ✅ Click "Stop" → should stop model, dot turns red
- ✅ Click "Restart" → should restart model
- ✅ "Chat" button should disappear when stopped

**Other buttons:**
- ✅ "Tail Logs" → should open Terminal with log tail
- ✅ "Ensure Running" → should start any autostart models

### Step 6: Test Real-Time Updates
The GUI polls status every few seconds:

1. **Start model via CLI** while GUI open:
   ```bash
   .venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config start test-model
   ```

2. **Stop model via CLI** while GUI open:
   ```bash
   .venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config stop test-model
   ```

**Expected Results:**
- ✅ GUI updates automatically (status dot changes color)
- ✅ Latency appears/disappears appropriately
- ✅ Buttons update (Chat appears/disappears)

### Step 7: Test Error Handling

**No CLI available:**
```bash
# Temporarily break CLI access
export PATH="/usr/bin:/bin"
swift run llamacpp-gui
```
**Expected:** GUI should handle CLI not found gracefully

**Invalid config:**
- Try with non-existent config directory
- GUI should show "No models configured" without crashing

## Advanced GUI Testing

### Multi-Model Testing
1. Add multiple models:
   ```bash
   .venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config config add model-1 ~/path/model1.gguf --port 8081
   .venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config config add model-2 ~/path/model2.gguf --port 8082
   ```

2. **Expected GUI behavior:**
   - Shows both models in list
   - Each has independent status indicators
   - Each has own control buttons
   - Refresh updates all statuses

### Stress Testing
1. **Rapid clicking:** Click buttons rapidly (shouldn't crash)
2. **Menu open/close:** Open and close menu rapidly
3. **Model start/stop cycles:** Start and stop models repeatedly
4. **Long-running test:** Leave GUI open for extended period

### Integration Testing
**Test Chat Functionality:**
1. Start a model via GUI
2. Click "Chat" button
3. Should open chat interface (Terminal or separate window)

**Test Log Viewing:**
1. Click "Tail Logs" for running model
2. Should open Terminal with `tail -f` of model logs
3. Generate some activity, verify logs update

## GUI Feature Matrix

| Feature | Status | Test Method |
|---------|--------|-------------|
| Menu bar icon | ✅ | Visual check |
| Menu opens/closes | ✅ | Click test |
| Model list display | ✅ | Add models, check display |
| Status indicators (🟢🔴) | ✅ | Start/stop models |
| Start button | ✅ | Click, verify model starts |
| Stop button | ✅ | Click, verify model stops |
| Restart button | ✅ | Click, verify restart |
| Chat button | ✅ | Click when model running |
| Tail Logs button | ✅ | Click, verify Terminal opens |
| Ensure Running | ✅ | Set autostart, test |
| Refresh | ✅ | Click, verify status updates |
| Open Config | ✅ | Click, verify Finder opens |
| Real-time polling | ✅ | Change model state via CLI |
| Quit | ✅ | Click, verify app quits |

## Regression Testing Checklist

Run this checklist for any GUI changes:

- [ ] ✅ GUI builds without warnings
- [ ] ✅ All tests pass (`swift test`)
- [ ] ✅ App launches and menu bar icon appears
- [ ] ✅ Menu opens and shows correct content
- [ ] ✅ "No models" state displays correctly
- [ ] ✅ Model list displays when models configured
- [ ] ✅ Status indicators work (🟢 running, 🔴 stopped)
- [ ] ✅ Start button starts models
- [ ] ✅ Stop button stops models
- [ ] ✅ Restart button works
- [ ] ✅ Chat button appears only when running
- [ ] ✅ Tail Logs opens Terminal
- [ ] ✅ Refresh updates status
- [ ] ✅ Open Config opens directory
- [ ] ✅ Ensure Running starts autostart models
- [ ] ✅ Real-time polling updates GUI
- [ ] ✅ Quit button exits app
- [ ] ✅ No crashes during normal operation
- [ ] ✅ Handles CLI errors gracefully
- [ ] ✅ Multiple models display correctly

## Troubleshooting

### GUI Won't Start
```bash
# Check build errors
cd gui-macos
swift build

# Check for CLI in path
which llamacpp-manager
echo $PATH
```

### Menu Bar Icon Missing
- Check Console.app for errors
- Verify macOS version (requires 13.0+)
- Try running from Xcode for better error messages

### "No models configured" Always Shows
```bash
# Verify CLI works
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config config list

# Check environment variables
echo $LLAMACPP_MANAGER_CONFIG_DIR
echo $LLAMACPP_MANAGER_LOG_DIR
```

### Buttons Don't Work
- Check Console.app for CLI execution errors
- Verify CLI is accessible: `which llamacpp-manager`
- Test CLI commands manually

### Status Not Updating
- Verify models are actually starting/stopping
- Check network connectivity to model ports
- Look for CLI timeout errors in Console

## Running GUI in Xcode (Recommended)

1. **Open Package:** `open gui-macos/Package.swift`

2. **Set Environment Variables** (in Xcode):
   - Product → Scheme → Edit Scheme
   - Arguments tab → Environment Variables
   - Add:
     - `LLAMACPP_MANAGER_CONFIG_DIR`: `~/Testing/llamacpp-config`
     - `LLAMACPP_MANAGER_LOG_DIR`: `~/Testing/llamacpp-logs`
     - `PATH`: `/Users/you/path/to/project/.venv/bin:$PATH`

3. **Run** with ▶️ button

4. **Debug** with Console output visible

This gives better error reporting and debugging capabilities than command-line execution.