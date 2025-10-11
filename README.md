# llamaCPPManager

Toolkit for managing local `llama-server` instances (from llama.cpp) on macOS.

## Project Configuration

### Directory Paths

The project uses a `.projectrc` file located in the project root to maintain consistent path references across development and build processes. This file contains environment variables defining key project paths.

**Location**: `/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/.projectrc`

To use these paths in scripts:
```bash
source .projectrc
echo "Project root is at: $PROJECT_ROOT"
echo "GUI Application is at: $APP_PATH"
```

### Version Management

For detailed information on how versions are managed in the GUI application, see [Version Update Process](docs/VERSION_UPDATE_PROCESS.md).

Key points:
- Versions are sourced from git tags
- Automatic updates to Info.plist and About text
- Semantic versioning enforced

### Model Management

For details on the "Stop All Models" functionality, see [Stop All Models Implementation](docs/STOP_ALL_MODELS.md).

## Updating and Releasing

### Automated GUI Release

Use the unified GUI release script to build and publish a new version:

```bash
# From project root
./build-gui-release.sh

# Or from gui-macos directory
./scripts/build-gui-release.sh
```

This script:
- Automatically increments version
- Builds GUI application
- Updates CHANGELOG
- Creates git tag
- Installs to Applications
- Copies DMG to Downloads
- Pushes changes to repository

### Manual Update

Update CLI or GUI manually:
```bash
# CLI only
pipx install --force .

# GUI only (from gui-macos directory)
cd gui-macos && ./build_app.sh
cp -R "build/llamaCPP Manager.app" /Applications/
```

### Versioning

- Uses semantic versioning (v1.2.3)
- Automatically updates Info.plist and About text
- Version tracked in git tags and CHANGELOG
- See [Version Update Process](docs/VERSION_UPDATE_PROCESS.md) for details