# CRITICAL: Restart Claude Code Session Required

**Date:** 2025-10-11
**Issue:** 6 zombie background bash shells persistently running stale Swift GUI code
**Impact:** GUI shows old code without "Stop All Models" button

## Problem

Six background bash shells (32f44c, 149cc3, b16974, eb8799, 6e0c17, 0405b6) are stuck running:
```bash
cd gui-macos && swift run llamacpp-gui
```

These shells:
- Keep restarting Swift processes even after `kill -9`
- Run STALE CODE from before commit `d64d1bd`
- Cannot be killed from within the session
- Prevent GUI updates from appearing

## Solution

**Restart Claude Code completely** to clear all background shells.

## After Restart - Proper Workflow

1. **Verify no stale processes:**
   ```bash
   ps aux | grep -E "(swift|llamacpp)" | grep -v grep
   ```
   Should return **0 processes**

2. **Build fresh executable:**
   ```bash
   cd gui-macos && swift build
   ```

3. **Open ONLY the built executable:**
   ```bash
   open ./.build/x86_64-apple-macosx/debug/llamacpp-gui
   ```

4. **Verify GUI shows:**
   - ✅ "Start All Models" button
   - ✅ "Stop All Models" button (in red)

## Prevention

**NEVER use `swift run` in background** - it creates persistent processes that:
- Don't respect kill signals
- Run stale code
- Require session restart to clear

**ALWAYS:**
- Build first: `swift build`
- Open executable: `open ./.build/.../llamacpp-gui`
- Kill explicitly before rebuilding

## Commits Applied

- `d64d1bd` - Fixed button visibility (removed `.buttonStyle(.borderless)`)
- `d57a743` - Added CLAUDE.md documentation
- `ccea88e` - Added VSCode settings

Code is correct, but zombie processes prevent it from running!
