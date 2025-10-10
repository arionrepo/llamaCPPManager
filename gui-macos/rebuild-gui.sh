#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/rebuild-gui.sh
# Description: Script to completely rebuild the GUI with latest changes
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-10

set -e

echo "🧹 Cleaning old build artifacts..."
rm -rf .build
rm -rf build

echo "🔨 Building GUI from source..."
swift build

echo "✅ Build complete!"
echo ""
echo "To run the GUI with latest changes:"
echo "  swift run llamacpp-gui"
echo ""
echo "Or build a .app bundle:"
echo "  swift build -c release"
echo "  open .build/release/llamacpp-gui"
