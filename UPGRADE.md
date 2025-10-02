# Upgrade Guide

Guide for upgrading llamaCPPManager safely while preserving your configuration.

## Configuration Preservation

**✅ Your model configuration is always preserved during upgrades.**

llamaCPPManager stores configuration separately from the code:
- **Config Location**: `~/Library/Application Support/llamaCPPManager/config.yaml`
- **Install Location**: `~/.local/pipx/venvs/llamacpp-manager/` (isolated)

When you run `pipx install -e .` or `pipx reinstall`, it **only updates the code**, never touches your config files.

## What Changed in Infrastructure Update

### Status Output Format Change

**Before (old format)**:
```
Models:
  phi3 @ 127.0.0.1:8081 - running
  smollm3 @ 127.0.0.1:8082 - running
```

**After (new format)**:
```
Infrastructure Components:
  ✓ cloudflared - running
  ✓ llm_controller - ok

Models:
  phi3 @ 127.0.0.1:8081 - running
  smollm3 @ 127.0.0.1:8082 - running
```

**Note**: Infrastructure section now appears **first**, followed by Models section. Your models are still there, just displayed below infrastructure!

### JSON Status Format Change

**Before**:
```json
[
  {"name": "phi3", "port": 8081, ...},
  {"name": "smollm3", "port": 8082, ...}
]
```

**After**:
```json
{
  "models": [
    {"name": "phi3", "port": 8081, ...},
    {"name": "smollm3", "port": 8082, ...}
  ],
  "infrastructure": [
    {"name": "cloudflared", ...},
    {"name": "llm_controller", ...}
  ]
}
```

## Safe Upgrade Procedure

### Method 1: Reinstall with pipx (Recommended)

```bash
# Your config is automatically preserved
pipx uninstall llamacpp-manager
pipx install -e /path/to/llamaCPPManager

# Verify your models are still there
llamacpp-manager config list
llamacpp-manager status
```

### Method 2: Upgrade in place

```bash
# Pull latest changes
cd ~/LocalProjects/GitHubProjectsDocuments/llamaCPPManager
git pull

# Reinstall (config is preserved)
pipx install --force -e .

# Verify
llamacpp-manager config list
```

## Verifying Configuration After Upgrade

```bash
# Check all models are present
llamacpp-manager config list

# Check status (models appear under "Models:" section)
llamacpp-manager status

# Check config file directly
cat ~/Library/Application\ Support/llamaCPPManager/config.yaml

# If models are running, check JSON output
llamacpp-manager status --json | python3 -m json.tool
```

## Configuration Backup (Optional but Recommended)

Before major upgrades, you can backup your config:

```bash
# Backup config
cp ~/Library/Application\ Support/llamaCPPManager/config.yaml \
   ~/Library/Application\ Support/llamaCPPManager/config.yaml.backup

# Restore if needed (rarely necessary)
cp ~/Library/Application\ Support/llamaCPPManager/config.yaml.backup \
   ~/Library/Application\ Support/llamaCPPManager/config.yaml
```

## What Gets Preserved

✅ **Always Preserved**:
- Model configurations (`config.yaml`)
- Infrastructure configurations (added to `config.yaml`)
- Log files
- PID files
- Monitoring state files

✅ **Never Deleted by Upgrade**:
- Your model files (`.gguf` files)
- Config directory contents
- Log directory contents
- LaunchAgents (monitoring daemon, GUI auto-start)

## What Gets Updated

🔄 **Updated During Upgrade**:
- Python code in the virtual environment
- CLI commands and features
- GUI app (if you rebuild it)

## Troubleshooting After Upgrade

### "I don't see my models"

Your models are still there! The new status format shows Infrastructure first, then Models.

```bash
# Check config - your models are here
llamacpp-manager config list

# Check status - scroll down past Infrastructure section
llamacpp-manager status

# Models section appears after Infrastructure section
```

### "Status format changed"

This is expected. The infrastructure update changed the output format:
- Infrastructure components shown first
- Models shown second
- JSON format now uses `{"models": [...], "infrastructure": [...]}`

Your data is intact, only the display format changed.

### "GUI doesn't show models"

The GUI was updated to show infrastructure first, then models:

```bash
# Rebuild and reinstall GUI
cd gui-macos
./build_app.sh
cp -R "build/llamaCPP Manager.app" /Applications/

# Launch it - you'll see Infrastructure section above Models section
```

## Migration Checklist

After upgrading, verify:

- [ ] Models appear in `llamacpp-manager config list`
- [ ] Models appear under "Models:" in `llamacpp-manager status`
- [ ] Running models still respond to queries
- [ ] Infrastructure section appears (new feature)
- [ ] Monitoring daemon still works (if installed)
- [ ] GUI shows both Infrastructure and Models sections (if using GUI)

## Rolling Back (If Needed)

If you need to go back to a previous version:

```bash
# Your config is always preserved, just reinstall old version
cd ~/LocalProjects/GitHubProjectsDocuments/llamaCPPManager
git checkout <previous-commit>
pipx install --force -e .
```

## Future-Proofing

The configuration format is designed to be **backward compatible**. New features add new sections (like `infrastructure:`) but never remove or break existing sections (like `models:`).

**Your model configurations will always be preserved across upgrades.**

## Getting Help

If something seems wrong after an upgrade:

1. Check your config file directly:
   ```bash
   cat ~/Library/Application\ Support/llamaCPPManager/config.yaml
   ```

2. Verify models section exists in the config

3. Check if models are just displayed in a different location in the output

4. Report issues at: https://github.com/anthropics/claude-code/issues
