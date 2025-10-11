#!/bin/bash
# Unified release script for LlamaCPP Manager

set -euxo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Version increment function
increment_version() {
    local version="${1#v}"  # Remove leading 'v'
    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)
    local patch=$(echo "$version" | cut -d. -f3)

    patch=$((patch + 1))
    echo "v${major}.${minor}.${patch}"
}

# Detect latest git tag or use 1.1.0 as base
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v1.1.0")
NEW_VERSION=$(increment_version "${CURRENT_VERSION}")

# Prompt for version confirmation
REPLY='y'  # Automatically accept version

echo "${YELLOW}Current version: ${CURRENT_VERSION}. Creating new version ${NEW_VERSION}${NC}"
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "${RED}Release cancelled.${NC}"
    exit 1
fi

# Create git tag
echo "${GREEN}Creating git tag: ${NEW_VERSION}${NC}"
git tag -a "${NEW_VERSION}" -m "Release ${NEW_VERSION}: Automated Release"

# Update CHANGELOG
echo "${GREEN}Updating CHANGELOG.md${NC}"
# Use a temporary file for cross-platform sed
sed "/## \[Unreleased\]/a\\
\\
## [${NEW_VERSION#v}] - $(date +%Y-%m-%d)\\
- Automated release\\
- Includes latest improvements and bug fixes" CHANGELOG.md > CHANGELOG.md.tmp
mv CHANGELOG.md.tmp CHANGELOG.md

# Build GUI
echo "${GREEN}Building GUI Application${NC}"
cd gui-macos
./build_app.sh

# Copy to Applications
echo "${GREEN}Installing to Applications${NC}"
cp -R "build/llamaCPP Manager.app" "/Applications/Llama CPP Manager.app"

# Copy DMG to Downloads
echo "${GREEN}Copying DMG to Downloads${NC}"
cp "build/llamaCPP-Manager-${NEW_VERSION#v}.dmg" ~/Downloads/

# Push changes
echo "${GREEN}Pushing changes to repository${NC}"
cd /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager
git add CHANGELOG.md
git commit -m "Bump version to ${NEW_VERSION}"
git push origin main
git push origin "${NEW_VERSION}"

echo "${GREEN}🎉 Release ${NEW_VERSION} complete!${NC}"
echo "Installed in: /Applications/Llama CPP Manager.app"
echo "DMG available in: ~/Downloads/llamaCPP-Manager-${NEW_VERSION#v}.dmg"