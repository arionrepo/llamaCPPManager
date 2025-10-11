#!/bin/bash
# Build script to create a distributable .app bundle for llamaCPP Manager GUI

set -e

# Configuration
APP_NAME="llamaCPP Manager"
BUNDLE_ID="com.llamacpp.manager"
# Get version from git tag, fallback to default
VERSION=$(git describe --tags --always 2>/dev/null || echo "v1.1.0")

# Always ensure version starts with 'v'
if [[ ! "$VERSION" =~ ^v ]]; then
    VERSION="v$VERSION"
fi

# Always use a clean version for display
if [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-.*)?$ ]]; then
    DISPLAY_VERSION="${VERSION#v}"
else
    # Force version to 1.1.0 if it doesn't match semantic versioning
    DISPLAY_VERSION="1.1.0"
    VERSION="v1.1.0"
fi
BUILD_DIR="build"
APP_DIR="$BUILD_DIR/$APP_NAME.app"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[BUILD]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Clean previous builds
log "Cleaning previous builds..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build the Swift executable
log "Building Swift executable..."
swift build -c release

# Get the actual build path
BIN_PATH=$(swift build -c release --show-bin-path)
log "Using build path: $BIN_PATH"

# Create app bundle structure
log "Creating .app bundle structure..."
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Copy executable
log "Installing executable..."
cp "$BIN_PATH/llamacpp-gui" "$APP_DIR/Contents/MacOS/llamacpp-gui"
chmod +x "$APP_DIR/Contents/MacOS/llamacpp-gui"

# Create Info.plist
log "Creating Info.plist..."
cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>llamacpp-gui</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$DISPLAY_VERSION</string>
    <key>CFBundleVersion</key>
    <string>$DISPLAY_VERSION</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © $(date +%Y). All rights reserved.</string>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
EOF

# Update APP_VERSION in App.swift
log "Updating APP_VERSION to $DISPLAY_VERSION..."
ABOUT_FILE="Sources/App.swift"

# Use perl for more reliable multi-line replacement
perl -i -pe "BEGIN{undef $/;} s/let APP_VERSION: String = \{\s*return \"[^\"]*\"\s*\}\(\)/let APP_VERSION: String = {\n    return \"$DISPLAY_VERSION\"\n}()/smg" "$ABOUT_FILE"

# Create app icon (if available)
if command -v sips &> /dev/null; then
    log "Creating app icon..."
    # Create a simple icon using system tools
    mkdir -p "$APP_DIR/Contents/Resources/AppIcon.iconset"

    # You can replace this with a proper icon creation process
    # For now, we'll skip the icon creation
    info "Icon creation skipped - add AppIcon.icns manually if desired"
fi

# Create launch script that ensures CLI is available
log "Creating launch wrapper..."
cat > "$APP_DIR/Contents/MacOS/launch_wrapper.sh" << 'EOF'
#!/bin/bash
# Launch wrapper for llamaCPP Manager GUI

# Set up environment
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Check for CLI availability
CLI_PATHS=(
    "/opt/homebrew/bin/llamacpp-manager"
    "/usr/local/bin/llamacpp-manager"
    "$(which llamacpp-manager 2>/dev/null)"
)

CLI_FOUND=""
for path in "${CLI_PATHS[@]}"; do
    if [[ -x "$path" ]]; then
        CLI_FOUND="$path"
        break
    fi
done

if [[ -z "$CLI_FOUND" ]]; then
    # Show user-friendly error dialog
    osascript -e 'display dialog "llamaCPP Manager CLI not found. Please install it first using:\n\nbrew install llamacpp-manager\n\nor\n\npip install llamacpp-manager" with title "llamaCPP Manager" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Launch the actual GUI
exec "$(dirname "$0")/llamacpp-gui"
EOF

chmod +x "$APP_DIR/Contents/MacOS/launch_wrapper.sh"

# Update Info.plist to use wrapper
sed -i '' 's|<string>llamacpp-gui</string>|<string>launch_wrapper.sh</string>|' "$APP_DIR/Contents/Info.plist"

# Create README for the app bundle
log "Creating bundle documentation..."
cat > "$BUILD_DIR/README.txt" << EOF
llamaCPP Manager v$VERSION
=========================

Installation Instructions:
1. Drag "$APP_NAME.app" to your Applications folder
2. Install the CLI component:
   brew install llamacpp-manager
   OR
   pip install llamacpp-manager

3. Launch the app - it will appear in your menu bar

Requirements:
- macOS 13.0+
- llamaCPP Manager CLI (installed separately)

Support:
- GitHub: https://github.com/your-repo/llamacpp-manager
- Issues: Report bugs via GitHub Issues

The app will appear as a brain icon (🧠) in your menu bar.
Click it to access model management controls.
EOF

# Sign the app (if developer certificate available)
if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    log "Code signing app bundle..."
    codesign --force --deep --sign "Developer ID Application" "$APP_DIR" 2>/dev/null || {
        info "Code signing failed - app will work but show security warnings"
    }
else
    info "No code signing certificate found - app will show security warnings"
fi

# Create distributable DMG (if available)
if command -v hdiutil &> /dev/null; then
    log "Creating distributable DMG..."
    DMG_NAME="$BUILD_DIR/llamaCPP-Manager-$DISPLAY_VERSION.dmg"

    # Create temporary dmg directory
    DMG_DIR="$BUILD_DIR/dmg"
    mkdir -p "$DMG_DIR"
    cp -R "$APP_DIR" "$DMG_DIR/"
    cp "$BUILD_DIR/README.txt" "$DMG_DIR/"

    # Create symbolic link to Applications
    ln -sf /Applications "$DMG_DIR/Applications"

    # Create DMG
    hdiutil create -srcfolder "$DMG_DIR" -format UDZO -o "$DMG_NAME"
    rm -rf "$DMG_DIR"

    log "DMG created: $DMG_NAME"
fi

# Final summary
echo
log "✅ App bundle creation complete!"
info "Bundle location: $APP_DIR"
info "Installation: Drag to Applications folder"
info "Requirements: CLI must be installed separately"

if [[ -f "$BUILD_DIR/llamaCPP-Manager-$DISPLAY_VERSION.dmg" ]]; then
    info "DMG available: $BUILD_DIR/llamaCPP-Manager-$DISPLAY_VERSION.dmg"
fi

echo
log "To test the bundle:"
log "1. Open '$APP_DIR' (should show app info)"
log "2. Install CLI: pip install -e .. (from project root)"
log "3. Double-click the app to launch"
log "4. Look for 🧠 icon in menu bar"