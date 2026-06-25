# Slice Coverage Audit

Date: 2026-06-25
Plan step: `prereq.audit-existing`
Companion plan: `docs/SLICE-IMPLEMENTATION-PLAN.md`
Companion catalog: `docs/E2E-SLICES.md`

This document maps the existing `tests/test_*.py` pytest suite to the slice catalog. It is an audit of current overlap, not a claim that a file fully covers a slice. Most existing pytest files provide unit or contract coverage for a slice area rather than full real-stack vertical-slice coverage.

Baseline at audit time:
- `pytest tests/ -q`: 135 collected tests, 3 skips, 0 failures when run unsandboxed.
- Existing pytest files: 24.
- Existing Swift tests are intentionally excluded here; this file audits only `tests/test_*.py` as required by Phase 0.3.

## File-to-slice map

| Pytest file | Test count | Primary slice IDs | Audit notes |
| --- | ---: | --- | --- |
| `tests/test_cli_config.py` | 2 | E | CLI config init/list/add/update/remove happy paths. Partial CRUD coverage only. |
| `tests/test_cli_launchd_flags.py` | 1 | D, I | CLI start/stop via `--launchd`; covers launchd-start lifecycle mechanics more than boot/autostart behavior. |
| `tests/test_cli_query.py` | 18 | C, T | CLI `query list/complete/chat` contracts, mostly mocked/unit-style; useful precursor coverage for chat slices, not real-stack slice coverage. |
| `tests/test_cli_start_stop.py` | 1 | D, T | CLI direct start/stop dry-run and pidfile behavior. |
| `tests/test_config.py` | 2 | E | Core config add/update/remove and port-conflict validation. |
| `tests/test_discovery_parse.py` | 1 | Q | Process discovery parsing only. |
| `tests/test_discovery_status.py` | 1 | Q, O | `status --json` fallback to process discovery when pidfile is missing. |
| `tests/test_ensure_running.py` | 2 | I | `ensure-running` for `autostart=true` models. |
| `tests/test_health.py` | 1 | W | Endpoint health probe against a local HTTP server. |
| `tests/test_idempotency.py` | 11 | E, I, U | Idempotent config writes, launchd/plist behavior, and log-related persistence edges. Broad utility coverage, not slice-complete. |
| `tests/test_infrastructure.py` | 22 | K | Infrastructure component config, start/stop/status, launchd/script-managed handling, log-path derivation. Strongest current pytest coverage area. |
| `tests/test_integrations.py` | 12 | none | Continue.dev sync/integration behavior. Useful external-consumer coverage, but not represented as a named slice in `docs/E2E-SLICES.md`. |
| `tests/test_launchd.py` | 1 | I | LaunchAgent plist rendering/program-argument contract. |
| `tests/test_launchd_install_uninstall.py` | 1 | I | CLI install/uninstall of per-model launchd agents. |
| `tests/test_logs.py` | 2 | U, M | Log rotation/append primitives. Backend-only; does not cover Logs Viewer UI flow. |
| `tests/test_mcp_server.py` | 18 | N | MCP tool handlers for list/start/stop/status/query/add/remove. Strong contract coverage, mostly mocked. |
| `tests/test_migrate.py` | 1 | E | Config/log migration path. |
| `tests/test_model_manager.py` | 11 | D, S | Model manager start/stop, exclusive-group behavior, active-model selection, deployment-type handling. Mostly service-layer coverage. |
| `tests/test_ports_and_warnings.py` | 2 | D, T | Busy-port warnings/refusals at config-add and start time. |
| `tests/test_process.py` | 2 | D, U | Process argument construction, logging hookup, and SIGTERM stop path. |
| `tests/test_query.py` | 17 | C | Query endpoint lookup, availability checks, completion/chat requests, and one real-server integration gate. |
| `tests/test_security_and_bincheck.py` | 2 | D, T | Binary presence check and remote-bind safety guard. |
| `tests/test_status.py` | 1 | O, W | `status --json` includes pid/health/infrastructure shape. |
| `tests/test_status_watch.py` | 3 | O, W | Table-vs-JSON consistency and watch-mode behavior; one skip due to signal-handling limitations under pytest. |

## Current coverage shape

Strong partial pytest coverage today:
- K `Infrastructure Components`
- N `MCP Agentic Surface`
- E `Model Configuration CRUD`
- O `status --json` schema-adjacent behavior
- W `Health Endpoint / Watch`
- C `Chat Send & Receive` command/query plumbing

Thin or indirect pytest-only coverage today:
- D `Start/Stop + GUI↔CLI Consistency`
- I `Autostart on Boot`
- Q `Discovery & Auto-detection`
- T `CLI Invocation from External Processes`
- U `Logging Configuration Lifecycle`

No meaningful pytest slice coverage yet:
- F `Model Download from Catalog`
- G `Model Comparison` as a real user flow
- H `Crash Detection & Auto-Restart`
- J `Docker / Colima Profile Lifecycle`
- L `Preferences Edit & Persist`
- M `Logs Viewing & Filtering` as a GUI/user flow
- P `Clean Shutdown & Cleanup`
- R `Bootstrap (mlx-vlm setup)`
- V `Cleanup Command`
- X `Lifecycle Log Schema Stability`
- Y `Minor UI Flows`
- Inst `Deployment & Installation`

## Notes for next phases

- The existing pytest suite is valuable as contract coverage, but it does not satisfy the plan's real-stack vertical-slice requirement on its own.
- Slices K, N, O, and W already have good structural footholds in pytest and should be extended rather than rewritten.
- `tests/test_integrations.py` should remain in place, but the slice catalog currently has no named bucket for Continue.dev sync behavior; if that integration becomes strategically important, consider adding a catalog note rather than forcing it into an unrelated slice.
