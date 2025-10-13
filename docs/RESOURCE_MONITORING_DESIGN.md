# Resource Monitoring Design (Modular)

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/RESOURCE_MONITORING_DESIGN.md
**Description:** Design document for standalone resource monitoring module
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-13

## Overview

Add **standalone resource monitoring** as an independent module that provides real-time CPU, memory, and throughput metrics without modifying existing CLI or GUI code.

## Business Purpose

**Problem:** Users running multiple LLM models don't know which models are consuming resources, making it hard to:
- Identify which models to stop when system is slow
- Plan capacity for additional models
- Detect resource leaks or performance issues
- Understand cost of running specific models

**Solution:** New `llamacpp-manager monitor` command providing standalone resource monitoring with clean APIs for optional future integration.

## Design Philosophy - Modular Architecture

✅ **Standalone Module:** Does NOT modify existing commands
✅ **Zero Breaking Changes:** Existing CLI/GUI unaffected
✅ **Clean APIs:** Easy to integrate later if desired
✅ **Optional Feature:** Users can ignore if not needed
✅ **Independent Testing:** Tested separately from core

## Requirements

### Functional Requirements

1. **Per-Model Metrics**
   - CPU usage percentage (per model process)
   - Memory usage (RSS - Resident Set Size in MB/GB)
   - Thread count
   - Process uptime
   - Running status

2. **System-Wide Metrics**
   - Total CPU usage by all models
   - Total memory usage by all models
   - System memory available
   - CPU core count
   - Number of models running

3. **Display Requirements**
   - CLI: New `monitor status` command with table output
   - CLI: `monitor status --json` for machine-readable output
   - CLI: `monitor watch` for live updating view
   - CLI: `monitor summary` for system-wide overview

### Non-Functional Requirements

- Metric collection must not impact model performance (< 1% overhead)
- Metrics updated every 2-5 seconds (configurable)
- Gracefully handle missing metrics (models without stats)
- Cross-platform support (macOS primary, Linux compatible)
- **No modifications to existing code**

## Architecture

### Module Structure

```
src/llamacpp_manager/
├── metrics.py              # NEW: Core metrics collection
└── cli.py                  # MODIFIED: Add `monitor` subcommand only

New CLI Commands:
  llamacpp-manager monitor status          # Show current resource usage
  llamacpp-manager monitor status --json   # JSON output for APIs
  llamacpp-manager monitor watch           # Live updating terminal view
  llamacpp-manager monitor summary         # System-wide summary only
```

### Data Models

**File:** `src/llamacpp_manager/metrics.py`

```python
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import time

@dataclass
class ProcessMetrics:
    """
    Resource metrics for a single process.

    Business Purpose: Provides detailed resource usage data for capacity planning
    and performance optimization decisions.
    """
    cpu_percent: float          # 0.0-100.0+ per core (can exceed 100 on multi-core)
    memory_mb: float            # Resident Set Size in MB
    memory_percent: float       # Percentage of system RAM
    threads: int                # Number of threads
    open_files: int             # Number of open file descriptors

@dataclass
class ModelMetrics:
    """
    Complete metrics for a model including process and performance data.

    Business Purpose: Combines all metrics into single object for easy
    consumption by CLI/GUI/API consumers.
    """
    name: str
    pid: Optional[int]

    # Process metrics (None if not running)
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    memory_percent: Optional[float] = None
    threads: Optional[int] = None

    # Status
    uptime_seconds: Optional[int] = None
    running: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)

@dataclass
class SystemMetrics:
    """
    System-wide resource metrics.

    Business Purpose: Provides overall system health context for understanding
    available capacity and resource contention.
    """
    total_cpu_percent: float        # Sum of all model CPU usage
    total_memory_mb: float          # Sum of all model memory usage
    available_memory_mb: float      # System memory available
    cpu_count: int                  # Number of CPU cores
    models_running: int             # Count of running models
    timestamp: float                # Unix timestamp of measurement

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)
```

