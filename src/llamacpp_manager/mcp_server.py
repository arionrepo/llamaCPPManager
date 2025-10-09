#!/usr/bin/env python3
"""
MCP Server for llamaCPPManager

Exposes llamaCPPManager functionality as MCP tools that can be used by MCP clients.
"""

import asyncio
import sys
import logging
from typing import Any, Dict, List, Optional

from mcp import server
from mcp.server import NotificationOptions
from mcp.types import TextContent, Tool
from pydantic import BaseModel

from .config import load_config, ModelSpec, add_model, remove_model, save_config
from .process import start_process, stop_process
from .health import check_endpoint
from .query import (
    query_model_completion,
    query_model_chat,
    list_available_models,
    check_model_available,
    ModelQueryError
)
from .utils import logs_dir, write_pid, read_pid, remove_pid, process_alive
from .launchd import render_plist, plist_path, write_plist, launchctl_bootstrap, launchctl_bootout
from pathlib import Path


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Tool input schemas
class ListModelsInput(BaseModel):
    pass


class StartModelInput(BaseModel):
    model_name: str
    mode: Optional[str] = "direct"  # "direct" or "launchd"


class StopModelInput(BaseModel):
    model_name: str
    mode: Optional[str] = "direct"  # "direct" or "launchd"


class ModelStatusInput(BaseModel):
    model_name: Optional[str] = None  # If None, show all models


class QueryCompletionInput(BaseModel):
    model_name: str
    prompt: str
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7


class QueryChatInput(BaseModel):
    model_name: str
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7


class AddModelInput(BaseModel):
    name: str
    model_path: str
    host: Optional[str] = "127.0.0.1"
    port: int
    extra_args: Optional[List[str]] = None
    autostart: Optional[bool] = False


class RemoveModelInput(BaseModel):
    name: str


# Create the MCP server instance
app = server.Server("llamacpp-manager")


