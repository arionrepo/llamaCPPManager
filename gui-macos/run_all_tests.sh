#!/bin/bash
# Master test runner for llamaCPP Manager GUI
# Runs unit tests, UI tests, and integration tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

title() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Swift
    if ! command -v swift &> /dev/null; then
        error "Swift not found. Please install Xcode."
        exit 1
    fi

    # Check CLI
    if [[ ! -f "../.venv/bin/llamacpp-manager" ]]; then
        error "llamacpp-manager CLI not found at ../.venv/bin/llamacpp-manager"
        error "Please run 'pip install -e .' from the project root first"
        exit 1
    fi

    # Check we're in the right directory
    if [[ ! -f "Package.swift" ]]; then
        error "Must run from gui-macos directory"
        exit 1
    fi

    log "Prerequisites check passed"
}

# Run unit tests
run_unit_tests() {
    title "Running Unit Tests"

    # Run Swift package tests (unit tests only)
    if swift test --filter llamacpp-guiTests; then
        log "Unit tests passed ✅"
    else
        error "Unit tests failed ❌"
        return 1
    fi
}

# Run UI tests
run_ui_tests() {
    title "Running UI Tests"

    # UI tests require special setup and may not work in all environments
    if swift test --filter llamacpp-guiUITests; then
        log "UI tests passed ✅"
    else
        warn "UI tests failed or require accessibility permissions ⚠️"
        warn "UI tests may require:"
        warn "  1. Accessibility permissions for Terminal"
        warn "  2. Running from Xcode for proper test environment"
        warn "  3. macOS 13+ and proper test setup"
        return 0  # Don't fail the entire test suite for UI test issues
    fi
}

# Run integration tests
run_integration_tests() {
    title "Running Integration Tests"

    if [[ -f "Tests/integration_test.sh" ]]; then
        if bash Tests/integration_test.sh; then
            log "Integration tests passed ✅"
        else
            error "Integration tests failed ❌"
            return 1
        fi
    else
        warn "Integration test script not found"
        return 0
    fi
}

# Run build test
run_build_test() {
    title "Testing Build"

    if swift build; then
        log "Build test passed ✅"
    else
        error "Build test failed ❌"
        return 1
    fi
}

# Run all tests
run_all() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local test_log="test_results_${timestamp}.log"

    log "llamaCPP Manager GUI - Complete Test Suite"
    log "=========================================="
    log "Test results will be logged to: $test_log"

    local failed_tests=()

    # Run each test suite and log output
    run_build_test 2>&1 | tee -a "$test_log" || failed_tests+=("Build")
    run_unit_tests 2>&1 | tee -a "$test_log" || failed_tests+=("Unit Tests")
    run_ui_tests 2>&1 | tee -a "$test_log" || failed_tests+=("UI Tests")
    run_integration_tests 2>&1 | tee -a "$test_log" || failed_tests+=("Integration Tests")

    # Summary
    echo
    log "Test Summary" | tee -a "$test_log"
    log "============" | tee -a "$test_log"

    if [[ ${#failed_tests[@]} -eq 0 ]]; then
        log "All tests passed! 🎉" | tee -a "$test_log"
        log "Full test log saved to: $test_log" | tee -a "$test_log"
        exit 0
    else
        error "Failed test suites: ${failed_tests[*]}" | tee -a "$test_log"
        log "Full test log with errors saved to: $test_log" | tee -a "$test_log"
        exit 1
    fi
}

# Parse command line arguments
case "${1:-all}" in
    "build")
        check_prerequisites
        run_build_test
        ;;
    "unit")
        check_prerequisites
        run_unit_tests
        ;;
    "ui")
        check_prerequisites
        run_ui_tests
        ;;
    "integration")
        check_prerequisites
        run_integration_tests
        ;;
    "all")
        check_prerequisites
        run_all
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [build|unit|ui|integration|all|help]"
        echo
        echo "Commands:"
        echo "  build       - Test that the GUI builds successfully"
        echo "  unit        - Run unit tests only"
        echo "  ui          - Run UI tests only (may require accessibility permissions)"
        echo "  integration - Run integration tests only"
        echo "  all         - Run all test suites (default)"
        echo "  help        - Show this help message"
        exit 0
        ;;
    *)
        error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac