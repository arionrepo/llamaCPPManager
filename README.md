# llamaCPPManager

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/README.md
**Description:** Toolkit for managing local llama-server instances (llama.cpp) on macOS with CLI and GUI interfaces
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2024-09-15
**Last Updated:** 2026-01-07
**Last Updated By:** Libor Ballaty <libor@arionetworks.com>

---

## Overview

llamaCPPManager is a comprehensive toolkit for managing multiple local `llama-server` instances from llama.cpp on macOS. It provides both a Python CLI and a native Swift/SwiftUI menu bar application for easy model management, chatting, and multi-model comparison.

**Key Features:**
- 🚀 **Multi-Model Management** - Run multiple llama.cpp models simultaneously on different ports
- 💬 **Chat Interface** - Interactive chat with local LLMs via CLI or GUI
- 📊 **Model Comparison** - Compare responses from multiple models side-by-side
- 💾 **Chat History** - SQLite database stores all conversations for later reference
- 🍎 **Native macOS GUI** - SwiftUI menu bar app with modern interface
- 🔧 **CLI Tools** - Full-featured command-line interface for automation
- 🔌 **MyRAGDB Integration** - Monitor and manage MyRAGDB search service
- 🎯 **Port Management** - Automatic port allocation and conflict detection

---

## Quick Start

### Installation

```bash
# Clone repository
cd /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager

# Install CLI with pipx (recommended)
pipx install .

# Or install in virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Build and install GUI application
./build-gui-release.sh
# App will be installed to /Applications/llamaCPP Manager.app
```

### Prerequisites

- **macOS** 12.0 or later (Apple Silicon or Intel)
- **Python 3.9+** (3.11+ recommended)
- **llama.cpp** installed (`brew install llama.cpp` or build from source)
- **Swift 5.9+** (for GUI compilation)
- **pipx** (optional, for CLI installation): `brew install pipx`

### Basic Usage

```bash
# Start a model
llamacpp-manager start phi3 --port 8081

# Chat with a model
llamacpp-manager query chat phi3 --message "user:What is the capital of France?"

# Check status of all models
llamacpp-manager status

# Compare multiple models
llamacpp-manager compare "Explain quantum computing" --models phi3,smollm3

# Stop all running models
llamacpp-manager stop-all

# Launch GUI application
open "/Applications/llamaCPP Manager.app"
```

---

## Features

### CLI Commands

```bash
# Model Management
llamacpp-manager list                    # List available models
llamacpp-manager start <model>           # Start a model server
llamacpp-manager stop <model>            # Stop a model server
llamacpp-manager stop-all                # Stop all running models
llamacpp-manager status                  # Show status of all models
llamacpp-manager status --json           # JSON output for scripting

# Chat Interface
llamacpp-manager query chat <model>      # Interactive chat session
llamacpp-manager query chat <model> --message "user:prompt"  # Single query
llamacpp-manager query completion <model> --prompt "text"    # Text completion

# Multi-Model Comparison
llamacpp-manager compare "prompt" --models phi3,smollm3,llama3
llamacpp-manager compare "prompt" --models phi3,smollm3 --output comparison.json

# Chat History
llamacpp-manager history list            # Show recent conversations
llamacpp-manager history search "keyword"  # Search chat history
llamacpp-manager history export --format json  # Export conversations

# Configuration
llamacpp-manager config show             # Display current configuration
llamacpp-manager config add-model <name> --path /path/to/model.gguf
llamacpp-manager config set-port <model> <port>  # Assign specific port
```

### GUI Application

The native macOS menu bar application provides:

- **Menu Bar Icon** - Quick access from anywhere
- **Model Management** - Start/stop models with one click
- **Chat Interface** - Native SwiftUI chat UI
- **Status Dashboard** - Real-time model status and resource usage
- **Settings** - Configure models, ports, and preferences
- **MyRAGDB Integration** - Monitor and control MyRAGDB search service
- **"Stop All Models" Button** - Emergency stop for all running models

**Accessing the GUI:**
1. Launch from Applications folder
2. Click menu bar icon (llama icon)
3. Select "Models" to manage servers
4. Select "Chat" to start conversing

