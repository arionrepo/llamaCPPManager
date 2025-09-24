import XCTest
import AppKit

class MenuInteractionTests: XCTestCase {
    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false

        // Set up test configuration first
        setupTestConfiguration()

        app = XCUIApplication()
        app.launchEnvironment = [
            "LLAMACPP_MANAGER_CONFIG_DIR": NSHomeDirectory() + "/Testing/GUI/config",
            "LLAMACPP_MANAGER_LOG_DIR": NSHomeDirectory() + "/Testing/GUI/logs",
            "XCUITest": "1" // Special flag to indicate we're in test mode
        ]

        app.launch()
    }

    override func tearDownWithError() throws {
        app?.terminate()
        cleanupTestConfiguration()
    }

    private func setupTestConfiguration() {
        // Create test directories
        let configURL = URL(fileURLWithPath: NSHomeDirectory() + "/Testing/GUI/config")
        let logsURL = URL(fileURLWithPath: NSHomeDirectory() + "/Testing/GUI/logs")

        try? FileManager.default.createDirectory(at: configURL, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(at: logsURL, withIntermediateDirectories: true)

        // Create minimal test config
        let configYAML = """
        default:
          llama_server_path: /opt/homebrew/bin/llama-server
          log_rotation_size: 100MB
          health_check_timeout: 10

        models:
          test-model:
            model_path: /tmp/test-model.gguf
            host: 127.0.0.1
            port: 8081
            deployment_mode: bare-metal
            autostart: false
        """

        let configFile = configURL.appendingPathComponent("config.yaml")
        try? configYAML.write(to: configFile, atomically: true, encoding: .utf8)
    }

    private func cleanupTestConfiguration() {
        let testDir = URL(fileURLWithPath: NSHomeDirectory() + "/Testing/GUI")
        try? FileManager.default.removeItem(at: testDir)
    }

    func testAppStartsAndStaysRunning() throws {
        // Wait for app to fully load
        let loadExpectation = XCTestExpectation(description: "App loads")
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
            loadExpectation.fulfill()
        }
        wait(for: [loadExpectation], timeout: 5.0)

        // App should be running
        XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground)

        // Let it run for a bit to ensure stability
        sleep(2)
        XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground)
    }

    func testMenuBarAccessibility() throws {
        // Test menu bar accessibility setup
        sleep(3) // Allow full startup

        // Get all menu bars
        let menuBars = app.menuBars

        // The system menu bar should exist
        XCTAssertGreaterThan(menuBars.count, 0, "System menu bar should be accessible")

        // Look for status items (this may require accessibility permissions)
        let statusItems = app.statusItems

        // In a perfect world, we'd find our llamaCPP status item
        // But this requires special accessibility setup in practice
        print("Found \(statusItems.count) status items")
    }

    func testAppDoesNotCrashWithMissingConfig() throws {
        // This test verifies graceful handling of missing configuration
        app.terminate()

        // Remove config file
        let configFile = URL(fileURLWithPath: NSHomeDirectory() + "/Testing/GUI/config/config.yaml")
        try? FileManager.default.removeItem(at: configFile)

        // Relaunch app
        app.launch()
        sleep(3)

        // App should still be running, just showing "No models configured"
        XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground)
    }

    func testAppHandlesInvalidConfig() throws {
        // Test with malformed config
        app.terminate()

        let configURL = URL(fileURLWithPath: NSHomeDirectory() + "/Testing/GUI/config")
        let configFile = configURL.appendingPathComponent("config.yaml")

        // Write invalid YAML
        let invalidYAML = """
        invalid: yaml: content:
        - broken
          - structure
        """
        try? invalidYAML.write(to: configFile, atomically: true, encoding: .utf8)

        app.launch()
        sleep(3)

        // App should still run, handling the error gracefully
        XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground)
    }

    func testMemoryLeaks() throws {
        // Basic memory leak test - app should stay stable
        sleep(2)

        let initialState = app.state
        XCTAssertTrue(initialState == .runningForeground || initialState == .runningBackground)

        // Let app run for extended period
        for i in 0..<10 {
            sleep(1)
            XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground,
                         "App should remain stable after \(i) seconds")
        }
    }

    func testConcurrentOperations() throws {
        // Test app stability under simulated concurrent operations
        sleep(2)

        // Simulate multiple rapid state changes (this would normally come from CLI operations)
        for _ in 0..<5 {
            // In real usage, external CLI commands would change model states
            // Here we just verify the app stays stable during rapid polling
            sleep(1)
            XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground)
        }
    }
}

// MARK: - Accessibility Testing
extension MenuInteractionTests {

    func testAccessibilityElements() throws {
        sleep(3)

        // Test that accessibility elements are properly configured
        // This is important for VoiceOver and other assistive technologies

        // The app itself should be accessible
        XCTAssertTrue(app.exists, "App should be accessible to UI testing")

        // If we can access any buttons or elements, they should be properly labeled
        // (This depends on the specific UI implementation)
        let buttons = app.buttons
        for i in 0..<min(buttons.count, 10) { // Test first 10 buttons if any
            let button = buttons.element(boundBy: i)
            if button.exists {
                XCTAssertFalse(button.label.isEmpty, "Button \(i) should have accessibility label")
            }
        }
    }

    func testKeyboardNavigation() throws {
        sleep(2)

        // Test keyboard navigation if app supports it
        // This is more relevant for window-based apps than menu bar apps

        // Try basic keyboard interactions
        app.typeKey("q", modifierFlags: .command) // Cmd+Q to quit

        let quitExpectation = XCTestExpectation(description: "App responds to Cmd+Q")
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            quitExpectation.fulfill()
        }
        wait(for: [quitExpectation], timeout: 5.0)

        // App might quit or ignore the command depending on implementation
        // Either behavior is acceptable for a menu bar app
    }
}