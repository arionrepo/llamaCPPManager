# Changelog

This project uses date-based versioning: `YYYY.MM.DD.N`. The current version
is in the repo's `VERSION` file. Use `/version-bump` or
`python3 ~/.ai-dev-dotfiles/tools/version-bump.py` to bump.

## [Unreleased]

## [2026.06.19.1] - 2026-06-19

### Added
- **Deterministic GUI installer** (`gui-macos/install_gui.sh`) — single
  command replaces the brittle `killall + rm + cp + open` pipeline.
  Auto-detects rebuild need, verifies MD5 of installed binary, reports
  version, confirms process is running. Distinct exit codes per failure mode.
- **CLI wrapper** `llamacpp-manager install-gui` with `--no-rebuild`,
  `--no-launch`, `--force`, `--quiet` flags. Lifecycle events:
  `cli.install_gui.{begin,result,interrupted}`.
- **Slash command** `/install-gui` in `.claude/commands/install-gui.md` for
  agentic / Claude Code use.
- **MLX-VLM deployment backend** for diffusion / vision-language models.
  - `src/llamacpp_manager/mlx_vlm_process.py` (new spawner with
    `start_new_session=True` for proper detachment + pre-flight check
    that emits actionable bootstrap-instruction errors).
  - `cmd_start` gained a new `elif spec.deployment_type == "mlx-vlm"` branch
    placed above existing branches so they remain byte-identical.
  - 4 new catalog entries: `mlx-diffusiongemma-26b-{4,5,6,8}bit` routed
    to `mlx_vlm.server`.
  - Legacy `diffusiongemma-26b` GGUF entry renamed to
    `-gguf-legacy` and marked `deprecated: true`.
- **`llamacpp-manager bootstrap mlx-vlm`** command — creates dedicated
  venv at `~/mlx_vlm_env`, installs mlx-vlm, auto-updates config with
  `mlx_vlm_python_path`. Lifecycle events:
  `bootstrap.mlx_vlm.{begin,success,failure,warning}`.
- **GUI awareness** of `deployment_type == "mlx-vlm"` (routes Start clicks
  through CLI `start`, which uses the Phase 1b branch). New pink
  `DIFFUSION` badge color in `formatBadgeColor()`.
- **JSON status payload** now carries `engine`, `deployment_type`,
  `experimental`, `deprecated`, `note` pass-through fields for the GUI.
- **README**: new "Supported Backends" table (native / container / mlx /
  mlx-vlm) and "Lifecycle Diagnostics" section.

### Changed
- `--deployment-type` argparse choices in `config add` now include
  `mlx-vlm` alongside `native`, `container`, `mlx`.
- `validate_model()` skips local-file-exists check for `mlx-vlm` models
  (they use HuggingFace repo IDs, downloaded lazily by `mlx_vlm.server`).
- `CLAUDE.md` GUI workflow now leads with `llamacpp-manager install-gui`;
  the 5-step manual sequence is preserved in a `<details>` block.
- `.claude/CLAUDE.md` versioning strategy clarified: date-based
  `YYYY.MM.DD.N` (not semver). Documents `/version-bump` and the
  canonical `VERSION` file.

### Notes
- Existing GGUF (`native`) and MLX (`mlx`) deployment paths verified
  unchanged across 7 phased commits (`git diff --stat` empty for
  `process.py`, `mlx_process.py`, `health.py`, `query.py`,
  `docker_manager.py`, `monitor.py`).

## [2026.06.16.2] - 2026-06-16
- Enriched model rows in GUI: filename, quantization badge, file size,
  live RAM / CPU% when running, catalog description.

## [2026.06.16.1] - 2026-06-16
- Structured lifecycle event log
  (`~/Library/Logs/llamaCPPManager/lifecycle.jsonl`).
- `llamacpp-manager lifecycle` diagnostic command with `--tail`, `--model`,
  `--follow`, `--path`.
- Fixed `start_process` Popen calls to use `start_new_session=True` so
  llama-server children survive the parent CLI exiting (was the cause of
  models dying ~25-30s after start).
- Active Downloads section pinned to top of menu bar; auto-detects
  externally-started downloads / loads.
- Catalog cleanup: filename case-sensitivity fixes + 7 stale repos replaced.

## [2026.03.26] - 2026-03-26
- Automated release
- Includes latest improvements and bug fixes
## [1.1.14] - 2025-10-11
- Automated release
- Includes latest improvements and bug fixes
## [1.1.13] - 2025-10-11
- Automated release
- Includes latest improvements and bug fixes
## [1.1.12] - 2025-10-11
### Fixed
- Version alignment across all artifacts (Info.plist, DMG filename, About dialog)
- DMG filename now uses numeric version without 'v' prefix
- Info.plist now uses numeric version per Apple standards
- Build script commits are now part of release process

## [1.1.11] - 2025-10-11
### Fixed
- About dialog now dynamically uses APP_VERSION constant
- Added Release Notes link to About dialog
- Improved version update mechanism with perl replacement

## [v1.1.0] - 2025-10-11
### Added
- Enhanced Model Downloader filtering mechanism
- More inclusive model filtering across different use cases
- Expanded search criteria for model categories (Agentic AI, Coding, Compliance, General)
- Improved versioning mechanism for GUI
- Added git-based version tracking in build script

### Improvements
- Model downloader now shows more diverse models
- Improved use case and description matching logic
- Better visibility of available models across different categories

### Fixed
- Model downloader filtering mechanism
- Potential issues with model list display
- Logging and error handling in the model download process

## [v1.0.0] - 2025-10-10
### Initial Release
- Basic model management functionality
- MenuBar extra interface for llamaCPP Manager