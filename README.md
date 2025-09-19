# llamaCPPManager

Toolkit for managing local `llama-server` instances (from llama.cpp) on macOS.

## Project Goals
- Provide a macOS-friendly launcher to start/stop/monitor multiple llama.cpp model services.
- Offer simple visibility into model status, ports, and logs.
- Package tooling so it can be launched from the Applications folder with an icon.

See `docs/requirements.md` for the detailed requirements backlog.

## Quick Start (M1 - CLI + Config)

- Install dependencies for development:
  - Python 3.11+ and `pipx` recommended: `pipx install --suffix=@local .` (from repo root)
  - Or use a venv: `python3 -m venv .venv && . .venv/bin/activate && pip install -e .`

- Initialize config and directories (default locations):
  - `llamacpp-manager init`

- Use custom locations (kept outside any repo):
  - `llamacpp-manager --config-dir ~/Configs/llamacpp --log-dir ~/Logs/llamacpp init`
  - These flags work with all commands and keep proprietary paths out of the repo.

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

## Local Testing

- One‑shot run: `make test`
- Unit only: `make test-unit`
- Integration only: `make test-integration`
- Direct script: `bash scripts/run_local_tests.sh`

See `docs/testing.md` for details on test structure and conventions.

- Add a model entry:
  - `llamacpp-manager config add smollm3 ~/llms/smollm3/SmolLM3-Q8_0.gguf --port 8081 --extra-args "-c 8192 -ngl 9999 -t 12 --parallel 4 --cont-batching"`

- View config (human or JSON):
  - `llamacpp-manager config list`
  - `llamacpp-manager config list --json`

More commands will arrive in subsequent milestones (`start/stop/status`, launchd, GUI). See `docs/implementation-plan.md`.
