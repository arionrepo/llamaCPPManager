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

# Copy source files directly (pip wheel building seems to truncate files)
echo "📦 Copying source files..."
rm -rf ~/.local/lib/python3.13/site-packages/llamacpp_manager
cp -r src/llamacpp_manager ~/.local/lib/python3.13/site-packages/

# Install dependencies only
echo "📦 Installing dependencies..."
pip3 install --target ~/.local/lib/python3.13/site-packages PyYAML>=6.0 mcp>=1.0.0 httpx>=0.25.0 pydantic>=2.0.0 docker>=6.1.0 jinja2>=3.1.0 --quiet

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
