# GUI Testing Guide
**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/gui-testing-guide.md
**Description:** Guide for testing the updated GUI features including Stop All Models, Help Window, and Model Downloader
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-10

## How to Run the GUI

From the project root directory:

```bash
cd gui-macos
swift build
swift run llamacpp-gui
```

## New Features to Test

### 1. Stop All Models Button

**Location:** Main menu, below the model list, before logging section

**Expected UI:**
```
Models
────────────────────────────────────────
[List of models here...]
────────────────────────────────────────
[Ensure Running]  [Stop All Models]
────────────────────────────────────────
```

**What to Test:**
1. Click the menu bar icon (brain.head.profile)
2. Scroll down past the model list
3. You should see two buttons side by side:
   - "Ensure Running" (default color)
   - "Stop All Models" (red color)
4. Hover over "Stop All Models" to see tooltip: "Stop all running models (infrastructure components continue running)"

**Expected Behavior:**
- Clicking "Stop All Models" should stop all running models
- Infrastructure components (cloudflared, llm_controller) should remain running
- Models with autostart=true may restart due to monitoring daemon

**Verification:**
```bash
# Before clicking
llamacpp-manager status | grep "up.*True"

# After clicking Stop All Models
llamacpp-manager status | grep "up.*True"
# Should show fewer models running

# Verify infrastructure still running
llamacpp-manager infra status
# Should show cloudflared and llm_controller still running
```

---

### 2. Help Window

**Location:** Main menu, near bottom before "About"

**Expected UI:**
```
────────────────────────────────────────
[Download Models]
────────────────────────────────────────
[Refresh]
[Open Config]
[Open CLI]
────────────────────────────────────────
[Help]
[About]
────────────────────────────────────────
[Quit]
```

**What to Test:**
1. Click "Help" button
2. A new window should open (900x700 pixels)
3. Window title: "llamaCPP Manager - User Manual"
4. Should display comprehensive manual with 14 sections

**Expected Content:**
- Quick Start
- GUI Controls (status indicators, model controls, global actions)
- Model Management (adding models, starting models)
- Model Downloader (downloading pre-configured models)
- Model Groups (exclusive groups explained)
- Infrastructure Management
- Monitoring & Auto-Restart
- CLI Commands (complete reference)
- Configuration Files
- Troubleshooting
- Advanced Features
- Keyboard Shortcuts
- Tips & Best Practices
- What's New

**Verification:**
- Window should be scrollable
- Text should be readable (13pt system font)
- Window should remain open when you interact with main menu
- Can close window with red X button
- Help window can be reopened after closing

---

### 3. Model Downloader Window

**Location:** Main menu, top of actions section

**Expected UI:**
```
────────────────────────────────────────
[Download Models]  <-- NEW!
────────────────────────────────────────
[Refresh]
[Open Config]
[Open CLI]
```

**What to Test:**
1. Click "Download Models" button
2. A new window should open (750x650 pixels)
3. Window title: "Model Downloader"

**Expected Window Layout:**
```
┌─────────────────────────────────────────────┐
│ Model Downloader                       [✕]  │
├─────────────────────────────────────────────┤
│ Size: [All Sizes ▾]  Use Case: [All... ▾]  │
│                            7 models         │
├─────────────────────────────────────────────┤
│ [Loading indicator or model cards here]     │
│                                             │
│ 🤖 qwen-coder-7b                            │
│ Best for tool calling and structured outputs│
│ 💾 7.54 GB  🧠 ~12 GB RAM                   │
│ Use: Agentic workflows, tool calling...    │
│ [✓ Downloaded]  [Configure] [Re-download]  │
│                                             │
│ 🤖 hermes-3-llama-8b                        │
│ Specifically trained for agentic use        │
│ 💾 7.95 GB  🧠 ~13 GB RAM                   │
│ Use: Multi-agent systems...                │
│ [Download]  [Info]                          │
└─────────────────────────────────────────────┘
```

**What to Test:**

#### A. Window Opens
- Click "Download Models"
- Window opens centered on screen
- Shows "Loading available models..." initially

#### B. Filter Functionality
- **Size Filter Dropdown:**
  - All Sizes (default)
  - Small (<10GB)
  - Medium (10-20GB)
  - Large (>20GB)
