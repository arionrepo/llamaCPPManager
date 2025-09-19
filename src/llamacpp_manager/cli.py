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
)
from .utils import app_support_dir, logs_dir, config_path, ensure_dir, to_json, migrate_directory, write_pid, read_pid, remove_pid, process_alive
from .process import start_process, stop_process, build_argv
from .health import check_endpoint
from .launchd import render_plist, plist_path, write_plist, launchctl_bootstrap, launchctl_kickstart, launchctl_bootout


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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="llamacpp-manager", description="Manage llama.cpp llama-server instances on macOS")
    p.add_argument("--version", action="version", version=f"llamacpp-manager {__version__}")
    p.add_argument("--config-dir", help="Override configuration directory (e.g., ~/my-llama-config)")
    p.add_argument("--log-dir", help="Override logs directory (e.g., ~/my-llama-logs)")
    sub = p.add_subparsers(dest="command", required=True)

    # init
    sp_init = sub.add_parser("init", help="Create default config and directories")
    sp_init.set_defaults(func=cmd_init)

    # config group
    sp_cfg = sub.add_parser("config", help="Manage model configuration")
    cfg_sub = sp_cfg.add_subparsers(dest="subcommand", required=True)

    sp_cfg_list = cfg_sub.add_parser("list", help="List config and models")
    sp_cfg_list.add_argument("--json", action="store_true", help="Output as JSON")
    sp_cfg_list.set_defaults(func=cmd_config)

    sp_cfg_add = cfg_sub.add_parser("add", help="Add a new model entry")
    sp_cfg_add.add_argument("name")
    sp_cfg_add.add_argument("model_path")
    sp_cfg_add.add_argument("--host", default="127.0.0.1")
    sp_cfg_add.add_argument("--port", type=int, required=True)
    sp_cfg_add.add_argument("--extra-args", help="Additional llama-server args as a single string")
    sp_cfg_add.add_argument("--env", nargs="*", help="Environment variables KEY=VALUE ...")
    sp_cfg_add.add_argument("--autostart", action="store_true", help="Mark model for autostart (used by launchd mode)")
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

    # start/stop/restart commands
    sp_start = sub.add_parser("start", help="Start a model or all models")
    sp_start.add_argument("target", help="Model name or 'all'")
    sp_start.add_argument("--dry-run", action="store_true", help="Print the command without executing")
    sp_start.set_defaults(func=cmd_start)

    sp_stop = sub.add_parser("stop", help="Stop a model or all models (via pid files)")
    sp_stop.add_argument("target", help="Model name or 'all'")
    sp_stop.set_defaults(func=cmd_stop)

    sp_restart = sub.add_parser("restart", help="Restart a model or all models")
    sp_restart.add_argument("target", help="Model name or 'all'")
    sp_restart.add_argument("--dry-run", action="store_true")
    sp_restart.set_defaults(func=cmd_restart)

    # status
    sp_status = sub.add_parser("status", help="Show model status and health")
    sp_status.add_argument("--json", action="store_true", help="Output JSON array")
    sp_status.add_argument("--watch", action="store_true", help="Refresh repeatedly")
    sp_status.add_argument("--interval", type=float, default=2.0, help="Watch refresh interval seconds")
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
        )
        argv = build_argv(llama_path, spec)
        if args.dry_run:
            print("DRY-RUN:", " ".join(shlex.quote(a) for a in argv))
            continue
        pid = start_process(llama_path, spec, log_dir)
        write_pid(spec.name, pid)
        print(f"started {spec.name} pid={pid} port={spec.port}")
    return rc


def cmd_stop(args: argparse.Namespace) -> int:
    cfg = load_config()
    selected = _select_models(cfg, args.target)
    rc = 0
    for m in selected:
        name = m["name"]
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
    r1 = cmd_stop(argparse.Namespace(target=args.target))
    if args.dry_run:
        return 0
    r2 = cmd_start(argparse.Namespace(target=args.target, dry_run=False))
    return max(r1, r2)


def _gather_status(cfg: Dict[str, Any]) -> list:
    timeout_ms = int(cfg.get("timeout_ms", 2000))
    out = []
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
            mode = "stopped"
        health = check_endpoint(host, port, timeout_ms=timeout_ms)
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
        }
        out.append(entry)
    return out


def _print_table(rows: list) -> None:
    headers = ["name", "mode", "pid", "host", "port", "up", "latency_ms"]
    print(" ".join(f"{h:>12}" for h in headers))
    for r in rows:
        vals = [r.get("name"), r.get("mode"), r.get("pid"), r.get("host"), r.get("port"), r.get("up"), r.get("latency_ms")]
        print(" ".join(f"{str(v):>12}" for v in vals))


def cmd_status(args: argparse.Namespace) -> int:
    cfg = load_config()
    import time
    while True:
        rows = _gather_status(cfg)
        if args.json:
            print(to_json(rows))
        else:
            _print_table(rows)
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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
