"""
Advanced model and infrastructure monitoring with crash detection and auto-restart.
Improves on the original ~/llms/bin/llm_monitor functionality.
"""

from __future__ import annotations

import json
import logging
import time
import threading
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

from .config import load_config, list_infrastructure_components
from .health import check_endpoint, check_infrastructure_component_health
from .utils import logs_dir, read_pid, process_alive
from .process import start_process
from .launchd import render_plist, plist_path, write_plist, launchctl_bootstrap, launchctl_kickstart
from . import infrastructure

logger = logging.getLogger(__name__)


class ModelMonitor:
    """Enhanced model and infrastructure monitoring with crash detection and auto-restart."""

    def __init__(self, check_interval: int = 10):
        self.check_interval = check_interval
        self.running = False
        self.tracked_models: Set[str] = set()
        self.infrastructure_stats: Dict[str, Dict[str, Any]] = {}  # Track failures and restarts
        self.state_dir = Path.home() / ".llamacpp-manager" / "monitor-state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._load_tracked_models()
        self._load_infrastructure_stats()

    def _load_tracked_models(self):
        """Load previously tracked models from state files."""
        for state_file in self.state_dir.glob("*.enabled"):
            model_name = state_file.stem
            self.tracked_models.add(model_name)
            logger.info(f"Loaded tracking for model: {model_name}")

    def track_model(self, model_name: str) -> None:
        """Track a model for auto-restart monitoring."""
        self.tracked_models.add(model_name)
        state_file = self.state_dir / f"{model_name}.enabled"
        state_file.touch()
        logger.info(f"Now tracking model '{model_name}' for auto-restart")

    def untrack_model(self, model_name: str) -> None:
        """Stop tracking a model."""
        self.tracked_models.discard(model_name)
        state_file = self.state_dir / f"{model_name}.enabled"
        state_file.unlink(missing_ok=True)
        logger.info(f"Stopped tracking model '{model_name}'")

    def get_tracked_models(self) -> List[str]:
        """Get list of currently tracked models."""
        return list(self.tracked_models)

    def get_model_status(self, model_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed status for a model including health state."""
        models = config.get("models", [])
        model_config = next((m for m in models if m["name"] == model_name), None)

        if not model_config:
            return {"error": f"Model '{model_name}' not found in config"}

        host = model_config.get("host", "127.0.0.1")
        port = int(model_config["port"])
        timeout_ms = int(config.get("timeout_ms", 3000))

        # Enhanced health check
        health = check_endpoint(host, port, timeout_ms=timeout_ms)

        # Check process state
        pid = None
        process_state = "unknown"
        try:
            pid = read_pid(model_name)
            process_state = "running" if process_alive(pid) else "dead"
        except FileNotFoundError:
            process_state = "not_started"

        return {
            "name": model_name,
            "host": host,
            "port": port,
            "pid": pid,
            "process_state": process_state,
            "health_state": health.get("health_state", "down"),
            "http_status": health.get("http_status"),
            "latency_ms": health.get("latency_ms", 0),
            "up": health.get("up", False),
            "version": health.get("version"),
            "tracked": model_name in self.tracked_models,
        }

    def check_model_health(self, model_name: str, config: Dict[str, Any]) -> bool:
        """Check if a model needs restart. Returns True if restart was attempted."""
        from .lifecycle_log import log_event
        if model_name not in self.tracked_models:
            return False

        status = self.get_model_status(model_name, config)
        health_state = status["health_state"]
        process_state = status["process_state"]

        log_event("monitor.check_health", model=model_name,
                  caller="monitor.check_model_health",
                  health_state=health_state, process_state=process_state,
                  pid=status.get("pid"))

        # Model is healthy - no action needed
        if health_state == "ok":
            return False

        # Model is starting - give it more time unless it's been too long
        if health_state == "starting":
            logger.debug(f"Model '{model_name}' is starting, waiting...")
            return False

        # Model is down - check if it should be running
        if health_state == "down":
            if process_state in ["running", "dead"]:
                logger.warning(f"Detected crashed model: {model_name} (process: {process_state}, health: {health_state})")
                return self._restart_model(model_name, config)

        return False

    def _restart_model(self, model_name: str, config: Dict[str, Any]) -> bool:
        """Restart a crashed model. Returns True if restart was attempted."""
        from .lifecycle_log import log_event
        log_event("monitor.restart.begin", model=model_name, caller="monitor._restart_model")
        try:
            models = config.get("models", [])
            model_config = next((m for m in models if m["name"] == model_name), None)

            if not model_config:
                logger.error(f"Cannot restart '{model_name}': model config not found")
                return False

            logger.info(f"Attempting to restart crashed model: {model_name}")

            # Build model spec (canonical mapping — previously dropped
            # mode/ctx_size/n_gpu_layers, so an auto-restart relaunched the model
            # in basic mode with default context regardless of its config)
            from .config import spec_from_dict
            spec = spec_from_dict(model_config)

            # Start the process
            llama_path = config.get("llama_server_path")
            log_dir = Path(config.get("log_dir"))
            logging_config = config.get("logging", {})

            pid = start_process(llama_path, spec, log_dir, logging_config=logging_config)

            from .utils import write_pid
            write_pid(spec.name, pid)

            logger.info(f"Restarted '{model_name}' with PID {pid}")

            # Wait a moment and verify restart
            time.sleep(3)
            status = self.get_model_status(model_name, config)

            if status["health_state"] in ["ok", "starting"]:
                logger.info(f"Successfully restarted '{model_name}' (health: {status['health_state']})")
                return True
            else:
                logger.error(f"Restart of '{model_name}' failed (health: {status['health_state']})")
                return False

        except Exception as e:
            logger.error(f"Failed to restart '{model_name}': {e}")
            return False

    def _load_infrastructure_stats(self):
        """Load infrastructure monitoring stats from state file."""
        stats_file = self.state_dir / "infrastructure_stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, "r") as f:
                    self.infrastructure_stats = json.load(f)
                logger.info(f"Loaded infrastructure stats for {len(self.infrastructure_stats)} components")
            except Exception as e:
                logger.warning(f"Failed to load infrastructure stats: {e}")
                self.infrastructure_stats = {}

    def _save_infrastructure_stats(self):
        """Save infrastructure monitoring stats to state file."""
        stats_file = self.state_dir / "infrastructure_stats.json"
        try:
            with open(stats_file, "w") as f:
                json.dump(self.infrastructure_stats, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save infrastructure stats: {e}")

    def check_infrastructure_health(self, name: str, component: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """
        Check infrastructure component health and restart if needed.

        Returns True if restart was attempted.
        """
        # Initialize stats if not exists
        if name not in self.infrastructure_stats:
            self.infrastructure_stats[name] = {
                "consecutive_failures": 0,
                "total_restarts": 0,
                "last_success_time": None,
                "last_failure_time": None,
                "last_restart_time": None
            }

        stats = self.infrastructure_stats[name]
        restart_policy = component.get("restart_policy", {})

        # Check health
        health = check_infrastructure_component_health(component)

        if health["healthy"]:
            # Component healthy
            if stats["consecutive_failures"] > 0:
                logger.info(f"Infrastructure '{name}' recovered (was failing {stats['consecutive_failures']} times)")
            stats["consecutive_failures"] = 0
            stats["last_success_time"] = time.time()
            self._save_infrastructure_stats()
            return False

        # Component unhealthy
        stats["consecutive_failures"] += 1
        stats["last_failure_time"] = time.time()

        # Check if restart is enabled
        if not restart_policy.get("enabled", True):
            logger.debug(f"Infrastructure '{name}' unhealthy but restart disabled: {health['status']}")
            self._save_infrastructure_stats()
            return False

        # Check failure threshold
        failure_threshold = restart_policy.get("health_check_failures_threshold", 3)
        if stats["consecutive_failures"] < failure_threshold:
            logger.debug(f"Infrastructure '{name}' failing ({stats['consecutive_failures']}/{failure_threshold}): {health['status']}")
            self._save_infrastructure_stats()
            return False

        # Check max retries
        max_retries = restart_policy.get("max_retries", 3)
        if stats["total_restarts"] >= max_retries:
            logger.error(f"Infrastructure '{name}' FAILED - exhausted {max_retries} restart attempts")
            self._save_infrastructure_stats()
            return False

        # Check backoff period
        backoff_seconds = restart_policy.get("backoff_seconds", 10)
        if stats["last_restart_time"]:
            time_since_restart = time.time() - stats["last_restart_time"]
            if time_since_restart < backoff_seconds:
                remaining = int(backoff_seconds - time_since_restart)
                logger.debug(f"Infrastructure '{name}' in backoff period ({remaining}s remaining)")
                return False

        # Attempt restart
        logger.warning(f"Attempting restart of infrastructure '{name}' (attempt {stats['total_restarts'] + 1}/{max_retries})")

        # Stop first
        success, msg = infrastructure.stop_infrastructure_component(component)
        if not success:
            logger.warning(f"Stop '{name}' warning: {msg}")

        # Brief delay
        time.sleep(2)

        # Start
        success, msg = infrastructure.start_infrastructure_component(component)

        stats["last_restart_time"] = time.time()
        stats["total_restarts"] += 1

        if success:
            logger.info(f"Successfully restarted infrastructure '{name}'")
            stats["consecutive_failures"] = 0
        else:
            logger.error(f"Failed to restart infrastructure '{name}': {msg}")

        self._save_infrastructure_stats()
        return True

    def monitor_loop(self):
        """Main monitoring loop - checks all tracked models and enabled infrastructure periodically."""
        logger.info(f"Starting monitor loop (check interval: {self.check_interval}s)")

        while self.running:
            try:
                config = load_config()
                restart_count = 0

                # Check models
                for model_name in list(self.tracked_models):
                    if self.check_model_health(model_name, config):
                        restart_count += 1

                # Check infrastructure (only if monitoring enabled)
                monitoring_config = config.get("monitoring", {})
                if monitoring_config.get("enabled", True):
                    components = list_infrastructure_components(config)
                    for name, component in components.items():
                        if component.get("enabled", True):
                            if self.check_infrastructure_health(name, component, config):
                                restart_count += 1

                if restart_count > 0:
                    logger.info(f"Monitor cycle complete - restarted {restart_count} component(s)")

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            # Sleep with early exit on stop
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Monitor loop stopped")

    def start_monitoring(self):
        """Start the monitoring daemon in a background thread."""
        if self.running:
            logger.warning("Monitor already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Model monitor started")

    def stop_monitoring(self):
        """Stop the monitoring daemon."""
        if not self.running:
            return

        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2)
        logger.info("Model monitor stopped")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        total_infrastructure_restarts = sum(s.get("total_restarts", 0) for s in self.infrastructure_stats.values())
        total_infrastructure_failures = sum(s.get("consecutive_failures", 0) for s in self.infrastructure_stats.values())

        return {
            "running": self.running,
            "tracked_models": list(self.tracked_models),
            "infrastructure_monitored": list(self.infrastructure_stats.keys()),
            "infrastructure_total_restarts": total_infrastructure_restarts,
            "infrastructure_total_failures": total_infrastructure_failures,
            "check_interval": self.check_interval,
            "state_dir": str(self.state_dir),
        }


# Global monitor instance
_monitor: Optional[ModelMonitor] = None


def get_monitor() -> ModelMonitor:
    """Get the global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ModelMonitor()
    return _monitor