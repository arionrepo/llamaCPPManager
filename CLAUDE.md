# llamaCPPManager Project - Claude Development Guidelines

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/CLAUDE.md
**Description:** Project-specific development guidelines for llamaCPPManager
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-11

## Project Overview

llamaCPPManager is a macOS tool for managing multiple llama.cpp server instances with:
- Python CLI (`llamacpp-manager`)
- Swift/SwiftUI MenuBarExtra GUI
- SQLite chat history database
- Multi-model comparison features

## Swift GUI Application Workflow (MANDATORY)

### Problem
GUI changes don't appear because multiple instances and stale compiled binaries persist.

### Solution: Follow This Workflow EVERY TIME

**After making ANY changes to `gui-macos/Sources/App.swift`:**

1. **Commit changes first:**
```bash
git add gui-macos/Sources/App.swift
git commit --no-verify -m "fix: description of change"
```

2. **Kill ALL running instances:**
```bash
killall "Llama CPP Manager" 2>/dev/null
pkill -9 swift
pkill -9 llamacpp-gui
sleep 2
```

3. **Rebuild the executable:**
```bash
/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/rebuild-gui.sh
```

4. **Open the updated executable:**
```bash
cd /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager
open ./.build/x86_64-apple-macosx/debug/llamacpp-gui
```

5. **Verify with user:**
Ask the user to confirm they see the changes before proceeding.

### Common Issues

- **"Stop All Models" button not visible:** Likely `.buttonStyle()` conflict on parent container
- **Help shows old content:** Old process still running, not killed properly
- **Changes don't appear:** Multiple `swift run` background processes persist with stale code

### Critical Rules

- ✅ **ALWAYS** commit before rebuilding
- ✅ **ALWAYS** kill all processes (use `pkill -9`)
- ✅ **ALWAYS** use the rebuild script, not just `swift run`
- ✅ **ALWAYS** verify changes with user
- ❌ **NEVER** assume `swift run` picks up changes
- ❌ **NEVER** skip the kill step

## Python CLI Development

### Testing After Changes

Always run regression tests:
```bash
.venv/bin/pytest tests/test_config.py tests/test_model_manager.py -v
```

Test core commands:
```bash
.venv/bin/llamacpp-manager status --json
.venv/bin/llamacpp-manager query chat phi3 --message "user:test"
.venv/bin/llamacpp-manager compare "test" --models phi3,smollm3
```

### Modular Architecture

When adding new features:
- Create NEW files rather than modifying existing code
- Add minimal functions to existing files (like cli.py)
- Avoid breaking existing functionality
- Use subprocess to call existing CLI commands

## File Structure

```
src/llamacpp_manager/
├── cli.py              # CLI entry point (add new commands here)
├── config.py           # Model configuration
├── chat_storage.py     # SQLite chat history (NEW)
├── multi_query.py      # Multi-model queries (NEW)
└── ...

gui-macos/
├── Sources/App.swift   # SwiftUI GUI (USE WORKFLOW ABOVE)
├── rebuild-gui.sh      # Rebuild script (MANDATORY)
└── build_app.sh        # Production .app builder
```

## Pre-commit Hook Bypass

Pre-existing test failures may block commits. Use `--no-verify` when failures are unrelated:
```bash
git commit --no-verify -m "message"
```

## Contact

Questions: libor@arionetworks.com
