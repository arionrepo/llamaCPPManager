# Integration Regression Test Checklist

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/INTEGRATION_REGRESSION_TEST.md
**Description:** Integration tests for GUI + CLI + System interactions
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-12

## Test Environment
- macOS Version:
- GUI Build: Debug/Release
- CLI Version:
- Git Branch:
- Git Commit:

## GUI + CLI Integration Tests

### Configuration Sync
- [ ] Add model via CLI → GUI reflects change on refresh
- [ ] Remove model via CLI → GUI reflects change on refresh
- [ ] Edit config file manually → GUI reflects changes
- [ ] Add model via GUI Model Downloader → CLI config list shows it

### Model State Sync
- [ ] Start model via CLI → GUI shows "up" status
- [ ] Stop model via CLI → GUI shows "down" status
- [ ] Start model via GUI → CLI status shows running
- [ ] Stop model via GUI → CLI status shows stopped
- [ ] Restart model via CLI → GUI shows brief transition
- [ ] Restart model via GUI → CLI reflects new PID

### Logging Sync
- [ ] Enable logging via CLI → GUI logging toggle reflects state
- [ ] Disable logging via CLI → GUI logging toggle reflects state
- [ ] Toggle logging via GUI → CLI status reflects change
- [ ] Timestamp toggle via CLI → GUI reflects state
- [ ] Timestamp toggle via GUI → CLI reflects state

### Chat History Sync
- [ ] Chat via GUI → CLI history shows conversation
- [ ] Chat via CLI → GUI chat window can load history (if implemented)
- [ ] Compare via CLI → History is saved
- [ ] Multiple GUI chat windows → All save to same history DB

## GUI + File System Integration Tests

### Configuration Files
- [ ] GUI reads config from correct location
- [ ] CLI reads config from correct location
- [ ] Both use same config file
- [ ] Config file format is consistent
- [ ] Config file updates are atomic (no corruption)

### Log Files
- [ ] GUI "Logs" button opens correct log file
- [ ] CLI logs command shows correct log file
- [ ] Both create logs in same directory
- [ ] Log rotation works correctly
- [ ] Old logs are accessible

### PID Files
- [ ] GUI creates PID files in correct location
- [ ] CLI creates PID files in correct location
- [ ] PID files are cleaned up on stop
- [ ] Stale PID files are handled gracefully
- [ ] PID file format is consistent

### Model Files
- [ ] Downloaded models are stored in standard location
- [ ] GUI can access CLI-downloaded models
- [ ] CLI can access GUI-downloaded models
- [ ] Model paths are correctly expanded (~/)
- [ ] Symlinks are handled correctly

## GUI + Process Management Integration Tests

### Process Lifecycle
- [ ] GUI-started process appears in `ps aux`
- [ ] CLI-started process appears in `ps aux`
- [ ] GUI can stop CLI-started process
- [ ] CLI can stop GUI-started process
- [ ] Processes survive GUI exit (if not killed)
- [ ] Kill process manually → GUI reflects state on refresh
- [ ] Kill process manually → CLI reflects state

### Multiple Instances
- [ ] Can run multiple GUI instances simultaneously
- [ ] Can run GUI + CLI commands simultaneously
- [ ] No race conditions when starting same model
- [ ] No race conditions when stopping same model
- [ ] Concurrent config changes are handled safely

### Process Monitoring
- [ ] GUI monitor toggle affects process behavior
- [ ] Monitored processes are restarted on crash
- [ ] Monitor state persists across GUI restarts
- [ ] CLI can query monitor state

## GUI + Network Integration Tests

### Port Management
- [ ] GUI and CLI use same port allocation
- [ ] Port conflicts are detected and reported
- [ ] Auto port allocation works consistently
- [ ] Health checks work from both GUI and CLI
- [ ] Same model uses same port across restarts

### Health Checks
- [ ] GUI health status matches CLI health status
- [ ] Health check failures are detected by both
- [ ] Latency measurements are consistent
- [ ] HTTP status codes are correct
- [ ] Version info is retrieved correctly

### Query Endpoints
- [ ] Chat queries work from both GUI and CLI
- [ ] Completion queries work from both GUI and CLI
- [ ] Embedding queries work from CLI
- [ ] Streaming works correctly in both interfaces
- [ ] Error responses are handled consistently

## GUI + Infrastructure Integration Tests

