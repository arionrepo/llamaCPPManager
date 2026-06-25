# CLI Exit Codes

Date: 2026-06-25

This document locks the externally observable exit-code contract for the `llamacpp-manager` CLI as exercised by `tests/test_cli_external_invocation.py`.

## Stable codes

| Exit code | Contract class | Representative cases |
| --- | --- | --- |
| `0` | Success | `status --json`, `config list --json`, `start --dry-run`, `stop` when the target is stopped successfully |
| `1` | Target/runtime state problem | Missing named model on `config show`, warning-style stop fallback where the command completes but the target was not running, log file not found in some log-tail flows |
| `2` | Usage/config/dependency/application error | Validation failure, binary missing, invalid query message format, unknown subcommand, refused remote bind, missing required dependency such as `llama-server` |
| `130` | Interrupted by user | `install-gui` interrupted with `Ctrl-C` |

## Notes

- The codebase is not yet fully normalized around a single semantic enum. This file documents the current intended operator-facing contract rather than claiming every subcommand has been centrally refactored.
- JSON-producing commands must keep machine-readable payloads on `stdout`. Diagnostics and warnings belong on `stderr`.
- Optional helper tools may degrade gracefully. For example, child-process cleanup in `stop` may warn if `pgrep` is unavailable, but the command can still succeed if the primary stop path succeeds.
