#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/deploy.sh
# Description: Repo-root deployment contract for llamaCPPManager. Builds, installs,
#              verifies, and dependency-checks the Python CLI/MCP entrypoints and
#              the macOS GUI bundle for local and aidevops-driven release workflows.
# Author: OpenAI Codex
# Created: 2026-06-25
#
# Usage:
#   deploy.sh check-deps [--source-revision <sha>]
#   deploy.sh build [--source-revision <sha>]
#   deploy.sh install [--source-revision <sha>]
#   deploy.sh verify [--source-revision <sha>]
#   deploy.sh deploy-local [--source-revision <sha>]
#
# Exit codes:
#   0 success
#   1 generic failure
#   2 dependency or environment check failed
#   3 build failed
#   4 install failed
#   5 verification failed
#   6 source revision mismatch

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
GUI_INSTALLER="${DEPLOY_GUI_INSTALLER:-$REPO_ROOT/gui-macos/install_gui.sh}"
GUI_APP="${DEPLOY_GUI_APP:-/Applications/llamaCPP Manager.app}"
SOURCE_REVISION=""
SUBCOMMAND=""
PYTHON_BIN=""
PIPX_BIN="${DEPLOY_PIPX_BIN:-pipx}"
CLI_BIN_NAME="${DEPLOY_CLI_BIN_NAME:-llamacpp-manager}"
MCP_BIN_NAME="${DEPLOY_MCP_BIN_NAME:-llamacpp-mcp-server}"
STATUS_OUTPUT_PATH="${DEPLOY_STATUS_OUTPUT_PATH:-/tmp/llamacpp-manager-status.json}"

log() { echo "▶ $*"; }
status() { echo "● $*"; }
warn() { echo "⚠ $*" >&2; }
fail() { echo "❌ $*" >&2; }

usage() {
    sed -n '4,22p' "$0" | sed 's/^# \{0,1\}//'
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --source-revision)
                [[ $# -ge 2 ]] || { fail "--source-revision requires a value"; exit 1; }
                SOURCE_REVISION="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            build|install|verify|deploy-local|check-deps)
                [[ -z "$SUBCOMMAND" ]] || { fail "multiple subcommands provided"; exit 1; }
                SUBCOMMAND="$1"
                shift
                ;;
            *)
                fail "unknown argument: $1"
                exit 1
                ;;
        esac
    done

    [[ -n "$SUBCOMMAND" ]] || { usage; exit 1; }
}

command_path() {
    command -v "$1" 2>/dev/null || true
}

select_python() {
    if [[ -n "$PYTHON_BIN" ]]; then
        return 0
    fi

    if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
        PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
    else
        PYTHON_BIN="$(command_path python3)"
    fi
}

version_ge() {
    local actual="$1"
    local minimum="$2"
    python3 - "$actual" "$minimum" <<'PY'
import sys
def normalize(value):
    parts = []
    for chunk in value.replace("-", ".").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return parts

actual = normalize(sys.argv[1])
minimum = normalize(sys.argv[2])
width = max(len(actual), len(minimum))
actual.extend([0] * (width - len(actual)))
minimum.extend([0] * (width - len(minimum)))
sys.exit(0 if actual >= minimum else 1)
PY
}

require_source_revision() {
    [[ -n "$SOURCE_REVISION" ]] || return 0
    if ! command -v git >/dev/null 2>&1; then
        fail "git is required when --source-revision is provided"
        exit 6
    fi
    local head
    head="$(git -C "$REPO_ROOT" rev-parse HEAD)"
    if [[ "$head" != "$SOURCE_REVISION" && "$head" != "$SOURCE_REVISION"* ]]; then
        fail "source revision mismatch: HEAD is $head but --source-revision requested $SOURCE_REVISION"
        exit 6
    fi
    status "source revision verified: $head"
}

