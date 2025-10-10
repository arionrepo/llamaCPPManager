# Port Allocations - llamaCPPManager
**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/PORT_ALLOCATIONS.md
**Description:** Comprehensive port allocation map for all llama.cpp models and infrastructure components
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-10

## Overview

This document tracks all port allocations for llamaCPPManager and related infrastructure to prevent conflicts and provide clear visibility into resource usage.

## Port Range

**Reserved Range:** 8081-8090 (llamaCPPManager models and infrastructure)
**Protocol:** HTTP (llama.cpp OpenAI-compatible API)
**Bind Address:** 127.0.0.1 (localhost only, not exposed externally)

## Current Allocations

### llama.cpp Models (llamaCPPManager)

| Port | Model Name | Status | Size (GB) | RAM (GB) | Use Case | Group |
|------|------------|--------|-----------|----------|----------|-------|
| 8081 | phi3 | Active | ~2 | ~4 | General purpose, fast inference | - |
| 8082 | smollm3 | Stopped | ~0.6 | ~2 | Lightweight, code completion | - |
| 8083 | mistral | Stopped | ~7 | ~10 | General purpose, instruction following | - |
| 8084 | qwen2.5-32b | Stopped | ~35 | ~40 | Complex reasoning, large context (131K) | - |
| 8085 | qwen-coder-7b | Active | 7.54 | 12 | Tool calling, structured JSON outputs | agentic-models |
| 8086 | hermes-3-llama-8b | Active | 7.95 | 13 | Multi-agent systems, autonomous workflows | agentic-models |
| 8087 | llama-3.1-8b | Stopped | 7.95 | 13 | Compliance queries, report generation | agentic-models |

### Infrastructure Components

| Port | Component | Purpose | Status | Health Check |
|------|-----------|---------|--------|--------------|
| 8090 | llm_controller | Model lifecycle orchestration | Active | HTTP /status endpoint |
| - | cloudflared | Cloudflare tunnel (no local port) | Active | launchd process check |

### External Conflicts Check

| Port | Project | Purpose | Conflict? |
|------|---------|---------|-----------|
| 8080 | xLLMArionComply | Swagger UI HTTP server | ❌ No (different port) |

## Model Groups

### agentic-models (Exclusive)
**Mutual Exclusion:** Only ONE model from this group can run at a time
**Auto-stop Timeout:** 60 minutes of inactivity
**Members:**
- qwen-coder-7b (port 8085)
- hermes-3-llama-8b (port 8086)
- llama-3.1-8b (port 8087)

**Rationale:** These 8B models each require 12-13GB RAM. Running multiple simultaneously would exceed available memory on M4 Max.

## Process Discovery Results

**Last Check:** 2025-10-10 15:30

```
Active Processes:
- PID 75924: llama-server @ 127.0.0.1:8081 (phi3)
- PID 63008: llama-server @ 127.0.0.1:8085 (qwen-coder-7b)
- PID 22966: llama-server @ 127.0.0.1:8086 (hermes-3-llama-8b)
- PID 23298: node @ *:8080 (external - likely xLLMArionComply Swagger UI)
- PID 83933: cloudflared (tunnel, no local port binding)
```

## Conflict Resolution

**No conflicts detected** between llamaCPPManager (8081-8090) and xLLMArionComply (8080).

## Port Assignment Guidelines

**When Adding New Models:**
1. Use next available port in 8081-8090 range
2. Update this document immediately
3. Verify no conflicts with `lsof -i -P | grep LISTEN | grep 808X`
4. Add to exclusive group if model requires >10GB RAM

**Reserved for Future Use:**
- 8088: Available
- 8089: Available

## Configuration Location

**File:** `~/Library/Application Support/llamaCPPManager/config.yaml`

**Verification Command:**
```bash
llamacpp-manager config list
```

## Health Monitoring

**Infrastructure Health Check:** Every 30 seconds
**Model Health Check:** On-demand via `llamacpp-manager status`

**Monitoring Configuration:**
```yaml
monitoring:
  enabled: true
  interval_seconds: 30
  alert_on_failure: true
```

## Known Issues

### Stale PID Detection (2025-10-10)
- **qwen-coder-7b:** Shows PID 63007 in status (actual: 63008)
- **hermes-3-llama-8b:** Shows PID 22965 in status (actual: 22966)
- **Root Cause:** Models started by llm_controller don't write PID files
- **Fix Status:** Pending - update status detection to use lsof port-based discovery

## Changelog

**2025-10-10:** Initial port allocation document created
- Documented 7 models on ports 8081-8087
- Documented infrastructure components (llm_controller on 8090, cloudflared)
- Verified no conflicts with xLLMArionComply project (uses 8080)
- Identified stale PID tracking issue

## See Also

- [design.md](design.md) - Architecture and deployment scenarios
- [requirements.md](requirements.md) - Port requirements and security defaults
- [user-manual.md](user-manual.md) - User guide for model management
