# llamaCPPManager

Toolkit for managing local `llama-server` instances (from llama.cpp) on macOS.

## Project Goals
- Provide a macOS-friendly launcher to start/stop/monitor multiple llama.cpp model services
- Manage supporting infrastructure components (cloudflared tunnel, LLM controller)
- Offer simple visibility into model and infrastructure status, ports, and logs
- Automatic health monitoring and crash recovery with configurable retry policies
- Package tooling so it can be launched from the Applications folder with an icon
- Auto-start capabilities via launchd for persistent operation

See `docs/requirements.md` for the detailed requirements backlog.

## Quick Start (M1 - CLI + Config)

### Installation

- Install dependencies for development:
  - Python 3.11+ and `pipx` recommended: `pipx install .` (from repo root)
  - Or use a venv: `python3 -m venv .venv && . .venv/bin/activate && pip install -e .`

- Initialize config and directories (default locations):
  - `llamacpp-manager init`

- Use custom locations (kept outside any repo):
  - `llamacpp-manager --config-dir ~/Configs/llamacpp --log-dir ~/Logs/llamacpp init`
  - These flags work with all commands and keep proprietary paths out of the repo.

### Updating

To update both CLI and GUI from the repo:

```bash
./update.sh
```

This script:
- Updates CLI via pipx (preserves your config)
- Optionally rebuilds and installs GUI app
- Provides instructions for restarting monitoring daemon

Or update manually:
```bash
# CLI only
pipx install --force .

# GUI only (from gui-macos directory)
cd gui-macos && ./build_app.sh
cp -R "build/llamaCPP Manager.app" /Applications/
```

## Usage Examples

- Add a model (with extra llama-server args):
  - `llamacpp-manager config add smollm3 ~/llms/smollm3/SmolLM3-Q8_0.gguf --port 8081 --extra-args "-c 8192 -ngl 9999 -t 12 --parallel 4 --cont-batching"`

- List config (human):
  - `llamacpp-manager config list`

- List config (JSON for GUI/automation):
  - `llamacpp-manager config list --json`

- Start a model (writes logs and a PID file):
  - `llamacpp-manager start smollm3`

- Start all configured models:
  - `llamacpp-manager start all`

- Dry‑run (print command only, do not start):
  - `llamacpp-manager start smollm3 --dry-run`

- Stop a model (reads PID file and sends SIGTERM):
  - `llamacpp-manager stop smollm3`

- Restart a model:
  - `llamacpp-manager restart smollm3`

- Migrate config and logs to new locations (kept outside your repo):
  - `llamacpp-manager config migrate --to-config-dir ~/Configs/llamacpp --to-log-dir ~/Logs/llamacpp --move --force`
  - After migrating, run commands with `--config-dir/--log-dir` or set `LLAMACPP_MANAGER_CONFIG_DIR` and `LLAMACPP_MANAGER_LOG_DIR`.

Notes:
- The CLI writes per‑model logs to the configured log directory and rotates them when large.
- PID files are maintained under the config directory in a `pids/` subfolder (overridable via `LLAMACPP_MANAGER_PID_DIR`).

### launchd integration

- Install launchd agents for one or all models:
  - `llamacpp-manager launchd install smollm3`
  - `llamacpp-manager launchd install all`
  - This writes `~/Library/LaunchAgents/ai.llamacpp.<name>.plist`, bootstraps and kickstarts it.

- Uninstall launchd agents:
  - `llamacpp-manager launchd uninstall smollm3`
  - `llamacpp-manager launchd uninstall all`

Notes:
- launchd mode is optional; direct start/stop works without it.
- Plists point stdout/stderr to `<log_dir>/<name>.out.log|.err.log` and keep the service alive.

### Auto-start missing services

- Start any models marked `autostart: true` that are currently unreachable:
  - Direct mode: `llamacpp-manager ensure-running`
  - Launchd mode: `llamacpp-manager ensure-running --mode launchd`
  - This uses a quick health check per model and starts only those that are down.

### Query models

- List available models:
  - `llamacpp-manager query list`

- Get text completion from a model:
  - `llamacpp-manager query complete model-name "Hello world"`
  - `llamacpp-manager query complete model-name "Hello world" --max-tokens 256 --temperature 0.9`
  - `llamacpp-manager query complete model-name "Hello world" --stream`

- Chat with a model:
  - `llamacpp-manager query chat model-name --message "user:Hello there"`
  - `llamacpp-manager query chat model-name --message "system:You are helpful" --message "user:Hello"`
  - `llamacpp-manager query chat model-name --message "user:Hello" --stream`

### Infrastructure Management

**⚠️ Platform: macOS only - Local components on the same machine**

Manage supporting infrastructure components running on your Mac alongside your models.