### Core Functions (Standalone API)

```python
def get_process_metrics(pid: int) -> Optional[ProcessMetrics]:
    """
    Get resource metrics for a specific process using psutil.

    Business Purpose: Provides resource usage data for a single process
    without dependencies on the rest of the system. Can be used independently
    for monitoring any process, not just llama-server.

    Args:
        pid: Process ID to monitor

    Returns:
        ProcessMetrics if process exists and accessible, None otherwise

    Example:
        metrics = get_process_metrics(12345)
        if metrics:
            print(f"CPU: {metrics.cpu_percent}%")
            print(f"Memory: {metrics.memory_mb}MB")
    """
    pass

def get_model_metrics(name: str, pid: Optional[int], start_time: Optional[float] = None) -> ModelMetrics:
    """
    Get complete metrics for a model by name and PID.

    Business Purpose: Combines process metrics with model identification
    to provide a complete resource picture for a specific model.

    Args:
        name: Model name from configuration
        pid: Process ID if running (None if stopped)
        start_time: Process start timestamp for uptime calculation

    Returns:
        ModelMetrics with all available data (metrics=None if not running)

    Example:
        metrics = get_model_metrics("phi3", 12345, time.time() - 3600)
        print(f"{metrics.name}: {metrics.cpu_percent}% CPU, {metrics.memory_mb}MB RAM")
    """
    pass

def get_all_model_metrics(config: Dict[str, Any]) -> List[ModelMetrics]:
    """
    Get metrics for all configured models by discovering running processes.

    Business Purpose: Single function to collect all model metrics
    for dashboard/monitoring views. Automatically discovers which
    models are running.

    Args:
        config: Configuration dict from load_config()

    Returns:
        List of ModelMetrics for all models (running and stopped)

    Example:
        from .config import load_config
        from .discovery import find_llama_processes

        cfg = load_config()
        metrics = get_all_model_metrics(cfg)

        for m in metrics:
            if m.running:
                print(f"{m.name}: {m.cpu_percent}% CPU, {m.memory_mb}MB RAM")
            else:
                print(f"{m.name}: stopped")
    """
    pass

def get_system_metrics(model_metrics: List[ModelMetrics]) -> SystemMetrics:
    """
    Get system-wide resource metrics aggregated from all models.

    Business Purpose: Provides overall system health context for capacity
    planning and resource allocation decisions.

    Args:
        model_metrics: List of ModelMetrics to aggregate

    Returns:
        SystemMetrics with system-wide data

    Example:
        model_metrics = get_all_model_metrics(config)
        sys = get_system_metrics(model_metrics)

        print(f"Total CPU: {sys.total_cpu_percent}%")
        print(f"Available RAM: {sys.available_memory_mb}MB")
        print(f"Models running: {sys.models_running}/{len(model_metrics)}")
    """
    pass

def format_metrics_table(model_metrics: List[ModelMetrics], system_metrics: SystemMetrics) -> str:
    """
    Format metrics as human-readable table.

    Business Purpose: Provides clean terminal output for CLI users
    to quickly assess resource usage.

    Args:
        model_metrics: List of model metrics
        system_metrics: System-wide metrics

    Returns:
        Formatted table string

    Example:
        table = format_metrics_table(model_metrics, system_metrics)
        print(table)
        # Output:
        # Name       Status  CPU%    Memory   Threads  Uptime
        # phi3       running 45.2%   1.8GB    8        02:15:30
        # smollm3    running 12.5%   512MB    4        02:15:30
        # mistral    stopped -       -        -        -
        #
        # System: CPU 57.7% (4 cores) | Memory 2.3GB used, 13.7GB available
    """
    pass
```

### CLI Integration (New Subcommand Only)

**File:** `src/llamacpp_manager/cli.py`

Add new `monitor` subcommand parser in `main()`:

