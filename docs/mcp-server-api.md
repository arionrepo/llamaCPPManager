# MCP Server API Documentation

## Overview

The llamaCPPManager MCP (Model Context Protocol) server exposes llamaCPPManager functionality as MCP tools that can be used by MCP-compatible clients like Claude Desktop, Continue.dev, and other AI assistants.

**Protocol**: Model Context Protocol (MCP) over stdio
**Server Name**: `llamacpp-manager`
**Launch Command**: `llamacpp-mcp-server`

## Installation & Setup

### 1. Install llamaCPPManager with MCP Support

```bash
# Install via pipx (recommended)
pipx install llamacpp-manager

# Or install in virtual environment
pip install llamacpp-manager
```

### 2. Configure MCP Client

#### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "llamacpp-manager": {
      "command": "llamacpp-mcp-server"
    }
  }
}
```

#### Continue.dev Configuration

Add to `.continuerc.json`:

```json
{
  "mcpServers": [
    {
      "name": "llamacpp-manager",
      "command": "llamacpp-mcp-server"
    }
  ]
}
```

### 3. Verify Server is Running

The MCP server communicates over stdio and doesn't have a standalone HTTP endpoint. To test it manually, you can run:

```bash
llamacpp-mcp-server
```

The server will start and wait for MCP protocol messages on stdin.

## Available MCP Tools

The MCP server exposes 9 tools for managing and querying llama.cpp models:

### 1. list_models

**Description**: List all configured models in llamaCPPManager

**Input Schema**:
```json
{}
```

**Example Response**:
```
Configured models:
- phi3 @ 127.0.0.1:8081 -> /Users/user/llms/phi3.gguf (autostart: false)
- smollm3 @ 127.0.0.1:8082 -> /Users/user/llms/smollm3.gguf (autostart: true)
```

**Use Case**: Get a list of all models configured in llamaCPPManager, whether they're running or not.

---

### 2. list_available_models

**Description**: List models that are currently running and available for queries

**Input Schema**:
```json
{}
```

**Example Response**:
```
Available models:
- phi3
- smollm3
```

**Use Case**: Check which models are actually running and ready to accept queries right now.

---

### 3. start_model

**Description**: Start a llama.cpp model server

**Input Schema**:
```json
{
  "model_name": "string (required)",
  "mode": "string (optional: 'direct' or 'launchd', default: 'direct')"
}
```

**Example Call**:
```json
{
  "model_name": "phi3",
  "mode": "direct"
}
```

**Example Response**:
```
Started phi3 directly with PID 12345 on 127.0.0.1:8081
```

**Use Case**: Start a specific model server. Use `mode: "direct"` for immediate startup or `mode: "launchd"` for managed startup via macOS launchd.

---

### 4. stop_model

**Description**: Stop a running llama.cpp model server

**Input Schema**:
```json
{
  "model_name": "string (required)",
  "mode": "string (optional: 'direct' or 'launchd', default: 'direct')"
}
```

**Example Call**:
```json
{
  "model_name": "phi3",
  "mode": "direct"
}
```

**Example Response**:
```
Stopped phi3 (PID 12345)
```

**Use Case**: Stop a running model server to free up resources.

---

### 5. model_status

**Description**: Get status information for models (running, health, latency, etc)

**Input Schema**:
```json
{
  "model_name": "string (optional: specific model name, or null for all models)"
}
```

**Example Call (all models)**:
```json
{}
```

**Example Call (specific model)**:
```json
{
  "model_name": "phi3"
}
```

**Example Response**:
```
phi3: UP (direct) PID=12345 127.0.0.1:8081 latency=5ms
smollm3: UP (direct) PID=12346 127.0.0.1:8082 latency=3ms
mistral: DOWN (stopped) PID=None 127.0.0.1:8083 latency=N/A
```

**Use Case**: Check if models are running, their health status, and response latency.

---

### 6. query_completion

**Description**: Query a model for text completion

**Input Schema**:
```json
{
  "model_name": "string (required)",
  "prompt": "string (required)",
  "max_tokens": "integer (optional, default: 512)",
  "temperature": "float (optional, default: 0.7)"
}
```

**Example Call**:
```json
{
  "model_name": "phi3",
  "prompt": "Explain quantum computing in simple terms:",
  "max_tokens": 200,
  "temperature": 0.7
}
```

**Example Response**:
```
Quantum computing is a type of computing that uses quantum-mechanical phenomena, such as superposition and entanglement, to perform operations on data. Unlike classical computers that use bits (0 or 1), quantum computers use quantum bits or "qubits" which can exist in multiple states simultaneously...
```

**Use Case**: Get text completions from a running model. Good for simple prompts and single-turn generation.

---

### 7. query_chat

**Description**: Query a model using chat/conversation format

**Input Schema**:
```json
{
  "model_name": "string (required)",
  "messages": "array of {role: string, content: string} (required)",
  "max_tokens": "integer (optional, default: 512)",
  "temperature": "float (optional, default: 0.7)"
}
```

**Example Call**:
```json
{
  "model_name": "phi3",
  "messages": [
    {"role": "system", "content": "You are a helpful AI assistant."},
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "The capital of France is Paris."},
    {"role": "user", "content": "What's the population?"}
  ],
  "max_tokens": 100,
  "temperature": 0.7
}
```

**Example Response**:
```
Paris has a population of approximately 2.1 million people within the city proper, and about 12 million in the greater metropolitan area.
```

**Use Case**: Have multi-turn conversations with models, maintaining chat history context.

---

### 8. add_model

**Description**: Add a new model configuration to llamaCPPManager

**Input Schema**:
```json
{
  "name": "string (required)",
  "model_path": "string (required: path to .gguf file)",
  "host": "string (optional, default: '127.0.0.1')",
  "port": "integer (required)",
  "extra_args": "array of strings (optional: additional llama-server arguments)",
  "autostart": "boolean (optional, default: false)"
}
```

**Example Call**:
```json
{
  "name": "llama3",
  "model_path": "/Users/user/llms/llama3-8b.gguf",
  "port": 8084,
  "extra_args": ["-c", "4096"],
  "autostart": true
}
```

**Example Response**:
```
Added model 'llama3' at 127.0.0.1:8084
```

**Use Case**: Dynamically add new models to llamaCPPManager configuration without editing config files.

---

### 9. remove_model

**Description**: Remove a model configuration from llamaCPPManager

**Input Schema**:
```json
{
  "name": "string (required)"
}
```

**Example Call**:
```json
{
  "name": "llama3"
}
```

**Example Response**:
```
Removed model 'llama3'
```

**Use Case**: Remove models from configuration when they're no longer needed.

---

## Testing MCP Server with MCP Inspector

Since the MCP server uses stdio protocol, you can't test it with curl. However, you can use the MCP Inspector tool:

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector with llamacpp-manager server
mcp-inspector llamacpp-mcp-server
```

This will open a web UI where you can interactively test all MCP tools.

## Programmatic Access (Python)

While MCP is primarily for AI assistant integration, you can also use the MCP client library programmatically:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp():
    server_params = StdioServerParameters(
        command="llamacpp-mcp-server",
        args=[],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            # Call a tool
            result = await session.call_tool("list_models", {})
            print(f"Models: {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(test_mcp())
```

## Common Workflows

### Workflow 1: Start a Model and Query It

```python
# Via MCP tools:
# 1. list_models - see what's configured
# 2. start_model - start the model you want
# 3. model_status - verify it's running
# 4. query_chat - send your questions
```

### Workflow 2: Add New Model and Use It

```python
# Via MCP tools:
# 1. add_model - configure new model
# 2. start_model - start it
# 3. query_completion - test it
```

### Workflow 3: Check All Running Models

```python
# Via MCP tools:
# 1. list_available_models - see what's running
# 2. model_status - get detailed health info
```

## Error Handling

All MCP tools return errors as text content:

**Example Error Response**:
```
Error executing start_model: Model 'nonexistent' not found in configuration
```

**Common Errors**:
- `Model 'X' not found in configuration` - Model doesn't exist, use `add_model` first
- `Model 'X' is not available` - Model isn't running, use `start_model` first
- `Port X already used by model 'Y'` - Port conflict, choose different port
- `model_path not found: /path/to/file.gguf` - Invalid model file path

## Architecture

```
┌─────────────────┐
│  MCP Client     │  (Claude Desktop, Continue.dev, etc)
│  (AI Assistant) │
└────────┬────────┘
         │ MCP Protocol (stdio)
         │
┌────────▼────────┐
│  MCP Server     │  llamacpp-mcp-server
│  (This Server)  │
└────────┬────────┘
         │ Python API
         │
┌────────▼────────┐
│ llamaCPPManager │  Config, Process Management, Health Checks
│   Core Modules  │
└────────┬────────┘
         │ subprocess / HTTP
         │
┌────────▼────────┐
│  llama-server   │  Actual LLM inference
│  (llama.cpp)    │
└─────────────────┘
```

## Limitations

**Platform**: macOS only (launchd integration)
**Protocol**: stdio only (no HTTP/WebSocket MCP transport)
**Scope**: Local models only (same machine as MCP server)
**Concurrency**: Single-threaded event loop

## Troubleshooting

### MCP Server Not Appearing in Claude Desktop

1. Check config path: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Verify command works: `which llamacpp-mcp-server`
3. Restart Claude Desktop completely
4. Check logs: `~/Library/Logs/Claude/mcp-server-llamacpp-manager.log`

### Tool Calls Failing

1. Verify CLI works: `llamacpp-manager status`
2. Check config exists: `~/Library/Application Support/llamaCPPManager/config.yaml`
3. Test model manually: `llamacpp-manager start phi3`

### Models Not Available for Queries

1. Check they're running: `llamacpp-manager status`
2. Verify ports are listening: `lsof -i :8081`
3. Test health endpoint: `curl http://127.0.0.1:8081/health`

## See Also

- [llamaCPPManager User Manual](user-manual.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/model-context-protocol)
