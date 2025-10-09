import argparse
import os
import shlex
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

from . import __version__
from .config import (
    DEFAULT_LLAMA_SERVER_PATH,
    ModelSpec,
    add_model,
    load_config,
    remove_model,
    save_config,
    update_model,
    list_infrastructure_components,
    get_infrastructure_component,
)
from .utils import app_support_dir, logs_dir, config_path, ensure_dir, to_json, migrate_directory, write_pid, read_pid, remove_pid, process_alive, port_in_use
from .process import start_process, stop_process, build_argv
from .health import check_endpoint
from .launchd import render_plist, plist_path, write_plist, launchctl_bootstrap, launchctl_kickstart, launchctl_bootout
from .discovery import find_llama_processes
from .query import query_model_completion, query_model_chat, list_available_models, ModelQueryError
from . import infrastructure


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
        spec = ModelSpec(
            name=args.name,
            model_path=args.model_path,
            host=args.host,
            port=int(args.port),
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
        return 0

    if sub == "update":
        updates: Dict[str, Any] = {}
        if args.model_path:
            updates["model_path"] = args.model_path
        if args.host:
            updates["host"] = args.host
        if args.port:
            updates["port"] = int(args.port)
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

    if sub == "remove":
        if not remove_model(cfg, args.name):
            print(f"error: model '{args.name}' not found", file=sys.stderr)
            return 2
        save_config(cfg)
        print(f"Removed model '{args.name}'")
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
    sp_cfg_add.add_argument("--port", type=int, required=True, help="Port number (required, e.g., 8081)")
    sp_cfg_add.add_argument("--extra-args", help="Additional llama-server args as quoted string")
    sp_cfg_add.add_argument("--env", nargs="*", help="Environment variables: KEY=VALUE KEY2=VALUE2")
    sp_cfg_add.add_argument("--autostart", action="store_true", help="Auto-start this model with 'ensure-running'")
    sp_cfg_add.set_defaults(func=cmd_config)

    sp_cfg_upd = cfg_sub.add_parser("update", help="Update an existing model entry")
    sp_cfg_upd.add_argument("name")
    sp_cfg_upd.add_argument("--model-path")
    sp_cfg_upd.add_argument("--host")
    sp_cfg_upd.add_argument("--port", type=int)
    sp_cfg_upd.add_argument("--extra-args", help="Replace extra args (single string)")
    sp_cfg_upd.add_argument("--env", nargs="*", help="Replace env vars: KEY=VALUE ... (omit to keep, pass empty to clear)")
    sp_cfg_upd.add_argument("--autostart", dest="autostart", action="store_true")
    sp_cfg_upd.add_argument("--no-autostart", dest="autostart", action="store_false")
    sp_cfg_upd.set_defaults(func=cmd_config)

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

    # start/stop/restart commands
    sp_start = sub.add_parser("start", help="▶️  Start model(s) - makes them available at http://localhost:PORT")
    sp_start.add_argument("target", help="Model name (e.g., 'phi3') or 'all' for all models")
    sp_start.add_argument("--dry-run", action="store_true", help="Show command that would run without executing")
    sp_start.add_argument("--launchd", action="store_true", help="Use macOS launchd for background service")
    sp_start.add_argument("--allow-remote", action="store_true", help="Allow external IP binds (security risk)")
    sp_start.set_defaults(func=cmd_start)

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
    sp_models_list.set_defaults(func=cmd_models)

    sp_models_download = models_sub.add_parser("download", help="⬇️  Download model from Hugging Face")
    sp_models_download.add_argument("model_name", help="Model name (e.g., qwen-coder-32b, qwen-coder-14b, deepseek-coder-lite)")
    sp_models_download.add_argument("--repo", help="Override Hugging Face repo ID")
    sp_models_download.add_argument("--filename", help="Override filename in repo")
    sp_models_download.set_defaults(func=cmd_models)

    sp_models_info = models_sub.add_parser("info", help="ℹ️  Show information about a model")
    sp_models_info.add_argument("model_name", help="Model name")
    sp_models_info.set_defaults(func=cmd_models)

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
    sp_query_complete.add_argument("--timeout", type=float, default=30.0, help="Request timeout seconds")
    sp_query_complete.set_defaults(func=cmd_query)

    sp_query_chat = query_sub.add_parser("chat",
        help="💬 Chat conversation (example: query chat phi3 -m 'user:Hello!' -m 'assistant:Hi there!' -m 'user:How are you?')")
    sp_query_chat.add_argument("model_name", help="Name of running model (e.g., phi3)")
    sp_query_chat.add_argument("--message", "-m", action="append",
        help="Add message: 'user:Hello' or 'system:You are helpful' or 'assistant:Hi!'")
    sp_query_chat.add_argument("--max-tokens", type=int, default=512, help="Max response length")
    sp_query_chat.add_argument("--temperature", type=float, default=0.7, help="Creativity level 0.0-2.0")
    sp_query_chat.add_argument("--stream", action="store_true", help="Stream response")
    sp_query_chat.add_argument("--timeout", type=float, default=30.0, help="Request timeout seconds")
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
    log_dir = Path(cfg.get("log_dir"))
    logging_config = cfg.get("logging", {})
    # Validate llama-server binary unless overridden for tests
    if not os.environ.get("LLAMACPP_MANAGER_SKIP_BIN_CHECK"):
        lp = Path(llama_path).expanduser()
        if not (lp.exists() and os.access(str(lp), os.X_OK)):
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
            group=m.get("group"),
            metadata=m.get("metadata"),
            logging=m.get("logging"),
        )
        # Warn/refuse remote binds unless explicitly allowed
        if spec.host not in ("127.0.0.1", "localhost", "::1") and not getattr(args, "allow_remote", False):
            print(f"error: refusing to bind non-local host '{spec.host}' without --allow-remote", file=sys.stderr)
            rc = 2
            continue
        argv = build_argv(llama_path, spec)
        if args.dry_run:
            print("DRY-RUN:", " ".join(shlex.quote(a) for a in argv))
            continue
        if getattr(args, "launchd", False):
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
            pid = start_process(llama_path, spec, log_dir, logging_config=logging_config)
            write_pid(spec.name, pid)
            print(f"started {spec.name} pid={pid} port={spec.port}")
    return rc