@app.list_tools()
async def list_tools():
    """List available MCP tools"""
    return [
        Tool(
            name="list_models",
            description="List all configured models in llamaCPPManager",
            inputSchema=ListModelsInput.model_json_schema()
        ),
        Tool(
            name="list_available_models",
            description="List models that are currently running and available for queries",
            inputSchema=ListModelsInput.model_json_schema()
        ),
        Tool(
            name="start_model",
            description="Start a llama.cpp model server",
            inputSchema=StartModelInput.model_json_schema()
        ),
        Tool(
            name="stop_model",
            description="Stop a running llama.cpp model server",
            inputSchema=StopModelInput.model_json_schema()
        ),
        Tool(
            name="model_status",
            description="Get status information for models (running, health, etc)",
            inputSchema=ModelStatusInput.model_json_schema()
        ),
        Tool(
            name="query_completion",
            description="Query a model for text completion",
            inputSchema=QueryCompletionInput.model_json_schema()
        ),
        Tool(
            name="query_chat",
            description="Query a model using chat/conversation format",
            inputSchema=QueryChatInput.model_json_schema()
        ),
        Tool(
            name="add_model",
            description="Add a new model configuration",
            inputSchema=AddModelInput.model_json_schema()
        ),
        Tool(
            name="remove_model",
            description="Remove a model configuration",
            inputSchema=RemoveModelInput.model_json_schema()
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "list_models":
            return await handle_list_models()
        elif name == "list_available_models":
            return await handle_list_available_models()
        elif name == "start_model":
            return await handle_start_model(StartModelInput(**arguments))
        elif name == "stop_model":
            return await handle_stop_model(StopModelInput(**arguments))
        elif name == "model_status":
            return await handle_model_status(ModelStatusInput(**arguments))
        elif name == "query_completion":
            return await handle_query_completion(QueryCompletionInput(**arguments))
        elif name == "query_chat":
            return await handle_query_chat(QueryChatInput(**arguments))
        elif name == "add_model":
            return await handle_add_model(AddModelInput(**arguments))
        elif name == "remove_model":
            return await handle_remove_model(RemoveModelInput(**arguments))
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def handle_list_models() -> List[TextContent]:
    """List all configured models"""
    try:
        cfg = load_config()
        models = cfg.get("models", [])

        if not models:
            return [TextContent(
                type="text",
                text="No models configured"
            )]

        result = "Configured models:\n"
        for model in models:
            name = model.get("name")
            host = model.get("host", "127.0.0.1")
            port = model.get("port")
            model_path = model.get("model_path")
            autostart = model.get("autostart", False)
            result += f"- {name} @ {host}:{port} -> {model_path} (autostart: {autostart})\n"

        return [TextContent(type="text", text=result.strip())]

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise


async def handle_list_available_models() -> List[TextContent]:
    """List models that are currently available"""
    try:
        available = list_available_models()

        if not available:
            return [TextContent(
                type="text",
                text="No models are currently available"
            )]

        result = "Available models:\n" + "\n".join(f"- {model}" for model in available)
        return [TextContent(type="text", text=result)]

    except Exception as e:
        logger.error(f"Failed to list available models: {e}")
        raise


async def handle_start_model(input_data: StartModelInput) -> List[TextContent]:
    """Start a model server"""
    try:
        cfg = load_config()
        models = cfg.get("models", [])
        model_info = next((m for m in models if m.get("name") == input_data.model_name), None)

        if not model_info:
            return [TextContent(
                type="text",
                text=f"Model '{input_data.model_name}' not found in configuration"
            )]

        spec = ModelSpec(
            name=model_info["name"],
            model_path=model_info["model_path"],
            host=model_info.get("host", "127.0.0.1"),
            port=int(model_info["port"]),
            args=list(model_info.get("args", []) or []),
            env=dict(model_info.get("env", {}) or {}),
            autostart=bool(model_info.get("autostart", False)),
            logging=model_info.get("logging"),
        )

        llama_path = cfg.get("llama_server_path")
        log_dir = Path(cfg.get("log_dir"))
        logging_config = cfg.get("logging", {})

        if input_data.mode == "launchd":
            # Start via launchd
            data = render_plist(llama_path, spec, log_dir=log_dir)
            p = plist_path(spec.name)
            write_plist(p, data)
            r1 = launchctl_bootstrap(p)
            if r1.returncode != 0 and "Service already loaded" not in (r1.stderr or ""):
                return [TextContent(
                    type="text",
                    text=f"Failed to start {spec.name} via launchd: {r1.stderr}"
                )]
            result = f"Started {spec.name} via launchd on {spec.host}:{spec.port}"
        else:
            # Direct start
            pid = start_process(llama_path, spec, log_dir, logging_config=logging_config)
            write_pid(spec.name, pid)
            result = f"Started {spec.name} directly with PID {pid} on {spec.host}:{spec.port}"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        logger.error(f"Failed to start model {input_data.model_name}: {e}")
        raise


async def handle_stop_model(input_data: StopModelInput) -> List[TextContent]:
    """Stop a model server"""
    try:
        if input_data.mode == "launchd":
            # Stop via launchd
            r = launchctl_bootout(input_data.model_name)
            p = plist_path(input_data.model_name)
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
            result = f"Stopped {input_data.model_name} via launchd"
        else:
            # Direct stop
            try:
                pid = read_pid(input_data.model_name)
                stop_process(pid)
                remove_pid(input_data.model_name)
                result = f"Stopped {input_data.model_name} (PID {pid})"
            except FileNotFoundError:
                result = f"No PID file found for {input_data.model_name}"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        logger.error(f"Failed to stop model {input_data.model_name}: {e}")
        raise


async def handle_model_status(input_data: ModelStatusInput) -> List[TextContent]:
    """Get model status"""
    try:
        cfg = load_config()
        timeout_ms = int(cfg.get("timeout_ms", 2000))
        models = cfg.get("models", [])

        if input_data.model_name:
            # Status for specific model
            model_info = next((m for m in models if m.get("name") == input_data.model_name), None)
            if not model_info:
                return [TextContent(
                    type="text",
                    text=f"Model '{input_data.model_name}' not found"
                )]
            models = [model_info]

        result_lines = []
        for model in models:
            name = model.get("name")
            host = model.get("host", "127.0.0.1")
            port = int(model.get("port"))

            # Check if process is running
            pid = None
            mode = "stopped"
            try:
                pid = read_pid(name)
                mode = "direct" if process_alive(pid) else "stopped"
            except Exception:
                pass

            # Check health
            health = check_endpoint(host, port, timeout_ms=timeout_ms)
            status = "UP" if health.get("up") else "DOWN"
            latency = health.get("latency_ms", "N/A")

            result_lines.append(f"{name}: {status} ({mode}) PID={pid} {host}:{port} latency={latency}ms")

        return [TextContent(type="text", text="\n".join(result_lines))]

    except Exception as e:
        logger.error(f"Failed to get model status: {e}")
        raise


async def handle_query_completion(input_data: QueryCompletionInput) -> List[TextContent]:
    """Query model for completion"""
    try:
        if not check_model_available(input_data.model_name):
            return [TextContent(
                type="text",
                text=f"Model '{input_data.model_name}' is not available"
            )]

        result = query_model_completion(
            input_data.model_name,
            input_data.prompt,
            max_tokens=input_data.max_tokens,
            temperature=input_data.temperature,
            stream=False
        )

        content = result.get("content", "No content in response")
        return [TextContent(type="text", text=content)]

    except ModelQueryError as e:
        logger.error(f"Query completion failed: {e}")
        return [TextContent(type="text", text=f"Query failed: {e}")]
    except Exception as e:
        logger.error(f"Unexpected error in query completion: {e}")
        raise


async def handle_query_chat(input_data: QueryChatInput) -> List[TextContent]:
    """Query model for chat"""
    try:
        if not check_model_available(input_data.model_name):
            return [TextContent(
                type="text",
                text=f"Model '{input_data.model_name}' is not available"
            )]

        result = query_model_chat(
            input_data.model_name,
            input_data.messages,
            max_tokens=input_data.max_tokens,
            temperature=input_data.temperature,
            stream=False
        )

        content = result.get("choices", [{}])[0].get("message", {}).get("content", "No content in response")
        return [TextContent(type="text", text=content)]

    except ModelQueryError as e:
        logger.error(f"Query chat failed: {e}")
        return [TextContent(type="text", text=f"Chat query failed: {e}")]
    except Exception as e:
        logger.error(f"Unexpected error in query chat: {e}")
        raise


async def handle_add_model(input_data: AddModelInput) -> List[TextContent]:
    """Add a new model configuration"""
    try:
        cfg = load_config()
        spec = ModelSpec(
            name=input_data.name,
            model_path=input_data.model_path,
            host=input_data.host,
            port=input_data.port,
            args=input_data.extra_args or [],
            env={},
            autostart=input_data.autostart,
        )

        add_model(cfg, spec)
        save_config(cfg)

        return [TextContent(
            type="text",
            text=f"Added model '{input_data.name}' at {input_data.host}:{input_data.port}"
        )]

    except Exception as e:
        logger.error(f"Failed to add model {input_data.name}: {e}")
        raise


async def handle_remove_model(input_data: RemoveModelInput) -> List[TextContent]:
    """Remove a model configuration"""
    try:
        cfg = load_config()
        if not remove_model(cfg, input_data.name):
            return [TextContent(
                type="text",
                text=f"Model '{input_data.name}' not found"
            )]

        save_config(cfg)
        return [TextContent(
            type="text",
            text=f"Removed model '{input_data.name}'"
        )]

    except Exception as e:
        logger.error(f"Failed to remove model {input_data.name}: {e}")
        raise


async def main():
    """Main entry point for the MCP server"""
    async with server.stdio_server() as (read_stream, write_stream):
        logger.info("llamaCPPManager MCP server starting...")
        await app.run(
            read_stream,
            write_stream,
            NotificationOptions(progress_notifications=False)
        )


if __name__ == "__main__":
    asyncio.run(main())