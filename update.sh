#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/update.sh
# Description: Update llamaCPPManager CLI and GUI to latest version from local repo
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-02

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}[UPDATE]${NC} llamaCPPManager Update Script"
echo ""

# Get script directory (repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if pipx is available
if ! command -v pipx &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} pipx not found. Install it first:"
    echo "  brew install pipx"
    echo "  pipx ensurepath"
    exit 1
fi

# Check if llamacpp-manager is currently installed
if ! pipx list | grep -q llamacpp-manager; then
    echo -e "${YELLOW}[WARN]${NC} llamacpp-manager not installed via pipx"
    echo -e "${BLUE}[INFO]${NC} Installing fresh..."
    pipx install .
else
    echo -e "${BLUE}[UPDATE]${NC} Updating CLI via pipx..."
    pipx install --force .
fi

echo ""
echo -e "${GREEN}[SUCCESS]${NC} CLI updated successfully"
echo ""

# Verify CLI is working
echo -e "${BLUE}[VERIFY]${NC} Testing CLI..."
if llamacpp-manager --version 2>/dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} CLI is working"
else
    echo -e "${YELLOW}[WARN]${NC} CLI test returned error (might be normal if --version not implemented)"
fi

echo ""

# Ask about GUI update
echo -e "${BLUE}[QUESTION]${NC} Do you want to update the GUI app? (y/N)"
read -r UPDATE_GUI

if [[ "$UPDATE_GUI" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}[BUILD]${NC} Building GUI app bundle..."

    cd "$SCRIPT_DIR/gui-macos"

    # Check if build script exists
    if [ ! -f "build_app.sh" ]; then
        echo -e "${RED}[ERROR]${NC} build_app.sh not found in gui-macos/"
        exit 1
    fi

    # Build the app
    ./build_app.sh

    echo ""
    echo -e "${BLUE}[INSTALL]${NC} Installing GUI to /Applications/..."

    # Check if app bundle was created
    if [ ! -d "build/llamaCPP Manager.app" ]; then
        echo -e "${RED}[ERROR]${NC} App bundle not found at build/llamaCPP Manager.app"
        exit 1
    fi

    # Kill running GUI if exists
    if pgrep -x "llamacpp-gui" > /dev/null; then
        echo -e "${BLUE}[INFO]${NC} Stopping running GUI app..."
        killall llamacpp-gui 2>/dev/null || true
        sleep 1
    fi

    # Copy to Applications
    cp -R "build/llamaCPP Manager.app" /Applications/

    echo -e "${GREEN}[SUCCESS]${NC} GUI installed to /Applications/llamaCPP Manager.app"

    # Ask about launching
    echo ""
    echo -e "${BLUE}[QUESTION]${NC} Launch GUI now? (y/N)"
    read -r LAUNCH_GUI

    if [[ "$LAUNCH_GUI" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}[LAUNCH]${NC} Starting GUI..."
        open "/Applications/llamaCPP Manager.app"
        echo -e "${GREEN}[SUCCESS]${NC} GUI launched - check your menu bar"
    fi
else
    echo -e "${BLUE}[SKIP]${NC} Skipping GUI update"
fi

echo ""
echo -e "${GREEN}[COMPLETE]${NC} Update complete!"
echo ""
echo -e "${BLUE}[INFO]${NC} Your configuration is preserved at:"
echo "  ~/Library/Application Support/llamaCPPManager/config.yaml"
echo ""
echo -e "${BLUE}[INFO]${NC} Verify everything works:"
echo "  llamacpp-manager status"
echo ""
echo -e "${BLUE}[INFO]${NC} If you have monitoring daemon installed, restart it:"
echo "  llamacpp-manager monitor launchd uninstall"
echo "  llamacpp-manager monitor launchd install"
echo ""

# Questions: libor@arionetworks.com
