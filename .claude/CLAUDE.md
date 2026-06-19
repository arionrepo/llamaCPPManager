# Project-Level Claude Development Guidelines

**Last Updated**: 2025-10-11
**Author**: Libor Ballaty <libor@arionetworks.com>

## Project Configuration

### Project Paths

The project uses a `.projectrc` file in the project root to manage consistent path references. Always source this file before working on the project:

```bash
source .projectrc
```

Key paths include:
- `$PROJECT_ROOT`: Base project directory
- `$GUI_DIR`: GUI application source
- `$CLI_DIR`: CLI source code
- `$APP_PATH`: Path to the built macOS application

### Versioning Strategy

This project (and **all repos owned by this user**, globally) uses
**date-based versioning with daily sequence**:

```
YYYY.MM.DD.N
```

Where `N` is the chronological build number for that day (starts at 1, increments
for additional builds on the same calendar day). Example: `2026.06.19.3` is the
3rd release made on June 19, 2026.

**Canonical source of truth**: the `VERSION` file at repo root.

**Bumping the version**: use the `/version-bump` slash command, which invokes
`/Users/liborballaty/.ai-dev-dotfiles/tools/version-bump.py`. The tool:
- Reads current `VERSION` file
- If same day → increments `.N`
- If new day → resets to `YYYY.MM.DD.1`
- Writes the new value back

**Where the version is read for builds**:
- `gui-macos/build_app.sh` reads `VERSION` first, falls back to latest git tag
- `gui-macos/Sources/App.swift` has `APP_VERSION` updated in place by `build_app.sh`
- `pyproject.toml` Python package version can be aligned manually if needed

**Release process**:
1. Make and commit code changes
2. Run `/version-bump` (or `python3 ~/.ai-dev-dotfiles/tools/version-bump.py`)
3. Update `CHANGELOG.md` with the new version's changes
4. Optionally tag in git: `git tag v$(cat VERSION)` (not strictly required —
   `build_app.sh` reads `VERSION` directly, not the tag)
5. Build: `llamacpp-manager install-gui --force` (or `gui-macos/build_app.sh`
   manually)
6. Commit `VERSION` + `CHANGELOG.md`

**Note**: previously this file recommended semantic versioning (`v1.2.3`).
That was superseded by the date-based scheme adopted across all of this
user's repos. Legacy `v1.x` tags from 2025 are preserved in git history
but new releases use the date scheme.

## Development Workflow

### Project Setup
1. Always source `.projectrc`
2. Verify project paths before starting work
3. Validate CLI is installed: `.venv/bin/llamacpp-manager`

### Commit Guidelines
- Provide clear, concise commit messages
- Reference specific changes
- Include emoji for visual identification
- Format: `type: Description of changes`
  - Example: `feat: Add dark mode toggle`
  - Example: `fix: Resolve model download filtering issue`

### Version Update Process
1. Update `CHANGELOG.md`
2. Create git tag
3. Build app with new version
4. Commit and push changes

## Code Quality

### Mandatory Checks
- Run tests before committing: `pytest tests/`
- Verify CLI and GUI build successfully
- Ensure no uncommitted changes in critical files

### Specific Project Requirements
- Swift code must compile without warnings
- Python code must pass type checking
- All new features require unit tests
- Update documentation for significant changes

## Security Considerations

- Never commit sensitive information
- Use environment variables for secrets
- Validate all user inputs
- Implement proper error handling

## Logging and Debugging

- Use structured logging
- Include context in error messages
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Provide clear, actionable log messages

## Performance Monitoring

- Profile GUI and CLI for performance
- Monitor memory usage
- Track startup and operation times
- Optimize critical code paths