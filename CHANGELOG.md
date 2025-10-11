# Changelog

## [Unreleased]

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