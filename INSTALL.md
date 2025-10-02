# llamaCPPManager Installation Guide

Quick installation guide for macOS.

## Prerequisites

- **macOS** (Ventura or newer, Apple Silicon recommended)
- **Python 3.9+**
- **pipx** (recommended) or **pip**
- **llama.cpp** installed (for model management)

## Step 1: Install pipx (if not already installed)

```bash
# Install pipx via Homebrew
brew install pipx

# Or via pip
python3 -m pip install --user pipx

# Ensure pipx is in PATH
pipx ensurepath

# Restart your terminal after this step
```

## Step 2: Install llamaCPPManager CLI

```bash
# Clone the repository (if not already done)
cd ~/LocalProjects/GitHubProjectsDocuments/llamaCPPManager

# Install with pipx (recommended - isolated environment)
pipx install -e .

# Verify installation
llamacpp-manager --version
```

**📌 Important**: Your configuration is stored separately at `~/Library/Application Support/llamaCPPManager/config.yaml`. Reinstalling or upgrading the CLI **never deletes your model configurations**. See [UPGRADE.md](UPGRADE.md) for details.

## Step 3: Initialize Configuration

```bash
# Initialize with default paths
llamacpp-manager init

# The config will be created at:
# - Config: ~/Library/Application Support/llamaCPPManager/config.yaml
# - Logs: ~/Library/Logs/llamaCPPManager/
```

## Step 4: (Optional) Install Monitoring Daemon

The monitoring daemon provides automatic health checks and crash recovery:

```bash
# Install as launchd agent (auto-starts on boot)
llamacpp-manager monitor launchd install

# Verify installation
llamacpp-manager monitor launchd status
```

## Step 5: (Optional) Install GUI App

```bash
# Build the GUI app
cd gui-macos
./build_app.sh

# Install to Applications folder
cp -R "build/llamaCPP Manager.app" /Applications/

# Optional: Set up auto-start on login
./install_gui_launchagent.sh
```

## Step 6: Add Your First Model

```bash
# Example: Add a model
llamacpp-manager config add smollm3 \
  ~/llms/smollm3/SmolLM3-Q8_0.gguf \
  --port 8081 \
  --extra-args "-c 8192 -ngl 9999"

# Start the model
llamacpp-manager start smollm3

# Check status
llamacpp-manager status
```

## Step 7: Verify Infrastructure Components

**Note**: Infrastructure management only works with specific local components on the same macOS machine.

```bash
# List configured infrastructure
llamacpp-manager infra list

# You should see:
# - cloudflared (if ~/llms/install_cloudflared_launchagent.sh exists)
# - llm_controller (if ~/llms/controller.sh exists)
```

## What's Installed

After completing these steps, you'll have:

✅ llamacpp-manager CLI tool (globally available)
✅ Configuration directory with config.yaml
✅ Log directory for model and daemon logs
✅ (Optional) Monitoring daemon running as launchd agent
✅ (Optional) GUI app in /Applications folder
✅ (Optional) GUI auto-start on login

## Quick Test

```bash
# Test CLI
llamacpp-manager --help

# Test status command
llamacpp-manager status

# Test infrastructure commands
llamacpp-manager infra list

# Test monitoring daemon
llamacpp-manager monitor launchd status
```

## Troubleshooting

### "Command not found: llamacpp-manager"

```bash
# Check if pipx bin directory is in PATH
pipx ensurepath

# Restart terminal and try again
```

### "No module named 'llamacpp_manager'"

```bash
# Reinstall with pipx
pipx uninstall llamacpp-manager
pipx install -e ~/LocalProjects/GitHubProjectsDocuments/llamaCPPManager
```

### GUI Won't Start

```bash
# Make sure CLI is installed first
which llamacpp-manager

# Rebuild the GUI app
cd gui-macos
./build_app.sh
```

## Next Steps

- Read [README.md](README.md) for usage examples
- Read [docs/user-manual.md](docs/user-manual.md) for comprehensive guide
- Read [docs/infrastructure-implementation-summary.md](docs/infrastructure-implementation-summary.md) for infrastructure details

## Uninstallation

```bash
# Uninstall monitoring daemon
llamacpp-manager monitor launchd uninstall

# Uninstall GUI auto-start (if installed)
launchctl unload ~/Library/LaunchAgents/com.llamacpp.manager.gui.plist
rm ~/Library/LaunchAgents/com.llamacpp.manager.gui.plist

# Uninstall CLI
pipx uninstall llamacpp-manager

# Remove configuration (optional)
rm -rf ~/Library/Application\ Support/llamaCPPManager
rm -rf ~/Library/Logs/llamaCPPManager

# Remove GUI app (optional)
rm -rf /Applications/llamaCPP\ Manager.app
```