### Container Management
- [ ] Start container via CLI → GUI shows running
- [ ] Start container via GUI → CLI shows running
- [ ] Stop container via CLI → GUI shows stopped
- [ ] Stop container via GUI → CLI shows stopped
- [ ] Container logs accessible from both interfaces
- [ ] Container health checks work from both

### Docker Integration
- [ ] Docker commands work from CLI
- [ ] GUI can display Docker container status
- [ ] Port mappings are correct
- [ ] Volume mounts are correct
- [ ] Container networking works

### Kubernetes Integration
- [ ] K8s deployments work from CLI
- [ ] GUI can display K8s pod status
- [ ] Service endpoints are accessible
- [ ] Pod logs are accessible

## Cross-Platform Integration Tests

### macOS Specific
- [ ] launchd integration works
- [ ] Keychain integration works (if implemented)
- [ ] Spotlight indexing doesn't break anything
- [ ] Gatekeeper allows GUI to run
- [ ] Code signing is valid

### File Permissions
- [ ] Config directory has correct permissions (755)
- [ ] Config file has correct permissions (644)
- [ ] Log directory has correct permissions (755)
- [ ] Log files have correct permissions (644)
- [ ] PID directory has correct permissions (755)
- [ ] Executable has correct permissions (755)

## User Experience Integration Tests

### First-Time Setup
- [ ] First launch creates config directory
- [ ] First launch creates default config
- [ ] No models configured → Clear message in GUI
- [ ] No models configured → Clear message in CLI
- [ ] Help documentation is accessible

### Upgrade Path
- [ ] Upgrade from previous version preserves config
- [ ] Old config format is migrated correctly
- [ ] Running models survive upgrade
- [ ] Chat history survives upgrade
- [ ] Preferences survive upgrade

### Error Recovery
- [ ] Corrupt config file → Clear error message + recovery
- [ ] Missing model files → Clear error message
- [ ] Port conflict → Clear error message + suggestion
- [ ] Disk full → Clear error message
- [ ] Network error → Clear error message

## Performance Integration Tests

### Resource Usage
- [ ] GUI memory usage is reasonable (<100MB idle)
- [ ] CLI memory usage is minimal
- [ ] CPU usage is low when idle
- [ ] Model startup time is reasonable (<5s)
- [ ] Health check interval doesn't cause load

### Scalability
- [ ] 5+ models configured → GUI performs well
- [ ] 5+ models running → GUI performs well
- [ ] 5+ models running → CLI performs well
- [ ] Large log files → GUI still responsive
- [ ] Large log files → CLI still responsive
- [ ] Large chat history → Queries still fast

### Responsiveness
- [ ] GUI status updates within refresh interval
- [ ] GUI buttons respond immediately
- [ ] CLI commands respond within 1 second
- [ ] Model queries respond within timeout
- [ ] Health checks complete quickly

## Data Integrity Tests

### Configuration
- [ ] Config changes are atomic
- [ ] Concurrent config edits don't corrupt file
- [ ] Config backup/restore works
- [ ] Invalid config is rejected with clear message

### Chat History
- [ ] Chat history SQLite database is not corrupted
- [ ] Concurrent writes don't cause corruption
- [ ] Large history doesn't slow down queries
- [ ] History can be exported
- [ ] History can be cleared

### Logs
- [ ] Log rotation doesn't lose data
- [ ] Concurrent writes don't corrupt logs
- [ ] Large logs are handled gracefully
- [ ] Log compression works (if implemented)

## Security Integration Tests

### File Access
- [ ] Config file is not world-readable (if sensitive)
- [ ] Log files don't contain sensitive data
- [ ] PID files don't leak information
- [ ] Model downloads verify checksums (if implemented)

### Process Security
- [ ] Processes run with correct user
- [ ] Processes don't run as root unnecessarily
- [ ] Environment variables are sanitized
- [ ] Command injection is prevented

### Network Security
- [ ] Health checks use correct protocol
- [ ] API keys are stored securely (if used)
- [ ] HTTPS is used where appropriate
- [ ] Localhost binding prevents external access

## Test Results

### Test Date: ___________
### Tester: ___________
### Pass/Fail: ___________

### Issues Found:
1.
2.
3.

### Notes:

### Performance Metrics:
- GUI Memory Usage (idle): _____ MB
- GUI Memory Usage (5 models): _____ MB
- CLI Command Response Time: _____ ms
- Model Startup Time: _____ seconds
- Health Check Latency: _____ ms
