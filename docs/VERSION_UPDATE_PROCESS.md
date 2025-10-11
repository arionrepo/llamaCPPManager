# Version Update Process for LlamaCPP Manager GUI

## Automatic Version Updating

The build script (`gui-macos/build_app.sh`) automatically updates the version in two key places:

1. **Info.plist**: Sets `CFBundleShortVersionString` and `CFBundleVersion`
2. **About Text**: Updates the version in the `aboutText` constant in `Sources/App.swift`

### Version Sourcing

The version is sourced from git tags, with the following priority:
1. Latest git tag (preferred)
2. Fallback to hardcoded version "1.1.0"

### Version Formats

- Git tag must start with 'v' (e.g., `v1.1.0`)
- Semantic versioning is enforced
- Example: `v1.1.0`, `v1.2.3-beta`

## Recommended Workflow

1. Create a new git tag for the release:
   ```bash
   git tag -a v1.2.0 -m "Release v1.2.0: Feature Description"
   ```

2. Build the application:
   ```bash
   cd gui-macos
   ./build_app.sh
   ```

The build script will automatically:
- Retrieve the version from the git tag
- Update Info.plist
- Update About text
- Build the application bundle

## Manual Override

If needed, you can manually set the version in the build script by modifying the fallback version.