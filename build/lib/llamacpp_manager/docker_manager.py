"""
Docker container management for llama.cpp models.

File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/docker_manager.py
Description: Manages Docker containers running llama.cpp server instances
Author: Libor Ballaty <libor@arionetworks.com>
Created: 2026-03-26
"""

import subprocess
import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class DockerContainerStatus:
    """Status information for a Docker container."""
    name: str
    port: int
    container_id: Optional[str]
    running: bool
    health_status: str  # "healthy", "unhealthy", "starting", "down"
    latency_ms: Optional[int]
    pid: Optional[int]
    mode: str = "basic"  # Startup mode: basic, tools, performance, extended


class DockerManager:
    """Manages Docker containers running llama.cpp models."""

    def __init__(self, docker_compose_path: str = None):
        """
        Initialize Docker manager.

        Args:
            docker_compose_path: Path to docker-compose.yml file
        """
        self.docker_compose_path = docker_compose_path or "docker-compose.yml"

        # Default port map as fallback (for when no containers exist yet)
        self._default_port_map = {
            "llm-phi3": 9081,
            "llm-mistral7b": 9082,
            "llm-hermes-3": 9083,
            "llm-llama-3.1-8b": 9084,
            "llm-qwen-coder-7b": 9085,
            "llm-smollm3": 9086,
            "llm-llama-4-scout-17b": 9087,
            "llm-qwen-32b": 9088,
            "llm-deepseek-32b": 9089,
            "llm-mistral-24b": 9090,
        }

        # Discover containers from Colima profiles
        self.port_map = self._discover_containers()

    def _run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """
        Run a shell command and return exit code, stdout, stderr.

        Args:
            cmd: Command to run as list of strings

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return -1, "", "Command timed out"
        except Exception as e:
            logger.error(f"Error running command {' '.join(cmd)}: {e}")
            return -1, "", str(e)

    def _discover_containers(self) -> Dict[str, int]:
        """
        Auto-discover Docker containers from all Colima profiles.

        Scans all running Colima profiles for containers with:
        - Name pattern: llm-* OR
        - Label: llamacpp-manager.model=*

        Returns:
            Dict mapping container names to host ports
        """
        discovered = {}

        # Get running Colima profiles
        exit_code, stdout, _ = self._run_command(["colima", "list"])
        if exit_code != 0:
            logger.debug("Colima not available, using default port map")
            return self._default_port_map

        # Parse Colima profiles
        lines = stdout.strip().split("\n")
        if len(lines) < 2:
            logger.debug("No Colima profiles found, using default port map")
            return self._default_port_map

        profiles = []
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 2 and parts[1].lower() == "running":
                profiles.append(parts[0])

        if not profiles:
            logger.debug("No running Colima profiles, using default port map")
            return self._default_port_map

        # Start with default port map (always show all 10 containers)
        result = self._default_port_map.copy()
        discovered_count = 0

        # Query containers from each profile to update with actual ports
        for profile in profiles:
            context = f"colima-{profile}"
            # Get containers with port mappings
            exit_code, stdout, _ = self._run_command([
                "docker", "--context", context, "ps", "-a",
                "--format", "{{.Names}}|{{.Ports}}",
                "--filter", "name=llm-"
            ])

            if exit_code == 0:
                for line in stdout.strip().split("\n"):
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        ports = parts[1].strip()

                        # Extract host port from format like "0.0.0.0:9081->8080/tcp"
                        if "->" in ports:
                            port_mapping = ports.split("->")[0]
                            if ":" in port_mapping:
                                host_port = int(port_mapping.split(":")[-1])
                                result[name] = host_port  # Update with actual port
                                discovered_count += 1
                                logger.debug(f"Discovered container {name} on port {host_port}")

        logger.info(f"Port map: {len(result)} total containers, {discovered_count} exist")
        return result

    def _check_container_health(self, container_name: str, port: int) -> Tuple[str, Optional[int]]:
        """
        Check container health by testing HTTP endpoint.

        Args:
            container_name: Docker container name
            port: Port to check

        Returns:
            Tuple of (health_status, latency_ms)
        """
        import socket
        import time as time_module

        # First check if port is listening
        try:
            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
            sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError):
            return "down", None

        # Try health endpoint
        try:
            import urllib.request
            import urllib.error

            start_time = time_module.time()
            response = urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health",
                timeout=2
            )
            latency_ms = int((time_module.time() - start_time) * 1000)

            if response.status == 200:
                data = json.loads(response.read().decode())
                status = data.get("status", "ok")
                return "healthy" if status == "ok" else "starting", latency_ms
            else:
                return "unhealthy", latency_ms
        except Exception as e:
            logger.debug(f"Health check failed for {container_name}: {e}")
            return "unhealthy", None

    def _get_container_pid(self, container_name: str, colima_profile: str = "app") -> Optional[int]:
        """
        Get the PID of the llama-server process inside the container.

        Args:
            container_name: Docker container name
            colima_profile: Colima profile (default: "app")

        Returns:
            Process ID or None
        """
        try:
            cmd = ["docker", "--context", f"colima-{colima_profile}", "inspect", "--format={{.State.Pid}}", container_name]
            exit_code, stdout, _ = self._run_command(cmd)
            if exit_code == 0:
                pid = int(stdout.strip())
                return pid if pid > 0 else None
        except (ValueError, IndexError):
            pass
        return None

    def _get_extra_args_for_mode(self, mode: str) -> str:
        """
        Convert mode name to llama-server command-line arguments.

        Args:
            mode: One of "basic", "tools", "performance", "extended"

        Returns:
            Extra arguments string for llama-server
        """
        mode_args = {
            "basic": "",
            "tools": "--jinja",
            "performance": "--jinja --n-parallel 4 --batch-size 512 --ubatch-size 512",
            "extended": "--jinja --flash-attn",
        }
        return mode_args.get(mode, "--jinja")  # Default to tools mode

    def _container_exists(self, container_name: str, colima_profile: str = "app") -> bool:
        """
        Check if a container exists (running or stopped).

        Args:
            container_name: Container name
            colima_profile: Colima profile (default: "app")

        Returns:
            True if container exists, False otherwise
        """
        exit_code, _, _ = self._run_command(
            ["docker", "--context", f"colima-{colima_profile}", "inspect", "--format={{.State.Running}}", container_name]
        )
        return exit_code == 0

    def _remove_container(self, container_name: str, colima_profile: str = "app") -> bool:
        """
        Remove a container (force remove if running).

        Args:
            container_name: Container name
            colima_profile: Colima profile (default: "app")

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Removing container: {container_name}")
        exit_code, _, stderr = self._run_command(
            ["docker", "--context", f"colima-{colima_profile}", "rm", "-f", container_name]
        )
        if exit_code != 0:
            logger.warning(f"Failed to remove container {container_name}: {stderr}")
            return False
        return True

    def _get_model_info(self, container_name: str) -> Optional[Dict]:
        """
        Get model info from config based on container name.

        Args:
            container_name: Container name (e.g., "llm-phi3")

        Returns:
            Model config dict or None
        """
        from .config import load_config

        # Strip "llm-" prefix to get model name
        model_name = container_name.replace("llm-", "", 1)

        cfg = load_config()
        models = cfg.get("models", [])
        return next((m for m in models if m.get("name") == model_name), None)

    def create_container(self, container_name: str, mode: str = "tools", model_path: str = None, colima_profile: str = "app") -> bool:
        """
        Create a new Docker container for a model.

        Args:
            container_name: Container name (e.g., "llm-phi3")
            mode: Startup mode (basic/tools/performance/extended)
            model_path: Path to model file (if None, looks up from config)
            colima_profile: Colima profile to use (default: "app")

        Returns:
            True if successful, False otherwise
        """
        print(f"📦 Creating Docker container: {container_name}")
        print(f"   Mode: {mode}")
        print(f"   Profile: {colima_profile}")
        logger.info(f"Creating Docker container: {container_name} in {mode} mode on profile {colima_profile}")

        # Get port
        port = self.port_map.get(container_name)
        if not port:
            print(f"❌ Error: No port mapping for container {container_name}")
            logger.error(f"No port mapping for container {container_name}")
            return False

        print(f"   Port: {port}")

        # Get model path
        if not model_path:
            model_info = self._get_model_info(container_name)
            if not model_info:
                print(f"❌ Error: No model config found for {container_name}")
                logger.error(f"No model config found for {container_name}")
                return False
            model_path = model_info.get("model_path")

        if not model_path:
            print(f"❌ Error: No model path available for {container_name}")
            logger.error(f"No model path available for {container_name}")
            return False

        print(f"   Model: {model_path}")

        # Get extra args based on mode
        extra_args = self._get_extra_args_for_mode(mode)
        if extra_args:
            print(f"   Args: {extra_args}")

        # Build docker run command with Colima context
        cmd = [
            "docker", "--context", f"colima-{colima_profile}",
            "run", "-d",
            "--name", container_name,
            "--label", f"llamacpp-manager.model={container_name}",
            "--label", f"llamacpp-manager.mode={mode}",
            "-p", f"{port}:8080",
            "-v", f"{model_path}:/models/model.gguf:ro",
            "-e", f"MODEL_PATH=/models/model.gguf",
            "-e", f"PORT=8080",
        ]

        if extra_args:
            cmd.extend(["-e", f"EXTRA_ARGS={extra_args}"])

        # Use the llamacpp Docker image (must be built first)
        cmd.append("llamacpp-manager:latest")

        print(f"🚀 Running: docker run ...")
        logger.info(f"Creating container with command: {' '.join(cmd)}")
        exit_code, stdout, stderr = self._run_command(cmd)

        if exit_code != 0:
            print(f"❌ Failed to create container: {stderr}")
            logger.error(f"Failed to create container {container_name}: {stderr}")
            return False

        print(f"✅ Container {container_name} created successfully")
        logger.info(f"Container {container_name} created successfully")
        return True

    def start(self, container_name: str, timeout: int = 120, mode: str = "tools", colima_profile: str = "app") -> bool:
        """
        Start a Docker container, recreating with specified mode if needed.

        Args:
            container_name: Container name (e.g., "llm-phi3")
            timeout: Timeout in seconds for startup
            mode: Startup mode (basic/tools/performance/extended)
            colima_profile: Colima profile (default: "app")

        Returns:
            True if successful, False otherwise
        """
        print(f"▶️  Starting Docker container: {container_name}")
        print(f"   Mode: {mode}")
        print(f"   Profile: {colima_profile}")
        logger.info(f"Starting Docker container: {container_name} in {mode} mode on {colima_profile}")

        # Check if container exists
        if self._container_exists(container_name, colima_profile):
            print(f"   Container exists, checking mode...")
            # Check current mode from labels
            exit_code, stdout, _ = self._run_command([
                "docker", "--context", f"colima-{colima_profile}", "inspect",
                "--format={{index .Config.Labels \"llamacpp-manager.mode\"}}",
                container_name
            ])

            current_mode = stdout.strip() if exit_code == 0 else None

            # If mode changed, recreate container
            if current_mode and current_mode != mode:
                print(f"   Mode changed: {current_mode} → {mode}")
                print(f"   Recreating container...")
                logger.info(f"Mode changed from {current_mode} to {mode}, recreating container")
                if not self._remove_container(container_name, colima_profile):
                    print(f"❌ Failed to remove old container")
                    return False
                if not self.create_container(container_name, mode, colima_profile=colima_profile):
                    return False
            else:
                # Same mode or no mode label, just start it
                print(f"   Starting existing container...")
                exit_code, _, stderr = self._run_command(
                    ["docker", "--context", f"colima-{colima_profile}", "start", container_name]
                )
                if exit_code != 0:
                    print(f"❌ Failed to start: {stderr}")
                    logger.error(f"Failed to start container {container_name}: {stderr}")
                    return False
        else:
            # Container doesn't exist, create it
            print(f"   Container doesn't exist, creating...")
            logger.info(f"Container {container_name} doesn't exist, creating it")
            if not self.create_container(container_name, mode, colima_profile=colima_profile):
                return False

        # Wait for container to be healthy
        port = self.port_map.get(container_name)
        if not port:
            logger.warning(f"Unknown port for container {container_name}")
            return True

        print(f"⏳ Waiting for container to be healthy on port {port}...")
        start_time = time.time()
        last_status = None
        while time.time() - start_time < timeout:
            health_status, latency_ms = self._check_container_health(container_name, port)
            if health_status != last_status:
                print(f"   Status: {health_status}")
                last_status = health_status

            if health_status == "healthy":
                print(f"✅ Container is healthy (latency: {latency_ms}ms)")
                logger.info(f"Container {container_name} is healthy")
                return True
            elif health_status == "down":
                time.sleep(1)
            else:
                time.sleep(2)

        print(f"⚠️  Container did not become healthy within {timeout}s, but may still be starting")
        logger.warning(f"Container {container_name} did not become healthy within {timeout}s")
        return True  # Still consider it started even if health check slow

    def stop(self, container_name: str, timeout: int = 30, colima_profile: str = "app") -> bool:
        """
        Stop a Docker container.

        Args:
            container_name: Container name
            timeout: Timeout in seconds for shutdown
            colima_profile: Colima profile (default: "app")

        Returns:
            True if successful, False otherwise
        """
        print(f"⏹️  Stopping Docker container: {container_name}")
        logger.info(f"Stopping Docker container: {container_name}")

        exit_code, stdout, stderr = self._run_command(
            ["docker", "--context", f"colima-{colima_profile}", "stop", "--time", str(timeout), container_name]
        )
        if exit_code != 0:
            print(f"❌ Failed to stop: {stderr}")
            logger.error(f"Failed to stop container {container_name}: {stderr}")
            return False

        # Verify port is no longer listening
        port = self.port_map.get(container_name)
        if port:
            max_retries = 10
            for i in range(max_retries):
                health_status, _ = self._check_container_health(container_name, port)
                if health_status == "down":
                    logger.info(f"Container {container_name} stopped successfully")
                    return True
                time.sleep(1)

        return True

    def restart(self, container_name: str) -> bool:
        """
        Restart a Docker container.

        Args:
            container_name: Container name

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Restarting Docker container: {container_name}")
        self.stop(container_name)
        time.sleep(2)
        return self.start(container_name)

    def status(self, container_name: str, colima_profile: str = "app") -> DockerContainerStatus:
        """
        Get status of a Docker container.

        Args:
            container_name: Container name
            colima_profile: Colima profile to check (default: "app")

        Returns:
            DockerContainerStatus object
        """
        port = self.port_map.get(container_name, 9081)

        # Check if running (need to specify Colima context)
        exit_code, stdout, stderr = self._run_command(
            ["docker", "--context", f"colima-{colima_profile}", "inspect", "--format={{.State.Running}}", container_name]
        )
        is_running = stdout.strip().lower() == "true" if exit_code == 0 else False

        logger.debug(f"Container {container_name} running check: exit={exit_code}, stdout='{stdout.strip()}', running={is_running}")

        # Get health status
        health_status, latency_ms = self._check_container_health(container_name, port)
        if not is_running:
            health_status = "down"
            latency_ms = None

        logger.debug(f"Container {container_name} health: {health_status}, latency: {latency_ms}ms")

        # Get PID
        pid = self._get_container_pid(container_name, colima_profile) if is_running else None

        # Get container ID
        exit_code, stdout, _ = self._run_command(
            ["docker", "--context", f"colima-{colima_profile}", "inspect", "--format={{.Id}}", container_name]
        )
        container_id = stdout.strip() if exit_code == 0 else None

        # Get mode from container labels
        exit_code, stdout, _ = self._run_command([
            "docker", "--context", f"colima-{colima_profile}", "inspect",
            "--format={{index .Config.Labels \"llamacpp-manager.mode\"}}",
            container_name
        ])
        mode = stdout.strip() if exit_code == 0 and stdout.strip() else "basic"

        return DockerContainerStatus(
            name=container_name,
            port=port,
            container_id=container_id,
            running=is_running,
            health_status=health_status,
            latency_ms=latency_ms,
            pid=pid,
            mode=mode
        )

    def status_all(self) -> List[DockerContainerStatus]:
        """
        Get status of all configured Docker containers.

        Returns:
            List of DockerContainerStatus objects
        """
        return [self.status(name) for name in self.port_map.keys()]

    def logs(self, container_name: str, tail: int = 100) -> str:
        """
        Get logs from a Docker container.

        Args:
            container_name: Container name
            tail: Number of lines to return

        Returns:
            Log output as string
        """
        exit_code, stdout, stderr = self._run_command(
            ["docker", "logs", "--tail", str(tail), container_name]
        )
        return stdout if exit_code == 0 else stderr

    def start_all(self) -> bool:
        """Start all Docker containers."""
        logger.info("Starting all Docker containers")
        success = True
        for container_name in self.port_map.keys():
            if not self.start(container_name):
                success = False
        return success

    def stop_all(self) -> bool:
        """Stop all Docker containers."""
        logger.info("Stopping all Docker containers")
        success = True
        for container_name in self.port_map.keys():
            if not self.stop(container_name):
                success = False
        return success

    def to_json(self) -> str:
        """
        Get status of all containers as JSON matching GUI StatusRow format.

        Returns:
            JSON string with container statuses
        """
        statuses = self.status_all()

        # Convert Docker container status to match GUI StatusRow format
        models = []
        for s in statuses:
            # Map health_status to GUI-expected values
            health_state = "ok" if s.health_status == "healthy" else s.health_status

            models.append({
                "name": s.name,
                "pid": s.pid,
                "host": "127.0.0.1",
                "port": s.port,
                "up": s.running,  # "running" → "up" for GUI compatibility
                "latency_ms": s.latency_ms,
                "http_status": 200 if s.health_status == "healthy" else None,
                "version": None,
                "mode": s.mode,  # Startup mode from container labels
                "log_path": None,
                "health_state": health_state,  # Map "healthy" → "ok" for GUI
                "uptime": None
            })

        data = {
            "models": models,
            "infrastructure": [],
            "logging": {
                "enabled": False,
                "max_bytes": 0,
                "backups": 0,
                "timestamps": False
            }
        }
        return json.dumps(data)
