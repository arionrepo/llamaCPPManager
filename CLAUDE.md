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

### Solution: One command (preferred)

After ANY change to anything under `gui-macos/Sources/`:

```bash
llamacpp-manager install-gui
```

Or in a Claude Code chat: `/llamacpp-install-gui`

That single command handles the full deterministic sequence:
build → kill running → replace `/Applications/llamaCPP Manager.app` → MD5 verify → launch → confirm process running.

Flags:
- `--force` — always rebuild + reinstall (even if MD5s match)
- `--no-rebuild` — install the existing build/ contents only
- `--no-launch` — install without opening the app
- `--quiet` — minimal output

The script is at `gui-macos/install_gui.sh`. The CLI wrapper is `cmd_install_gui` in `cli.py`. Slash command spec is at `.claude/commands/llamacpp-install-gui.md` (the `llamacpp-` prefix avoids collisions with similar commands in other repos).

### Legacy manual workflow (only if `install-gui` is broken)

<details>
<summary>Click to expand the old 5-step manual sequence</summary>

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

</details>

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

### CLI is pipx-installed (non-editable)

The `llamacpp-manager` CLI is installed via pipx from this local source directory, but **not in editable mode**. Source changes in `src/llamacpp_manager/` are NOT live until reinstalled:

```bash
pipx reinstall llamacpp-manager
```

A PostToolUse hook in `.claude/settings.json` injects a reminder whenever a file under `src/llamacpp_manager/` is edited.

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

---

## File Reservation

File reservation is required before first write.

- If `/Users/liborballaty/.codex/memories/AGENT-WORK-QUEUE.md` exists, use it as the authoritative coordination queue before editing any file.
- If the global queue is unavailable, use the repo-local fallback queue when the repo defines one.
- Use `queuectl reserve`, `queuectl verify`, `queuectl renew`, and `queuectl release` when queue tooling is available.
- Claim the exact files you will modify before the first write.
- Do not edit shared or canonical files without an active claim.
- Keep claims narrow, short-lived, and limited to actual write scope.
- If a required file is already claimed, do not overlap edits; continue with disjoint work if possible and re-check later.

