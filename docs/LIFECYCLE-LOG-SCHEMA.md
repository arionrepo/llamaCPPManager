# Lifecycle Log Schema

Date: 2026-06-25
Source of truth for file format: `~/Library/Logs/llamaCPPManager/lifecycle.jsonl`

## Envelope

Every lifecycle line is one JSON object.

Required on every line:

| Field | Type | Notes |
| --- | --- | --- |
| `ts` | string | Timestamp string as emitted by the producer. Python currently uses `YYYY-MM-DDTHH:MM:SS+ZZZZ`; GUI currently uses ISO-8601 UTC with `Z`. |
| `event` | string | Dot-namespaced event name. |
| `pid_self` | integer | PID of the emitting process. |

Optional common fields:

| Field | Type |
| --- | --- |
| `ppid` | integer |
| `source` | string |
| `model` | string |
| `caller` | string |
| `pid` | integer |

Rule:
- Unknown extra fields are allowed. Event-specific payloads extend the common envelope.

## Event Contract

The table below lists every event name emitted by the current source tree and the required event-specific fields beyond the common envelope.

| Event | Required event-specific fields | Source |
| --- | --- | --- |
| `bootstrap.mlx_vlm.begin` | `caller:string`, `pip_spec:string`, `venv_path:string` | `src/llamacpp_manager/bootstrap.py` |
| `bootstrap.mlx_vlm.failure` | `reason:string` and either `stderr:string` or `arch:string` + `platform:string` | `src/llamacpp_manager/bootstrap.py` |
| `bootstrap.mlx_vlm.success` | `mlx_vlm_version:string`, `python_path:string`, `venv_path:string` | `src/llamacpp_manager/bootstrap.py` |
| `bootstrap.mlx_vlm.warning` | `reason:string`, `stderr:string` | `src/llamacpp_manager/bootstrap.py` |
| `cli.chat.reply_failed` | `model:string`, `error:string` | `gui-macos/Sources/ViewModels/ChatViewModel.swift` |
| `cli.chat.reply_received` | `model:string`, `reply_length:integer` | `gui-macos/Sources/ViewModels/ChatViewModel.swift` |
| `cli.install_gui.begin` | `caller:string`, `flags:object|array|string`, `script:string` | `src/llamacpp_manager/cli.py` |
| `cli.install_gui.interrupted` | none | `src/llamacpp_manager/cli.py` |
| `cli.install_gui.result` | `exit_code:integer` | `src/llamacpp_manager/cli.py` |
| `cli.start.begin` | `caller:string`, `dry_run:boolean`, `launchd:boolean`, `target:string` | `src/llamacpp_manager/cli.py` |
| `cli.status.fetched` | `model_count:integer`, `infrastructure_count:integer` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `cli.stop.begin` | `caller:string`, `launchd:boolean`, `target:string` | `src/llamacpp_manager/cli.py` |
| `monitor.check_health` | `caller:string`, `health_state:string`, `model:string`, `pid:integer`, `process_state:string` | `src/llamacpp_manager/monitor.py` |
| `monitor.restart.begin` | `caller:string`, `model:string` | `src/llamacpp_manager/monitor.py` |
| `process.start.begin` | `argv:array`, `caller:string`, `deployment:string`, `model:string`, `port:integer` | Python and MLX/MLX-VLM process starters |
| `process.start.begin` for native-only logging path | plus `logging_enabled:boolean`, `timestamps:boolean` | `src/llamacpp_manager/process.py` |
| `process.start.child_resolved` | `llama_server_pid:integer`, `model:string`, `returned_pid:integer`, `wrapper_pid:integer` | `src/llamacpp_manager/process.py` |
| `process.start.direct_spawned` | `mode:string`, `model:string`, `pid:integer` | `src/llamacpp_manager/process.py`, `mlx_process.py`, `mlx_vlm_process.py` |
| `process.start.preflight_failed` | `caller:string`, `model:string`, `reason:string` | `src/llamacpp_manager/mlx_vlm_process.py` |
| `process.start.spawn_failed` | `caller:string`, `error:string`, `error_type:string`, `model:string` | `src/llamacpp_manager/mlx_vlm_process.py` |
| `process.start.wrapper_spawned` | `model:string`, `pid:integer`, `wrapper_path:string` | `src/llamacpp_manager/process.py` |
| `process.stop.error` | `error:string`, `error_type:string`, `pid:integer` | `src/llamacpp_manager/process.py` |
| `process.stop.exited_after_sigterm` | `pid:integer` | `src/llamacpp_manager/process.py` |
| `process.stop.exited_before_sigkill` | `pid:integer` | `src/llamacpp_manager/process.py` |
| `process.stop.no_such_process` | `error:string`, `pid:integer` | `src/llamacpp_manager/process.py` |
| `process.stop.sigkill` | `pid:integer`, `reason:string` | `src/llamacpp_manager/process.py` |
| `process.stop.sigterm` | `caller:string`, `pid:integer`, `timeout:number` | `src/llamacpp_manager/process.py` |
| `ui.app.did_finish_launching` | `activation_policy:integer` | `gui-macos/Sources/AppDelegate.swift` |
| `ui.app.last_window_closed` | `activation_policy:integer`, `returning:boolean` | `gui-macos/Sources/AppDelegate.swift` |
| `ui.app.will_terminate` | `activation_policy:integer`, `windows_open:integer` | `gui-macos/Sources/AppDelegate.swift` |
| `ui.chat.window_did_close` | `model:string`, `activation_policy_after:integer`, `visible_windows_after_close:integer` | `gui-macos/Sources/Delegates/ChatWindowDelegate.swift` |
| `ui.chat.window_opened` | `model:string`, `activation_policy_after:integer`, `activation_policy_before:integer` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `ui.chat.window_reactivated` | `model:string`, `activation_policy_after:integer`, `activation_policy_before:integer` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `ui.chat.window_will_close` | `model:string`, `activation_policy_before:integer`, `visible_windows_before_close:integer` | `gui-macos/Sources/Delegates/ChatWindowDelegate.swift` |
| `ui.start.cli_invoke` | `model:string`, `command:string`, `deployment:string` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `ui.start.cli_result` | `model:string`, `command:string`, `exit_code:integer` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `ui.start.clicked` | `model:string`, `deployment:string`, `isDocker:boolean`, `mode:string` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `ui.start.failure_surfaced` | `model:string`, `reason:string` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `ui.stop.cli_invoke` | `model:string`, `command:string` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `ui.stop.cli_result` | `model:string`, `command:string`, `exit_code:integer` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |
| `ui.stop.clicked` | `model:string`, `isDocker:boolean` | `gui-macos/Sources/ViewModels/StatusViewModel.swift` |

## Stability rules

- Producers may add new optional fields, but existing required fields for an event name must not disappear or change type silently.
- Producers may emit different timestamp formats as long as `ts` remains a string. Consumers must not parse on one exact format only.
- Multiple producers append to the same file. Consumers must not assume key order.
- Rotation must preserve line-level JSON validity in both the rotated file and the newly reopened active file.