```python
def main() -> int:
    # ... existing parser setup ...

    # NEW: Add monitor subcommand
    monitor_parser = subparsers.add_parser("monitor", help="Resource monitoring (CPU, memory)")
    monitor_sub = monitor_parser.add_subparsers(dest="subcommand", required=True)

    # monitor status
    status_parser = monitor_sub.add_parser("status", help="Show current resource usage")
    status_parser.add_argument("--json", action="store_true", help="Output JSON")

    # monitor watch
    watch_parser = monitor_sub.add_parser("watch", help="Live updating resource view")
    watch_parser.add_argument("--interval", type=int, default=2, help="Refresh interval (seconds)")

    # monitor summary
    summary_parser = monitor_sub.add_parser("summary", help="System-wide summary")

    # ... existing code continues ...
```

Add new command handler:

```python
def cmd_monitor(args: argparse.Namespace) -> int:
    """
    Resource monitoring commands (standalone module).

    Business Purpose: Provides dedicated monitoring interface without
    cluttering existing status/config commands. Can be used independently
    or integrated later.
    """
    from .config import load_config
    from .metrics import (
        get_all_model_metrics,
        get_system_metrics,
        format_metrics_table
    )
    from .utils import to_json

    cfg = load_config()
    sub = args.subcommand

    if sub == "status":
        # Get all metrics
        model_metrics = get_all_model_metrics(cfg)
        system_metrics = get_system_metrics(model_metrics)

        if args.json:
            output = {
                "models": [m.to_dict() for m in model_metrics],
                "system": system_metrics.to_dict()
            }
            print(to_json(output))
        else:
            # Print formatted table
            print(format_metrics_table(model_metrics, system_metrics))
        return 0

    if sub == "watch":
        # Live updating view
        import os
        import time

        try:
            while True:
                os.system('clear' if os.name != 'nt' else 'cls')

                model_metrics = get_all_model_metrics(cfg)
                system_metrics = get_system_metrics(model_metrics)

                print(format_metrics_table(model_metrics, system_metrics))
                print(f"\nRefreshing every {args.interval}s... (Ctrl+C to stop)")

                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
        return 0

    if sub == "summary":
        # System-wide summary only
        model_metrics = get_all_model_metrics(cfg)
        system_metrics = get_system_metrics(model_metrics)

        print(f"CPU Usage: {system_metrics.total_cpu_percent:.1f}% ({system_metrics.cpu_count} cores)")
        print(f"Memory Used: {system_metrics.total_memory_mb:.0f}MB")
        print(f"Memory Available: {system_metrics.available_memory_mb:.0f}MB")
        print(f"Models Running: {system_metrics.models_running}")
        return 0

    return 1
```

## Data Format Examples

### JSON Output (`monitor status --json`)

```json
{
  "models": [
    {
      "name": "phi3",
      "pid": 19941,
      "cpu_percent": 45.2,
      "memory_mb": 1823.5,
      "memory_percent": 11.4,
      "threads": 8,
      "uptime_seconds": 29044,
      "running": true
    },
    {
      "name": "smollm3",
      "pid": 19942,
      "cpu_percent": 12.5,
      "memory_mb": 512.3,
      "memory_percent": 3.2,
      "threads": 4,
      "uptime_seconds": 29044,
      "running": true
    },
    {
      "name": "mistral",
      "pid": null,
      "cpu_percent": null,
      "memory_mb": null,
      "memory_percent": null,
      "threads": null,
      "uptime_seconds": null,
      "running": false
    }
  ],
  "system": {
    "total_cpu_percent": 57.7,
    "total_memory_mb": 2335.8,
    "available_memory_mb": 13742.2,
    "cpu_count": 4,
    "models_running": 2,
    "timestamp": 1697234567.123
  }
}
```

### CLI Table Output (`monitor status`)