**Current Scope**: 2 specific local components:
- `cloudflared` - Cloudflare tunnel (via launchd)
- `llm_controller` - Local HTTP controller service (http://127.0.0.1:8090)

**Limitations**: Not for remote infrastructure, multi-platform deployments, or cloud services. All components must run on the same macOS machine as llamaCPPManager.

- List configured infrastructure components:
  - `llamacpp-manager infra list`

- View infrastructure status:
  - `llamacpp-manager infra status`

- Control individual components:
  - `llamacpp-manager infra start cloudflared`
  - `llamacpp-manager infra stop llm_controller`
  - `llamacpp-manager infra restart cloudflared`

- View component logs:
  - `llamacpp-manager infra logs llm_controller`

- View combined status (models + infrastructure):
  - `llamacpp-manager status --json`

Infrastructure components are configured in `config.yaml` under the `infrastructure` section. See `docs/infrastructure-implementation-summary.md` for complete details and limitations.

### Health Monitoring & Auto-Restart

Monitor models and infrastructure components with automatic restart on failure:

- Track a model for auto-restart:
  - `llamacpp-manager monitor track smollm3`

- Stop tracking a model:
  - `llamacpp-manager monitor untrack smollm3`

- View monitoring status:
  - `llamacpp-manager monitor status`
  - `llamacpp-manager monitor status --detailed`

- Start monitoring daemon:
  - `llamacpp-manager monitor start`

- Stop monitoring daemon:
  - `llamacpp-manager monitor stop`

- Install monitoring daemon as launchd agent (auto-start on boot):
  - `llamacpp-manager monitor launchd install`
  - `llamacpp-manager monitor launchd status`
  - `llamacpp-manager monitor launchd uninstall`

The monitoring daemon runs in the background and automatically restarts tracked models and enabled infrastructure components when they crash or become unhealthy. It uses exponential backoff with configurable retry limits.

### MCP Server

Run as an MCP (Model Context Protocol) server to expose llamaCPPManager functionality to AI assistants:

**Quick Start**:
```bash
# Start MCP server (stdio protocol)
llamacpp-mcp-server
```

**Claude Desktop Configuration** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "llamacpp-manager": {
      "command": "llamacpp-mcp-server"
    }
  }
}
```

**Available MCP Tools** (9 total):
- `list_models` - List all configured models
- `list_available_models` - List running models only
- `start_model` - Start a model server
- `stop_model` - Stop a model server
- `model_status` - Get detailed health status
- `query_completion` - Get text completions from models
- `query_chat` - Have conversations with models
- `add_model` - Add new model configuration
- `remove_model` - Remove model configuration

**Example AI Interactions**:
- "Start my phi3 model and ask it to explain quantum computing"
- "Which of my models are currently running?"
- "Add llama3 model from ~/llms/llama3.gguf on port 8084"

**Documentation**: See [MCP Server API Guide](docs/mcp-server-api.md) for complete documentation with examples, workflows, and troubleshooting.

## Security Notes

- Local binds by default: models should bind to `127.0.0.1` (or `localhost`).
- The CLI refuses to start models bound to non‑local hosts unless you pass `--allow-remote` explicitly (e.g., for a trusted LAN).
- Port checks: the CLI detects when a target port is already in use and will refuse to start a model on that port.
- Binary check: `llamacpp-manager start` validates that `llama_server_path` exists and is executable (bypass for tests via `LLAMACPP_MANAGER_SKIP_BIN_CHECK=1`).

## Local Testing

- One‑shot run: `make test`
- Unit only: `make test-unit`
- Integration only: `make test-integration`
- Direct script: `bash scripts/run_local_tests.sh`

See `docs/testing.md` for details on test structure and conventions.

## GUI (SwiftUI Menu Bar)

### Features

The menu bar GUI provides a visual interface for managing both models and infrastructure:

- **Infrastructure Section**: View and control infrastructure components (cloudflared, llm_controller)
  - Health indicators (🟢 healthy, 🟠 unhealthy, 🔴 stopped, ⚫ disabled)
  - Start/Stop/Restart/Logs buttons for each component
  - Real-time status updates

- **Models Section**: Manage llama.cpp model servers
  - Health indicators and latency display
  - Start/Stop/Restart/Chat/Monitor/Logs buttons
  - Process status and HTTP health check results

- **Global Actions**: Ensure Running, Refresh, Config, CLI access
- **Auto-polling**: Status updates every 2 seconds

### Building and Running

- Location: `gui-macos/` (Swift Package with an executable target)

- Build app bundle:
  - `cd gui-macos && ./build_app.sh`
  - Creates `build/llamaCPP Manager.app` and DMG

- Install to Applications:
  - `cp -R "build/llamaCPP Manager.app" /Applications/`

- Install GUI auto-start (optional):
  - `cd gui-macos && ./install_gui_launchagent.sh`
  - Configures app to launch automatically on login

- Run tests:
  - `make gui-test` (runs `swift test` in `gui-macos/`)

- Run from Xcode:
  - Open `gui-macos/Package.swift` in Xcode
  - Run the `llamacpp-gui` scheme
  - The app appears in the menu bar as "🧠 llamaCPP"

### Requirements

- The GUI calls the CLI `llamacpp-manager` under the hood. Ensure it's on your PATH or at one of:
  - `/opt/homebrew/bin/llamacpp-manager`
  - `/usr/local/bin/llamacpp-manager`
  - `~/.local/bin/llamacpp-manager`

- To use a custom config/logs location set in the CLI, export:
  - `LLAMACPP_MANAGER_CONFIG_DIR=/path/to/config`
  - `LLAMACPP_MANAGER_LOG_DIR=/path/to/logs`


- Add a model entry:
  - `llamacpp-manager config add smollm3 ~/llms/smollm3/SmolLM3-Q8_0.gguf --port 8081 --extra-args "-c 8192 -ngl 9999 -t 12 --parallel 4 --cont-batching"`

- View config (human or JSON):
  - `llamacpp-manager config list`
  - `llamacpp-manager config list --json`

More commands will arrive in subsequent milestones (`start/stop/status`, launchd, GUI). See `docs/implementation-plan.md`.
