# CLI Regression Test Checklist

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/CLI_REGRESSION_TEST.md
**Description:** Comprehensive regression test checklist for CLI commands
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-12

## Test Environment
- macOS Version:
- Python Version:
- Virtual Environment: .venv
- Git Branch:
- Git Commit:

## Installation Tests

### Package Installation
- [ ] `pip install -e .` - Installs package successfully
- [ ] `llamacpp-manager --version` - Shows correct version
- [ ] `llamacpp-manager --help` - Shows help message
- [ ] Package is accessible from PATH

## Status Commands

### Basic Status
- [ ] `llamacpp-manager status` - Shows text status of all models
- [ ] `llamacpp-manager status --json` - Shows JSON status
- [ ] `llamacpp-manager status --verbose` - Shows verbose output
- [ ] Status shows correct PID for running models
- [ ] Status shows correct port numbers
- [ ] Status shows "up" for running models
- [ ] Status shows "down" for stopped models
- [ ] Status shows health check information
- [ ] Status shows latency_ms
- [ ] Status shows version information

### Infrastructure Status
- [ ] `llamacpp-manager status` includes infrastructure section
- [ ] Infrastructure shows container status
- [ ] Infrastructure shows health status

## Model Management Commands

### Starting Models
- [ ] `llamacpp-manager start <model>` - Starts single model
- [ ] `llamacpp-manager start <model1> <model2>` - Starts multiple models
- [ ] `llamacpp-manager start all` - Starts all configured models
- [ ] Starting already running model shows appropriate message
- [ ] Starting non-existent model shows error
- [ ] Model starts with correct port
- [ ] Model starts with correct path
- [ ] PID file is created correctly

### Stopping Models
- [ ] `llamacpp-manager stop <model>` - Stops single model
- [ ] `llamacpp-manager stop <model1> <model2>` - Stops multiple models
- [ ] `llamacpp-manager stop all` - Stops all running models
- [ ] Stopping already stopped model shows appropriate message
- [ ] Stopping non-existent model shows error
- [ ] PID file is removed correctly
- [ ] Process is killed cleanly

### Restarting Models
- [ ] `llamacpp-manager restart <model>` - Restarts single model
- [ ] `llamacpp-manager restart <model1> <model2>` - Restarts multiple models
- [ ] `llamacpp-manager restart all` - Restarts all models
- [ ] Restart stops then starts model correctly
- [ ] New PID is assigned after restart

## Configuration Commands

### List Configuration
- [ ] `llamacpp-manager config list` - Lists all configured models
- [ ] `llamacpp-manager config list --json` - Shows JSON output
- [ ] Output shows model name
- [ ] Output shows model path
- [ ] Output shows port number
- [ ] Output shows additional configuration

### Add Configuration
- [ ] `llamacpp-manager config add <name> <path>` - Adds model with auto port
- [ ] `llamacpp-manager config add <name> <path> --port 8080` - Adds with specific port
- [ ] Adding duplicate model name shows error
- [ ] Adding with invalid path shows error
- [ ] Adding with conflicting port shows error
- [ ] Configuration file is updated correctly

### Remove Configuration
- [ ] `llamacpp-manager config remove <name>` - Removes model configuration
- [ ] Removing non-existent model shows error
- [ ] Configuration file is updated correctly
- [ ] Running model is NOT stopped when config removed

### Edit Configuration
- [ ] `llamacpp-manager config edit` - Opens config file in editor
- [ ] Config file opens in default editor
- [ ] Manual edits are preserved

### Show Configuration Path
- [ ] `llamacpp-manager config show-path` - Shows config directory path
- [ ] Path is correct and accessible

## Query Commands

### Chat Query
- [ ] `llamacpp-manager query chat <model> --message "user:test"` - Basic chat
- [ ] `llamacpp-manager query chat <model> --message "user:test" --json` - JSON output
- [ ] `llamacpp-manager query chat <model> --message "user:hi" --system "You are helpful"` - System prompt
- [ ] `llamacpp-manager query chat <model> --message "user:test" --max-tokens 100` - Max tokens
- [ ] `llamacpp-manager query chat <model> --message "user:test" --temperature 0.5` - Temperature
- [ ] Query to stopped model shows error
- [ ] Query to non-existent model shows error
- [ ] Response is properly formatted
- [ ] Streaming responses work correctly

### Completion Query
- [ ] `llamacpp-manager query completion <model> --prompt "Once upon a time"` - Basic completion
- [ ] `llamacpp-manager query completion <model> --prompt "test" --json` - JSON output
- [ ] `llamacpp-manager query completion <model> --prompt "test" --max-tokens 50` - Max tokens
- [ ] Completion to stopped model shows error

### Embedding Query
- [ ] `llamacpp-manager query embedding <model> --text "test"` - Basic embedding
- [ ] `llamacpp-manager query embedding <model> --text "test" --json` - JSON output
- [ ] Embedding returns vector of correct dimensions
- [ ] Embedding to stopped model shows error

## Model Discovery Commands

### List Available Models
- [ ] `llamacpp-manager models list` - Lists available models for download
- [ ] `llamacpp-manager models list --json` - Shows JSON output
- [ ] `llamacpp-manager models list --available` - Shows only downloadable models
- [ ] Output shows model name
- [ ] Output shows size
- [ ] Output shows use case
- [ ] Output shows description