```
Resource Monitor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name         Status   CPU%    Memory    Threads  Uptime
───────────────────────────────────────────────────────────────────
phi3         running  45.2%   1.8GB     8        08:04:04
smollm3      running  12.5%   512MB     4        08:04:04
mistral      stopped  -       -         -        -
qwen2.5-32b  running  89.3%   4.2GB     12       08:04:04

System Resources
───────────────────────────────────────────────────────────────────
CPU:    147.0% / 400% (4 cores)
Memory: 6.5GB used, 9.5GB available (40.6% utilization)
Models: 3 running, 1 stopped
```

### Summary Output (`monitor summary`)

```
CPU Usage: 147.0% (4 cores)
Memory Used: 6656MB
Memory Available: 9728MB
Models Running: 3
```

## Dependencies

### New Python Dependency

```toml
# pyproject.toml
dependencies = [
    # ... existing dependencies ...
    "psutil>=5.9.0",
]
```

**Why psutil:**
- Cross-platform (macOS, Linux, Windows)
- Mature, actively maintained (10+ years)
- Minimal overhead (<0.5% CPU for monitoring)
- Comprehensive process metrics
- BSD license (compatible)
- No system dependencies required

## Implementation Plan

### Phase 1: Core Metrics Module (2 hours)
1. Add `psutil>=5.9.0` to `pyproject.toml`
2. Create `src/llamacpp_manager/metrics.py` with data models
3. Implement `get_process_metrics()` using psutil.Process
4. Implement `get_model_metrics()` and `get_all_model_metrics()`
5. Implement `get_system_metrics()` and `format_metrics_table()`
6. Add unit tests with mock processes

**Files Created:**
- `src/llamacpp_manager/metrics.py` (~300 lines)
- `tests/test_metrics.py` (~150 lines)

### Phase 2: CLI Integration (1 hour)
1. Add `monitor` subcommand parser to `cli.py`
2. Implement `cmd_monitor()` function
3. Wire up to main parser
4. Test all three commands (status, watch, summary)

**Files Modified:**
- `src/llamacpp_manager/cli.py` (add ~100 lines)

### Phase 3: Testing & Documentation (1 hour)
1. Run with multiple models and verify accuracy
2. Measure performance overhead (should be <1%)
3. Update user manual with `monitor` commands
4. Add examples to README
5. Update CHANGELOG

**Files Modified:**
- `docs/user-manual.md`
- `README.md`
- `CHANGELOG.md`

**Total Estimated Time:** 4 hours

## Future Integration Options (Not Part of This Implementation)

The modular design allows optional integration later:

### Option 1: Add `--metrics` flag to existing `status` command
```python
# Future enhancement in cmd_status()
if args.metrics:
    from .metrics import get_model_metrics
    # Add metrics to existing output
```

### Option 2: GUI can call monitor API
```bash
# GUI subprocess call
llamacpp-manager monitor status --json | jq '.models'
```

### Option 3: Python API for external tools
```python
# External scripts can import directly
from llamacpp_manager.metrics import get_all_model_metrics
from llamacpp_manager.config import load_config

metrics = get_all_model_metrics(load_config())
for m in metrics:
    if m.cpu_percent and m.cpu_percent > 80:
        print(f"WARNING: {m.name} using {m.cpu_percent}% CPU")
```

## Performance Considerations

1. **Caching:** psutil caches process info internally
2. **Lazy Loading:** Only query processes that exist
3. **Error Handling:** Gracefully handle missing/terminated PIDs
4. **Overhead:** Target <1% CPU impact for monitoring

## Testing Strategy

1. **Unit Tests:** Mock psutil.Process for deterministic tests
2. **Integration Tests:** Run actual models and verify metrics
3. **Performance Tests:** Measure overhead with `time` command
4. **Cross-Platform:** Test on macOS and Linux

## Success Criteria

- ✅ New `monitor` commands work independently
- ✅ No changes to existing commands
- ✅ Metrics collection overhead < 1% CPU
- ✅ JSON output for API consumers
- ✅ Graceful handling of stopped models
- ✅ Cross-platform compatibility (macOS + Linux)
- ✅ Clean, documented APIs for future integration

## Contact

Questions: libor@arionetworks.com
