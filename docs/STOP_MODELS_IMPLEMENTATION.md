# Stop Models Implementation in llamaCPP Manager

## Overview

The `cmd_stop()` function in the CLI provides a comprehensive mechanism for stopping models, with special handling for the "all" target.

## Stop Strategies

When stopping models, the CLI uses multiple strategies in the following order:

1. **Launchd Service Stopping**
   ```python
   if getattr(args, "launchd", False):
       r = launchctl_bootout(name)
       # Remove launchd plist file
   ```
   - Stops models managed by launchd
   - Removes the corresponding .plist file

2. **PID File Approach**
   ```python
   pid = read_pid(name)
   stop_process(pid)
   remove_pid(name)
   ```
   - Reads the PID from a stored file
   - Stops the process using the PID
   - Removes the PID file

3. **ModelManager Fallback**
   ```python
   success, msg = manager.stop_model(name)
   ```
   - Uses the ModelManager to attempt stopping the model

4. **Last Resort: Port-based Process Killing**
   ```python
   result = subprocess.run(["lsof", "-ti", f":{port}"])
   subprocess.run(["kill", str(pid)])
   ```
   - Finds process by listening port
   - Kills the process if found

## "Stop All" Implementation

When the target is "all", the function:
1. Loads all configured models from the config
2. Applies the above stopping strategies to each model
3. Tracks overall return code to indicate success/failure

### Key Characteristics

- Stops all running models, regardless of their current state
- Supports both direct process and launchd-managed models
- Provides multiple fallback mechanisms
- Returns an exit code indicating overall success/failure
  - 0: All models stopped successfully
  - 1: Some models had warnings
  - 2: Critical errors occurred

## Error Handling

- Continues attempting to stop other models if one fails
- Logs warnings and errors for each model
- Provides detailed feedback about stopping process

## Use Cases

- Clean shutdown of all running model instances
- Preparing system for maintenance
- Releasing resources before configuration changes

## Example CLI Usage

```bash
# Stop all running models
llamacpp-manager stop all

# Stop models via launchd
llamacpp-manager stop all --launchd
```

## Precautions

- Does NOT stop infrastructure components
- May forcefully kill processes if gentler methods fail
- Recommended to use with caution in production environments