def cmd_stop(args: argparse.Namespace) -> int:
    cfg = load_config()
    selected = _select_models(cfg, args.target)
    rc = 0
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
            try:
                pid = read_pid(name)
            except FileNotFoundError:
                print(f"warning: no pid file for {name}", file=sys.stderr)
                rc = max(rc, 1)
                continue
            try:
                stop_process(pid)
                remove_pid(name)
                print(f"stopped {name} pid={pid}")
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
        get_coding_model_info
    )

    sub = args.subcommand

    if sub == "list":
        try:
            if args.available:
                # Show available pre-configured models
                print("Available Coding Models:")
                print()
                models = list_available_coding_models()
                for name, info in models.items():
                    print(f"  {name}")
                    print(f"    Description: {info['description']}")
                    print(f"    Size: ~{info['size_gb']} GB")
                    print(f"    RAM needed: ~{info['ram_gb']} GB")
                    print(f"    Use case: {info['use_case']}")
                    print()
                print(f"Download with: llamacpp-manager models download <name>")
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
            print(f"error: {e}", file=sys.stderr)
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
            print(f"error: {e}", file=sys.stderr)
            print()
            print("Install huggingface_hub with:")
            print("  pip install huggingface_hub")
            return 2
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
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
            print(f"error: {e}", file=sys.stderr)
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
        mode = "stopped"
        try:
            pid = read_pid(name)
            mode = "direct" if process_alive(pid) else "stopped"
        except Exception:
            # try to match discovered processes by model_path or --port
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
                mode = "direct"
        health = check_endpoint(host, port, timeout_ms=timeout_ms)

        # Get uptime if process is running
        from .infrastructure import get_process_uptime
        uptime = get_process_uptime(pid) if pid else None

        entry = {
            "name": name,
            "pid": pid,
            "host": host,
            "port": port,
            "up": bool(health.get("up")),
            "latency_ms": health.get("latency_ms"),
            "http_status": health.get("http_status"),
            "version": health.get("version"),
            "mode": mode,
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
