"""
Docker CLI commands for managing containerized llama.cpp models.

File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/docker_commands.py
Description: CLI commands for Docker container lifecycle management
Author: Libor Ballaty <libor@arionetworks.com>
Created: 2026-03-26
"""

import click
import json
import os
from pathlib import Path

from .docker_manager import DockerManager

# Get the docker-compose.yml path
DOCKER_COMPOSE_PATH = Path(__file__).parent.parent.parent / "docker-compose.yml"
DEFAULT_DOCKER_COMPOSE = str(DOCKER_COMPOSE_PATH) if DOCKER_COMPOSE_PATH.exists() else "docker-compose.yml"

# Initialize Docker manager
docker_mgr = None


def get_docker_manager():
    """Get or create the Docker manager instance."""
    global docker_mgr
    if docker_mgr is None:
        docker_mgr = DockerManager(DEFAULT_DOCKER_COMPOSE)
    return docker_mgr


@click.group()
def docker():
    """Manage Docker containers running llama.cpp models."""
    pass


@docker.command()
@click.argument("model_name", default="all")
def start(model_name):
    """
    Start a Docker container for a model.

    Examples:
        llamacpp-manager docker start phi3
        llamacpp-manager docker start all
    """
    mgr = get_docker_manager()

    if model_name == "all":
        click.echo("Starting all Docker containers...")
        success = mgr.start_all()
        if success:
            click.echo("All Docker containers started successfully")
        else:
            click.echo("Some containers failed to start", err=True)
            exit(1)
    else:
        container_name = f"llm-{model_name}" if not model_name.startswith("llm-") else model_name
        click.echo(f"Starting Docker container: {container_name}...")
        success = mgr.start(container_name)
        if success:
            status = mgr.status(container_name)
            click.echo(f"Container {container_name} started successfully")
            click.echo(f"  Port: {status.port}")
            click.echo(f"  Status: {status.health_status}")
        else:
            click.echo(f"Failed to start container {container_name}", err=True)
            exit(1)


@docker.command()
@click.argument("model_name", default="all")
def stop(model_name):
    """
    Stop a Docker container.

    Examples:
        llamacpp-manager docker stop phi3
        llamacpp-manager docker stop all
    """
    mgr = get_docker_manager()

    if model_name == "all":
        click.echo("Stopping all Docker containers...")
        success = mgr.stop_all()
        if success:
            click.echo("All Docker containers stopped successfully")
        else:
            click.echo("Some containers failed to stop", err=True)
            exit(1)
    else:
        container_name = f"llm-{model_name}" if not model_name.startswith("llm-") else model_name
        click.echo(f"Stopping Docker container: {container_name}...")
        success = mgr.stop(container_name)
        if success:
            click.echo(f"Container {container_name} stopped successfully")
        else:
            click.echo(f"Failed to stop container {container_name}", err=True)
            exit(1)


@docker.command()
@click.argument("model_name")
def restart(model_name):
    """
    Restart a Docker container.

    Examples:
        llamacpp-manager docker restart phi3
    """
    mgr = get_docker_manager()
    container_name = f"llm-{model_name}" if not model_name.startswith("llm-") else model_name

    click.echo(f"Restarting Docker container: {container_name}...")
    success = mgr.restart(container_name)
    if success:
        status = mgr.status(container_name)
        click.echo(f"Container {container_name} restarted successfully")
        click.echo(f"  Port: {status.port}")
        click.echo(f"  Status: {status.health_status}")
    else:
        click.echo(f"Failed to restart container {container_name}", err=True)
        exit(1)


@docker.command()
@click.argument("model_name", required=False, default=None)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def status(model_name, output_json):
    """
    Check status of Docker container(s).

    Examples:
        llamacpp-manager docker status
        llamacpp-manager docker status phi3
        llamacpp-manager docker status --json
    """
    mgr = get_docker_manager()

    if model_name is None:
        # Show all containers
        if output_json:
            click.echo(mgr.to_json())
        else:
            statuses = mgr.status_all()
            if not statuses:
                click.echo("No Docker containers configured")
                return

            click.echo("Docker Container Status:")
            click.echo("-" * 80)
            for status in statuses:
                health_icon = "🟢" if status.health_status == "healthy" else \
                             "🟠" if status.health_status == "starting" else \
                             "🔴"
                click.echo(f"{health_icon} {status.name}")
                click.echo(f"   Port: {status.port}")
                click.echo(f"   Status: {status.health_status}")
                if status.latency_ms:
                    click.echo(f"   Latency: {status.latency_ms}ms")
                if status.pid:
                    click.echo(f"   PID: {status.pid}")
    else:
        # Show specific container
        container_name = f"llm-{model_name}" if not model_name.startswith("llm-") else model_name
        st = mgr.status(container_name)

        if output_json:
            click.echo(json.dumps({
                "models": [{
                    "name": st.name,
                    "port": st.port,
                    "container_id": st.container_id,
                    "running": st.running,
                    "health_status": st.health_status,
                    "latency_ms": st.latency_ms,
                    "pid": st.pid
                }],
                "infrastructure": [],
                "logging": {
                    "enabled": False,
                    "max_bytes": 0,
                    "backups": 0,
                    "timestamps": False
                }
            }))
        else:
            health_icon = "🟢" if st.health_status == "healthy" else \
                         "🟠" if st.health_status == "starting" else \
                         "🔴"
            click.echo(f"{health_icon} {st.name}")
            click.echo(f"   Port: {st.port}")
            click.echo(f"   Running: {st.running}")
            click.echo(f"   Status: {st.health_status}")
            if st.latency_ms:
                click.echo(f"   Latency: {st.latency_ms}ms")
            if st.pid:
                click.echo(f"   PID: {st.pid}")


@docker.command()
@click.argument("model_name")
@click.option("--tail", default=50, help="Number of lines to show")
def logs(model_name, tail):
    """
    View logs from a Docker container.

    Examples:
        llamacpp-manager docker logs phi3
        llamacpp-manager docker logs phi3 --tail 100
    """
    mgr = get_docker_manager()
    container_name = f"llm-{model_name}" if not model_name.startswith("llm-") else model_name

    click.echo(f"Fetching logs from {container_name}...")
    output = mgr.logs(container_name, tail=tail)
    click.echo(output)
