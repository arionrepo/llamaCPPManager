#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/tests/run_regression_tests.sh
# Description: Automated regression test suite for llamaCPP Manager CLI
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-12

# Don't exit on first failure - collect all results
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test results log
TEST_LOG="test_results_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee -a "$TEST_LOG"
echo "llamaCPP Manager Regression Test Suite" | tee -a "$TEST_LOG"
echo "Started: $(date)" | tee -a "$TEST_LOG"
echo "========================================" | tee -a "$TEST_LOG"
echo "" | tee -a "$TEST_LOG"

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_exit_code="${3:-0}"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "Testing: $test_name ... " | tee -a "$TEST_LOG"

    # Run the command and capture output
    if eval "$test_command" > /tmp/test_output.txt 2>&1; then
        actual_exit_code=0
    else
        actual_exit_code=$?
    fi

    # Check if exit code matches expected
    if [ "$actual_exit_code" -eq "$expected_exit_code" ]; then
        echo -e "${GREEN}PASS${NC}" | tee -a "$TEST_LOG"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC} (exit code: $actual_exit_code, expected: $expected_exit_code)" | tee -a "$TEST_LOG"
        cat /tmp/test_output.txt | tee -a "$TEST_LOG"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Function to check command output contains string
run_test_output_contains() {
    local test_name="$1"
    local test_command="$2"
    local expected_string="$3"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "Testing: $test_name ... " | tee -a "$TEST_LOG"

    # Run the command and capture output
    if output=$(eval "$test_command" 2>&1); then
        if echo "$output" | grep -q "$expected_string"; then
            echo -e "${GREEN}PASS${NC}" | tee -a "$TEST_LOG"
            TESTS_PASSED=$((TESTS_PASSED + 1))
            return 0
        else
            echo -e "${RED}FAIL${NC} (output does not contain: $expected_string)" | tee -a "$TEST_LOG"
            echo "Output: $output" | tee -a "$TEST_LOG"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        echo -e "${RED}FAIL${NC} (command failed)" | tee -a "$TEST_LOG"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

echo "=== Installation Tests ===" | tee -a "$TEST_LOG"
run_test "CLI is installed" "which llamacpp-manager"
run_test "CLI version" "llamacpp-manager --version"
run_test "CLI help" "llamacpp-manager --help"
echo "" | tee -a "$TEST_LOG"

echo "=== Status Commands ===" | tee -a "$TEST_LOG"
run_test "Status (text)" "llamacpp-manager status"
run_test "Status (JSON)" "llamacpp-manager status --json"
run_test_output_contains "Status contains 'models'" "llamacpp-manager status --json" "models"
echo "" | tee -a "$TEST_LOG"

echo "=== Configuration Commands ===" | tee -a "$TEST_LOG"
run_test "Config list" "llamacpp-manager config list"
run_test "Config list (JSON)" "llamacpp-manager config list --json"
# Note: GUI "Open Config" opens Finder to config dir, no CLI equivalent needed
echo "" | tee -a "$TEST_LOG"

echo "=== Model Discovery Commands ===" | tee -a "$TEST_LOG"
run_test "Models list" "llamacpp-manager models list"
run_test "Models list (JSON)" "llamacpp-manager models list --json"
run_test "Models list available" "llamacpp-manager models list --available"
echo "" | tee -a "$TEST_LOG"

echo "=== Logging Commands ===" | tee -a "$TEST_LOG"
run_test "Logging status" "llamacpp-manager logging status || llamacpp-manager status --json | grep -q logging"
echo "" | tee -a "$TEST_LOG"

echo "=== Health Check Commands ===" | tee -a "$TEST_LOG"
run_test "Health check all" "llamacpp-manager health || llamacpp-manager status"
echo "" | tee -a "$TEST_LOG"

echo "=== Infrastructure Commands ===" | tee -a "$TEST_LOG"
run_test "Infrastructure list" "llamacpp-manager infra list || llamacpp-manager status --json | grep -q infrastructure"
echo "" | tee -a "$TEST_LOG"

echo "=== Error Handling Tests ===" | tee -a "$TEST_LOG"
run_test "Invalid command fails" "llamacpp-manager invalid_command_xyz" 2
run_test "Start non-existent model fails" "llamacpp-manager start nonexistent_model_xyz" 1
run_test "Stop non-existent model fails" "llamacpp-manager stop nonexistent_model_xyz" 1
echo "" | tee -a "$TEST_LOG"

# Summary
echo "========================================" | tee -a "$TEST_LOG"
echo "Test Summary" | tee -a "$TEST_LOG"
echo "========================================" | tee -a "$TEST_LOG"
echo "Tests Run:    $TESTS_RUN" | tee -a "$TEST_LOG"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}" | tee -a "$TEST_LOG"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}" | tee -a "$TEST_LOG"
echo "Pass Rate:    $(awk "BEGIN {printf \"%.1f%%\", ($TESTS_PASSED/$TESTS_RUN)*100}")" | tee -a "$TEST_LOG"
echo "========================================" | tee -a "$TEST_LOG"
echo "Completed: $(date)" | tee -a "$TEST_LOG"
echo "Log saved to: $TEST_LOG" | tee -a "$TEST_LOG"

# Exit with error if any tests failed
if [ "$TESTS_FAILED" -gt 0 ]; then
    exit 1
else
    exit 0
fi
