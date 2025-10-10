#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/install-cli.sh
# Description: Install llamacpp-manager CLI to ~/.local/bin for GUI access
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-10

set -e

echo "🔧 Installing llamacpp-manager CLI to ~/.local/bin..."

# Create directories
mkdir -p ~/.local/bin
mkdir -p ~/.local/lib/python3.13/site-packages

# Install package
echo "📦 Installing Python package..."
pip3 install --target ~/.local/lib/python3.13/site-packages .

# Create executable wrapper
echo "🔗 Creating executable wrapper..."
cat > ~/.local/bin/llamacpp-manager << 'WRAPPER'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.expanduser('~/.local/lib/python3.13/site-packages'))
from llamacpp_manager.cli import main
if __name__ == '__main__':
    sys.exit(main())
WRAPPER

chmod +x ~/.local/bin/llamacpp-manager

echo "✅ Installation complete!"
echo ""
echo "The GUI will now use: ~/.local/bin/llamacpp-manager"
echo ""
echo "Test it with:"
echo "  ~/.local/bin/llamacpp-manager --version"