---

## Project Structure

```
llamaCPPManager/
├── src/llamacpp_manager/        # Python CLI source
│   ├── cli.py                   # CLI entry point
│   ├── config.py                # Model configuration
│   ├── chat_storage.py          # SQLite chat history
│   ├── multi_query.py           # Multi-model comparison
│   ├── model_manager.py         # Core model management
│   └── version.py               # Version info
├── gui-macos/                   # Swift GUI application
│   ├── Sources/App.swift        # SwiftUI GUI main file
│   ├── Package.swift            # Swift package manifest
│   ├── rebuild-gui.sh           # Development rebuild script
│   ├── build_app.sh             # Production .app builder
│   └── scripts/                 # Build automation scripts
├── tests/                       # Test suite
│   ├── test_config.py
│   ├── test_model_manager.py
│   └── test_chat_storage.py
├── docs/                        # Documentation
│   ├── VERSION_UPDATE_PROCESS.md
│   ├── STOP_ALL_MODELS.md
│   └── DISTRIBUTION.md
├── Formula/                     # Homebrew formula (future)
├── .projectrc                   # Project path configuration
├── CLAUDE.md                    # Development guidelines
├── CHANGELOG.md                 # Version history
├── build-gui-release.sh         # Unified release builder
├── Makefile                     # Build automation
├── pyproject.toml               # Python package config
└── README.md                    # This file
```

---

## Configuration

### Project Configuration (.projectrc)

The `.projectrc` file maintains consistent path references across development and build processes:

```bash
source .projectrc
echo "Project root: $PROJECT_ROOT"
echo "GUI app path: $APP_PATH"
```

### Model Configuration

Models are configured in `~/.config/llamacpp-manager/models.yaml`:

```yaml
models:
  phi3:
    path: /Users/username/models/phi-3-mini-4k-instruct.Q4_K_M.gguf
    port: 8081
    context_size: 4096
    auto_start: false

  smollm3:
    path: /Users/username/models/SmolLM2-1.7B-Instruct-Q8_0.gguf
    port: 8082
    context_size: 2048
    auto_start: false
```

**Configuration Fields:**
- `path`: Absolute path to GGUF model file
- `port`: Port number for llama-server (8081-8089 recommended)
- `context_size`: Context window size (tokens)
- `auto_start`: Whether to start on system boot (future feature)

### Port Management

llamaCPPManager follows centralized port management via [project-config](../project-config/):

- **Recommended Range:** 8081-8089 (local LLM servers)
- **Reserved:** 8081-8085 (critical LLM services)
- **See:** [PORT-RESERVATIONS.md](PORT-RESERVATIONS.md) for full allocations

---

## Development

### Development Setup

```bash
# Clone and setup
git clone <repository-url>
cd llamaCPPManager

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# All tests
pytest

# Specific test files
pytest tests/test_config.py tests/test_model_manager.py -v

# With coverage
pytest --cov=src/llamacpp_manager --cov-report=html
```

### GUI Development Workflow

**⚠️ CRITICAL:** Follow this workflow EVERY TIME you modify `gui-macos/Sources/App.swift`:

1. **Commit changes first**
   ```bash
   git add gui-macos/Sources/App.swift
   git commit --no-verify -m "fix: description"
   ```

2. **Kill ALL running instances**
   ```bash
   killall "Llama CPP Manager" 2>/dev/null
   pkill -9 swift
   pkill -9 llamacpp-gui
   sleep 2
   ```

3. **Rebuild executable**
   ```bash
   ./gui-macos/rebuild-gui.sh
   ```

4. **Launch updated executable**
   ```bash
   open ./.build/x86_64-apple-macosx/debug/llamacpp-gui
   ```

5. **Verify with user before proceeding**

**Why this workflow?**
- Multiple Swift instances persist with stale code
- `swift run` doesn't always pick up changes
- `.build/` directory caches compiled binaries

See [CLAUDE.md](CLAUDE.md) for detailed GUI development guidelines.

---

## Updating and Releasing

### Automated GUI Release

Use the unified release script to build and publish a new version:

```bash
# From project root
./build-gui-release.sh

# Or from gui-macos directory
cd gui-macos && ./scripts/build-gui-release.sh
```

