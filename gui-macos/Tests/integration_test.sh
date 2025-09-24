#!/bin/bash
# Integration test script for llamaCPP Manager GUI
# Tests the complete workflow: CLI setup -> GUI launch -> interaction -> cleanup

set -e  # Exit on any error

# Configuration
TEST_CONFIG_DIR="$HOME/Testing/GUI-Integration/config"
TEST_LOG_DIR="$HOME/Testing/GUI-Integration/logs"
TEST_MODEL_PATH="/tmp/test-model.gguf"
CLI_PATH="../.venv/bin/llamacpp-manager"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log "Cleaning up test environment..."

    # Kill GUI if running
    if [[ ! -z "$GUI_PID" ]]; then
        kill $GUI_PID 2>/dev/null || true
        wait $GUI_PID 2>/dev/null || true
    fi

    # Stop any test models
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" --log-dir "$TEST_LOG_DIR" stop all 2>/dev/null || true

    # Remove test directories
    rm -rf "$TEST_CONFIG_DIR" "$TEST_LOG_DIR" 2>/dev/null || true
    rm -f "$TEST_MODEL_PATH" 2>/dev/null || true

    log "Cleanup complete"
}

# Set up cleanup trap
trap cleanup EXIT

# Test setup
setup_test_environment() {
    log "Setting up test environment..."

    # Create test directories
    mkdir -p "$TEST_CONFIG_DIR" "$TEST_LOG_DIR"

    # Create a fake model file for testing
    echo "# Fake GGUF model for testing" > "$TEST_MODEL_PATH"

    # Verify CLI is available
    if [[ ! -f "$CLI_PATH" ]]; then
        error "CLI not found at $CLI_PATH"
        exit 1
    fi

    log "Test environment setup complete"
}

# Initialize configuration
setup_configuration() {
    log "Initializing configuration..."

    # Initialize config
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" --log-dir "$TEST_LOG_DIR" init

    # Add test model (will fail to start but that's OK for GUI testing)
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" \
        config add test-model \
        "$TEST_MODEL_PATH" \
        --port 8091 \
        --extra-args "-c 2048"

    # Verify configuration
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" config list

    log "Configuration initialized"
}

# Test CLI integration
test_cli_operations() {
    log "Testing CLI operations..."

    # Test config operations
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" config list --json > /tmp/test-config.json
    if [[ ! -s /tmp/test-config.json ]]; then
        error "Config list JSON output is empty"
        exit 1
    fi

    # Test status operations
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" status --json > /tmp/test-status.json
    if [[ ! -f /tmp/test-status.json ]]; then
        error "Status JSON output not created"
        exit 1
    fi

    log "CLI operations test passed"
}

# Launch GUI
launch_gui() {
    log "Launching GUI..."

    # Set environment variables for GUI
    export LLAMACPP_MANAGER_CONFIG_DIR="$TEST_CONFIG_DIR"
    export LLAMACPP_MANAGER_LOG_DIR="$TEST_LOG_DIR"
    export PATH="../.venv/bin:$PATH"

    # Launch GUI in background
    swift run llamacpp-gui > /tmp/gui-output.log 2>&1 &
    GUI_PID=$!

    # Give GUI time to start
    sleep 5

    # Verify GUI is still running
    if ! kill -0 $GUI_PID 2>/dev/null; then
        error "GUI failed to start or crashed"
        cat /tmp/gui-output.log
        exit 1
    fi

    log "GUI launched successfully (PID: $GUI_PID)"
}

# Test GUI stability
test_gui_stability() {
    log "Testing GUI stability..."

    # Let GUI run for a while
    for i in {1..10}; do
        if ! kill -0 $GUI_PID 2>/dev/null; then
            error "GUI crashed after $i seconds"
            cat /tmp/gui-output.log
            exit 1
        fi
        sleep 1
    done

    log "GUI stability test passed"
}

# Test CLI-GUI integration
test_cli_gui_integration() {
    log "Testing CLI-GUI integration..."

    # Perform CLI operations while GUI is running
    # This tests if GUI can handle real-time updates

    # Update model config
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" \
        config update test-model --port 8092

    sleep 2  # Let GUI poll for updates

    # Check if GUI is still stable
    if ! kill -0 $GUI_PID 2>/dev/null; then
        error "GUI crashed during config update"
        cat /tmp/gui-output.log
        exit 1
    fi

    # Try to start model (will fail but GUI should handle it)
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" \
        start test-model 2>/dev/null || true

    sleep 2

    # GUI should still be running
    if ! kill -0 $GUI_PID 2>/dev/null; then
        error "GUI crashed during model start attempt"
        cat /tmp/gui-output.log
        exit 1
    fi

    log "CLI-GUI integration test passed"
}

# Test error handling
test_error_handling() {
    log "Testing error handling..."

    # Create invalid YAML to test error handling (but don't crash the CLI)
    echo "invalid_yaml_syntax_without_colons_or_structure" > "$TEST_CONFIG_DIR/config.yaml"

    sleep 3  # Let GUI detect the change

    # GUI should still be running (graceful error handling)
    if ! kill -0 $GUI_PID 2>/dev/null; then
        error "GUI crashed on config error"
        cat /tmp/gui-output.log
        exit 1
    fi

    # Restore valid config
    $CLI_PATH --config-dir "$TEST_CONFIG_DIR" --log-dir "$TEST_LOG_DIR" init

    log "Error handling test passed"
}

# Test memory usage
test_memory_usage() {
    log "Testing memory usage..."

    # Get initial memory usage
    local initial_memory=$(ps -o rss= -p $GUI_PID 2>/dev/null || echo "0")

    # Let GUI run with activity for extended period
    for i in {1..20}; do
        # Trigger GUI activity by updating config
        $CLI_PATH --config-dir "$TEST_CONFIG_DIR" config list > /dev/null 2>&1 || true
        sleep 1
    done

    # Check final memory usage
    local final_memory=$(ps -o rss= -p $GUI_PID 2>/dev/null || echo "0")

    if [[ $final_memory -gt $((initial_memory * 3)) ]]; then
        warn "Memory usage increased significantly: $initial_memory KB -> $final_memory KB"
    else
        log "Memory usage stable: $initial_memory KB -> $final_memory KB"
    fi
}

# Run all tests
run_all_tests() {
    log "Starting integration tests..."

    setup_test_environment
    setup_configuration
    test_cli_operations
    launch_gui
    test_gui_stability
    test_cli_gui_integration
    test_error_handling
    test_memory_usage

    log "All integration tests passed! ✅"
}

# Main execution
main() {
    log "llamaCPP Manager GUI Integration Test"
    log "====================================="

    # Check if we're in the right directory
    if [[ ! -f "Package.swift" ]]; then
        error "Must run from gui-macos directory"
        exit 1
    fi

    run_all_tests
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi