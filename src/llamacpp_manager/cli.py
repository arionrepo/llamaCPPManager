import argparse
import shlex
import sys
from typing import Any, Dict, List

from . import __version__
from .config import (
    DEFAULT_LLAMA_SERVER_PATH,
    ModelSpec,
    add_model,
    app_support_dir,  # type: ignore[attr-defined]
    load_config,
    logs_dir,  # type: ignore[attr-defined]
    remove_model,
    save_config,
    update_model,
)
from .utils import config_path, ensure_dir, to_json


def parse_env(items: List[str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for it in items:
        if "=" not in it:
            raise SystemExit(f"invalid env item (expected KEY=VALUE): {it}")
        k, v = it.split("=", 1)
        env[k] = v
    return env


def parse_args_list(s: str | None) -> List[str]:
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

    print("unknown config subcommand", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="llamacpp-manager", description="Manage llama.cpp llama-server instances on macOS")
    p.add_argument("--version", action="version", version=f"llamacpp-manager {__version__}")
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

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