**This script:**
- Automatically increments version
- Builds GUI application (.app bundle)
- Updates CHANGELOG.md
- Creates git tag
- Installs to /Applications/
- Copies DMG to ~/Downloads/
- Pushes changes to repository

### Manual Update

```bash
# CLI only
pipx install --force .

# GUI only (from gui-macos directory)
cd gui-macos
./build_app.sh
cp -R "build/llamaCPP Manager.app" /Applications/
```

### Versioning

- **Format:** Semantic versioning (v1.2.3)
- **Tracking:** Git tags and CHANGELOG.md
- **Automation:** Versions auto-update in Info.plist and About text
- **Documentation:** [VERSION_UPDATE_PROCESS.md](docs/VERSION_UPDATE_PROCESS.md)

---

## MyRAGDB Integration

llamaCPPManager includes special support for [MyRAGDB](../myragdb/), the hybrid search service:

### Features

- **Status Monitoring** - Check if MyRAGDB is running
- **Startup Control** - Launch MyRAGDB from GUI
- **Health Checks** - Verify MyRAGDB API connectivity
- **Port Coordination** - Ensures no port conflicts (MyRAGDB uses 3003)

### Usage

```bash
# Check MyRAGDB status
llamacpp-manager status --include-myragdb

# Start MyRAGDB (if installed)
# Uses start.sh script from myragdb directory
```

---

## Troubleshooting

### Common Issues

#### **Models Won't Start**

```bash
# Check if port is already in use
lsof -i :8081

# Kill existing process
kill -9 <PID>

# Verify model path exists
llamacpp-manager config show
```

#### **GUI Changes Don't Appear**

Follow the [GUI Development Workflow](#gui-development-workflow) exactly:
1. Commit first
2. Kill ALL processes (`pkill -9 swift`)
3. Rebuild with script
4. Launch fresh executable

#### **Chat History Not Saving**

```bash
# Check database location
ls -la ~/.local/share/llamacpp-manager/chat_history.db

# Verify permissions
chmod 644 ~/.local/share/llamacpp-manager/chat_history.db
```

#### **Import Errors**

```bash
# Reinstall in virtual environment
source .venv/bin/activate
pip install -e .

# Or reinstall with pipx
pipx reinstall .
```

---

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Development guidelines and workflows
- **[VERSION_UPDATE_PROCESS.md](docs/VERSION_UPDATE_PROCESS.md)** - Version management details
- **[STOP_ALL_MODELS.md](docs/STOP_ALL_MODELS.md)** - "Stop All Models" implementation
- **[DISTRIBUTION.md](DISTRIBUTION.md)** - Distribution and packaging guide
- **[GUI_TESTING.md](GUI_TESTING.md)** - GUI testing procedures
- **[INSTALL.md](INSTALL.md)** - Detailed installation guide
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

---

## Project Status

**Current Version:** See [CHANGELOG.md](CHANGELOG.md)
**Last Major Update:** January 2026
**Development Status:** Active

### Recent Changes (January 2026)

- Optimized MyRAGDB startup timing and monitoring thresholds
- Enhanced port management integration
- Improved GUI stability and rebuild workflow
- Added comprehensive testing infrastructure

### Active Development Areas

- Multi-model comparison enhancements
- Chat history search improvements
- GUI performance optimization
- Distribution packaging (Homebrew formula)

---

## Contributing

This is a private project. For questions or collaboration:

**Contact:** libor@arionetworks.com

**Development Guidelines:**
1. Follow [CLAUDE.md](CLAUDE.md) for project-specific standards
2. Use GUI development workflow for Swift changes
3. Add tests for new features
4. Run pytest before committing
5. Use `--no-verify` for commits if pre-existing test failures are unrelated

---

## License

Private project - All rights reserved

---

## Related Projects

- **[myragdb](../myragdb/)** - Hybrid search service for code/documentation discovery
- **[project-config](../project-config/)** - Centralized port management and configuration
- **[xLLMArionComply](../xLLMArionComply/)** - AI-enhanced compliance platform

---

**Questions:** libor@arionetworks.com
