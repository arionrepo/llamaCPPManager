# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/model_manager.py
# Description: Unified manager for native and containerized model deployments with exclusive group support
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-07

"""
Unified model lifecycle management.

Business Purpose: Provide single interface for starting/stopping
models regardless of deployment type (native or container), with
support for exclusive model groups and resource management.
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path
import time

from .config import (
    load_config,
    get_model,
    list_models,
    get_model_group,
    get_model_group_for_model,
    list_model_groups,
    ModelSpec
)
from .process import start_process, stop_process
from .utils import write_pid, read_pid, process_alive, port_in_use


class DeploymentType(Enum):
    """Model deployment types."""
    NATIVE = "native"        # Direct llama-server process
    CONTAINER = "container"  # Docker container via Colima


class ModelManager:
    """
    Unified model lifecycle manager.

    Handles both native and containerized deployments with
    support for exclusive model groups to prevent resource
    conflicts.

    Business Purpose: Provides consistent interface for model
    management regardless of deployment type, with automatic
    enforcement of exclusive group constraints.
    """

    def __init__(self):
        """Initialize model manager."""
        self.config = load_config()
        self._load_model_groups()

    def _load_model_groups(self):
        """Load model groups from configuration."""
        self.model_groups = list_model_groups(self.config)

    def start_model(
        self,
        model_name: str,
        force_deployment: Optional[DeploymentType] = None
    ) -> Tuple[bool, str]:
        """
        Start model using configured or specified deployment type.

        Args:
            model_name: Name of model to start
            force_deployment: Override config deployment type

        Returns:
            Tuple of (success: bool, message: str)

        Example:
            manager = ModelManager()

            # Start using config deployment type (native)
            success, msg = manager.start_model("qwen-coder-32b")

            # Force container deployment
            success, msg = manager.start_model(
                "qwen-coder-32b",
                force_deployment=DeploymentType.CONTAINER
            )
        """
        model_config = get_model(self.config, model_name)
        if not model_config:
            return False, f"model '{model_name}' not found in configuration"

        # Check if model is in exclusive group and stop siblings
        group_name = get_model_group_for_model(self.config, model_name)
        if group_name:
            group = get_model_group(self.config, group_name)
            if group and group.get("exclusive"):
                self._stop_group_siblings(model_name, group)

        # Determine deployment type
        deployment = force_deployment or self._get_deployment_type(model_config)

        # Route to appropriate launcher
        if deployment == DeploymentType.NATIVE:
            return self._start_native(model_config)
        elif deployment == DeploymentType.CONTAINER:
            return self._start_container(model_config)

        return False, f"unknown deployment type: {deployment}"

    def stop_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Stop model regardless of deployment type.

        Automatically detects if model is native or containerized
        and uses appropriate stop method.

        Args:
            model_name: Name of model to stop

        Returns:
            Tuple of (success: bool, message: str)

        Example:
            manager = ModelManager()
            success, msg = manager.stop_model("qwen-coder-32b")
        """
        model_config = get_model(self.config, model_name)
        if not model_config:
            return False, f"model '{model_name}' not found in configuration"

        # Detect current deployment type
        deployment = self._detect_current_deployment(model_config)

        if deployment == DeploymentType.NATIVE:
            return self._stop_native(model_config)
        elif deployment == DeploymentType.CONTAINER:
            return self._stop_container(model_config)

        return False, f"model '{model_name}' is not running"

    def _get_deployment_type(self, model_config: Dict[str, Any]) -> DeploymentType:
        """Get deployment type from model configuration."""
        dtype = model_config.get("deployment_type", "native")
        try:
            return DeploymentType(dtype)
        except ValueError:
            # Default to native if invalid
            return DeploymentType.NATIVE

    def _detect_current_deployment(self, model_config: Dict[str, Any]) -> Optional[DeploymentType]:
        """
        Detect how a model is currently deployed.

        Returns:
            DeploymentType if model is running, None otherwise
        """
        model_name = model_config["name"]

        # Check if running as native process via PID file
        try:
            pid = read_pid(model_name)
            if process_alive(pid):
                return DeploymentType.NATIVE
        except FileNotFoundError:
            pass

        # TODO: Check if running as container when container support is added

        return None

    def _start_native(self, model_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Start model as native process.

        Uses process.start_process() to spawn llama-server.
        """
        llama_path = self.config.get("llama_server_path")
        log_dir = Path(self.config.get("log_dir"))

        # Create ModelSpec from config
        spec = ModelSpec(
            name=model_config["name"],
            model_path=model_config["model_path"],
            host=model_config.get("host", "127.0.0.1"),
            port=int(model_config["port"]),
            args=list(model_config.get("args", []) or []),
            env=dict(model_config.get("env", {}) or {}),
            autostart=bool(model_config.get("autostart", False)),
            deployment_type=model_config.get("deployment_type", "native"),
            group=model_config.get("group"),
            metadata=model_config.get("metadata")
        )

        # Check port availability
        if port_in_use(spec.host, spec.port):
            return False, f"port {spec.port} on {spec.host} is already in use"

        try:
            # Start the process
            pid = start_process(llama_path, spec, log_dir)
            write_pid(spec.name, pid)
            return True, f"started pid={pid} port={spec.port}"
        except Exception as e:
            return False, f"failed to start: {e}"

    def _stop_native(self, model_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Stop model running as native process.

        Uses process.stop_process() to terminate llama-server.
        """
        model_name = model_config["name"]

        try:
            # Read PID file
            pid = read_pid(model_name)
        except FileNotFoundError:
            return False, f"no pid file found for {model_name}"

        # Check if process is actually alive
        if not process_alive(pid):
            return False, f"process {pid} is not running"

        try:
            # Stop the process
            stop_process(pid, timeout=5.0)
            return True, f"stopped pid={pid}"
        except Exception as e:
            return False, f"failed to stop: {e}"

    def _start_container(self, model_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Start model as Docker container.

        This is a placeholder for future container support.
        """
        # TODO: Implement container deployment when containers module is ready
        return False, "container deployment not yet implemented - use deployment_type: native"

    def _stop_container(self, model_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Stop model running as Docker container.

        This is a placeholder for future container support.
        """
        # TODO: Implement container stop when containers module is ready
        return False, "container deployment not yet implemented"

    def _stop_group_siblings(self, model_name: str, group: Dict[str, Any]):
        """
        Stop other models in same exclusive group.

        Args:
            model_name: Model being started (will not be stopped)
            group: Group configuration dictionary
        """
        members = group.get("members", [])
        for sibling in members:
            if sibling != model_name:
                # Check if sibling is running
                sibling_config = get_model(self.config, sibling)
                if sibling_config:
                    deployment = self._detect_current_deployment(sibling_config)
                    if deployment:
                        # Stop the sibling
                        self.stop_model(sibling)
                        # Give it a moment to shut down
                        time.sleep(0.5)

    def get_active_models(self) -> List[Dict[str, Any]]:
        """
        Get list of currently running models with deployment info.

        Returns:
            List of dicts with model name, deployment_type, group, etc.

        Example:
            manager = ModelManager()
            active = manager.get_active_models()
            for model in active:
                print(f"{model['name']} running as {model['deployment_type']}")
        """
        active = []
        for model_config in list_models(self.config):
            deployment = self._detect_current_deployment(model_config)
            if deployment:
                active.append({
                    "name": model_config["name"],
                    "deployment_type": deployment.value,
                    "group": model_config.get("group"),
                    "host": model_config.get("host", "127.0.0.1"),
                    "port": model_config.get("port"),
                    "metadata": model_config.get("metadata", {})
                })
        return active

    def get_group_active_model(self, group_name: str) -> Optional[str]:
        """
        Get the currently active model in a group.

        Args:
            group_name: Name of model group

        Returns:
            Name of active model in group, or None if no model is running

        Example:
            manager = ModelManager()
            active = manager.get_group_active_model("coding-models")
            if active:
                print(f"Active coding model: {active}")
        """
        group = get_model_group(self.config, group_name)
        if not group:
            return None

        members = group.get("members", [])
        for member in members:
            model_config = get_model(self.config, member)
            if model_config:
                deployment = self._detect_current_deployment(model_config)
                if deployment:
                    return member

        return None
