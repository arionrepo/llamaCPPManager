#!/bin/bash
# llamaCPP Manager Installation Script
# Supports multiple installation methods: pip, pipx, homebrew

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() { echo -e "${GREEN}[INSTALL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

# Configuration
REPO_URL="https://github.com/your-username/llamacpp-manager"
CLI_NAME="llamacpp-manager"
GUI_APP_NAME="llamaCPP Manager.app"

# Check system requirements
check_requirements() {
    log "Checking system requirements..."

    # Check macOS
    if [[ "$(uname)" != "Darwin" ]]; then
        error "This installer is designed for macOS only"
        exit 1
    fi

    # Check macOS version (require 13.0+ for GUI)
    macos_version=$(sw_vers -productVersion)
    if [[ "$(printf '%s\n' "13.0" "$macos_version" | sort -V | head -n1)" != "13.0" ]]; then
        warn "macOS 13.0+ recommended for GUI features. Current version: $macos_version"
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3.9+ is required but not installed"
        info "Install Python via: brew install python@3.11"
        exit 1
    fi

    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    if [[ "$(printf '%s\n' "3.9" "$python_version" | sort -V | head -n1)" != "3.9" ]]; then
        error "Python 3.9+ required, found $python_version"
        exit 1
    fi

    log "System requirements check passed ✅"
}

# Install via pipx (recommended)
install_pipx() {
    log "Installing via pipx (recommended method)..."

    # Install pipx if not available
    if ! command -v pipx &> /dev/null; then
        log "Installing pipx..."
        if command -v brew &> /dev/null; then
            brew install pipx
            pipx ensurepath
        else
            python3 -m pip install --user pipx
            python3 -m pipx ensurepath
        fi

        # Reload shell
        export PATH="$HOME/.local/bin:$PATH"
    fi

    # Install llamacpp-manager
    if [[ -d "$(pwd)/src/llamacpp_manager" ]]; then
        # Local development install
        log "Installing from local source..."
        pipx install --force .
    else
        # Remote install (when published)
        log "Installing from PyPI..."
        pipx install $CLI_NAME
    fi

    log "pipx installation complete ✅"
}

# Install via pip
install_pip() {
    log "Installing via pip..."

    if [[ -d "$(pwd)/src/llamacpp_manager" ]]; then
        # Local development install
        log "Installing from local source..."
        python3 -m pip install --user .
    else
        # Remote install
        log "Installing from PyPI..."
        python3 -m pip install --user $CLI_NAME
    fi

    log "pip installation complete ✅"
}

# Install via Homebrew
install_homebrew() {
    log "Installing via Homebrew..."

    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        error "Homebrew not found. Install from: https://brew.sh"
        exit 1
    fi

    # Add custom tap (if using custom formula)
    if [[ -f "Formula/llamacpp-manager.rb" ]]; then
        log "Using local formula..."
        brew install --formula Formula/llamacpp-manager.rb
    else
        # Install from official tap (when published)
        log "Installing from Homebrew..."
        brew install llamacpp-manager
    fi

    log "Homebrew installation complete ✅"
}

# Install GUI app
install_gui() {
    log "Installing GUI application..."

    local app_source=""
    local install_dir="/Applications"

    # Find GUI app
    if [[ -f "gui-macos/build/$GUI_APP_NAME" ]]; then
        app_source="gui-macos/build/$GUI_APP_NAME"
    elif [[ -f "gui-macos/build/llamaCPP-Manager-1.0.0.dmg" ]]; then
        log "Found DMG file, mounting and installing..."
        local dmg_path="gui-macos/build/llamaCPP-Manager-1.0.0.dmg"
        local mount_point=$(hdiutil attach "$dmg_path" | grep -o '/Volumes/.*')
        app_source="$mount_point/$GUI_APP_NAME"
    else
        warn "GUI app not found. Build it first with: cd gui-macos && ./build_app.sh"
        return 0
    fi

    if [[ -n "$app_source" ]]; then
        log "Installing GUI to $install_dir..."
        cp -R "$app_source" "$install_dir/"

        log "GUI installed to $install_dir/$GUI_APP_NAME ✅"
        log "Launch the app - it will appear in your menu bar as 🧠"

        # Unmount DMG if we mounted one
        if [[ "$app_source" == *"/Volumes/"* ]]; then
            hdiutil detach "$(dirname "$app_source")" &>/dev/null || true
        fi
    fi
}

# Post-installation setup
post_install() {
    log "Running post-installation setup..."

    # Initialize configuration
    if command -v $CLI_NAME &> /dev/null; then
        log "Initializing default configuration..."
        $CLI_NAME init || warn "Configuration initialization failed (this may be normal)"
    fi

    # Check llama.cpp dependency
    if ! command -v llama-server &> /dev/null; then
        warn "llama-server not found in PATH"
        info "Install llama.cpp with: brew install llama.cpp"
        info "Or build from source: https://github.com/ggerganov/llama.cpp"
    fi

    log "Post-installation setup complete ✅"
}

# Verify installation
verify_installation() {
    log "Verifying installation..."

    # Check CLI
    if command -v $CLI_NAME &> /dev/null; then
        local version=$($CLI_NAME --version 2>/dev/null || echo "unknown")
        log "CLI installed: $CLI_NAME $version ✅"
    else
        error "CLI installation failed"
        return 1
    fi

    # Check MCP server
    if command -v llamacpp-mcp-server &> /dev/null; then
        log "MCP server installed ✅"
    else
        warn "MCP server not found"
    fi

    # Check GUI
    if [[ -f "/Applications/$GUI_APP_NAME/Contents/Info.plist" ]]; then
        log "GUI app installed ✅"
    else
        info "GUI app not installed (optional)"
    fi

    log "Installation verification complete ✅"
}

# Show usage instructions
show_usage() {
    echo
    log "🎉 llamaCPP Manager installation complete!"
    echo
    info "Quick Start:"
    info "1. Initialize configuration:"
    info "   $CLI_NAME init"
    echo
    info "2. Add a model:"
    info "   $CLI_NAME config add mymodel /path/to/model.gguf --port 8081"
    echo
    info "3. Start the model:"
    info "   $CLI_NAME start mymodel"
    echo
    info "4. Launch GUI (if installed):"
    info "   Open 'Applications/$GUI_APP_NAME' or look for 🧠 in menu bar"
    echo
    info "Documentation: https://github.com/your-username/llamacpp-manager/blob/main/docs/user-manual.md"
    info "Issues: https://github.com/your-username/llamacpp-manager/issues"
}

# Main installation function
main() {
    local method="${1:-pipx}"
    local install_gui_flag="${2:-yes}"

    log "llamaCPP Manager Installer"
    log "=========================="

    check_requirements

    case "$method" in
        "pipx")
            install_pipx
            ;;
        "pip")
            install_pip
            ;;
        "homebrew"|"brew")
            install_homebrew
            ;;
        *)
            error "Unknown installation method: $method"
            echo "Usage: $0 [pipx|pip|homebrew] [yes|no (for GUI)]"
            exit 1
            ;;
    esac

    # Install GUI if requested
    if [[ "$install_gui_flag" == "yes" ]]; then
        install_gui
    fi

    post_install
    verify_installation
    show_usage
}

# Parse command line arguments
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi