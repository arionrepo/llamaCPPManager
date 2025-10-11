# Stop All Models Implementation

## Functionality

The `stopAllModels()` method in the GUI provides a way to stop all running model instances with a single action.

## Code Breakdown

```swift
func stopAllModels() {
    Task { [weak self] in
        guard let self = self else { return }
        let result = await service.run(["stop", "all"])
        if result == 0 {
            AppLogger.log("Successfully stopped all models", level: .info)
            refresh()
        } else {
            AppLogger.log("Failed to stop all models", level: .error)
        }
    }
}
```

### Key Components

1. **Asynchronous Execution**:
   - Uses Swift's `Task` for asynchronous operation
   - Prevents blocking the UI while stopping models
   - Weak self reference prevents retain cycles

2. **CLI Command**:
   - Runs `llamacpp-manager stop all` via the CLI service
   - `["stop", "all"]` is the command that stops all running models

3. **Result Handling**:
   - `result == 0` indicates successful execution
   - Logs success or failure using `AppLogger`
   - Calls `refresh()` to update the UI state after stopping models

## User Interface

The button is styled in red with the text "Stop All Models" and includes a help tooltip explaining its purpose.

### Tooltip
"Stop all running models (infrastructure components continue running)"

## Important Notes

- Does NOT stop infrastructure components
- Provides immediate UI feedback through logging
- Refreshes the UI to reflect the new model states

## Potential Use Cases

- Quick cleanup of all running model instances
- Preparing for system resources management
- Stopping models before switching configurations

## Error Handling

If the stop command fails:
- Logs an error message
- Does not throw an exception
- Allows user to retry or investigate further