### Model Info
- [ ] `llamacpp-manager models info <name>` - Shows detailed model info
- [ ] `llamacpp-manager models info <name> --json` - JSON output
- [ ] Shows repository ID
- [ ] Shows filename
- [ ] Shows size in GB
- [ ] Shows RAM requirements
- [ ] Shows use case
- [ ] Shows description

### Download Models
- [ ] `llamacpp-manager models download <name>` - Downloads model
- [ ] Download shows progress bar
- [ ] Download can be cancelled with Ctrl+C
- [ ] Downloaded files are placed in correct directory
- [ ] Download of already downloaded model shows appropriate message
- [ ] Download of non-existent model shows error

## Logging Commands

### Enable/Disable Logging
- [ ] `llamacpp-manager logging enable` - Enables logging
- [ ] `llamacpp-manager logging disable` - Disables logging
- [ ] Status reflects logging state correctly

### Configure Log Levels
- [ ] `llamacpp-manager logging set-level debug` - Sets debug level
- [ ] `llamacpp-manager logging set-level info` - Sets info level
- [ ] `llamacpp-manager logging set-level warning` - Sets warning level
- [ ] `llamacpp-manager logging set-level error` - Sets error level

### Enable/Disable Timestamps
- [ ] `llamacpp-manager logging timestamps on` - Enables timestamps
- [ ] `llamacpp-manager logging timestamps off` - Disables timestamps
- [ ] Log files reflect timestamp setting

### View Logs
- [ ] `llamacpp-manager logs <model>` - Shows logs for model
- [ ] `llamacpp-manager logs <model> --tail 50` - Shows last N lines
- [ ] `llamacpp-manager logs <model> --follow` - Follows log output
- [ ] Logs for non-existent model show error
- [ ] Logs for stopped model show historical logs

## Health Check Commands

### Health Status
- [ ] `llamacpp-manager health` - Shows health of all models
- [ ] `llamacpp-manager health <model>` - Shows health of specific model
- [ ] `llamacpp-manager health --json` - JSON output
- [ ] Health check shows latency
- [ ] Health check shows HTTP status code
- [ ] Health check shows "ok", "starting", or "down" state

## Infrastructure Commands

### List Infrastructure
- [ ] `llamacpp-manager infra list` - Lists infrastructure containers
- [ ] `llamacpp-manager infra list --json` - JSON output
- [ ] Shows container names
- [ ] Shows container status
- [ ] Shows ports

### Start Infrastructure
- [ ] `llamacpp-manager infra start <name>` - Starts container
- [ ] `llamacpp-manager infra start all` - Starts all containers
- [ ] Starting already running container shows message

### Stop Infrastructure
- [ ] `llamacpp-manager infra stop <name>` - Stops container
- [ ] `llamacpp-manager infra stop all` - Stops all containers
- [ ] Stopping already stopped container shows message

### Restart Infrastructure
- [ ] `llamacpp-manager infra restart <name>` - Restarts container
- [ ] Restart cleans up properly

### Infrastructure Logs
- [ ] `llamacpp-manager infra logs <name>` - Shows container logs
- [ ] `llamacpp-manager infra logs <name> --follow` - Follows logs

## Comparison Commands

### Multi-Model Comparison
- [ ] `llamacpp-manager compare "test query" --models model1,model2` - Compares responses
- [ ] `llamacpp-manager compare "test" --models model1,model2 --json` - JSON output
- [ ] Comparison shows side-by-side responses
- [ ] Comparison shows latency for each model
- [ ] Comparison with stopped model shows error
- [ ] Comparison saves to chat history

### Chat History
- [ ] `llamacpp-manager history list` - Lists all chat sessions
- [ ] `llamacpp-manager history show <session_id>` - Shows specific session
- [ ] `llamacpp-manager history search "query"` - Searches chat history
- [ ] History persists across CLI sessions

## MCP Server Commands

### MCP Server Status
- [ ] `llamacpp-manager mcp status` - Shows MCP server status
- [ ] `llamacpp-manager mcp start` - Starts MCP server
- [ ] `llamacpp-manager mcp stop` - Stops MCP server
- [ ] MCP server integrates with Claude desktop

## Error Handling

### Invalid Commands
- [ ] Invalid command shows helpful error
- [ ] Invalid arguments show helpful error
- [ ] Missing required arguments show error
- [ ] `--help` flag works on all commands

### Edge Cases
- [ ] Running command when no models configured
- [ ] Running command when config file is corrupted
- [ ] Running command when another instance is running
- [ ] Handling process crashes gracefully
- [ ] Handling port conflicts
- [ ] Handling disk space issues during download

## Integration Tests

### CLI + Config File
- [ ] Config changes persist across commands
- [ ] Config file format is valid JSON
- [ ] Config file has correct permissions

### CLI + Process Management
- [ ] PIDs are tracked correctly
- [ ] Zombie processes are cleaned up
- [ ] Process monitoring works correctly

### CLI + Network
- [ ] Port allocation works correctly
- [ ] Health checks work over HTTP
- [ ] Model responses work over HTTP

### CLI + File System
- [ ] Log files are created in correct location
- [ ] PID files are created in correct location
- [ ] Model files are stored in correct location
- [ ] Permissions are set correctly

## Performance Tests

- [ ] Starting 5+ models simultaneously
- [ ] Stopping 5+ models simultaneously
- [ ] Querying multiple models in parallel
- [ ] Large file download (>10GB model)
- [ ] Long-running model stability (24+ hours)

## Test Results

### Test Date: ___________
### Tester: ___________
### Pass/Fail: ___________

### Issues Found:
1.
2.
3.

### Notes:
