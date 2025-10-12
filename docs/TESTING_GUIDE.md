# Testing Guide

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/TESTING_GUIDE.md
**Description:** Master testing guide for llamaCPP Manager project
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-12

## Overview

This guide describes the complete testing strategy for llamaCPP Manager, including unit tests, integration tests, regression tests, and manual testing procedures.

## Test Suite Structure

```
tests/
├── test_config.py              # Unit tests for configuration
├── test_model_manager.py       # Unit tests for model management
├── test_integrations.py        # Integration tests
├── run_regression_tests.sh     # Automated CLI regression tests
└── test_results/               # Test results and logs

docs/
├── GUI_REGRESSION_TEST.md      # Manual GUI regression checklist
├── CLI_REGRESSION_TEST.md      # Manual CLI regression checklist
├── INTEGRATION_REGRESSION_TEST.md  # Integration test checklist
└── TESTING_GUIDE.md            # This file
```

## Testing Levels

### 1. Unit Tests (Automated)

**Location:** `tests/test_*.py`

**Run with:**
```bash
.venv/bin/pytest tests/ -v
```

**Coverage:**
- Configuration management
- Model manager logic
- Utility functions
- Data validation

**When to run:**
- Before every commit
- During development
- In CI/CD pipeline

### 2. CLI Regression Tests (Semi-Automated)

**Location:** `tests/run_regression_tests.sh`

**Run with:**
```bash
./tests/run_regression_tests.sh
```

**Coverage:**
- All CLI commands
- Error handling
- Output formats (text, JSON)
- Edge cases

**When to run:**
- Before releases
- After CLI changes
- Weekly during active development

### 3. GUI Regression Tests (Manual)

**Location:** `docs/GUI_REGRESSION_TEST.md`

**Process:**
1. Start GUI: `open gui-macos/.build/x86_64-apple-macosx/debug/llamacpp-gui`
2. Follow checklist in GUI_REGRESSION_TEST.md
3. Document results in checklist
4. Report issues

**Coverage:**
- All GUI buttons and controls
- Window behavior
- Visual feedback
- User interactions

**When to run:**
- Before releases
- After GUI changes
- After any Swift code changes

### 4. Integration Tests (Manual + Automated)

**Location:** `docs/INTEGRATION_REGRESSION_TEST.md`

**Coverage:**
- GUI + CLI interactions
- File system integration
- Process management
- Network behavior
- Data persistence

**When to run:**
- Before releases
- After major changes
- Monthly during active development

## Pre-Release Testing Checklist

### Week Before Release

- [ ] Run all unit tests: `pytest tests/ -v`
- [ ] Run CLI regression: `./tests/run_regression_tests.sh`
- [ ] Review and update test documentation
- [ ] Set up clean test environment

### 3 Days Before Release

- [ ] Complete GUI regression testing (GUI_REGRESSION_TEST.md)
- [ ] Complete CLI regression testing (CLI_REGRESSION_TEST.md)
- [ ] Document all issues found
- [ ] Create bug fix tasks

### 1 Day Before Release

- [ ] Complete integration testing (INTEGRATION_REGRESSION_TEST.md)
- [ ] Verify all critical bugs are fixed
- [ ] Re-run failed tests
- [ ] Update CHANGELOG with test results

### Release Day

- [ ] Final smoke test of critical paths
- [ ] Verify version numbers are correct
- [ ] Test installation on clean system
- [ ] Archive test results

## Test Environment Setup

### Prerequisites

```bash
# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Swift environment
cd gui-macos
swift build

# Clean slate for testing
rm -rf ~/.config/llamacpp-manager/
rm -rf ~/Library/Logs/llamaCPPManager/
rm -rf ~/Library/Application\ Support/llamaCPPManager/
```

### Test Data

Create test models configuration:
```bash
llamacpp-manager config add test-model1 ~/llms/test-model1/ --port 8081
llamacpp-manager config add test-model2 ~/llms/test-model2/ --port 8082
```

### Clean Up After Testing

```bash
# Stop all models
llamacpp-manager stop all

# Remove test configuration
rm -rf ~/.config/llamacpp-manager/config.json.test

# Clean logs
rm -rf ~/Library/Logs/llamaCPPManager/*.test.log
```

## Continuous Integration

### GitHub Actions Workflow (Recommended)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pytest
      - name: Run unit tests
        run: pytest tests/ -v

  cli-regression:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .
      - name: Run CLI regression tests
        run: ./tests/run_regression_tests.sh

  swift-build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Swift GUI
        run: |
          cd gui-macos
          swift build
```

## Bug Reporting Template

When tests fail, use this template:

```markdown
## Bug Report

**Test:** [Test name from checklist]
**Severity:** Critical / High / Medium / Low
**Reproducible:** Always / Sometimes / Rare

### Steps to Reproduce:
1.
2.
3.

### Expected Behavior:


### Actual Behavior:


### Environment:
- OS: macOS [version]
- GUI Build: [debug/release]
- CLI Version: [version]
- Git Commit: [hash]

### Logs:
```
[Paste relevant logs]
```

### Screenshots:
[If applicable]
```

## Test Metrics

Track these metrics for each release:

- **Unit Test Coverage:** Target 80%+
- **CLI Regression Pass Rate:** Target 100%
- **GUI Regression Pass Rate:** Target 95%+
- **Integration Test Pass Rate:** Target 90%+
- **Critical Bugs at Release:** Target 0
- **Known Issues:** Document in CHANGELOG

## Testing Best Practices

### For Developers

1. **Write tests first** (TDD when possible)
2. **Run unit tests before commit**
3. **Update tests when changing functionality**
4. **Document breaking changes in tests**
5. **Add regression tests for bug fixes**

### For Testers

1. **Follow checklists completely**
2. **Document every issue found**
3. **Include reproduction steps**
4. **Test on clean environment**
5. **Verify fixes thoroughly**

### For Release Managers

1. **Require passing tests before merge**
2. **Archive test results for each release**
3. **Track test metrics over time**
4. **Review test coverage regularly**
5. **Update test documentation**

## Common Issues and Solutions

### Tests Fail Due to Environment

**Problem:** Tests pass locally but fail in CI
**Solution:** Ensure environment variables are set, dependencies are installed, and permissions are correct

### GUI Tests Can't Be Automated

**Problem:** GUI testing is manual and time-consuming
**Solution:** Consider adding XCTest UI tests for critical paths

### Flaky Tests

**Problem:** Tests pass sometimes but fail randomly
**Solution:** Identify timing issues, race conditions, or external dependencies

### Slow Test Suite

**Problem:** Tests take too long to run
**Solution:** Parallelize tests, mock external services, optimize test data

## Future Improvements

- [ ] Add XCTest UI tests for Swift GUI
- [ ] Implement snapshot testing for GUI
- [ ] Add performance benchmarking tests
- [ ] Create Docker-based test environment
- [ ] Implement mutation testing
- [ ] Add load testing for concurrent operations
- [ ] Create visual regression testing

## Contact

For questions about testing:
- Email: libor@arionetworks.com
- Issues: https://github.com/arionrepo/llamaCPPManager/issues
