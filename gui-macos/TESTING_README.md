# llamaCPP Manager GUI - Automated Testing Suite

Complete automated testing setup using **XCUITest** (Apple's free testing framework) and integration scripts.

## 🧪 Test Structure

```
gui-macos/
├── Tests/
│   ├── Unit/
│   │   ├── JSONParsingTests.swift      # JSON parsing tests (original)
│   │   └── StatusViewModelTests.swift  # Enhanced ViewModel tests
│   ├── UI/
│   │   ├── MenuBarUITests.swift        # Basic UI stability tests
│   │   └── MenuInteractionTests.swift  # Advanced UI interaction tests
│   └── integration_test.sh             # CLI-GUI integration testing
├── run_all_tests.sh                    # Master test runner
└── Package.swift                       # Updated with UI test target
```

## 🚀 Quick Start

### Run All Tests
```bash
cd gui-macos
./run_all_tests.sh
```

### Run Specific Test Suites
```bash
# Just build test
./run_all_tests.sh build

# Unit tests only
./run_all_tests.sh unit

# UI tests only (may require accessibility permissions)
./run_all_tests.sh ui

# Integration tests only
./run_all_tests.sh integration

# Help
./run_all_tests.sh help
```

## 📋 Test Categories

### **1. Unit Tests** ✅ Ready
**Location:** `Tests/Unit/`
**What they test:**
- JSON parsing with various data formats
- StatusRow data model validation
- Edge cases and error handling
- Unicode support

**Run:** `swift test --filter llamacpp-guiTests`

### **2. UI Tests** ⚠️ May Require Setup
**Location:** `Tests/UI/`
**What they test:**
- App launch and stability
- Menu bar integration
- Error handling (missing config, invalid config)
- Memory leak detection
- Accessibility compliance

**Requirements:**
- macOS 13+
- Accessibility permissions for Terminal (if running via command line)
- Or run from Xcode for better environment

**Run:** `swift test --filter llamacpp-guiUITests`

### **3. Integration Tests** ✅ Ready
**Location:** `Tests/integration_test.sh`
**What they test:**
- CLI setup → GUI launch → interaction cycle
- Real-time updates between CLI and GUI
- Configuration changes while GUI running
- Memory usage over time
- Error recovery

**Run:** `bash Tests/integration_test.sh`

## 🛠️ Prerequisites

### Required
- ✅ **Swift/Xcode** (free from Mac App Store)
- ✅ **llamacpp-manager CLI** (`.venv/bin/llamacpp-manager`)

### Optional (for UI Tests)
- **Accessibility permissions** for Terminal app
- **macOS 13+** for full UI test support

## 🎯 Test Coverage

| Component | Unit Tests | UI Tests | Integration |
|-----------|------------|----------|-------------|
| JSON Parsing | ✅ | - | ✅ |
| App Launch | - | ✅ | ✅ |
| Menu Bar | - | ⚠️ | ✅ |
| CLI Integration | - | - | ✅ |
| Error Handling | ✅ | ✅ | ✅ |
| Memory Leaks | - | ✅ | ✅ |
| Config Changes | ✅ | ✅ | ✅ |

**Legend:**
- ✅ Fully tested
- ⚠️ Basic coverage (menu bar testing is challenging)
- `-` Not applicable

## 🔧 Running from Xcode (Recommended for UI Tests)

1. **Open Package:**
   ```bash
   open gui-macos/Package.swift
   ```

2. **Set Scheme:** Select "llamacpp-gui" scheme

3. **Add Environment Variables** (Product → Scheme → Edit Scheme → Arguments):
   - `LLAMACPP_MANAGER_CONFIG_DIR`: `~/Testing/llamacpp-config`
   - `LLAMACPP_MANAGER_LOG_DIR`: `~/Testing/llamacpp-logs`
   - `PATH`: `/path/to/.venv/bin:$PATH`

4. **Run Tests:** Product → Test (⌘U)

## 🐛 Troubleshooting

### "UI Tests Fail"
```bash
# Grant accessibility permissions:
System Preferences → Security & Privacy → Privacy → Accessibility
# Add Terminal.app and Xcode.app
```

### "CLI Not Found"
```bash
# Verify CLI installation
ls -la ../.venv/bin/llamacpp-manager

# If missing, install CLI first:
cd .. && pip install -e .
```

### "Menu Bar Tests Don't Work"
Menu bar testing is inherently challenging because:
- Menu bar items require special accessibility setup
- System-level UI elements have restricted access
- XCUITest has limited menu bar support

**Workaround:** Our tests focus on:
- App stability (does it crash?)
- Process lifecycle (start/stop properly?)
- Integration with CLI (real-world usage)

### "Integration Tests Fail"
```bash
# Check permissions
ls -la Tests/integration_test.sh  # Should be executable

# Run manually for debugging
cd gui-macos
bash Tests/integration_test.sh
```

## 📊 Interpreting Test Results

### ✅ Success Output
```
[INFO] All tests passed! 🎉

Test Summary
============
Build: ✅
Unit Tests: ✅
UI Tests: ✅
Integration Tests: ✅
```

### ❌ Failure Output
```
[ERROR] Failed test suites: UI Tests

# Check specific error:
swift test --filter llamacpp-guiUITests --verbose
```

### ⚠️ Partial Success
```
[WARN] UI tests failed or require accessibility permissions ⚠️
[INFO] All other tests passed! ✅
```
This is acceptable - UI tests are optional and challenging to set up.

## 🔄 Continuous Integration

### GitHub Actions Example
```yaml
# .github/workflows/gui-tests.yml
name: GUI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest
    steps:
    - uses: actions/checkout@v3
    - name: Install CLI
      run: pip install -e .
    - name: Run GUI Tests
      run: |
        cd gui-macos
        ./run_all_tests.sh unit integration
        # Note: UI tests skipped in CI (require GUI environment)
```

## 🎖️ Test Quality Standards

### Passing Criteria
- ✅ **Build:** No compilation errors or warnings
- ✅ **Unit Tests:** All assertions pass, 100% success rate
- ⚠️ **UI Tests:** Basic app stability (menu bar interaction optional)
- ✅ **Integration:** Full CLI-GUI workflow works end-to-end

### Performance Criteria
- **Startup Time:** App launches within 5 seconds
- **Memory Usage:** No more than 2x growth during testing
- **Stability:** No crashes during 30+ second runs

## 💡 Extending Tests

### Add New Unit Test
```swift
// Tests/Unit/YourNewTests.swift
import XCTest
@testable import llamacpp_gui

final class YourNewTests: XCTestCase {
    func testYourFeature() {
        // Your test here
        XCTAssertTrue(true)
    }
}
```

### Add New UI Test
```swift
// Tests/UI/YourUITests.swift
import XCTest

class YourUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUpWithError() throws {
        app = XCUIApplication()
        app.launch()
    }

    func testYourUIFeature() {
        // Your UI test here
    }
}
```

### Add Integration Test Step
```bash
# In Tests/integration_test.sh, add new function:
test_your_feature() {
    log "Testing your feature..."
    # Your test logic here
    log "Your feature test passed"
}

# Add to run_all_tests function:
test_your_feature
```

---

## 🏆 Summary

You now have a **complete, free automated testing suite** for your SwiftUI GUI:

- **Free tools only** (XCUITest + shell scripts)
- **Comprehensive coverage** (unit + UI + integration)
- **Easy to run** (`./run_all_tests.sh`)
- **CI-ready** (works in automated environments)
- **Extensible** (easy to add new tests)

The testing approach balances thorough coverage with practical limitations of menu bar app testing, focusing on the most important aspects: **stability, integration, and user workflows**.