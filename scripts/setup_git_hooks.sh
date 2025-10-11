#!/usr/bin/env bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/scripts/setup_git_hooks.sh
# Description: Setup script for automated regression testing git hooks
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-11

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

echo "🔧 Setting up automated regression testing git hooks..."

# Ensure hooks are executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push

# Verify hooks exist
if [[ -f ".git/hooks/pre-commit" && -x ".git/hooks/pre-commit" ]]; then
    echo "✅ Pre-commit hook installed and executable"
else
    echo "❌ Pre-commit hook missing or not executable"
    exit 1
fi

if [[ -f ".git/hooks/pre-push" && -x ".git/hooks/pre-push" ]]; then
    echo "✅ Pre-push hook installed and executable"
else
    echo "❌ Pre-push hook missing or not executable"
    exit 1
fi

# Test that the environment can run the hooks
PYTHON=${PYTHON:-python3}
VENV=.venv

if [[ ! -d "$VENV" ]]; then
    echo "🔧 Creating test environment for hooks..."
    "$PYTHON" -m venv "$VENV"
    "$VENV/bin/pip" install -U pip
    "$VENV/bin/pip" install -e . -r requirements-dev.txt
fi

echo ""
echo "🎉 Git hooks setup complete!"
echo ""
echo "Automated regression testing is now enabled:"
echo ""
echo "📋 On every commit:"
echo "  ✅ Critical idempotency tests"
echo "  ✅ Config idempotency tests (if config files changed)"
echo "  ✅ Core functionality tests"
echo "  ✅ Security tests (if security files changed)"
echo ""
echo "📋 On every push:"
echo "  ✅ Complete idempotency test suite"
echo "  ✅ Full unit test suite"
echo "  ✅ Integration tests"
echo "  ✅ Model manager tests"
echo "  ✅ CLI tests"
echo ""
echo "💡 To bypass hooks (not recommended): git commit --no-verify"
echo "💡 To test hooks manually: ./scripts/run_idempotency_tests.sh"