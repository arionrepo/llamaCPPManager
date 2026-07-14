#!/bin/bash
# File: scripts/pre-commit-version-check.sh
# Description: Pre-commit hook (symlinked from .git/hooks/pre-commit) that
#              validates embedded version literals against the VERSION file.
#              VALIDATES ONLY — never mutates. Per the release-engineering
#              spec, version bumps must run BEFORE commit via /commit-and-sync
#              (which invokes version-bump.py + .versionbump.yaml), not here.
# Author: Libor Ballaty <libor@arionetworks.com>
# Updated: 2026-06-24 — rewritten to compare against the VERSION file instead of
#                      tag descriptions (the rejected `git-describe --tags`
#                      pattern). Closes the chicken-and-egg that forced
#                      --no-verify on every release commit.
# Updated: 2026-07-14 — confirmed compliant with the now-normative Versioning
#                      spec §1.5. This repo keeps its tailored gui-scoped
#                      validator; the reusable equivalent lives at
#                      ~/.ai-dev-dotfiles/tools/hooks/version-validate.pre-commit.sh
# Reference:           ~/.ai-dev-dotfiles/repo-specs/release-engineering/CLAUDE.md

set -e

# Only validate when GUI files are part of this commit.
if ! git diff --cached --name-only | grep -q "gui-macos/"; then
    exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"

# 1. Read canonical version from VERSION file.
if [[ ! -f "$REPO_ROOT/VERSION" ]]; then
    echo "Error: VERSION file missing at repo root."
    exit 1
fi
CANONICAL_VERSION="$(tr -d '[:space:]' < "$REPO_ROOT/VERSION")"

# 2. Read APP_VERSION literal from AppConstants.swift.
APP_SWIFT_FILE="$REPO_ROOT/gui-macos/Sources/AppConstants.swift"
APP_SWIFT_VERSION=""
if [[ -f "$APP_SWIFT_FILE" ]]; then
    APP_SWIFT_VERSION=$(grep 'return "' "$APP_SWIFT_FILE" | head -1 | sed -E 's/.*return "(.*)".*/\1/')
fi

# 3. About-dialog interpolation sanity check (warning only).
ABOUT_FILE="$REPO_ROOT/gui-macos/Sources/ViewModels/StatusViewModel.swift"
if [[ -f "$ABOUT_FILE" ]] && ! grep -q 'llamaCPP Manager v\\(APP_VERSION)' "$ABOUT_FILE"; then
    echo "Warning: About dialog does not use APP_VERSION interpolation"
fi

# 4. Validate.
if [[ -z "$APP_SWIFT_VERSION" ]]; then
    echo "Error: Could not read APP_VERSION from $APP_SWIFT_FILE"
    exit 1
fi

if [[ "$CANONICAL_VERSION" != "$APP_SWIFT_VERSION" ]]; then
    echo "Error: VERSION file and AppConstants.swift APP_VERSION do not match!"
    echo
    echo "Version Details:"
    echo "  VERSION file:           $CANONICAL_VERSION"
    echo "  AppConstants.swift:     $APP_SWIFT_VERSION"
    echo
    echo "Run version-bump.py before committing, or rerun install-gui to sync"
    echo "AppConstants.swift to the current VERSION."
    exit 1
fi

# Info.plist is a build artifact (gitignored), updated by build_app.sh during
# install-gui. We deliberately do NOT validate it here — it may not exist on a
# fresh clone, and it always trails VERSION until the next build.

exit 0
