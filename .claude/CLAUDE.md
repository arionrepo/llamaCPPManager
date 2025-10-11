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

- Use semantic versioning (v1.2.3)
- Update `CHANGELOG.md` with each release
- Use git tags to mark releases
- Maintain detailed release notes

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