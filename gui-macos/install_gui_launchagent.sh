#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/install_gui_launchagent.sh
# Description: Install llamaCPP Manager GUI as a launchd agent to start on boot
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-02

set -e

LABEL="com.llamacpp.manager.gui"
PLIST_FILE="$HOME/Library/LaunchAgents/$LABEL.plist"
APP_PATH="/Applications/llamaCPP Manager.app/Contents/MacOS/llamacpp-gui"

# Check if app exists
if [ ! -f "$APP_PATH" ]; then
    echo "Error: GUI app not found at $APP_PATH"
    echo "Please install the app to /Applications first:"
    echo "  cp -R 'build/llamaCPP Manager.app' /Applications/"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Create plist content
cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$APP_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
</dict>
</plist>
EOF

echo "✓ Created launchd plist: $PLIST_FILE"

# Load the agent
launchctl load "$PLIST_FILE" 2>&1 || {
    echo "Warning: launchctl load returned non-zero"
    echo "The plist has been created. You may need to log out and log back in."
}

echo "✓ GUI app installed as launchd agent"
echo "  Label: $LABEL"
echo "  App: $APP_PATH"
echo "  The GUI will start automatically when you log in"
echo ""
echo "To uninstall:"
echo "  launchctl unload \"$PLIST_FILE\""
echo "  rm \"$PLIST_FILE\""