- **Use Case Filter Dropdown:**
  - All Use Cases (default)
  - Agentic AI
  - Coding
  - Compliance
  - General

- Test filtering by size - model list should update
- Test filtering by use case - model list should update
- Counters should show "X models" based on filters

#### C. Model Cards
Each model card should show:
- Model icon (brain.head.profile)
- Model name
- Description
- Size (GB)
- RAM requirement (GB)
- Use case description
- Status badge (Downloaded vs Available)
- Action buttons

#### D. Downloaded vs Available Models
- **Downloaded models** show:
  - Green checkmark icon
  - "Downloaded" badge
  - [Configure] button (primary blue)
  - [Re-download] button (bordered)

- **Available models** show:
  - No badge
  - [Download] button (primary blue)
  - [Info] button (bordered)

#### E. Download Workflow
1. Find a model that's not downloaded
2. Click [Download] button
3. Progress indicator should appear (currently placeholder)
4. After download completes:
   - Status changes to "Downloaded"
   - Buttons change to [Configure] and [Re-download]

#### F. Configuration
1. Find a downloaded model
2. Click [Configure] button
3. Model should be added to config (CLI command runs)

#### G. Multiple Windows
- Open Model Downloader
- Try clicking "Download Models" again
- Should bring existing window to front (not open duplicate)
- Close window and reopen - should work correctly

---

## Troubleshooting

### "Stop All Models" button not visible

**Solution:**
```bash
cd gui-macos
rm -rf .build
swift build
swift run llamacpp-gui
```

### Help window shows only basic text

This is expected - the fallback help is embedded in the code. To use the full user-manual.md:
1. Copy docs/user-manual.md to gui-macos/Resources/
2. Update Package.swift to include resources (future enhancement)

### Model Downloader shows "Loading..." forever

**Check CLI availability:**
```bash
llamacpp-manager models list --available --json
```

Should return JSON array of models. If this fails, the GUI will show loading forever.

**Verify Python venv is activated:**
```bash
which llamacpp-manager
# Should show path to venv or system install
```

### No models appear in downloader

**Check downloader.py:**
```bash
llamacpp-manager models list --available
```

Should show list of available models. If empty, check src/llamacpp_manager/models/downloader.py

---

## Expected Model List (Model Downloader)

**Agentic & Tool-Calling Models:**
1. qwen-coder-7b (7.54 GB)
2. hermes-3-llama-8b (7.95 GB)
3. llama-3.1-8b (7.95 GB)
4. qwen-2.5-14b (16 GB)

**Traditional Coding Models:**
5. qwen-coder-32b (35 GB)
6. deepseek-coder-6.7b (7 GB)
7. deepseek-coder-33b (35 GB)

---

## Verification Commands

### Check all models status
```bash
llamacpp-manager status
```

### Stop all models (CLI equivalent of GUI button)
```bash
llamacpp-manager stop all
```

### List available models for download
```bash
llamacpp-manager models list --available
```

### Check infrastructure is still running after stop all
```bash
llamacpp-manager infra status
```

---

## Success Criteria

✅ **Stop All Models:**
- Button visible in main menu
- Red color indicates destructive action
- Tooltip explains behavior
- Stops models but not infrastructure

✅ **Help Window:**
- Opens in separate 900x700 window
- Shows comprehensive 14-section manual
- Non-blocking (can interact with main menu)
- Window can be closed and reopened

✅ **Model Downloader:**
- Opens in separate 750x650 window
- Shows 7 available models
- Filters work correctly
- Downloaded status accurate
- Download and Configure buttons functional
- Only one window instance at a time

---

## Next Steps After Testing

Once you've verified these features work:

1. **Container/VLLM Management** - Add UI for Docker/containerized deployments
2. **MCP Server Enhancements** - Add tools for model downloader and infrastructure
3. **Architecture Review** - Review overall system design and identify improvements

---

## Build Commands Reference

```bash
# Clean rebuild
cd gui-macos
rm -rf .build
swift build

# Run GUI
swift run llamacpp-gui

# Check build status
swift build 2>&1 | grep -E "error|warning"

# Kill running GUI
pkill -f llamacpp-gui
```
