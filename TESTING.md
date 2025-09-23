# Manual Testing Guide

Quick guide to manually test llamaCPP Manager functionality.

## Prerequisites ✅

- ✅ CLI installed: `llamacpp-manager` is available
- ✅ llama-server binary: `/opt/homebrew/bin/llama-server`
- ✅ MCP server: `llamacpp-mcp-server` is available

## Step 1: Basic Setup & Initialization

```bash
# 1. Initialize with custom directories (recommended)
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs init

# 2. Verify initialization
ls -la ~/Testing/llamacpp-config/
ls -la ~/Testing/llamacpp-logs/

# 3. Check config file was created
cat ~/Testing/llamacpp-config/config.yaml
```

**Expected Output:**
- Directories created successfully
- `config.yaml` file exists with default settings
- No errors

## Step 2: Download a Test Model

```bash
# Create model directory
mkdir -p ~/Testing/test-models

# Download a small test model (SmolLM2 - ~1.7GB)
cd ~/Testing/test-models
curl -L -O "https://huggingface.co/bartowski/SmolLM2-1.7B-Instruct-GGUF/resolve/main/SmolLM2-1.7B-Instruct-Q8_0.gguf"

# Verify download
ls -lh SmolLM2-1.7B-Instruct-Q8_0.gguf
```

**Expected Output:**
- File ~1.7GB downloaded successfully
- No corruption errors

## Step 3: Add Model to Configuration

```bash
# Add model with basic configuration
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs \
  config add test-model \
  ~/Testing/test-models/SmolLM2-1.7B-Instruct-Q8_0.gguf \
  --port 8081 \
  --extra-args "-c 4096 -ngl 999"

# List configuration to verify
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config config list

# Check JSON output
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config config list --json
```

**Expected Output:**
- Model added successfully
- Configuration shows model with correct path and port
- JSON output is valid

## Step 4: Start Model (Bare-Metal Mode)

```bash
# Start the model
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs \
  start test-model

# Check if it started successfully
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config status

# Check process is running
ps aux | grep llama-server

# Check port is bound
lsof -i :8081
```

**Expected Output:**
- "Model started successfully" message
- Status shows model as "running"
- Process visible in `ps` output
- Port 8081 is bound to llama-server

## Step 5: Test Model Queries

```bash
# Test completion API
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config \
  query complete test-model "Hello, world! My name is"

# Test with parameters
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config \
  query complete test-model "Once upon a time" --max-tokens 50 --temperature 0.7

# Test chat API
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config \
  query chat test-model --message "user:Hello there!"

# Test streaming (optional)
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config \
  query complete test-model "Tell me a short story" --stream
```

**Expected Output:**
- Text completions generated successfully
- Chat responses work
- No HTTP errors
- Reasonable response times (<10 seconds for small model)

## Step 6: Test Direct HTTP API

```bash
# Test health endpoint
curl -s http://127.0.0.1:8081/health

# Test completion endpoint directly
curl -X POST http://127.0.0.1:8081/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world", "n_predict": 10}'

# Test streaming
curl -X POST http://127.0.0.1:8081/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Count to 5:", "n_predict": 20, "stream": true}'
```

**Expected Output:**
- Health endpoint returns status info
- Completion endpoint returns generated text
- Streaming shows incremental responses

## Step 7: Test Logs and Monitoring

```bash
# View model logs
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs \
  logs test-model --tail 20

# Follow logs in real-time (open in separate terminal)
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs \
  logs test-model --follow

# Check status with health info
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config status --json
```

**Expected Output:**
- Log files exist and contain startup/request logs
- Real-time logs show API requests
- Status includes health check latency

## Step 8: Test Stop/Restart

```bash
# Stop the model
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs \
  stop test-model

# Verify it stopped
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config status
ps aux | grep llama-server
lsof -i :8081

# Restart the model
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs \
  restart test-model

# Verify it restarted
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config status
```

