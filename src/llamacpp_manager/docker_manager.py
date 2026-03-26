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


class DockerManager:
    """Manages Docker containers running llama.cpp models."""

    def __init__(self, docker_compose_path: str = None):
        """
        Initialize Docker manager.

        Args:
            docker_compose_path: Path to docker-compose.yml file
        """
        self.docker_compose_path = docker_compose_path or "docker-compose.yml"
        self.port_map = {
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

    def _get_container_pid(self, container_name: str) -> Optional[int]:
        """
        Get the PID of the llama-server process inside the container.

        Args:
            container_name: Docker container name

        Returns:
            Process ID or None
        """
        try:
            cmd = ["docker", "inspect", "--format={{.State.Pid}}", container_name]
            exit_code, stdout, _ = self._run_command(cmd)
            if exit_code == 0:
                pid = int(stdout.strip())
                return pid if pid > 0 else None
        except (ValueError, IndexError):
            pass
        return None

    def start(self, container_name: str, timeout: int = 120) -> bool:
        """
        Start a Docker container.

        Args:
            container_name: Container name
            timeout: Timeout in seconds for startup

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting Docker container: {container_name}")

        exit_code, stdout, stderr = self._run_command(["docker", "start", container_name])
        if exit_code != 0:
            logger.error(f"Failed to start container {container_name}: {stderr}")
            return False

        # Wait for container to be healthy
        port = self.port_map.get(container_name)
        if not port:
            logger.warning(f"Unknown port for container {container_name}")
            return True

        start_time = time.time()
        while time.time() - start_time < timeout:
            health_status, _ = self._check_container_health(container_name, port)
            if health_status == "healthy":
                logger.info(f"Container {container_name} is healthy")
                return True
            elif health_status == "down":
                time.sleep(1)
            else:
                time.sleep(2)

        logger.warning(f"Container {container_name} did not become healthy within {timeout}s")
        return True  # Still consider it started even if health check slow

    def stop(self, container_name: str, timeout: int = 30) -> bool:
        """
        Stop a Docker container.

        Args:
            container_name: Container name
            timeout: Timeout in seconds for shutdown

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Stopping Docker container: {container_name}")

        exit_code, stdout, stderr = self._run_command(
            ["docker", "stop", "--time", str(timeout), container_name]
        )
        if exit_code != 0:
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

    def status(self, container_name: str) -> DockerContainerStatus:
        """
        Get status of a Docker container.

        Args:
            container_name: Container name

        Returns:
            DockerContainerStatus object
        """
        port = self.port_map.get(container_name, 9081)

        # Check if running
        exit_code, stdout, _ = self._run_command(
            ["docker", "inspect", "--format={{.State.Running}}", container_name]
        )
        is_running = stdout.strip().lower() == "true" if exit_code == 0 else False

        # Get health status
        health_status, latency_ms = self._check_container_health(container_name, port)
        if not is_running:
            health_status = "down"
            latency_ms = None

        # Get PID
        pid = self._get_container_pid(container_name) if is_running else None

        # Get container ID
        exit_code, stdout, _ = self._run_command(
            ["docker", "inspect", "--format={{.Id}}", container_name]
        )
        container_id = stdout.strip() if exit_code == 0 else None

        return DockerContainerStatus(
            name=container_name,
            port=port,
            container_id=container_id,
            running=is_running,
            health_status=health_status,
            latency_ms=latency_ms,
            pid=pid
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
        Get status of all containers as JSON.

        Returns:
            JSON string with container statuses
        """
        statuses = self.status_all()
        data = {
            "models": [asdict(s) for s in statuses],
            "infrastructure": [],
            "logging": {
                "enabled": False,
                "max_bytes": 0,
                "backups": 0,
                "timestamps": False
            }
        }
        return json.dumps(data)
