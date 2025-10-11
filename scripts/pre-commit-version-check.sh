#!/bin/bash
# Pre-commit hook to validate version consistency

set -e

# Function to log version details
log_version_details() {
    echo "Git Tag Version:        $GIT_VERSION"
    echo "Info.plist Version:     $PLIST_VERSION"
    echo "App.swift Version:      $APP_SWIFT_VERSION"
    echo "AboutView Version:      $ABOUT_VIEW_VERSION"
}

# Check if this is a GUI-related commit
if git diff --cached --name-only | grep -q "gui-macos/"; then
    # Get the latest git tag
    GIT_TAG=$(git describe --tags --abbrev=0)

    # Remove 'v' prefix if present
    GIT_VERSION="${GIT_TAG#v}"

    # Check Info.plist version
    PLIST_VERSION=$(grep -A1 CFBundleShortVersionString gui-macos/build/llamaCPP\ Manager.app/Contents/Info.plist | tail -n1 | sed -E 's/.*<string>(.*)<\/string>.*/\1/')

    # Check App.swift version
    APP_SWIFT_VERSION=$(grep 'return "' gui-macos/Sources/App.swift | head -1 | sed -E 's/.*return "(.*)".*/\1/')

    # Check that AboutView uses APP_VERSION interpolation
    if ! grep -q 'llamaCPP Manager v\\(APP_VERSION)' gui-macos/Sources/App.swift; then
        echo "Warning: AboutView does not use APP_VERSION interpolation"
    fi

    # Validate versions match
    MISMATCH=0

    if [[ "$GIT_VERSION" != "$PLIST_VERSION" ]]; then
        echo "Error: Git Version and Info.plist Version do not match!"
        MISMATCH=1
    fi

    if [[ "$GIT_VERSION" != "$APP_SWIFT_VERSION" ]]; then
        echo "Error: Git Version and App.swift Version do not match!"
        MISMATCH=1
    fi

    if [[ $MISMATCH -eq 1 ]]; then
        echo
        echo "Version Details:"
        log_version_details
        echo
        echo "Please update all versions to match the latest git tag before committing."
        exit 1
    fi
fi

exit 0