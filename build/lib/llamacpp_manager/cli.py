import argparse
import os
import shlex
import subprocess
import sys
import traceback
from typing import Any, Dict, List, Optional
from pathlib import Path

from . import __version__
from .config import (
    DEFAULT_LLAMA_SERVER_PATH,
    ModelSpec,
    add_model,
    get_model,
    load_config,
    remove_model,
    save_config,
    update_model,
    find_next_available_port,
    list_infrastructure_components,
    get_infrastructure_component,
)
from .utils import app_support_dir, logs_dir, config_path, ensure_dir, to_json, migrate_directory, write_pid, read_pid, remove_pid, process_alive, port_in_use
from .process import start_process, stop_process, build_argv
from .mlx_process import start_mlx_process, build_mlx_argv
from .health import check_endpoint
from .launchd import render_plist, plist_path, write_plist, launchctl_bootstrap, launchctl_kickstart, launchctl_bootout
from .discovery import find_llama_processes
from .query import query_model_completion, query_model_chat, list_available_models, ModelQueryError
from . import infrastructure
from .docker_manager import DockerManager


def parse_env(items: List[str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for it in items:
        if "=" not in it:
            raise SystemExit(f"invalid env item (expected KEY=VALUE): {it}")
        k, v = it.split("=", 1)
        env[k] = v
    return env


def parse_args_list(s: Optional[str]) -> List[str]:
    if not s:
        return []
    try:
        return list(shlex.split(s))
    except ValueError as e:
        raise SystemExit(f"failed parsing --extra-args: {e}")


def cmd_init(args: argparse.Namespace) -> int:
    # Ensure directories and default config
    ensure_dir(app_support_dir())
    ensure_dir(logs_dir())
    cfg = load_config()
    # Backfill default paths if missing
    cfg.setdefault("llama_server_path", DEFAULT_LLAMA_SERVER_PATH)
    cfg.setdefault("log_dir", str(logs_dir()))
    save_config(cfg)
    print(f"Initialized config at {config_path()}")
    print(f"Logs directory at {logs_dir()}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    cfg = load_config()
    sub = args.subcommand
    if sub == "list":
        if args.json:
            print(to_json({
                "llama_server_path": cfg.get("llama_server_path"),
                "log_dir": cfg.get("log_dir"),
                "timeout_ms": cfg.get("timeout_ms"),
                "models": cfg.get("models", []),
            }))
        else:
            print(f"llama_server_path: {cfg.get('llama_server_path')}")
            print(f"log_dir: {cfg.get('log_dir')}")
            print("models:")
            for m in cfg.get("models", []):
                args_preview = " ".join(m.get("args", []) or [])
                print(f"- {m.get('name')} @ {m.get('host')}:{m.get('port')} -> {m.get('model_path')} {args_preview}")
        return 0

    if sub == "add":
        # Handle automatic port allocation
        if str(args.port).lower() == "auto":
            port = find_next_available_port(cfg)
            print(f"Auto-allocated port: {port}")
        else:
            port = int(args.port)

        # Handle automatic model path detection for downloaded models
        model_path = args.model_path
        if model_path.startswith("~/llms/") and model_path.endswith("/"):
            # Try to find the .gguf file in the directory
            expanded_path = Path(model_path).expanduser()
            if expanded_path.exists():
                gguf_files = list(expanded_path.glob("*.gguf"))
                if gguf_files:
                    # Use the largest .gguf file
                    model_path = str(max(gguf_files, key=lambda p: p.stat().st_size))
                    print(f"Auto-detected model file: {model_path}")

        spec = ModelSpec(
            name=args.name,
            model_path=model_path,
            host=args.host,
            port=port,
            mode=args.mode,
            deployment_type=getattr(args, 'deployment_type', 'native'),
            args=parse_args_list(args.extra_args),
            env=parse_env(args.env or []),
            autostart=args.autostart,
        )
        try:
            add_model(cfg, spec)
            save_config(cfg)
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        # Friendly warning if port looks busy now (non-fatal)
        try:
            if port_in_use(spec.host, spec.port):
                print(f"warning: port {spec.port} on {spec.host} appears in use right now", file=sys.stderr)
        except Exception:
            pass
        print(f"Added model '{spec.name}'")

        # Add to continue.dev configuration
        try:
            from .integrations import add_model_to_continue
            was_added = add_model_to_continue(spec.name, spec.port, host=spec.host)
            if was_added:
                print(f"✓ Added to continue.dev configuration")
            else:
                print(f"✓ Updated in continue.dev configuration")
        except Exception as e:
            print(f"warning: could not update continue.dev config: {e}", file=sys.stderr)
        return 0

    if sub == "update":
        updates: Dict[str, Any] = {}
        if args.model_path:
            updates["model_path"] = args.model_path
        if args.host:
            updates["host"] = args.host
        if args.port:
            updates["port"] = int(args.port)
        if args.mode:
            updates["mode"] = args.mode
        if args.extra_args is not None:
            updates["args"] = parse_args_list(args.extra_args)
        if args.env is not None:
            updates["env"] = parse_env(args.env)
        if args.autostart is not None:
            updates["autostart"] = bool(args.autostart)
        try:
            update_model(cfg, args.name, updates)
            save_config(cfg)
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        # Friendly warning if updated port looks busy
        try:
            m = [m for m in cfg.get("models", []) if m.get("name") == args.name][0]
            host = m.get("host", "127.0.0.1"); port = int(m.get("port"))
            if port_in_use(host, port):
                print(f"warning: port {port} on {host} appears in use right now", file=sys.stderr)
        except Exception:
            pass
        print(f"Updated model '{args.name}'")
        return 0

    if sub == "show":
        m = get_model(cfg, args.name)
        if not m:
            print(f"error: model '{args.name}' not found", file=sys.stderr)
            return 1

        # Build the full command that would be executed
        spec = ModelSpec(
            name=m["name"],
            model_path=m["model_path"],
            host=m.get("host", "127.0.0.1"),
            port=int(m["port"]),
            mode=m.get("mode", "basic"),
            args=list(m.get("args", []) or []),
            env=dict(m.get("env", {}) or {}),
            autostart=bool(m.get("autostart", False)),
            deployment_type=m.get("deployment_type", "native"),
        )

        from .process import build_argv
        llama_path = cfg.get("llama_server_path", "/opt/homebrew/bin/llama-server")
        argv = build_argv(llama_path, spec)

        if args.json:
            import json
            output = {
                "name": spec.name,
                "model_path": spec.model_path,
                "host": spec.host,
                "port": spec.port,
                "mode": spec.mode,
                "deployment_type": spec.deployment_type,
                "autostart": spec.autostart,
                "extra_args": spec.args,
                "env": spec.env,
                "full_command": argv,
                "mode_flags": {
                    "basic": "none",
                    "tools": "--jinja",
                    "performance": "--jinja --n-parallel 4 --batch-size 512 --ubatch-size 512",
                    "extended": "--jinja --flash-attn"
                }.get(spec.mode, "none")
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Model: {spec.name}")
            print(f"Path: {spec.model_path}")
            print(f"Endpoint: http://{spec.host}:{spec.port}")
            print(f"Mode: {spec.mode}")
            print(f"Deployment: {spec.deployment_type}")
            print(f"Autostart: {spec.autostart}")

            mode_flags = {
                "basic": "(no mode flags)",
                "tools": "--jinja",
                "performance": "--jinja --n-parallel 4 --batch-size 512 --ubatch-size 512",
                "extended": "--jinja --flash-attn"
            }
            print(f"\nMode adds: {mode_flags.get(spec.mode, 'none')}")

            if spec.args:
                print(f"Extra args: {' '.join(spec.args)}")
            else:
                print("Extra args: (none)")

            if spec.env:
                print("\nEnvironment variables:")
                for k, v in spec.env.items():
                    print(f"  {k}={v}")

            print(f"\nFull command that will be executed:")
            print(" ".join(argv))
        return 0

    if sub == "options":
        print("=== Available Modes ===\n")
        print("Modes are predefined parameter sets for common use cases:\n")
        print("  basic       - Minimal mode, no special features")
        print("  tools       - Enables function calling with --jinja")
        print("  performance - Optimized for speed:")
        print("                --jinja --n-parallel 4 --batch-size 512 --ubatch-size 512")
        print("  extended    - Advanced features with Flash Attention:")
        print("                --jinja --flash-attn")

        print("\n=== Common llama-server Parameters ===\n")
        print("Use these with --extra-args when configuring a model:")
        print()
        print("Context & Memory:")
        print("  --ctx-size N         - Context size (default: 512, common: 2048-32768)")
        print("  --n-gpu-layers N     - Number of layers to offload to GPU (default: 0)")
        print("  --threads N          - Number of CPU threads (default: system dependent)")
        print()
        print("Generation:")
        print("  --temp T             - Temperature for sampling (default: 0.8)")
        print("  --top-k N            - Top-k sampling (default: 40)")
        print("  --top-p P            - Top-p sampling (default: 0.95)")
        print("  --repeat-penalty P   - Penalize repeat tokens (default: 1.1)")
        print()
        print("Performance:")
        print("  --batch-size N       - Batch size for prompt eval (default: 512)")
        print("  --ubatch-size N      - Micro-batch size (default: batch-size)")
        print("  --n-parallel N       - Number of parallel sequences (default: 1)")
        print("  --cont-batching      - Enable continuous batching")
        print("  --flash-attn         - Enable Flash Attention (if supported)")
        print()
        print("Chat Templates:")
        print("  --jinja              - Use jinja2 for chat templates (enables tools)")
        print("  --chat-template STR  - Custom chat template string")
        print()
        print("Specialized:")
        print("  --embeddings         - Enable embeddings endpoint")
        print("  --reranking          - Enable reranking endpoint")
        print("  --no-mmap            - Disable memory mapping")
        print("  --numa isolate       - Pin to NUMA node (better performance)")

        print("\n=== Examples ===\n")
        print("# Configure high-context model with GPU acceleration:")
        print('llamacpp-manager config update phi3 --mode tools \\')
        print('  --extra-args "--ctx-size 8192 --n-gpu-layers 35"')
        print()
        print("# Configure for embeddings:")
        print('llamacpp-manager config update nomic --mode basic \\')
        print('  --extra-args "--embeddings --pooling mean --ctx-size 8192"')
        print()
        print("# High-performance configuration:")
        print('llamacpp-manager config update mistral --mode performance \\')
        print('  --extra-args "--n-gpu-layers -1 --cont-batching --numa isolate"')
        print()
        print("# Check what will be executed:")
        print("llamacpp-manager config show phi3")
        print("llamacpp-manager start phi3 --dry-run")

        return 0

    if sub == "remove":
        if not remove_model(cfg, args.name):
            print(f"error: model '{args.name}' not found", file=sys.stderr)
            return 2
        save_config(cfg)
        print(f"Removed model '{args.name}'")

        # Remove from continue.dev configuration
        try:
            from .integrations import remove_model_from_continue
            was_removed = remove_model_from_continue(args.name)
            if was_removed:
                print(f"✓ Removed from continue.dev configuration")
        except Exception as e:
            print(f"warning: could not update continue.dev config: {e}", file=sys.stderr)
        return 0

    if sub == "migrate":
        # Determine current directories from environment (already applied in main)
        cur_cfg_dir = app_support_dir()
        cur_log_dir = logs_dir()
        to_cfg = args.to_config_dir
        to_logs = args.to_log_dir
        move_flag = args.move
        force_flag = args.force
        if not to_cfg and not to_logs:
            print("error: specify at least --to-config-dir or --to-log-dir", file=sys.stderr)
            return 2
        try:
            if to_cfg:
                msg = migrate_directory(cur_cfg_dir, Path(to_cfg).expanduser().resolve(), move=move_flag, force=force_flag)
                print(msg)
            if to_logs:
                msg = migrate_directory(cur_log_dir, Path(to_logs).expanduser().resolve(), move=move_flag, force=force_flag)
                print(msg)
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print("Migration complete. Use --config-dir/--log-dir flags (or env LLAMACPP_MANAGER_CONFIG_DIR/LLAMACPP_MANAGER_LOG_DIR) to use the new locations.")
        return 0

    print("unknown config subcommand", file=sys.stderr)
    return 2


def cmd_infra(args: argparse.Namespace) -> int:
    """
    Handle infrastructure component management commands.

    Business Purpose: Provides unified control over infrastructure components
    (cloudflared tunnel and LLM controller) through wrapping existing management scripts.
    """
    cfg = load_config()
    sub = args.subcommand

    if sub == "list":
        components = list_infrastructure_components(cfg)
        if args.json:
            print(to_json(components))
        else:
            print("Infrastructure Components:")
            for name, comp in components.items():
                enabled = "enabled" if comp.get("enabled", True) else "disabled"
                comp_type = comp.get("type", "unknown")
                print(f"  {name} ({comp_type}) - {enabled}")
                if comp_type == "script_managed":
                    script = comp.get("management_script", "N/A")
                    print(f"    Management script: {script}")
                elif comp_type == "launchd_managed":
                    label = comp.get("launchd_label", "N/A")
                    installer = comp.get("installer_script", "N/A")
                    print(f"    Launchd label: {label}")
                    print(f"    Installer script: {installer}")
        return 0

    if sub == "start":
        target = args.target
        components = list_infrastructure_components(cfg)

        if target == "all":
            targets = [(name, comp) for name, comp in components.items() if comp.get("enabled", True)]
        else:
            comp = get_infrastructure_component(cfg, target)
            if not comp:
                print(f"error: infrastructure component '{target}' not found", file=sys.stderr)
                return 2
            targets = [(target, comp)]

        rc = 0
        for name, comp in targets:
            print(f"Starting {name}...")
            success, msg = infrastructure.start_infrastructure_component(comp)
            if success:
                print(f"  ✓ {name}: {msg}")
            else:
                print(f"  ✗ {name}: {msg}", file=sys.stderr)
                rc = max(rc, 2)
        return rc

    if sub == "stop":
        target = args.target
        components = list_infrastructure_components(cfg)

        if target == "all":
            targets = [(name, comp) for name, comp in components.items()]
        else:
            comp = get_infrastructure_component(cfg, target)
            if not comp:
                print(f"error: infrastructure component '{target}' not found", file=sys.stderr)
                return 2
            targets = [(target, comp)]

        rc = 0
        for name, comp in targets:
            print(f"Stopping {name}...")
            success, msg = infrastructure.stop_infrastructure_component(comp)
            if success:
                print(f"  ✓ {name}: {msg}")
            else:
                print(f"  ✗ {name}: {msg}", file=sys.stderr)
                rc = max(rc, 2)
        return rc

    if sub == "restart":
        target = args.target
        components = list_infrastructure_components(cfg)

        if target == "all":
            targets = [(name, comp) for name, comp in components.items() if comp.get("enabled", True)]
        else:
            comp = get_infrastructure_component(cfg, target)
            if not comp:
                print(f"error: infrastructure component '{target}' not found", file=sys.stderr)
                return 2
            targets = [(target, comp)]

        rc = 0
        for name, comp in targets:
            print(f"Restarting {name}...")
            # Stop first
            success, msg = infrastructure.stop_infrastructure_component(comp)
            if not success:
                print(f"  Warning during stop: {msg}", file=sys.stderr)

            # Brief delay
            import time
            time.sleep(2)

            # Start
            success, msg = infrastructure.start_infrastructure_component(comp)
            if success:
                print(f"  ✓ {name}: restarted - {msg}")
            else:
                print(f"  ✗ {name}: failed to restart - {msg}", file=sys.stderr)
                rc = max(rc, 2)
        return rc

    if sub == "status":
        components = list_infrastructure_components(cfg)
        statuses = []

        for name, comp in components.items():
            running, status_msg = infrastructure.get_infrastructure_status(comp)
            statuses.append({
                "name": name,
                "type": comp.get("type", "unknown"),
                "enabled": comp.get("enabled", True),
                "running": running,
                "status": status_msg
            })

        if args.json:
            print(to_json({"infrastructure": statuses}))
        else:
            print("Infrastructure Component Status:")
            for s in statuses:
                indicator = "✓" if s["running"] else "✗"
                enabled_str = "" if s["enabled"] else " (disabled)"
                print(f"  {indicator} {s['name']}{enabled_str}: {s['status']}")
        return 0

    if sub == "logs":
        component_name = args.component
        comp = get_infrastructure_component(cfg, component_name)
        if not comp:
            print(f"error: infrastructure component '{component_name}' not found", file=sys.stderr)
            return 2

        log_type = "err" if args.stderr else "out"
        log_path = infrastructure.get_log_path(comp, log_type)

        if not log_path:
            print(f"error: no log directory configured for {component_name}", file=sys.stderr)
            return 2

        if not Path(log_path).exists():
            print(f"warning: log file not found: {log_path}", file=sys.stderr)
            return 1

        if args.tail:
            # Stream logs
            try:
                import subprocess
                subprocess.run(["tail", "-f", log_path])
            except KeyboardInterrupt:
                print("\nStopped tailing logs")
            return 0
        else:
            # Show last 50 lines
            try:
                import subprocess
                result = subprocess.run(
                    ["tail", "-n", "50", log_path],
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                return 0
            except Exception as e:
                print(f"error: failed to read logs: {e}", file=sys.stderr)
                return 2

    print("unknown infra subcommand", file=sys.stderr)
    return 2


def cmd_docker(args: argparse.Namespace) -> int:
    """
    Handle Docker container commands for containerized llama.cpp models.

    Supports: start, stop, restart, status, logs
    """
    subcommand = getattr(args, "subcommand", None)
    if not subcommand:
        print("docker: missing subcommand", file=sys.stderr)
        return 2

    # Initialize Docker manager
    docker_mgr = DockerManager()

    try:
        if subcommand == "start":
            target = getattr(args, "target", "all")
            if target == "all":
                print("Starting all Docker containers...")
                success = docker_mgr.start_all()
                if success:
                    print("All Docker containers started successfully")
                else:
                    print("Some containers failed to start", file=sys.stderr)
                    return 1
            else:
                container_name = f"llm-{target}" if not target.startswith("llm-") else target

                # Get mode from args or model config
                cfg = load_config()
                mode_from_args = getattr(args, "mode", None)

                # Find the model in config to get saved mode
                model_name = target.replace("llm-", "") if target.startswith("llm-") else target
                models = cfg.get("models", [])
                saved_mode = "basic"  # Default if not found

                for model in models:
                    if model.get("name") == model_name and model.get("deployment_type") == "container":
                        saved_mode = model.get("mode", "basic")
                        break

                # Use arg mode if provided, otherwise use saved mode
                mode = mode_from_args if mode_from_args else saved_mode

                # Update config if mode was explicitly provided
                if mode_from_args and mode_from_args != saved_mode:
                    update_model(cfg, model_name, {"mode": mode_from_args})
                    save_config(cfg)

                print(f"Starting Docker container: {container_name} in {mode} mode...")
                success = docker_mgr.start(container_name, mode=mode)
                if success:
                    status = docker_mgr.status(container_name)
                    print(f"Container {container_name} started successfully")
                    print(f"  Port: {status.port}")
                    print(f"  Mode: {mode}")
                    print(f"  Status: {status.health_status}")
                else:
                    print(f"Failed to start container {container_name}", file=sys.stderr)
                    return 1

        elif subcommand == "stop":
            target = getattr(args, "target", "all")
            if target == "all":
                print("Stopping all Docker containers...")
                success = docker_mgr.stop_all()
                if success:
                    print("All Docker containers stopped successfully")
                else:
                    print("Some containers failed to stop", file=sys.stderr)
                    return 1
            else:
                container_name = f"llm-{target}" if not target.startswith("llm-") else target
                print(f"Stopping Docker container: {container_name}...")
                success = docker_mgr.stop(container_name)
                if success:
                    print(f"Container {container_name} stopped successfully")
                else:
                    print(f"Failed to stop container {container_name}", file=sys.stderr)
                    return 1

        elif subcommand == "restart":
            target = getattr(args, "target", None)
            if not target:
                print("docker restart: target model name required", file=sys.stderr)
                return 2
            container_name = f"llm-{target}" if not target.startswith("llm-") else target
            print(f"Restarting Docker container: {container_name}...")
            success = docker_mgr.restart(container_name)
            if success:
                status = docker_mgr.status(container_name)
                print(f"Container {container_name} restarted successfully")
                print(f"  Port: {status.port}")
                print(f"  Status: {status.health_status}")
            else:
                print(f"Failed to restart container {container_name}", file=sys.stderr)
                return 1

        elif subcommand == "status":
            target = getattr(args, "target", None)
            output_json = getattr(args, "json", False)

            if target is None:
                # Show all containers
                if output_json:
                    print(docker_mgr.to_json())
                else:
                    statuses = docker_mgr.status_all()
                    if not statuses:
                        print("No Docker containers configured")
                        return 0

                    print("Docker Container Status:")
                    print("-" * 80)
                    for st in statuses:
                        health_icon = "🟢" if st.health_status == "healthy" else \
                                     "🟠" if st.health_status == "starting" else "🔴"
                        print(f"{health_icon} {st.name}")
                        print(f"   Port: {st.port}")
                        print(f"   Status: {st.health_status}")
                        if st.latency_ms:
                            print(f"   Latency: {st.latency_ms}ms")
                        if st.pid:
                            print(f"   PID: {st.pid}")
            else:
                # Show specific container
                container_name = f"llm-{target}" if not target.startswith("llm-") else target
                st = docker_mgr.status(container_name)

                if output_json:
                    print(to_json({
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
                                 "🟠" if st.health_status == "starting" else "🔴"
                    print(f"{health_icon} {st.name}")
                    print(f"   Port: {st.port}")
                    print(f"   Running: {st.running}")
                    print(f"   Status: {st.health_status}")
                    if st.latency_ms:
                        print(f"   Latency: {st.latency_ms}ms")
                    if st.pid:
                        print(f"   PID: {st.pid}")

        elif subcommand == "logs":
            target = getattr(args, "target", None)
            if not target:
                print("docker logs: target model name required", file=sys.stderr)
                return 2
            tail = getattr(args, "tail", 50)
            container_name = f"llm-{target}" if not target.startswith("llm-") else target
            output = docker_mgr.logs(container_name, tail=tail)
            print(output)

        elif subcommand == "create":
            target = getattr(args, "target", None)
            if not target:
                print("docker create: target model name required", file=sys.stderr)
                return 2
            container_name = f"llm-{target}" if not target.startswith("llm-") else target

            # Get mode from args or model config
            mode_from_args = getattr(args, "mode", None)
            model_name = target.replace("llm-", "") if target.startswith("llm-") else target

            # Find model in config to get saved mode
            cfg = load_config()
            models = cfg.get("models", [])
            saved_mode = "basic"
            for model in models:
                if model.get("name") == model_name and model.get("deployment_type") == "container":
                    saved_mode = model.get("mode", "basic")
                    break

            # Use arg mode if provided, otherwise use saved mode
            mode = mode_from_args if mode_from_args else saved_mode
            model_path = getattr(args, "model_path", None)

            print(f"Creating Docker container: {container_name} in {mode} mode...")
            success = docker_mgr.create_container(container_name, mode=mode, model_path=model_path)
            if success:
                status = docker_mgr.status(container_name)
                print(f"Container {container_name} created successfully")
                print(f"  Port: {status.port}")
                print(f"  Mode: {mode}")
                print(f"  Status: {status.health_status}")
            else:
                print(f"Failed to create container {container_name}", file=sys.stderr)
                return 1

        else:
            print(f"unknown docker subcommand: {subcommand}", file=sys.stderr)
            return 2

        return 0

    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="llamacpp-manager",
        description="""Manage llama.cpp llama-server instances on macOS

Examples:
  # Quick Start
  llamacpp-manager init                                    # Initialize config
  llamacpp-manager config add mymodel ~/models/model.gguf --port 8081  # Add model
  llamacpp-manager start mymodel                          # Start model
  llamacpp-manager status                                 # Check status

  # Query running models
  llamacpp-manager query complete mymodel "Write a poem about AI"
  llamacpp-manager query chat mymodel --message "user:Hello there!"

  # Browse to http://127.0.0.1:8081 to use web interface
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--version", action="version", version=f"llamacpp-manager {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", default=False,
                   help="Show full tracebacks on errors")
    p.add_argument("--config-dir", help="Override configuration directory (e.g., ~/my-llama-config)")
    p.add_argument("--log-dir", help="Override logs directory (e.g., ~/my-llama-logs)")
    sub = p.add_subparsers(dest="command", required=True, help="Available commands")

    # init
    sp_init = sub.add_parser("init", help="🚀 Create default config and directories (run this first)")
    sp_init.set_defaults(func=cmd_init)

    # config group
    sp_cfg = sub.add_parser("config", help="⚙️  Manage model configuration")
    cfg_sub = sp_cfg.add_subparsers(dest="subcommand", required=True, help="Configuration commands")

    sp_cfg_list = cfg_sub.add_parser("list", help="📋 List configured models and settings")
    sp_cfg_list.add_argument("--json", action="store_true", help="Output as JSON")
    sp_cfg_list.set_defaults(func=cmd_config)

    sp_cfg_add = cfg_sub.add_parser("add",
        help="➕ Add a model (example: config add phi3 ~/models/phi3.gguf --port 8081)")
    sp_cfg_add.add_argument("name", help="Model name (used for start/stop commands)")
    sp_cfg_add.add_argument("model_path", help="Path to .gguf model file")
    sp_cfg_add.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    sp_cfg_add.add_argument("--port", required=True, help="Port number (e.g., 8081) or 'auto' for automatic allocation")
    sp_cfg_add.add_argument("--mode", choices=["basic", "tools", "performance", "extended"], default="basic",
                            help="Startup mode: basic (minimal), tools (--jinja), performance (optimized), extended (flash-attn)")
    sp_cfg_add.add_argument("--deployment-type", choices=["native", "container", "mlx"], default="native",
                            help="Deployment type: native (llama.cpp), container (Docker), mlx (Apple Silicon)")
    sp_cfg_add.add_argument("--extra-args", help="Additional llama-server args as quoted string")
    sp_cfg_add.add_argument("--env", nargs="*", help="Environment variables: KEY=VALUE KEY2=VALUE2")
    sp_cfg_add.add_argument("--autostart", action="store_true", help="Auto-start this model with 'ensure-running'")
    sp_cfg_add.set_defaults(func=cmd_config)

    sp_cfg_upd = cfg_sub.add_parser("update", help="Update an existing model entry")
    sp_cfg_upd.add_argument("name")
    sp_cfg_upd.add_argument("--model-path")
    sp_cfg_upd.add_argument("--host")
    sp_cfg_upd.add_argument("--port", type=int)
    sp_cfg_upd.add_argument("--mode", choices=["basic", "tools", "performance", "extended"],
                            help="Startup mode: basic (minimal), tools (--jinja), performance (optimized), extended (flash-attn)")
    sp_cfg_upd.add_argument("--extra-args", help="Replace extra args (single string)")
    sp_cfg_upd.add_argument("--env", nargs="*", help="Replace env vars: KEY=VALUE ... (omit to keep, pass empty to clear)")
    sp_cfg_upd.add_argument("--autostart", dest="autostart", action="store_true")
    sp_cfg_upd.add_argument("--no-autostart", dest="autostart", action="store_false")
    sp_cfg_upd.set_defaults(func=cmd_config)

    sp_cfg_show = cfg_sub.add_parser("show", help="🔍 Show detailed model configuration and parameters")
    sp_cfg_show.add_argument("name", help="Model name to show details for")
    sp_cfg_show.add_argument("--json", action="store_true", help="Output as JSON")
    sp_cfg_show.set_defaults(func=cmd_config)

    sp_cfg_options = cfg_sub.add_parser("options", help="📚 Show available modes and parameters")
    sp_cfg_options.set_defaults(func=cmd_config)

    sp_cfg_rm = cfg_sub.add_parser("remove", help="Remove a model entry")
    sp_cfg_rm.add_argument("name")
    sp_cfg_rm.set_defaults(func=cmd_config)

    sp_cfg_mig = cfg_sub.add_parser("migrate", help="Migrate config and/or logs to new locations")
    sp_cfg_mig.add_argument("--to-config-dir", help="Destination directory for config (Application Support)")
    sp_cfg_mig.add_argument("--to-log-dir", help="Destination directory for logs")
    sp_cfg_mig.add_argument("--move", action="store_true", help="Move instead of copy (removes source)")
    sp_cfg_mig.add_argument("--force", action="store_true", help="Backup and overwrite destination if it exists")
    sp_cfg_mig.set_defaults(func=cmd_config)

    # infra group - infrastructure management
    sp_infra = sub.add_parser("infra", help="🏗️  Manage infrastructure components (cloudflared, controller)")
    infra_sub = sp_infra.add_subparsers(dest="subcommand", required=True, help="Infrastructure commands")

    sp_infra_list = infra_sub.add_parser("list", help="📋 List configured infrastructure components")
    sp_infra_list.add_argument("--json", action="store_true", help="Output as JSON")
    sp_infra_list.set_defaults(func=cmd_infra)

    sp_infra_start = infra_sub.add_parser("start", help="▶️  Start infrastructure component(s)")
    sp_infra_start.add_argument("target", help="Component name (cloudflared, llm_controller) or 'all'")
    sp_infra_start.set_defaults(func=cmd_infra)

    sp_infra_stop = infra_sub.add_parser("stop", help="⏹️  Stop infrastructure component(s)")
    sp_infra_stop.add_argument("target", help="Component name or 'all'")
    sp_infra_stop.set_defaults(func=cmd_infra)

    sp_infra_restart = infra_sub.add_parser("restart", help="🔄 Restart infrastructure component(s)")
    sp_infra_restart.add_argument("target", help="Component name or 'all'")
    sp_infra_restart.set_defaults(func=cmd_infra)

    sp_infra_status = infra_sub.add_parser("status", help="📊 Show infrastructure component status")
    sp_infra_status.add_argument("--json", action="store_true", help="Output as JSON")
    sp_infra_status.set_defaults(func=cmd_infra)

    sp_infra_logs = infra_sub.add_parser("logs", help="📜 View logs for infrastructure component")
    sp_infra_logs.add_argument("component", help="Component name (cloudflared, llm_controller)")
    sp_infra_logs.add_argument("--tail", action="store_true", help="Follow log output (like tail -f)")
    sp_infra_logs.add_argument("--stderr", action="store_true", help="Show stderr instead of stdout")
    sp_infra_logs.set_defaults(func=cmd_infra)

    # docker group - Docker container management
    sp_docker = sub.add_parser("docker", help="🐳 Manage Docker containers running llama.cpp models")
    docker_sub = sp_docker.add_subparsers(dest="subcommand", required=True, help="Docker commands")

    sp_docker_start = docker_sub.add_parser("start", help="▶️  Start a Docker container")
    sp_docker_start.add_argument("target", nargs="?", default="all", help="Model name (e.g., 'phi3') or 'all' (default: all)")
    sp_docker_start.add_argument("--mode", choices=["basic", "tools", "performance", "extended"], help="Startup mode (uses saved mode if not specified)")
    sp_docker_start.set_defaults(func=cmd_docker)

    sp_docker_stop = docker_sub.add_parser("stop", help="⏹️  Stop a Docker container")
    sp_docker_stop.add_argument("target", nargs="?", default="all", help="Model name (e.g., 'phi3') or 'all' (default: all)")
    sp_docker_stop.set_defaults(func=cmd_docker)

    sp_docker_restart = docker_sub.add_parser("restart", help="🔄 Restart a Docker container")
    sp_docker_restart.add_argument("target", help="Model name (e.g., 'phi3')")
    sp_docker_restart.set_defaults(func=cmd_docker)

    sp_docker_status = docker_sub.add_parser("status", help="📊 Show Docker container status")
    sp_docker_status.add_argument("target", nargs="?", default=None, help="Model name (optional, default: show all)")
    sp_docker_status.add_argument("--json", action="store_true", help="Output as JSON")
    sp_docker_status.set_defaults(func=cmd_docker)

    sp_docker_logs = docker_sub.add_parser("logs", help="📜 View logs from Docker container")
    sp_docker_logs.add_argument("target", help="Model name (e.g., 'phi3')")
    sp_docker_logs.add_argument("--tail", type=int, default=50, help="Number of log lines to show (default: 50)")
    sp_docker_logs.set_defaults(func=cmd_docker)

    sp_docker_create = docker_sub.add_parser("create", help="🔧 Create a new Docker container")
    sp_docker_create.add_argument("target", help="Model name (e.g., 'phi3')")
    sp_docker_create.add_argument("--mode", choices=["basic", "tools", "performance", "extended"], help="Startup mode (uses saved mode if not specified)")
    sp_docker_create.add_argument("--model-path", help="Path to model file (optional, auto-detected from config)")
    sp_docker_create.set_defaults(func=cmd_docker)

    # start/stop/restart commands
    sp_start = sub.add_parser("start", help="▶️  Start model(s) - makes them available at http://localhost:PORT")
    sp_start.add_argument("target", help="Model name (e.g., 'phi3') or 'all' for all models")
    sp_start.add_argument("--dry-run", action="store_true", help="Show command that would run without executing")
    sp_start.add_argument("--launchd", action="store_true", help="Use macOS launchd for background service")
    sp_start.add_argument("--allow-remote", action="store_true", help="Allow external IP binds (security risk)")
    sp_start.set_defaults(func=cmd_start)

    sp_start_script = sub.add_parser("start-script", help="▶️  Start model using restart-llm-interactive.sh script")
    sp_start_script.add_argument("target", help="Model name")
    sp_start_script.add_argument(
        "--mode",
        choices=["basic", "tools", "performance", "extended"],
        default="basic",
        help="Mode to start model in"
    )
    sp_start_script.add_argument("--dry-run", action="store_true", help="Show command without executing")
    sp_start_script.set_defaults(func=cmd_start_script)

    sp_stop = sub.add_parser("stop", help="⏹️  Stop running model(s)")
    sp_stop.add_argument("target", help="Model name (e.g., 'phi3') or 'all' for all models")
    sp_stop.add_argument("--launchd", action="store_true", help="Stop launchd service instead of direct process")
    sp_stop.set_defaults(func=cmd_stop)

    sp_restart = sub.add_parser("restart", help="🔄 Restart model(s) (stop + start)")
    sp_restart.add_argument("target", help="Model name (e.g., 'phi3') or 'all' for all models")
    sp_restart.add_argument("--dry-run", action="store_true", help="Show commands without executing")
    sp_restart.add_argument("--launchd", action="store_true", help="Use launchd for restart")
    sp_restart.add_argument("--allow-remote", action="store_true", help="Allow external IP binds")
    sp_restart.set_defaults(func=cmd_restart)

    # launch (unified model manager with exclusive groups)
    sp_launch = sub.add_parser("launch", help="🚀 Launch model (auto-stops siblings in exclusive groups)")
    sp_launch.add_argument("model_name", help="Model name to launch")
    sp_launch.add_argument("--native", dest="deployment", action="store_const", const="native", help="Force native deployment")
    sp_launch.add_argument("--container", dest="deployment", action="store_const", const="container", help="Force container deployment")
    sp_launch.set_defaults(func=cmd_launch)

    # models group (download and manage model files)
    sp_models = sub.add_parser("models", help="📦 Download and manage model files")
    models_sub = sp_models.add_subparsers(dest="subcommand", required=True, help="Model management commands")

    sp_models_list = models_sub.add_parser("list", help="📋 List downloaded models")
    sp_models_list.add_argument("--available", action="store_true", help="Show available pre-configured models")
    sp_models_list.add_argument("--format", choices=["gguf", "mlx", "all"], default="all", help="Filter by model format (default: all)")
    sp_models_list.add_argument("--refresh", action="store_true", help="Force refresh catalog from HuggingFace API (bypasses 24-hour cache)")
    sp_models_list.add_argument("--json", action="store_true", help="Output in JSON format")
    sp_models_list.set_defaults(func=cmd_models)

    sp_models_download = models_sub.add_parser("download", help="⬇️  Download model from Hugging Face")
    sp_models_download.add_argument("model_name", help="Model name (e.g., qwen-coder-32b, qwen-coder-14b, deepseek-coder-lite)")
    sp_models_download.add_argument("--repo", help="Override Hugging Face repo ID")
    sp_models_download.add_argument("--filename", help="Override filename in repo")
    sp_models_download.set_defaults(func=cmd_models)

    sp_models_info = models_sub.add_parser("info", help="ℹ️  Show information about a model")
    sp_models_info.add_argument("model_name", help="Model name")
    sp_models_info.set_defaults(func=cmd_models)

    sp_models_check = models_sub.add_parser("check-updates", help="🔄 Check for model updates")
    sp_models_check.add_argument("--json", action="store_true", help="Output as JSON")
    sp_models_check.set_defaults(func=cmd_models)

    # status
    sp_status = sub.add_parser("status", help="📊 Show model status, health, and response times")
    sp_status.add_argument("--json", action="store_true", help="Output as JSON for scripting")
    sp_status.add_argument("--watch", action="store_true", help="Live refresh (press Ctrl+C to exit)")
    sp_status.add_argument("--interval", type=float, default=2.0, help="Refresh interval in seconds")
    sp_status.set_defaults(func=cmd_status)

    # launchd
    sp_ld = sub.add_parser("launchd", help="Manage launchd agents per model")
    ld_sub = sp_ld.add_subparsers(dest="subcommand", required=True)

    sp_ld_install = ld_sub.add_parser("install", help="Generate plist and bootstrap it")
    sp_ld_install.add_argument("target", help="Model name or 'all'")
    sp_ld_install.set_defaults(func=cmd_launchd)

    sp_ld_uninstall = ld_sub.add_parser("uninstall", help="Bootout and remove plist")
    sp_ld_uninstall.add_argument("target", help="Model name or 'all'")
    sp_ld_uninstall.set_defaults(func=cmd_launchd)

    # ensure-running (auto-start missing autostart models)
    sp_ens = sub.add_parser("ensure-running", help="Start models with autostart=true that are not reachable")
    sp_ens.add_argument("--mode", choices=["direct", "launchd"], default="direct", help="How to start missing models")
    sp_ens.set_defaults(func=cmd_ensure_running)

    # compare (multi-model comparison)
    sp_compare = sub.add_parser("compare", help="🔍 Query multiple models simultaneously for comparison")
    sp_compare.add_argument("question", help="Question to ask all models")
    sp_compare.add_argument("--models", required=True, help="Comma-separated model names (e.g., phi3,qwen-coder-7b,hermes-3)")
    sp_compare.add_argument("--save", action="store_true", help="Save to chat history database")
    sp_compare.add_argument("--title", help="Conversation title (if saving)")
    sp_compare.add_argument("--timeout", type=int, default=30, help="Timeout per model in seconds (default: 30)")
    sp_compare.add_argument("--format", choices=["table", "json", "markdown"], default="table", help="Output format")
    sp_compare.set_defaults(func=cmd_compare)

    # monitor commands (enhanced crash monitoring)
    sp_mon = sub.add_parser("monitor", help="🔍 Advanced model monitoring and crash detection")
    mon_sub = sp_mon.add_subparsers(dest="subcommand", required=True, help="Monitor commands")

    sp_mon_track = mon_sub.add_parser("track", help="📌 Track model for auto-restart monitoring")
    sp_mon_track.add_argument("model_name", help="Name of model to track")
    sp_mon_track.set_defaults(func=cmd_monitor)

    sp_mon_untrack = mon_sub.add_parser("untrack", help="📌 Stop tracking model")
    sp_mon_untrack.add_argument("model_name", help="Name of model to untrack")
    sp_mon_untrack.set_defaults(func=cmd_monitor)

    sp_mon_status = mon_sub.add_parser("status", help="📊 Show monitoring status and tracked models")
    sp_mon_status.add_argument("--detailed", action="store_true", help="Show detailed health for each tracked model")
    sp_mon_status.set_defaults(func=cmd_monitor)

    sp_mon_start = mon_sub.add_parser("start", help="🚀 Start monitoring daemon (background)")
    sp_mon_start.set_defaults(func=cmd_monitor)

    sp_mon_stop = mon_sub.add_parser("stop", help="⏹️ Stop monitoring daemon")
    sp_mon_stop.set_defaults(func=cmd_monitor)

    sp_mon_launchd = mon_sub.add_parser("launchd", help="🚀 Install/uninstall monitoring daemon as launchd agent")
    sp_mon_launchd.add_argument("action", choices=["install", "uninstall", "status"], help="Action to perform")
    sp_mon_launchd.set_defaults(func=cmd_monitor)

    # query commands
    sp_query = sub.add_parser("query", help="💬 Query running models for AI responses")
    query_sub = sp_query.add_subparsers(dest="subcommand", required=True, help="Query commands")

    sp_query_complete = query_sub.add_parser("complete",
        help="🤖 Get text completion (example: query complete phi3 'Write a story about')")
    sp_query_complete.add_argument("model_name", help="Name of running model (e.g., phi3)")
    sp_query_complete.add_argument("prompt", help="Text prompt to complete")
    sp_query_complete.add_argument("--max-tokens", type=int, default=512, help="Max response length (default: 512)")
    sp_query_complete.add_argument("--temperature", type=float, default=0.7, help="Creativity level 0.0-2.0 (default: 0.7)")
    sp_query_complete.add_argument("--stream", action="store_true", help="Stream response word-by-word")
    sp_query_complete.add_argument("--timeout", type=float, default=90.0, help="Request timeout seconds (default: 90)")
    sp_query_complete.set_defaults(func=cmd_query)

    sp_query_chat = query_sub.add_parser("chat",
        help="💬 Chat conversation (example: query chat phi3 -m 'user:Hello!' -m 'assistant:Hi there!' -m 'user:How are you?')")
    sp_query_chat.add_argument("model_name", help="Name of running model (e.g., phi3)")
    sp_query_chat.add_argument("--message", "-m", action="append",
        help="Add message: 'user:Hello' or 'system:You are helpful' or 'assistant:Hi!'")
    sp_query_chat.add_argument("--max-tokens", type=int, default=512, help="Max response length")
    sp_query_chat.add_argument("--temperature", type=float, default=0.7, help="Creativity level 0.0-2.0")
    sp_query_chat.add_argument("--stream", action="store_true", help="Stream response")
    sp_query_chat.add_argument("--timeout", type=float, default=90.0, help="Request timeout seconds (default: 90)")
    sp_query_chat.set_defaults(func=cmd_query)

    sp_query_list = query_sub.add_parser("list", help="📋 List currently running models")
    sp_query_list.set_defaults(func=cmd_query)

    # logging group
    sp_logging = sub.add_parser("logging", help="📝 Manage logging configuration")
    logging_sub = sp_logging.add_subparsers(dest="subcommand", required=True, help="Logging commands")

    sp_logging_status = logging_sub.add_parser("status", help="📊 Show current logging configuration")
    sp_logging_status.add_argument("--json", action="store_true", help="Output as JSON")
    sp_logging_status.set_defaults(func=cmd_logging)

    sp_logging_enable = logging_sub.add_parser("enable", help="✅ Enable logging globally")
    sp_logging_enable.set_defaults(func=cmd_logging)

    sp_logging_disable = logging_sub.add_parser("disable", help="🚫 Disable logging globally")
    sp_logging_disable.set_defaults(func=cmd_logging)

    sp_logging_timestamps = logging_sub.add_parser("timestamps", help="⏰ Toggle timestamps on/off")
    sp_logging_timestamps.add_argument("value", choices=["on", "off"], help="Enable or disable timestamps")
    sp_logging_timestamps.set_defaults(func=cmd_logging)

    sp_logging_set = logging_sub.add_parser("set", help="⚙️  Configure logging parameters")
    sp_logging_set.add_argument("--max-bytes", type=int, help="Max log file size in bytes")
    sp_logging_set.add_argument("--backups", type=int, help="Number of backup files to keep")
    sp_logging_set.set_defaults(func=cmd_logging)

    # logs command - view/filter logs
    sp_logs = sub.add_parser("logs", help="📜 View and filter model logs")
    sp_logs.add_argument("model_name", help="Model name to view logs for")
    sp_logs.add_argument("--filter", choices=["all", "info", "error"], default="all",
                         help="Filter by log level (all=both, info=stdout only, error=stderr only)")
    sp_logs.add_argument("--tail", type=int, metavar="N", help="Show last N lines (default: 50)")
    sp_logs.add_argument("--follow", "-f", action="store_true", help="Follow log output (like tail -f)")
    sp_logs.set_defaults(func=cmd_logs)

    return p


from typing import Optional


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Apply directory overrides early so all helpers resolve paths consistently
    if getattr(args, "config_dir", None):
        os.environ["LLAMACPP_MANAGER_CONFIG_DIR"] = args.config_dir
    if getattr(args, "log_dir", None):
        os.environ["LLAMACPP_MANAGER_LOG_DIR"] = args.log_dir
    return args.func(args)


def _select_models(cfg: Dict[str, Any], target: str) -> List[Dict[str, Any]]:
    models = cfg.get("models", [])
    if target == "all":
        return models
    sel = [m for m in models if m.get("name") == target]
    if not sel:
        raise SystemExit(f"model '{target}' not found")
    return sel


def cmd_start(args: argparse.Namespace) -> int:
    cfg = load_config()
    llama_path = cfg.get("llama_server_path")
    mlx_python_path = cfg.get("mlx_python_path", "python3")
    log_dir = Path(cfg.get("log_dir"))
    logging_config = cfg.get("logging", {})
    # Validate llama-server binary unless overridden for tests or using MLX
    if not os.environ.get("LLAMACPP_MANAGER_SKIP_BIN_CHECK"):
        lp = Path(llama_path).expanduser()
        if not (lp.exists() and os.access(str(lp), os.X_OK)):
            # Check if we're only starting MLX models
            selected = _select_models(cfg, args.target)
            all_mlx = all(m.get("deployment_type") == "mlx" for m in selected)
            if not all_mlx:
                print(f"error: llama-server not found or not executable at {lp}. Install via Homebrew: brew install llama.cpp", file=sys.stderr)
                return 2
    selected = _select_models(cfg, args.target)
    rc = 0
    for m in selected:
        spec = ModelSpec(
            name=m["name"],
            model_path=m["model_path"],
            host=m.get("host", "127.0.0.1"),
            port=int(m["port"]),
            args=list(m.get("args", []) or []),
            env=dict(m.get("env", {}) or {}),
            autostart=bool(m.get("autostart", False)),
            deployment_type=m.get("deployment_type", "native"),
            mode=m.get("mode", "basic"),
            group=m.get("group"),
            metadata=m.get("metadata"),
            logging=m.get("logging"),
        )
        # Warn/refuse remote binds unless explicitly allowed
        if spec.host not in ("127.0.0.1", "localhost", "::1") and not getattr(args, "allow_remote", False):
            print(f"error: refusing to bind non-local host '{spec.host}' without --allow-remote", file=sys.stderr)
            rc = 2
            continue

        # Route to appropriate runtime based on deployment type
        is_mlx = spec.deployment_type == "mlx"

        if is_mlx:
            # MLX models
            argv = build_mlx_argv(mlx_python_path, spec)
        else:
            # Native llama.cpp models
            argv = build_argv(llama_path, spec)

        if args.dry_run:
            print("DRY-RUN:", " ".join(shlex.quote(a) for a in argv))
            continue

        if getattr(args, "launchd", False):
            # TODO: MLX launchd support
            if is_mlx:
                print(f"error: launchd not yet supported for MLX models", file=sys.stderr)
                rc = 2
                continue
            data = render_plist(llama_path, spec, log_dir=log_dir)
            p = plist_path(spec.name)
            write_plist(p, data)
            r1 = launchctl_bootstrap(p)
            if r1.returncode != 0 and "Service already loaded" not in (r1.stderr or ""):
                print(f"error: launchctl bootstrap failed for {spec.name}: {r1.stderr}", file=sys.stderr)
                rc = 2
                continue
            _ = launchctl_kickstart(spec.name)
            print(f"launchd started {spec.name} port={spec.port}")
        else:
            # Prevent collision if port already in use by some service
            if port_in_use(spec.host, spec.port):
                print(f"error: port {spec.port} on {spec.host} is already in use; cannot start {spec.name}", file=sys.stderr)
                rc = 2
                continue

            if is_mlx:
                # Start MLX model
                pid = start_mlx_process(mlx_python_path, spec, log_dir, logging_config=logging_config)
                deployment_info = "mlx"
            else:
                # Start native llama.cpp model
                pid = start_process(llama_path, spec, log_dir, logging_config=logging_config)
                deployment_info = "native"

            write_pid(spec.name, pid)
            print(f"started {spec.name} pid={pid} port={spec.port} ({deployment_info})")
    return rc


def cmd_start_script(args: argparse.Namespace) -> int:
    """
    Start model using restart-llm-interactive.sh script.

    This delegates to the proven script with proper mode handling.
    """
    cfg = load_config()
    model_name = args.target
    mode = args.mode or "basic"

    # Find model in config to validate it exists
    models = cfg.get("models", [])
    model_found = None
    for m in models:
        if m.get("name") == model_name:
            model_found = m
            break

    if not model_found:
        print(f"error: model '{model_name}' not found in config", file=sys.stderr)
        return 1

    # Get script path from config, fallback to default
    script_path = cfg.get(
        "restart_script_path",
        "/Users/liborballaty/llms/restart-llm-interactive.sh"
    )

    if not os.path.exists(script_path):
        print(f"error: restart script not found at {script_path}", file=sys.stderr)
        print(f"Set 'restart_script_path' in config.yaml", file=sys.stderr)
        return 1

    # Call the script
    cmd = [script_path, model_name, mode]

    if args.dry_run:
        print("DRY-RUN:", " ".join(shlex.quote(c) for c in cmd))
        return 0

    print(f"Starting {model_name} in {mode} mode using restart script...")
    result = subprocess.run(cmd)

    return result.returncode


def cmd_stop(args: argparse.Namespace) -> int:
    cfg = load_config()
    selected = _select_models(cfg, args.target)
    rc = 0

    # Try using ModelManager first for models without PID files
    from .model_manager import ModelManager
    manager = ModelManager()

    for m in selected:
        name = m["name"]
        if getattr(args, "launchd", False):
            r = launchctl_bootout(name)
            if r.returncode != 0 and "No such process" not in (r.stderr or ""):
                print(f"warning: bootout returned {r.returncode} for {name}: {r.stderr}", file=sys.stderr)
            p = plist_path(name)
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
            print(f"launchd stopped {name}")
        else:
            # Try PID file approach first (legacy)
            try:
                pid = read_pid(name)

                # DEFENSIVE FIX: Kill any child processes first
                # This handles cases where PID file contains bash wrapper PID
                # and the actual llama-server is a child process
                import subprocess
                try:
                    children = subprocess.run(
                        ['pgrep', '-P', str(pid)],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if children.returncode == 0 and children.stdout.strip():
                        for child_pid_str in children.stdout.strip().split('\n'):
                            if child_pid_str.strip():
                                try:
                                    child_pid = int(child_pid_str.strip())
                                    os.kill(child_pid, signal.SIGTERM)
                                except (ValueError, ProcessLookupError, PermissionError):
                                    pass
                except subprocess.TimeoutExpired:
                    pass

                stop_process(pid)
                remove_pid(name)
                print(f"stopped {name} pid={pid}")
                continue
            except FileNotFoundError:
                # No PID file - try ModelManager instead
                pass
            except Exception as e:
                print(f"error stopping {name}: {e}", file=sys.stderr)
                rc = 2
                continue

            # Use ModelManager as fallback
            try:
                success, msg = manager.stop_model(name)
                if success:
                    print(f"stopped {name}")
                else:
                    # Last resort: try to kill by port
                    import subprocess
                    port = m.get("port")
                    if port:
                        try:
                            # Find process listening on this port
                            result = subprocess.run(
                                ["lsof", "-ti", f":{port}"],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if result.returncode == 0 and result.stdout.strip():
                                pid = int(result.stdout.strip().split()[0])
                                subprocess.run(["kill", str(pid)], timeout=2)
                                print(f"stopped {name} (killed PID {pid} on port {port})")
                            else:
                                print(f"warning: {msg}", file=sys.stderr)
                                rc = max(rc, 1)
                        except Exception as kill_err:
                            print(f"warning: {msg}", file=sys.stderr)
                            rc = max(rc, 1)
                    else:
                        print(f"warning: {msg}", file=sys.stderr)
                        rc = max(rc, 1)
            except Exception as e:
                print(f"error stopping {name}: {e}", file=sys.stderr)
                rc = 2
    return rc


def cmd_restart(args: argparse.Namespace) -> int:
    # Stop ignores missing pid files
    r1 = cmd_stop(argparse.Namespace(target=args.target, launchd=getattr(args, "launchd", False)))
    if args.dry_run:
        return 0
    r2 = cmd_start(argparse.Namespace(target=args.target, dry_run=False, launchd=getattr(args, "launchd", False), allow_remote=getattr(args, "allow_remote", False)))
    return max(r1, r2)


def cmd_launch(args: argparse.Namespace) -> int:
    """
    Launch a model using unified model manager.

    Automatically stops sibling models in exclusive groups.
    Supports both native and container deployment types.
    """
    from .model_manager import ModelManager, DeploymentType

    try:
        manager = ModelManager()
        model_name = args.model_name

        # Determine deployment type
        force_deployment = None
        if args.deployment:
            try:
                force_deployment = DeploymentType(args.deployment)
            except ValueError:
                print(f"error: invalid deployment type '{args.deployment}'", file=sys.stderr)
                return 2

        # Launch the model
        success, message = manager.start_model(model_name, force_deployment=force_deployment)

        if success:
            print(f"✓ Launched {model_name}: {message}")
            return 0
        else:
            print(f"✗ Failed to launch {model_name}: {message}", file=sys.stderr)
            return 2

    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


def cmd_models(args: argparse.Namespace) -> int:
    """
    Manage model downloads and information.

    Supports listing, downloading, and getting info about models.
    """
    from .models.downloader import (
        ModelDownloader,
        list_available_coding_models,
        get_coding_model_info,
        check_model_updates,
        fetch_live_catalog,
        CATALOG_CACHE_PATH
    )

    sub = args.subcommand

    if sub == "list":
        try:
            if args.available:
                # Fetch live catalog with optional force refresh
                force_refresh = getattr(args, "refresh", False)
                if force_refresh and CATALOG_CACHE_PATH.exists():
                    CATALOG_CACHE_PATH.unlink()

                models = fetch_live_catalog(force_refresh=force_refresh)

                # Extract catalog metadata
                catalog_source = models.pop('__catalog_source', 'static')
                catalog_fetched_at = models.pop('__catalog_fetched_at', None)

                # Get format filter (convert "all" to None for filtering)
                format_filter = None if args.format == "all" else args.format
                if format_filter:
                    models = {k: v for k, v in models.items() if v.get('format') == format_filter}

                if args.json:
                    # Output as JSON array with metadata
                    import json
                    models_list = []
                    for name, info in models.items():
                        model_dict = {
                            "name": name,
                            "repo_id": info["repo_id"],
                            "filename": info.get("filename"),
                            "description": info["description"],
                            "size_gb": info["size_gb"],
                            "ram_gb": info["ram_gb"],
                            "use_case": info["use_case"],
                            "format": info.get("format", "gguf"),
                            "version": info.get("version", "1.0")
                        }
                        # Add requires field for MLX models
                        if info.get("requires"):
                            model_dict["requires"] = info["requires"]
                        models_list.append(model_dict)

                    # Add metadata to output
                    output = {
                        "models": models_list,
                        "catalog_fetched_at": catalog_fetched_at,
                        "catalog_source": catalog_source
                    }
                    print(json.dumps(output, indent=2))
                else:
                    # Show available pre-configured models
                    # Separate GGUF and MLX models
                    gguf_models = {k: v for k, v in models.items() if v.get('format') == 'gguf'}
                    mlx_models = {k: v for k, v in models.items() if v.get('format') == 'mlx'}

                    if gguf_models:
                        print("=== GGUF Models (llama.cpp compatible) ===")
                        print()
                        for name, info in gguf_models.items():
                            print(f"  {name}")
                            print(f"    Description: {info['description']}")
                            print(f"    Size: ~{info['size_gb']} GB")
                            print(f"    RAM needed: ~{info['ram_gb']} GB")
                            print(f"    Use case: {info['use_case']}")
                            print()

                    if mlx_models:
                        print("=== MLX Models (Apple Silicon optimized) ===")
                        print()
                        for name, info in mlx_models.items():
                            print(f"  {name}")
                            print(f"    Description: {info['description']}")
                            print(f"    Size: ~{info['size_gb']} GB (4-bit quantized)")
                            print(f"    RAM needed: ~{info['ram_gb']} GB")
                            print(f"    Use case: {info['use_case']}")
                            print(f"    Requires: {info['requires']}")
                            print()

                    print(f"Download with: llamacpp-manager models download <name>")
                    print(f"Filter: --format gguf|mlx|all")
            else:
                # Show downloaded models
                downloader = ModelDownloader()
                models = downloader.list_downloaded_models()

                if not models:
                    print("No models downloaded yet")
                    print()
                    print("See available models with: llamacpp-manager models list --available")
                    return 0

                print("Downloaded Models:")
                print()
                for name, info in models.items():
                    print(f"  {name}")
                    print(f"    Path: {info['path']}")
                    print(f"    Size: {info['size_gb']:.2f} GB")
                    print()

            return 0
        except Exception as e:
            print(f"error ({type(e).__name__}): {e}", file=sys.stderr)
            if getattr(args, "verbose", False):
                traceback.print_exc(file=sys.stderr)
            return 2

    if sub == "download":
        try:
            model_name = args.model_name
            downloader = ModelDownloader()

            # Check if this is a pre-configured model
            model_info = get_coding_model_info(model_name)

            if model_info:
                # Use pre-configured settings
                repo_id = args.repo or model_info["repo_id"]
                filename = args.filename or model_info["filename"]

                print(f"Downloading: {model_info['description']}")
                print(f"Estimated size: ~{model_info['size_gb']} GB")
                print(f"RAM needed: ~{model_info['ram_gb']} GB")
                print()

            elif args.repo and args.filename:
                # Custom model with explicit repo and filename
                repo_id = args.repo
                filename = args.filename

            else:
                print(f"error: unknown model '{model_name}'", file=sys.stderr)
                print()
                print("Available models:")
                for name in list_available_coding_models().keys():
                    print(f"  - {name}")
                print()
                print("Or specify --repo and --filename for custom models")
                return 2

            # Download the model
            model_path = downloader.download_gguf(repo_id, filename, model_name)

            print()
            print(f"✓ Model downloaded successfully!")
            print(f"  Path: {model_path}")
            print()
            print("Add to config with:")
            print(f"  llamacpp-manager config add {model_name} {model_path} --port <PORT>")

            return 0

        except ImportError as e:
            print(f"error (ImportError): {e}", file=sys.stderr)
            if getattr(args, "verbose", False):
                traceback.print_exc(file=sys.stderr)
            print()
            print("Install huggingface_hub with:")
            print("  pip install huggingface_hub")
            return 2
        except Exception as e:
            print(f"error ({type(e).__name__}): {e}", file=sys.stderr)
            if getattr(args, "verbose", False):
                traceback.print_exc(file=sys.stderr)
            return 2

    if sub == "check-updates":
        try:
            from .models.downloader import check_model_updates

            downloader = ModelDownloader()
            updates = check_model_updates(downloader)

            if args.json:
                import json
                print(json.dumps(updates, indent=2))
            else:
                if not updates:
                    print("✅ All models are up to date!")
                else:
                    print("🔄 Updates available:")
                    print()
                    for model_name, info in updates.items():
                        print(f"  {model_name}:")
                        print(f"    Current version: {info['current']}")
                        print(f"    Available version: {info['available']}")
                        print(f"    Size: ~{info['size_gb']} GB")
                        print()
                    print("To update, download the new version:")
                    for model_name in updates:
                        print(f"  llamacpp-manager models download {model_name}")

            return 0
        except Exception as e:
            print(f"error ({type(e).__name__}): {e}", file=sys.stderr)
            if getattr(args, "verbose", False):
                traceback.print_exc(file=sys.stderr)
            return 2

    if sub == "info":
        try:
            model_name = args.model_name

            # Check downloaded models first
            downloader = ModelDownloader()
            downloaded = downloader.get_model_info(model_name)

            if downloaded:
                print(f"Downloaded Model: {model_name}")
                print(f"  Path: {downloaded['path']}")
                print(f"  Size: {downloaded['size_gb']:.2f} GB")
                print(f"  Filename: {downloaded['filename']}")
                print()

            # Check pre-configured info
            model_info = get_coding_model_info(model_name)
            if model_info:
                print(f"Pre-configured Model: {model_name}")
                print(f"  Description: {model_info['description']}")
                print(f"  Repository: {model_info['repo_id']}")
                print(f"  Filename: {model_info['filename']}")
                print(f"  Size: ~{model_info['size_gb']} GB")
                print(f"  RAM needed: ~{model_info['ram_gb']} GB")
                print(f"  Use case: {model_info['use_case']}")
                print()

                if not downloaded:
                    print("Download with:")
                    print(f"  llamacpp-manager models download {model_name}")

            if not downloaded and not model_info:
                print(f"Model '{model_name}' not found")
                print()
                print("See available models with:")
                print("  llamacpp-manager models list --available")
                return 1

            return 0

        except Exception as e:
            print(f"error ({type(e).__name__}): {e}", file=sys.stderr)
            if getattr(args, "verbose", False):
                traceback.print_exc(file=sys.stderr)
            return 2

    print("unknown models subcommand", file=sys.stderr)
    return 2


def _gather_status(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gather status for models and infrastructure components.

    Business Purpose: Provides unified status view across all managed
    components for operators to assess system health quickly.

    Returns:
        Dict with 'models' and 'infrastructure' keys containing status lists
    """
    timeout_ms = int(cfg.get("timeout_ms", 2000))
    procs = find_llama_processes()
    models_status = []
    infrastructure_status = []

    # Gather model status
    for m in cfg.get("models", []):
        name = m.get("name")
        host = m.get("host", "127.0.0.1")
        port = int(m.get("port"))
        pid = None
        process_source = "stopped"  # Track how process was started (stopped/direct/launchd)

        # Try to read PID from file first
        try:
            pid_from_file = read_pid(name)
            if process_alive(pid_from_file):
                # PID file is valid and process exists
                pid = pid_from_file
                process_source = "direct"
            else:
                # PID file exists but process is dead - fall through to discovery
                pid = None
                process_source = "stopped"
        except Exception:
            # No PID file - continue to discovery
            pass

        # If no valid PID from file, try process discovery
        if pid is None:
            model_path = str(m.get("model_path", ""))
            found = None
            for p in procs:
                argv = p.get("argv", [])
                if model_path and model_path in argv:
                    found = p
                    break
                if "--port" in argv:
                    try:
                        idx = argv.index("--port")
                        if str(port) == argv[idx + 1]:
                            found = p
                            break
                    except Exception:
                        pass
            if found:
                pid = found.get("pid")
                process_source = "direct"
        health = check_endpoint(host, port, timeout_ms=timeout_ms)

        # Get uptime if process is running
        from .infrastructure import get_process_uptime
        uptime = get_process_uptime(pid) if pid else None

        # Get startup mode from config (basic/tools/performance/extended)
        startup_mode = m.get("mode", "basic")

        # Infer format from model path
        model_path = str(m.get("model_path", "")).lower()
        if ".gguf" in model_path:
            format_type = "gguf"
        elif "mlx" in model_path:
            format_type = "mlx"
        elif "moe" in model_path:
            format_type = "moe"
        elif model_path and Path(model_path).expanduser().exists():
            # Probe filesystem for ambiguous paths (directory without "mlx" / "gguf" in name)
            p = Path(model_path).expanduser()
            if p.is_dir():
                files = list(p.glob("*"))
                if any(".gguf" in f.name.lower() for f in files):
                    format_type = "gguf"
                elif any(f.name.lower().endswith(".safetensors") or "mlx" in f.name.lower() for f in files):
                    format_type = "mlx"
                else:
                    format_type = "unknown"
            else:
                format_type = "unknown"
        else:
            format_type = "unknown"

        entry = {
            "name": name,
            "pid": pid,
            "host": host,
            "port": port,
            "up": bool(health.get("up")),
            "latency_ms": health.get("latency_ms"),
            "http_status": health.get("http_status"),
            "version": health.get("version"),
            "mode": startup_mode,  # Startup mode from config
            "format": format_type,  # Model format: gguf, mlx, moe
            "process_source": process_source,  # How process was started
            "log_path": str(Path(cfg.get("log_dir")).expanduser() / f"{name}.log"),
            "health_state": health.get("health_state", "down"),  # Enhanced health state
            "uptime": uptime,
        }
        models_status.append(entry)

    # Gather infrastructure status
    from .health import check_infrastructure_component_health
    components = list_infrastructure_components(cfg)
    for name, comp in components.items():
        running, status_msg = infrastructure.get_infrastructure_status(comp)
        health = check_infrastructure_component_health(comp)

        # Get uptime from PID in health details or parse from status message
        pid = health.get("details", {}).get("pid")
        if not pid:
            # Try to parse PID from status message like "running: PID 12345"
            import re
            pid_match = re.search(r'PID\s+(\d+)', status_msg)
            if pid_match:
                pid = int(pid_match.group(1))

        uptime = get_process_uptime(pid) if pid else None

        entry = {
            "name": name,
            "type": comp.get("type", "unknown"),
            "enabled": comp.get("enabled", True),
            "running": running,
            "healthy": health.get("healthy", False),
            "status": status_msg,
            "health_status": health.get("status", "unknown"),
            "latency_ms": health.get("latency_ms", 0),
            "details": health.get("details", {}),
            "uptime": uptime,
        }
        infrastructure_status.append(entry)

    # Add global logging configuration to status
    logging_config = cfg.get("logging", {
        "enabled": True,
        "max_bytes": 10 * 1024 * 1024,
        "backups": 5,
        "timestamps": True
    })

    return {
        "models": models_status,
        "infrastructure": infrastructure_status,
        "logging": logging_config
    }


def _print_table(status_data: Dict[str, Any]) -> None:
    """
    Print formatted status table for models and infrastructure.

    Business Purpose: Provides human-readable status output for terminal use.
    """
    # Print infrastructure status
    infra = status_data.get("infrastructure", [])
    if infra:
        print("\nInfrastructure Components:")
        print("-" * 80)
        for comp in infra:
            indicator = "✓" if comp.get("healthy", False) else "✗"
            enabled = "" if comp.get("enabled", True) else " (disabled)"
            latency = comp.get("latency_ms", 0)
            latency_str = f"{latency}ms" if latency > 0 else ""
            uptime = comp.get("uptime", "")
            uptime_str = f" (up {uptime})" if uptime else ""
            print(f"  {indicator} {comp['name']}{enabled:15s} {comp.get('status', 'unknown'):30s} {latency_str}{uptime_str}")
        print()

    # Print model status
    models = status_data.get("models", [])
    if models:
        print("Models:")
        print("-" * 80)
        headers = ["name", "mode", "pid", "host", "port", "up", "latency_ms", "uptime"]
        print(" ".join(f"{h:>12}" for h in headers))
        for r in models:
            vals = [r.get("name"), r.get("mode"), r.get("pid"), r.get("host"), r.get("port"), r.get("up"), r.get("latency_ms"), r.get("uptime", "")]
            print(" ".join(f"{str(v):>12}" for v in vals))


def cmd_status(args: argparse.Namespace) -> int:
    cfg = load_config()
    import time
    while True:
        status_data = _gather_status(cfg)
        if args.json:
            print(to_json(status_data))
        else:
            _print_table(status_data)
        if not args.watch:
            break
        try:
            time.sleep(max(0.2, float(args.interval)))
        except KeyboardInterrupt:
            break
    return 0


def cmd_launchd(args: argparse.Namespace) -> int:
    cfg = load_config()
    selected = _select_models(cfg, args.target)
    llama_path = cfg.get("llama_server_path")
    log_dir = Path(cfg.get("log_dir")).expanduser()
    if args.subcommand == "install":
        for m in selected:
            spec = ModelSpec(
                name=m["name"],
                model_path=m["model_path"],
                host=m.get("host", "127.0.0.1"),
                port=int(m["port"]),
                args=list(m.get("args", []) or []),
                env=dict(m.get("env", {}) or {}),
                autostart=bool(m.get("autostart", False)),
            )
            data = render_plist(llama_path, spec, log_dir=log_dir)
            p = plist_path(spec.name)
            write_plist(p, data)
            r1 = launchctl_bootstrap(p)
            if r1.returncode != 0 and "Service already loaded" not in (r1.stderr or ""):
                print(f"error: launchctl bootstrap failed for {spec.name}: {r1.stderr}", file=sys.stderr)
                return 2
            r2 = launchctl_kickstart(spec.name)
            if r2.returncode != 0:
                print(f"warning: kickstart may have failed for {spec.name}: {r2.stderr}", file=sys.stderr)
            print(f"installed launchd agent for {spec.name}: {p}")
        return 0

    if args.subcommand == "uninstall":
        for m in selected:
            name = m["name"]
            r = launchctl_bootout(name)
            if r.returncode != 0 and "No such process" not in (r.stderr or ""):
                print(f"warning: bootout returned {r.returncode} for {name}: {r.stderr}", file=sys.stderr)
            p = plist_path(name)
            try:
                if p.exists():
                    p.unlink()
            except Exception as e:
                print(f"warning: failed to remove plist {p}: {e}", file=sys.stderr)
            print(f"uninstalled launchd agent for {name}")
        return 0

    print("unknown launchd subcommand", file=sys.stderr)
    return 2


def cmd_ensure_running(args: argparse.Namespace) -> int:
    cfg = load_config()
    llama_path = cfg.get("llama_server_path")
    log_dir = Path(cfg.get("log_dir")).expanduser()
    timeout_ms = int(cfg.get("timeout_ms", 2000))
    started = 0
    for m in cfg.get("models", []):
        if not bool(m.get("autostart", False)):
            continue
        name = m.get("name")
        host = m.get("host", "127.0.0.1")
        port = int(m.get("port"))
        health = check_endpoint(host, port, timeout_ms=timeout_ms)
        if health.get("up"):
            continue
        spec = ModelSpec(
            name=name,
            model_path=m["model_path"],
            host=host,
            port=port,
            args=list(m.get("args", []) or []),
            env=dict(m.get("env", {}) or {}),
            autostart=True,
        )
        if args.mode == "launchd":
            data = render_plist(llama_path, spec, log_dir=log_dir)
            p = plist_path(spec.name)
            write_plist(p, data)
            r1 = launchctl_bootstrap(p)
            if r1.returncode != 0 and "Service already loaded" not in (r1.stderr or ""):
                print(f"error: launchctl bootstrap failed for {spec.name}: {r1.stderr}", file=sys.stderr)
                continue
            _ = launchctl_kickstart(spec.name)
            print(f"launchd started {spec.name} on {host}:{port}")
            started += 1
        else:
            pid = start_process(llama_path, spec, log_dir, logging_config=logging_config)
            write_pid(spec.name, pid)
            print(f"started {spec.name} pid={pid} port={spec.port}")
            started += 1
    print(f"ensure-running: started {started} model(s)")
    return 0


def cmd_monitor(args: argparse.Namespace) -> int:
    from .monitor import get_monitor
    monitor = get_monitor()
    sub = args.subcommand

    if sub == "track":
        try:
            # Verify model exists in config
            cfg = load_config()
            models = cfg.get("models", [])
            if not any(m.get("name") == args.model_name for m in models):
                print(f"error: model '{args.model_name}' not found in configuration", file=sys.stderr)
                print("Available models:", ", ".join(m.get("name", "") for m in models), file=sys.stderr)
                return 2

            monitor.track_model(args.model_name)
            print(f"Now tracking '{args.model_name}' for auto-restart")
            return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if sub == "untrack":
        try:
            monitor.untrack_model(args.model_name)
            print(f"Stopped tracking '{args.model_name}'")
            return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if sub == "status":
        try:
            status = monitor.get_monitoring_status()
            print(f"Monitor Status: {'RUNNING' if status['running'] else 'STOPPED'}")
            print(f"Check Interval: {status['check_interval']}s")
            print(f"State Directory: {status['state_dir']}")
            print()

            tracked = status["tracked_models"]
            if not tracked:
                print("No models currently tracked for auto-restart")
                return 0

            print("Tracked Models:")
            if not args.detailed:
                for model in tracked:
                    print(f"  - {model}")
            else:
                cfg = load_config()
                print(f"{'Model':<12} {'Health':<10} {'Process':<10} {'Port':<6} {'Latency':<8} {'Status'}")
                print("-" * 65)

                for model in tracked:
                    model_status = monitor.get_model_status(model, cfg)
                    health = model_status.get("health_state", "unknown")
                    process = model_status.get("process_state", "unknown")
                    port = model_status.get("port", "?")
                    latency = model_status.get("latency_ms", 0)
                    http_status = model_status.get("http_status", "")

                    status_str = f"HTTP {http_status}" if http_status else ""
                    print(f"{model:<12} {health:<10} {process:<10} {port:<6} {latency:<8} {status_str}")

            return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if sub == "start":
        try:
            monitor.start_monitoring()
            print("Model monitoring daemon started")
            print("Use 'llamacpp-manager monitor status' to check status")
            return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if sub == "stop":
        try:
            monitor.stop_monitoring()
            print("Model monitoring daemon stopped")
            return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if sub == "launchd":
        action = args.action
        label = "com.llamacpp.manager.monitor"
        plist_file = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"

        if action == "install":
            try:
                # Get the path to the llamacpp-manager executable
                import shutil
                exec_path = shutil.which("llamacpp-manager")
                if not exec_path:
                    print("error: llamacpp-manager executable not found in PATH", file=sys.stderr)
                    return 2

                # Create plist content
                plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exec_path}</string>
        <string>monitor</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>{logs_dir()}/monitor-daemon.log</string>
    <key>StandardErrorPath</key>
    <string>{logs_dir()}/monitor-daemon-error.log</string>
    <key>WorkingDirectory</key>
    <string>{Path.home()}</string>
</dict>
</plist>"""

                # Ensure LaunchAgents directory exists
                plist_file.parent.mkdir(parents=True, exist_ok=True)

                # Write plist file
                plist_file.write_text(plist_content)
                print(f"✓ Created launchd plist: {plist_file}")

                # Load the agent
                import subprocess
                result = subprocess.run(
                    ["launchctl", "load", str(plist_file)],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    print(f"✓ Monitoring daemon installed and loaded")
                    print(f"  Label: {label}")
                    print(f"  The daemon will start automatically on boot")
                    print(f"  Logs: {logs_dir()}/monitor-daemon.log")
                    return 0
                else:
                    print(f"warning: launchctl load returned {result.returncode}", file=sys.stderr)
                    if result.stderr:
                        print(f"  {result.stderr.strip()}", file=sys.stderr)
                    print(f"  Plist created at: {plist_file}")
                    return 1

            except Exception as e:
                print(f"error: {e}", file=sys.stderr)
                return 2

        elif action == "uninstall":
            try:
                if not plist_file.exists():
                    print(f"Monitoring daemon is not installed (plist not found: {plist_file})")
                    return 0

                # Unload the agent
                import subprocess
                result = subprocess.run(
                    ["launchctl", "unload", str(plist_file)],
                    capture_output=True,
                    text=True
                )

                # Remove plist file
                plist_file.unlink()
                print(f"✓ Monitoring daemon uninstalled")
                print(f"  Removed: {plist_file}")

                if result.returncode != 0 and result.stderr:
                    print(f"note: {result.stderr.strip()}")

                return 0

            except Exception as e:
                print(f"error: {e}", file=sys.stderr)
                return 2

        elif action == "status":
            try:
                import subprocess
                result = subprocess.run(
                    ["launchctl", "list", label],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    print(f"✓ Monitoring daemon is loaded")
                    print(f"  Label: {label}")
                    print(f"  Plist: {plist_file}")
                    if plist_file.exists():
                        print(f"  Status: installed and loaded")
                    else:
                        print(f"  Status: loaded but plist missing")

                    # Parse PID from output
                    for line in result.stdout.split('\n'):
                        parts = line.split()
                        if len(parts) >= 1 and parts[0].isdigit():
                            print(f"  PID: {parts[0]}")
                            break
                else:
                    print(f"✗ Monitoring daemon is not loaded")
                    if plist_file.exists():
                        print(f"  Plist exists but agent is not loaded: {plist_file}")
                        print(f"  Run 'llamacpp-manager monitor launchd install' to load it")
                    else:
                        print(f"  Not installed (plist not found: {plist_file})")

                return 0

            except Exception as e:
                print(f"error: {e}", file=sys.stderr)
                return 2

    print("unknown monitor subcommand", file=sys.stderr)
    return 2


def cmd_compare(args: argparse.Namespace) -> int:
    """
    Compare responses from multiple models simultaneously.

    Business Purpose: Allows users to evaluate different models' responses
    to the same question for quality comparison and model selection.
    """
    from .multi_query import compare_models_sync
    import json

    # Parse comma-separated model list
    model_names = [m.strip() for m in args.models.split(",")]

    if len(model_names) < 2:
        print("error: specify at least 2 models for comparison", file=sys.stderr)
        return 2

    try:
        # Query all models
        print(f"Querying {len(model_names)} models...\n")
        responses = compare_models_sync(
            question=args.question,
            models=model_names,
            save_to_history=args.save,
            timeout=args.timeout
        )

        if args.format == "json":
            # JSON output
            output = {
                "question": args.question,
                "models": len(model_names),
                "responses": [
                    {
                        "model": r.model_name,
                        "content": r.content,
                        "response_time_ms": r.response_time_ms,
                        "error": r.error
                    }
                    for r in responses
                ]
            }
            print(json.dumps(output, indent=2))

        elif args.format == "markdown":
            # Markdown output
            print(f"# Question\n{args.question}\n")
            for r in responses:
                print(f"## {r.model_name} ({r.response_time_ms}ms)")
                if r.error:
                    print(f"**Error:** {r.error}\n")
                else:
                    print(f"{r.content}\n")

        else:
            # Table output (default)
            print(f"Question: {args.question}\n")
            print("=" * 80)

            for r in responses:
                print(f"\n{r.model_name} ({r.response_time_ms}ms):")
                print("-" * 80)
                if r.error:
                    print(f"ERROR: {r.error}")
                else:
                    # Word wrap long responses
                    words = r.content.split()
                    line = ""
                    for word in words:
                        if len(line) + len(word) + 1 > 78:
                            print(line)
                            line = word
                        else:
                            line = line + " " + word if line else word
                    if line:
                        print(line)

            print("\n" + "=" * 80)

            # Show summary
            successful = [r for r in responses if not r.error]
            if successful:
                fastest = min(successful, key=lambda x: x.response_time_ms)
                print(f"\nFastest: {fastest.model_name} ({fastest.response_time_ms}ms)")
                print(f"Success rate: {len(successful)}/{len(responses)} models")

        if args.save:
            print(f"\n✓ Saved to chat history database")
            if args.title:
                print(f"  Title: {args.title}")

        return 0

    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


def cmd_query(args: argparse.Namespace) -> int:
    sub = args.subcommand

    if sub == "list":
        try:
            available = list_available_models()
            if available:
                print("Available models:")
                for model in available:
                    print(f"  - {model}")
            else:
                print("No models are currently available")
            return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if sub == "complete":
        try:
            if args.stream:
                for chunk in query_model_completion(
                    args.model_name,
                    args.prompt,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    stream=True,
                    timeout=args.timeout
                ):
                    content = chunk.get("content", "")
                    if content:
                        print(content, end="", flush=True)
                print()  # Final newline
            else:
                result = query_model_completion(
                    args.model_name,
                    args.prompt,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    stream=False,
                    timeout=args.timeout
                )
                print(result.get("content", ""))
            return 0
        except ModelQueryError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if sub == "chat":
        if not args.message:
            print("error: at least one --message is required", file=sys.stderr)
            return 2

        messages = []
        try:
            for msg in args.message:
                if ":" not in msg:
                    print(f"error: invalid message format '{msg}' (expected 'role:content')", file=sys.stderr)
                    return 2
                role, content = msg.split(":", 1)
                if role not in ["system", "user", "assistant"]:
                    print(f"error: invalid role '{role}' (must be system, user, or assistant)", file=sys.stderr)
                    return 2
                messages.append({"role": role, "content": content})

            if args.stream:
                for chunk in query_model_chat(
                    args.model_name,
                    messages,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    stream=True,
                    timeout=args.timeout
                ):
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        print(content, end="", flush=True)
                print()  # Final newline
            else:
                result = query_model_chat(
                    args.model_name,
                    messages,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    stream=False,
                    timeout=args.timeout
                )
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(content)
            return 0
        except ModelQueryError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    print("unknown query subcommand", file=sys.stderr)
    return 2


def cmd_logging(args: argparse.Namespace) -> int:
    """
    Manage logging configuration.

    Business Purpose: Allows users to control logging behavior globally
    and view current logging settings.
    """
    cfg = load_config()
    sub = args.subcommand

    if sub == "status":
        logging_config = cfg.get("logging", {})

        if args.json:
            print(to_json(logging_config))
            return 0

        enabled = logging_config.get("enabled", True)
        max_bytes = logging_config.get("max_bytes", 10 * 1024 * 1024)
        backups = logging_config.get("backups", 5)
        timestamps = logging_config.get("timestamps", True)

        print("Logging Configuration:")
        print(f"  Enabled: {enabled}")
        print(f"  Timestamps: {timestamps}")
        print(f"  Max file size: {max_bytes:,} bytes ({max_bytes / (1024*1024):.1f} MB)")
        print(f"  Backup files: {backups}")
        print(f"\nLog directory: {cfg.get('log_dir')}")
        return 0

    elif sub == "enable":
        if "logging" not in cfg:
            cfg["logging"] = {}
        cfg["logging"]["enabled"] = True
        save_config(cfg)
        print("✓ Logging enabled globally")
        print("  Note: Restart running models for changes to take effect")
        return 0

    elif sub == "disable":
        if "logging" not in cfg:
            cfg["logging"] = {}
        cfg["logging"]["enabled"] = False
        save_config(cfg)
        print("✓ Logging disabled globally")
        print("  Note: Restart running models for changes to take effect")
        return 0

    elif sub == "timestamps":
        if "logging" not in cfg:
            cfg["logging"] = {}
        cfg["logging"]["timestamps"] = (args.value == "on")
        save_config(cfg)
        print(f"✓ Timestamps {'enabled' if args.value == 'on' else 'disabled'}")
        print("  Note: Restart running models for changes to take effect")
        return 0

    elif sub == "set":
        if "logging" not in cfg:
            cfg["logging"] = {}

        changed = False
        if args.max_bytes is not None:
            cfg["logging"]["max_bytes"] = args.max_bytes
            changed = True
            print(f"✓ Max file size set to {args.max_bytes:,} bytes ({args.max_bytes / (1024*1024):.1f} MB)")

        if args.backups is not None:
            cfg["logging"]["backups"] = args.backups
            changed = True
            print(f"✓ Backup file count set to {args.backups}")

        if changed:
            save_config(cfg)
            print("  Note: Restart running models for changes to take effect")
            return 0
        else:
            print("error: no parameters specified", file=sys.stderr)
            return 2

    print("unknown logging subcommand", file=sys.stderr)
    return 2


def cmd_logs(args: argparse.Namespace) -> int:
    """
    View and filter model logs with color coding.

    Business Purpose: Allows operators to quickly view logs and identify
    errors without opening external log viewers.
    """
    cfg = load_config()
    model_name = args.model_name

    # Verify model exists
    model = None
    for m in cfg.get("models", []):
        if m.get("name") == model_name:
            model = m
            break

    if not model:
        print(f"error: model '{model_name}' not found", file=sys.stderr)
        return 2

    # Get log file path
    log_dir = Path(cfg.get("log_dir"))
    log_path = log_dir / f"{model_name}.log"

    if not log_path.exists():
        print(f"error: log file not found: {log_path}", file=sys.stderr)
        return 2

    # ANSI color codes
    RED = '\033[91m'      # Bright red for errors
    GREEN = '\033[92m'    # Green for info
    YELLOW = '\033[93m'   # Yellow for timestamps
    RESET = '\033[0m'     # Reset color

    def colorize_line(line: str) -> str:
        """Add color codes to log line based on level."""
        if '[ERROR]' in line:
            # Highlight ERROR tag in red
            line = line.replace('[ERROR]', f'{RED}[ERROR]{RESET}')
            # Make entire line slightly red-tinted
            return f'{RED}{line}{RESET}'
        elif '[INFO]' in line:
            # Highlight INFO tag in green
            line = line.replace('[INFO]', f'{GREEN}[INFO]{RESET}')
            return line
        return line

    def filter_line(line: str, filter_type: str) -> bool:
        """Return True if line should be shown based on filter."""
        if filter_type == "all":
            return True
        elif filter_type == "error":
            return '[ERROR]' in line
        elif filter_type == "info":
            return '[INFO]' in line
        return True

    # Follow mode (like tail -f)
    if args.follow:
        import time
        try:
            with log_path.open("r") as f:
                # Seek to end minus some lines
                tail_lines = args.tail or 10
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()

                # Estimate: go back ~100 bytes per line
                seek_pos = max(0, file_size - (tail_lines * 100))
                f.seek(seek_pos)
                f.readline()  # Skip partial line

                # Print initial tail
                for line in f:
                    line = line.rstrip('\n')
                    if filter_line(line, args.filter):
                        print(colorize_line(line))

                # Follow new lines
                while True:
                    line = f.readline()
                    if line:
                        line = line.rstrip('\n')
                        if filter_line(line, args.filter):
                            print(colorize_line(line))
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            return 0

    # Regular tail mode
    else:
        tail_count = args.tail or 50

        # Read last N lines
        with log_path.open("r") as f:
            lines = f.readlines()

        # Get last N lines
        lines_to_show = lines[-tail_count:] if len(lines) > tail_count else lines

        # Filter and colorize
        for line in lines_to_show:
            line = line.rstrip('\n')
            if filter_line(line, args.filter):
                print(colorize_line(line))

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
