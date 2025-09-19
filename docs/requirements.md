# llamaCPPManager Requirements

## 1. Purpose
Create a lightweight macOS-friendly utility that helps operate multiple `llama-server` (llama.cpp) instances, exposing easy start/stop controls, health status, and quick access to logs/configs.

## 2. Target Environment
- macOS (Apple Silicon, Ventura or newer)
- Existing llama.cpp installations via Homebrew (`/opt/homebrew/bin/llama-server`)
- Models hosted locally under `~/llms/...`

## 3. Functional Requirements
1. **Service Discovery**: Detect currently running `llama-server` processes and capture model path, port, and runtime settings.
2. **Process Control**: Provide start/stop/restart actions for configured models.
3. **Configuration Management**: Store model definitions (name, GGUF path, port, launch flags) in a simple config file (YAML or JSON).
4. **Status Dashboard**: Present health (reachable, responding latency) and log tails for each configured model.
5. **Application Launcher**: Ship as a double-clickable macOS app/shortcut placed in Applications, optionally built via `py2app`, `Platypus`, or Automator.
6. **Logging**: Centralize stdout/stderr from each managed process into rotating log files.

## 4. Non-Functional Requirements
- Clear CLI usage with helpful `--help` output.
- Configurable via environment variables for advanced users.
- Minimal dependencies; prefer Python standard library where feasible.
- Safe shutdown handling to avoid orphaned processes.

## 5. Stretch Goals (Optional)
- Menu bar widget showing live status.
- Prometheus endpoint exposing metrics.
- Quick actions to switch model quantizations or update binaries.

## 6. Open Questions
- Preferred implementation language (Python vs Swift/SwiftUI).
- Desired packaging approach for the macOS app icon/launcher.
- Need for multi-user support or per-user configs.

Update this document as requirements evolve.