**Expected Output:**
- Model stops cleanly (no hanging processes)
- Status shows "stopped"
- Port 8081 is released
- Restart brings it back online

## Step 9: Test MCP Server

```bash
# Start MCP server in background
.venv/bin/llamacpp-mcp-server --config-dir ~/Testing/llamacpp-config &
MCP_PID=$!

# Test MCP server is responding (check if it starts without errors)
sleep 2
ps -p $MCP_PID

# Stop MCP server
kill $MCP_PID
```

**Expected Output:**
- MCP server starts without errors
- Process runs briefly
- No crash/exception messages

## Step 10: Test GUI (If Available)

```bash
# Check if GUI can be built
cd gui-macos
swift build

# Try to run tests
swift test

# If successful, try running (will open GUI)
# swift run llamacpp-gui
```

**Expected Output:**
- Swift build succeeds
- Tests pass (if any)
- GUI app launches (if run)

## Step 11: Test Configuration Management

```bash
# Add a second model configuration
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config \
  config add test-model-2 \
  ~/Testing/test-models/SmolLM2-1.7B-Instruct-Q8_0.gguf \
  --port 8082 \
  --autostart true

# Update existing model
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config \
  config update test-model --autostart true --port 8083

# List all models
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config config list

# Remove test model 2
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config \
  config remove test-model-2
```

**Expected Output:**
- Second model added successfully
- Update changes port/autostart setting
- List shows all configured models
- Remove operation works cleanly

## Troubleshooting Common Issues

### Issue: "Port already in use"
```bash
# Check what's using the port
lsof -i :8081
# Kill conflicting process or use different port
```

### Issue: "Model file not found"
```bash
# Verify file exists and is readable
ls -la ~/Testing/test-models/SmolLM2-1.7B-Instruct-Q8_0.gguf
file ~/Testing/test-models/SmolLM2-1.7B-Instruct-Q8_0.gguf
```

### Issue: "llama-server binary not found"
```bash
# Check binary exists
which llama-server
# If not found: brew install llama.cpp
```

### Issue: Model won't start
```bash
# Check logs for errors
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs \
  logs test-model --tail 50

# Try manual start to see errors
/opt/homebrew/bin/llama-server --model ~/Testing/test-models/SmolLM2-1.7B-Instruct-Q8_0.gguf --port 8081 --host 127.0.0.1
```

### Issue: Slow responses
```bash
# Check if GPU acceleration is working
# Look for "Using metal" or similar in logs
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs \
  logs test-model | grep -i metal
```

## Test Results Checklist

Mark off each successful test:

- [ ] ✅ CLI installation and help
- [ ] ✅ Initialization creates directories and config
- [ ] ✅ Model download completes
- [ ] ✅ Model configuration (add/list/update/remove)
- [ ] ✅ Model starts successfully
- [ ] ✅ Status reporting works
- [ ] ✅ Query API (completion/chat) works
- [ ] ✅ Direct HTTP API works
- [ ] ✅ Logs are accessible and updating
- [ ] ✅ Stop/restart cycle works
- [ ] ✅ MCP server starts without errors
- [ ] ✅ GUI builds (if tested)

## Next Steps After Basic Testing

1. **Test launchd integration** (auto-start):
   ```bash
   .venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config launchd install test-model
   .venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config ensure-running
   ```

2. **Test with multiple models** simultaneously

3. **Performance testing** with larger models

4. **Container testing** (once Docker features are implemented)

5. **Kubernetes testing** (once K8s features are implemented)

## Cleanup After Testing

```bash
# Stop all models
.venv/bin/llamacpp-manager --config-dir ~/Testing/llamacpp-config --log-dir ~/Testing/llamacpp-logs stop all

# Remove test directories (optional)
rm -rf ~/Testing/llamacpp-config
rm -rf ~/Testing/llamacpp-logs
rm -rf ~/Testing/test-models
```