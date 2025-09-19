# llamaCPPManager — Design

## Overview
A macOS‑friendly toolkit to configure, launch, and monitor multiple llama.cpp `llama-server` instances with clear status, logs, optional autostart via launchd, and a native menu bar GUI.

## Architecture

```mermaid
graph TD
  U[User] -->|Menu actions| GUI[SwiftUI Menu Bar App]
  U -->|Terminal| CLI[llamacpp-manager CLI]

  subgraph Core_Modules_Python
    CLI --> CFG[config.py]
    CLI --> PROC[process.py]
    CLI --> H[health.py]
    CLI --> L[logs.py]
    CLI --> LD[launchd.py]
  end

  GUI -->|exec and parse JSON| CLI

  CFG -->|YAML read and write| Y[Config: ~/Library/Application Support/llamaCPPManager/config.yaml]
  L -->|append and rotate| LOGS[Logs: ~/Library/Logs/llamaCPPManager/*.log]

  PROC -->|spawn or terminate| OS([macOS])
  OS -->|exec| S1[llama-server A]
  OS -->|exec| S2[llama-server B]
  OS -->|exec| S3[llama-server C]

  LD -->|generate and load| P1[launchd agents]
  P1 --> OS

  H -->|HTTP checks| S1
  H -->|HTTP checks| S2
  H -->|HTTP checks| S3
```

Communication paths:
- GUI → CLI: invoke subcommands, parse `--json` outputs
- CLI ↔ Config: YAML load/validate/write
- CLI → Process: subprocess spawn/terminate; optional `launchctl` for launchd mode
- Health → Server: HTTP on `host:port` (local by default)
- Logs: process stdout/stderr → rotating files

## Start/Stop Flow (Direct Mode)

```mermaid
sequenceDiagram
  participant U as User
  participant GUI as GUI SwiftUI
  participant CLI as CLI llamacpp-manager
  participant CFG as config.py
  participant PROC as process.py
  participant OS as macOS
  participant S as llama-server
  participant LOG as log file

  U->>GUI: Start model
  GUI->>CLI: start <name>
  CLI->>CFG: load and validate (model, ports, paths)
  CFG-->>CLI: model spec (args, env, port)
  CLI->>PROC: spawn (stdout and stderr to LOG)
  PROC->>OS: exec llama-server ...
  OS->>S: start process
  S-->>LOG: write stdout and stderr
  CLI-->>GUI: ok with pid and log path
```

## Autostart Flow (launchd Mode)

```mermaid
sequenceDiagram
  participant GUI as GUI
  participant CLI as CLI
  participant LD as launchd.py
  participant PLIST as ai.llamacpp.<name>.plist
  participant LCTL as launchctl
  participant S as llama-server

  GUI->>CLI: launchd install <name>
  CLI->>LD: render plist (ProgramArguments, Env, Logs, KeepAlive)
  LD->>PLIST: write LaunchAgents plist
  CLI->>LCTL: bootstrap gui/$UID plist
  LCTL->>S: manage lifecycle (RunAtLoad and KeepAlive)
  CLI-->>GUI: installed and active
```

## Status/Health Poll

```mermaid
sequenceDiagram
  participant GUI as Menu Bar App (refresh N seconds)
  participant CLI as llamacpp-manager
  participant DISC as process discovery
  participant H as health.py
  participant S as llama-server

  loop every N seconds
    GUI->>CLI: status --json
    CLI->>DISC: ps and launchctl discovery
    CLI->>H: check each host:port
    H->>S: GET /v1/models or /
    S-->>H: 200 with latency and version
    H-->>CLI: aggregated status
    CLI-->>GUI: status JSON array
    GUI-->>GUI: update menu items and badges
  end
```

## Data Model (Config)

- Location: `~/Library/Application Support/llamaCPPManager/config.yaml`
- Schema (simplified):
  - `llama_server_path` (string; default `/opt/homebrew/bin/llama-server`)
  - `log_dir` (string; default `~/Library/Logs/llamaCPPManager`)
  - `timeout_ms` (int; default 2000)
  - `models[]`:
    - `name` (unique)
    - `model_path` (GGUF)
    - `host` (default `127.0.0.1`)
    - `port` (unique)
    - `args[]` (additional flags, e.g., `-c`, `8192`, `-ngl`, `9999`)
    - `env{}` (optional)
    - `autostart` (bool)

Example:
```yaml
llama_server_path: /opt/homebrew/bin/llama-server
log_dir: /Users/you/Library/Logs/llamaCPPManager
timeout_ms: 2000
models:
  - name: smollm3
    model_path: /Users/you/llms/smollm3/SmolLM3-Q8_0.gguf
    host: 127.0.0.1
    port: 8081
    args: ["-c","8192","-ngl","9999","-t","12","--parallel","4","--cont-batching"]
    env: {}
    autostart: true
```

## CLI Surface

- `init` – create config and dirs
- `config add|remove|update|list` – manage model entries with validation
- `start <name|all>` – direct or `--launchd`; `--dry-run`
- `stop <name|all>` – direct or `--launchd`
- `restart <name|all>`
- `status [--json] [--watch]`
- `logs <name|all> [--tail]`
- `launchd install|uninstall <name|all>`

## GUI (SwiftUI Menu Bar)

- Status list with per‑model indicators (up/down, latency, pid, port)
- Actions: Start, Stop, Restart, Tail Logs, Open Config, Refresh
- Preferences: `llama_server_path`, `log_dir`, refresh interval, launch at login
- Communication: run CLI with `Process`, parse JSON; no long‑lived daemon

## Logging

- Per‑model rotating logs in `log_dir` (e.g., 10MB × 5)
- CLI shortcuts:
  - `logs <name> --tail`
  - `logs --all --tail`

## Error Handling

- Missing `llama-server`, bad `model_path`, or busy `port` → clear messages + exit codes
- Graceful shutdown with timeout fallback

## Packaging

- Python package with console script `llamacpp-manager` (pipx‑friendly)
- GUI app in `gui-macos/` (SwiftUI, macOS 14+), distributed as `.app`
- Optional Automator app as interim launcher

## GUI Mockups

The following Mermaid diagrams approximate the menu bar dropdown and a simple preferences window for a native macOS app. These are conceptual wireframes to communicate layout and actions; final visuals will follow macOS system styles.

```mermaid
flowchart TB
  subgraph Menu_Bar_Dropdown
    title[llamaCPPManager]
    status[Overall status: 2 running, 1 stopped]

    sm[SmolLM3 127.0.0.1:8081 UP 12ms]
    sm_actions[Start  Stop  Restart  Tail Logs]

    mi[Mistral7B 127.0.0.1:8082 UP 18ms]
    mi_actions[Start  Stop  Restart  Tail Logs]

    phi[Phi3 127.0.0.1:8083 DOWN]
    phi_actions[Start  Stop  Restart  Tail Logs]

    sep1[---]
    prefs[Preferences]
    open_cfg[Open Config]
    sep2[---]
    quit[Quit]
  end

  status --> sm
  status --> mi
  status --> phi
  sm --> sm_actions
  mi --> mi_actions
  phi --> phi_actions
  prefs -.-> open_cfg
```

```mermaid
flowchart LR
  subgraph Preferences_Window
    hdr[Preferences]
    llama_path[Llama server path]
    log_dir[Log directory]
    refresh_int[Refresh interval seconds]
    launch_login[Launch at login toggle]
    sep[---]
    save_btn[Save]
    cancel_btn[Cancel]
  end

  hdr --> llama_path --> log_dir --> refresh_int --> launch_login
  launch_login --> save_btn
  launch_login --> cancel_btn
```
