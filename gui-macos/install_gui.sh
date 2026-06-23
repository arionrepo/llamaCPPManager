#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/install_gui.sh
# Description: Deterministic install of the freshly-built GUI to /Applications.
#              Kills running instances, replaces the bundle, verifies MD5, and launches.
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-06-19
#
# Usage:
#   install_gui.sh                # build (if missing) + install + launch
#   install_gui.sh --no-rebuild   # skip rebuild even if build is stale
#   install_gui.sh --no-launch    # install but don't open
#   install_gui.sh --force        # rebuild even if a build already exists
#   install_gui.sh --quiet        # less verbose output (status lines only)
#
# Exit codes:
#   0 success (or already up-to-date)
#   1 generic failure
#   2 build failed
#   3 install failed (permission, etc.)
#   4 launch failed
#   5 verification failed (MD5 mismatch)

set -eo pipefail

# --- Configuration ---
APP_NAME="llamaCPP Manager"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_APP="$SCRIPT_DIR/build/$APP_NAME.app"
INSTALL_APP="/Applications/$APP_NAME.app"
BUILD_SCRIPT="$SCRIPT_DIR/build_app.sh"

# --- Flags ---
REBUILD="auto"
LAUNCH="true"
FORCE="false"
QUIET="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-rebuild) REBUILD="false" ;;
        --no-launch)  LAUNCH="false" ;;
        --force)      FORCE="true" ;;
        --quiet)      QUIET="true" ;;
        -h|--help)
            sed -n '4,20p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "❌ Unknown flag: $1" >&2
            exit 1
            ;;
    esac
    shift
done

# --- Helpers ---
log()    { [[ "$QUIET" == "true" ]] || echo "▶ $*"; }
status() { echo "● $*"; }
fail()   { echo "❌ $*" >&2; }

md5_of() {
    local f="$1"
    [[ -f "$f" ]] || { echo "missing"; return; }
    md5 -q "$f" 2>/dev/null || md5sum "$f" 2>/dev/null | awk '{print $1}'
}

# --- 1. Decide whether to rebuild ---
NEED_REBUILD="false"
if [[ "$FORCE" == "true" ]]; then
    NEED_REBUILD="true"
    log "Forcing rebuild (--force)"
elif [[ ! -d "$BUILD_APP" ]]; then
    NEED_REBUILD="true"
    log "No existing build found; will rebuild"
elif [[ "$REBUILD" == "auto" ]]; then
    # Rebuild if any source file is newer than the built binary
    BUILT_BIN="$BUILD_APP/Contents/MacOS/llamacpp-gui"
    if [[ -f "$BUILT_BIN" ]]; then
        # mtime comparison
        if find "$SCRIPT_DIR/Sources" -name "*.swift" -newer "$BUILT_BIN" -print -quit 2>/dev/null | grep -q .; then
            NEED_REBUILD="true"
            log "Sources newer than built binary; will rebuild"
        elif [[ -f "$REPO_ROOT/VERSION" ]] && [[ "$REPO_ROOT/VERSION" -nt "$BUILT_BIN" ]]; then
            NEED_REBUILD="true"
            log "VERSION newer than built binary; will rebuild"
        else
            log "Build is up-to-date; skipping rebuild"
        fi
    else
        NEED_REBUILD="true"
        log "Built binary missing; will rebuild"
    fi
elif [[ "$REBUILD" == "false" ]]; then
    log "Skipping rebuild (--no-rebuild)"
fi

if [[ "$NEED_REBUILD" == "true" ]]; then
    log "Building app bundle..."
    # build_app.sh uses relative paths (Sources/App.swift, swift build), so
    # we MUST cd to gui-macos first.
    if ! (cd "$SCRIPT_DIR" && "$BUILD_SCRIPT" >/dev/null 2>&1); then
        fail "Build failed - re-running with output:"
        (cd "$SCRIPT_DIR" && "$BUILD_SCRIPT" 2>&1 | tail -30) >&2
        exit 2
    fi
    status "Build complete"
fi

# --- 2. Verify build artifact exists ---
if [[ ! -f "$BUILD_APP/Contents/MacOS/llamacpp-gui" ]]; then
    fail "Build app missing at $BUILD_APP"
    exit 2
fi

BUILD_MD5=$(md5_of "$BUILD_APP/Contents/MacOS/llamacpp-gui")
log "Build MD5:     $BUILD_MD5"

# --- 3. Check if already installed and identical ---
if [[ -d "$INSTALL_APP" ]]; then
    INSTALL_MD5=$(md5_of "$INSTALL_APP/Contents/MacOS/llamacpp-gui")
    log "Installed MD5: $INSTALL_MD5"
    if [[ "$BUILD_MD5" == "$INSTALL_MD5" ]] && [[ "$FORCE" == "false" ]]; then
        status "Already up-to-date (MD5 match)"
        # Still launch if requested and not running
        if [[ "$LAUNCH" == "true" ]]; then
            if pgrep -f "llamacpp-gui" >/dev/null; then
                log "App already running"
            else
                log "Launching..."
                open "$INSTALL_APP"
                status "Launched"
            fi
        fi
        exit 0
    fi
fi

# --- 4. Kill any running instances ---
log "Stopping any running instances..."
killall "$APP_NAME" 2>/dev/null || true
pkill -9 -f llamacpp-gui 2>/dev/null || true
# Give the FS time to release file handles
sleep 1.5

# Confirm nothing's running
if pgrep -f "llamacpp-gui" >/dev/null 2>&1; then
    fail "Could not kill all GUI processes - try manually: killall '$APP_NAME'"
    exit 3
fi

# --- 5. Remove old and copy new ---
log "Removing old install at $INSTALL_APP..."
if ! rm -rf "$INSTALL_APP" 2>/dev/null; then
    fail "Could not remove $INSTALL_APP - check permissions"
    exit 3
fi

log "Copying new build to $INSTALL_APP..."
if ! cp -R "$BUILD_APP" "$INSTALL_APP"; then
    fail "Copy to /Applications failed - check write permission"
    exit 3
fi

# --- 6. Verify the copy ---
INSTALLED_MD5=$(md5_of "$INSTALL_APP/Contents/MacOS/llamacpp-gui")
if [[ "$INSTALLED_MD5" != "$BUILD_MD5" ]]; then
    fail "MD5 mismatch after copy: expected $BUILD_MD5, got $INSTALLED_MD5"
    exit 5
fi
status "Installed:     $INSTALLED_MD5 ✓"

# --- 7. Extract and report version ---
# Best-effort: prefer the repo's VERSION file (deterministic), else try to
# grep the binary's embedded strings. Either failure is non-fatal (|| true).
VERSION_STR=""
if [[ -f "$REPO_ROOT/VERSION" ]]; then
    VERSION_STR=$(tr -d '[:space:]' < "$REPO_ROOT/VERSION" 2>/dev/null || true)
fi
if [[ -z "$VERSION_STR" ]]; then
    VERSION_STR=$( (strings "$INSTALL_APP/Contents/MacOS/llamacpp-gui" 2>/dev/null \
        | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1) || true )
fi
[[ -n "$VERSION_STR" ]] && status "Version:       $VERSION_STR"

# --- 8. Launch ---
if [[ "$LAUNCH" == "true" ]]; then
    log "Launching..."
    if ! open "$INSTALL_APP"; then
        fail "open command failed"
        exit 4
    fi
    sleep 1
    if pgrep -f "llamacpp-gui" >/dev/null; then
        status "Launched ✓"
    else
        fail "App opened but process not detected - check Console.app"
        exit 4
    fi
else
    log "(skipping launch per --no-launch)"
fi

status "Done"
exit 0
