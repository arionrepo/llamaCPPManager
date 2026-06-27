# Deploy Script Contract

Date: 2026-06-25
Primary script: `./deploy.sh`

## Purpose

`deploy.sh` is the repo-root release/deployment entrypoint for llamaCPPManager. It covers:

- Python CLI packaging and installation via `pipx`
- MCP console-script availability (`llamacpp-mcp-server`)
- macOS GUI installation via the existing `gui-macos/install_gui.sh`
- local verification suitable for aidevops Release Workflow integration

## Subcommands

| Subcommand | Behavior |
| --- | --- |
| `check-deps` | Verifies macOS, Python, Swift, `pipx`, and the Python `build` module. |
| `build` | Runs `python3 -m build` at repo root and `swift build` in `gui-macos/`. |
| `install` | Runs `pipx install --force .` and then installs the GUI via `gui-macos/install_gui.sh --no-launch`. Verifies `llamacpp-manager` and `llamacpp-mcp-server` are on `PATH`. |
| `verify` | Runs `llamacpp-manager status --json`, validates the JSON shape, checks `/Applications/llamaCPP Manager.app`, and verifies both console scripts are on `PATH`. |
| `deploy-local` | Runs `build`, then `install`, then `verify`. |

## Source revision pin

All subcommands accept:

```bash
./deploy.sh <subcommand> --source-revision <sha>
```

The script does not mutate the checkout. It verifies that `git rev-parse HEAD`
matches the requested revision (full SHA or prefix) and exits with code `6` on mismatch.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Generic failure or invalid invocation |
| `2` | Dependency/environment check failed |
| `3` | Build failed |
| `4` | Install failed |
| `5` | Verification failed |
| `6` | Source revision mismatch |

## Notes

- `install` is intentionally idempotent: `pipx install --force .` and `install_gui.sh --no-launch` are safe to re-run on the same machine.
- `verify` writes a temporary JSON snapshot to `/tmp/llamacpp-manager-status.json` during validation.
- The GUI installer remains the canonical implementation of the app-bundle copy/replace/launch logic. `deploy.sh` composes it rather than re-implementing it.
