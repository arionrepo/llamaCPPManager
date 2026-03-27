#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/infrastructure/scripts/_shared.sh
# Description: Shared functions, configuration, and utilities for infrastructure management
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-01-05

set -o pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration - Infrastructure Services
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRASTRUCTURE_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "$INFRASTRUCTURE_ROOT")" && pwd)"

# Colima Configuration
COLIMA_PROFILE="${COLIMA_PROFILE:-app}"
COLIMA_HOME="${HOME}/.colima"
COLIMA_SOCKET="${COLIMA_HOME}/${COLIMA_PROFILE}/docker.sock"

# MyRAGDB Configuration
MYRAGDB_PORT="${MYRAGDB_PORT:-3003}"
MYRAGDB_PATH="${HOME}/LocalProjects/GitHubProjectsDocuments/myragdb"
MYRAGDB_LOG="/tmp/myragdb_server.log"
MYRAGDB_HEALTH_ENDPOINT="http://127.0.0.1:${MYRAGDB_PORT}/health"

# Health Check Configuration
HEALTH_TIMEOUT_MS="${HEALTH_TIMEOUT_MS:-5000}"
HEALTH_RETRY_COUNT="${HEALTH_RETRY_COUNT:-5}"
HEALTH_RETRY_INTERVAL="${HEALTH_RETRY_INTERVAL:-30}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Color Output Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Colima Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

colima_is_running() {
    if [ -S "$COLIMA_SOCKET" ]; then
        export DOCKER_HOST="unix://${COLIMA_SOCKET}"
        docker ps >/dev/null 2>&1
        return $?
    fi
    return 1
}

colima_start() {
    if colima_is_running; then
        print_success "Colima already running"
        return 0
    fi

    if colima start "$COLIMA_PROFILE" >/dev/null 2>&1; then
        if wait_for_colima_socket 30; then
            print_success "Colima started successfully"
            return 0
        fi
    fi

    print_error "Failed to start Colima"
    return 1
}

colima_stop() {
    if ! colima_is_running; then
        print_success "Colima already stopped"
        return 0
    fi

    if colima stop "$COLIMA_PROFILE" 2>/dev/null; then
        print_success "Colima stopped successfully"
        return 0
    fi

    print_error "Failed to stop Colima"
    return 1
}

wait_for_colima_socket() {
    local timeout=${1:-30}
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if [ -S "$COLIMA_SOCKET" ]; then
            export DOCKER_HOST="unix://${COLIMA_SOCKET}"
            if docker ps >/dev/null 2>&1; then
                return 0
            fi
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    return 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Docker Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

docker_is_ready() {
    if [ -S "$COLIMA_SOCKET" ]; then
        export DOCKER_HOST="unix://${COLIMA_SOCKET}"
        docker ps >/dev/null 2>&1
        return $?
    fi
    return 1
}

docker_set_host() {
    if [ -S "$COLIMA_SOCKET" ]; then
        export DOCKER_HOST="unix://${COLIMA_SOCKET}"
        return 0
    fi
    return 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MyRAGDB Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

myragdb_is_running() {
    if [ -f "$MYRAGDB_PATH/.server.pid" ]; then
        local pid=$(cat "$MYRAGDB_PATH/.server.pid")
        if ps -p "$pid" >/dev/null 2>&1; then
            return 0
        fi
    fi

    # Fallback: check for running process
    pgrep -f "python -m myragdb.api.server" >/dev/null 2>&1
    return $?
}

myragdb_get_pid() {
    if [ -f "$MYRAGDB_PATH/.server.pid" ]; then
        cat "$MYRAGDB_PATH/.server.pid"
    else
        pgrep -f "python -m myragdb.api.server" | head -n 1
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Health Check Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

wait_for_health() {
    local url=$1
    local name=$2
    local timeout_ms=${3:-$HEALTH_TIMEOUT_MS}
    local max_retries=${4:-$HEALTH_RETRY_COUNT}
    local retry_interval=${5:-$HEALTH_RETRY_INTERVAL}

    local retry=0
    local timeout_seconds=$((timeout_ms / 1000))

    while [ $retry -lt $max_retries ]; do
        if curl -s --max-time "$timeout_seconds" "$url" >/dev/null 2>&1; then
            print_success "$name is healthy"
            return 0
        fi

        print_warning "$name not responding yet (attempt $((retry + 1))/$max_retries)"
        sleep "$retry_interval"
        retry=$((retry + 1))
    done

    print_error "Timeout waiting for $name health check after $((max_retries * retry_interval)) seconds"
    return 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Status Display Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

service_status_display() {
    local service=$1
    local is_running=$2
    local details=$3

    if [ "$is_running" = "true" ]; then
        print_success "$service is running ($details)"
    else
        print_error "$service is not running"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utility Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ensure_command_exists() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        print_error "Required command not found: $cmd"
        return 1
    fi
    return 0
}
