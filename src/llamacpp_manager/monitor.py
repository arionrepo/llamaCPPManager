"""
Advanced model monitoring and crash detection.
Improves on the original ~/llms/bin/llm_monitor functionality.
"""

from __future__ import annotations

import json
import logging
import time
import threading
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

from .config import load_config
from .health import check_endpoint
from .utils import logs_dir, read_pid, process_alive
from .process import start_process
from .launchd import render_plist, plist_path, write_plist, launchctl_bootstrap, launchctl_kickstart

logger = logging.getLogger(__name__)


class ModelMonitor:
    """Enhanced model monitoring with crash detection and auto-restart."""

    def __init__(self, check_interval: int = 10):
        self.check_interval = check_interval
        self.running = False
        self.tracked_models: Set[str] = set()
        self.state_dir = Path.home() / ".llamacpp-manager" / "monitor-state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._load_tracked_models()

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
        if model_name not in self.tracked_models:
            return False

        status = self.get_model_status(model_name, config)
        health_state = status["health_state"]
        process_state = status["process_state"]

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
        try:
            models = config.get("models", [])
            model_config = next((m for m in models if m["name"] == model_name), None)

            if not model_config:
                logger.error(f"Cannot restart '{model_name}': model config not found")
                return False

            logger.info(f"Attempting to restart crashed model: {model_name}")

            # Build model spec
            from .config import ModelSpec
            spec = ModelSpec(
                name=model_config["name"],
                model_path=model_config["model_path"],
                host=model_config.get("host", "127.0.0.1"),
                port=int(model_config["port"]),
                args=list(model_config.get("args", []) or []),
                env=dict(model_config.get("env", {}) or {}),
                autostart=bool(model_config.get("autostart", False)),
            )

            # Start the process
            llama_path = config.get("llama_server_path")
            log_dir = Path(config.get("log_dir"))

            pid = start_process(llama_path, spec, log_dir)

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

    def monitor_loop(self):
        """Main monitoring loop - checks all tracked models periodically."""
        logger.info(f"Starting monitor loop (check interval: {self.check_interval}s)")

        while self.running:
            try:
                config = load_config()
                restart_count = 0

                for model_name in list(self.tracked_models):
                    if self.check_model_health(model_name, config):
                        restart_count += 1

                if restart_count > 0:
                    logger.info(f"Monitor cycle complete - restarted {restart_count} model(s)")

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
        return {
            "running": self.running,
            "tracked_models": list(self.tracked_models),
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