check_deps() {
    local missing=0
    select_python

    if [[ "$(uname)" != "Darwin" ]]; then
        fail "macOS is required"
        exit 2
    fi

    local macos_version
    macos_version="$(sw_vers -productVersion)"
    if ! version_ge "$macos_version" "13.0"; then
        fail "macOS 13.0+ required, found $macos_version"
        missing=1
    else
        status "macOS $macos_version"
    fi

    if [[ -z "$PYTHON_BIN" ]]; then
        fail "python3 not found"
        missing=1
    else
        local python_version
        python_version="$("$PYTHON_BIN" -c 'import platform; print(platform.python_version())')"
        if ! version_ge "$python_version" "3.10"; then
            fail "Python 3.10+ required, found $python_version"
            missing=1
        else
            status "python $python_version ($PYTHON_BIN)"
        fi
    fi

    if ! command -v swift >/dev/null 2>&1; then
        fail "swift not found"
        missing=1
    else
        local swift_version
        swift_version="$(swift --version | awk '/Apple Swift version/ {print $4; exit}')"
        if [[ -z "$swift_version" ]]; then
            warn "could not parse Swift version"
        elif ! version_ge "$swift_version" "5.9"; then
            fail "Swift 5.9+ required, found $swift_version"
            missing=1
        else
            status "swift $swift_version"
        fi
    fi

    if ! command -v "$PIPX_BIN" >/dev/null 2>&1; then
        fail "pipx not found"
        missing=1
    else
        status "pipx $("$PIPX_BIN" --version)"
    fi

    if ! "$PYTHON_BIN" -m build --version >/dev/null 2>&1; then
        fail "python build module not available (install with: python3 -m pip install build)"
        missing=1
    else
        status "python build module available"
    fi

    if [[ $missing -ne 0 ]]; then
        exit 2
    fi
}

build_artifacts() {
    require_source_revision
    check_deps

    log "Building Python package artifacts"
    if ! (cd "$REPO_ROOT" && "$PYTHON_BIN" -m build); then
        fail "python package build failed"
        exit 3
    fi

    log "Building Swift package"
    if ! (cd "$REPO_ROOT/gui-macos" && swift build); then
        fail "swift build failed"
        exit 3
    fi

    status "build complete"
}

install_artifacts() {
    require_source_revision
    check_deps

    log "Installing Python CLI + MCP server via pipx"
    if ! (cd "$REPO_ROOT" && "$PIPX_BIN" install --force .); then
        fail "pipx install failed"
        exit 4
    fi

    log "Installing GUI application"
    if ! (cd "$REPO_ROOT/gui-macos" && bash "$GUI_INSTALLER" --no-launch); then
        fail "GUI install failed"
        exit 4
    fi

    local cli_path mcp_path
    cli_path="$(command_path "$CLI_BIN_NAME")"
    mcp_path="$(command_path "$MCP_BIN_NAME")"
    [[ -n "$cli_path" ]] || { fail "llamacpp-manager not found on PATH after install"; exit 4; }
    [[ -n "$mcp_path" ]] || { fail "llamacpp-mcp-server not found on PATH after install"; exit 4; }

    status "installed CLI at $cli_path"
    status "installed MCP entrypoint at $mcp_path"
}

verify_installation() {
    require_source_revision
    check_deps

    local cli_path mcp_path
    cli_path="$(command_path "$CLI_BIN_NAME")"
    mcp_path="$(command_path "$MCP_BIN_NAME")"
    [[ -n "$cli_path" ]] || { fail "llamacpp-manager not found on PATH"; exit 5; }
    [[ -n "$mcp_path" ]] || { fail "llamacpp-mcp-server not found on PATH"; exit 5; }
    [[ -d "$GUI_APP" ]] || { fail "GUI app not found at $GUI_APP"; exit 5; }

    log "Running CLI status sanity check"
    if ! "$cli_path" status --json >"$STATUS_OUTPUT_PATH"; then
        fail "llamacpp-manager status --json failed"
        exit 5
    fi
    STATUS_OUTPUT_PATH="$STATUS_OUTPUT_PATH" "$PYTHON_BIN" - <<'PY'
import json
import os
from pathlib import Path
payload = json.loads(Path(os.environ["STATUS_OUTPUT_PATH"]).read_text())
assert isinstance(payload, dict)
assert "models" in payload
assert "infrastructure" in payload
assert "logging" in payload
PY

    status "verify complete"
}

deploy_local() {
    build_artifacts
    install_artifacts
    verify_installation
}

parse_args "$@"

case "$SUBCOMMAND" in
    check-deps)
        require_source_revision
        check_deps
        ;;
    build)
        build_artifacts
        ;;
    install)
        install_artifacts
        ;;
    verify)
        verify_installation
        ;;
    deploy-local)
        deploy_local
        ;;
esac
