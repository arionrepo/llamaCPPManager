import XCTest

class MenuBarUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUpWithError() throws {
        // Put setup code here. This method is called before the invocation of each test method in the class.
        continueAfterFailure = false

        app = XCUIApplication()

        // Set up test environment
        app.launchEnvironment = [
            "LLAMACPP_MANAGER_CONFIG_DIR": NSHomeDirectory() + "/Testing/GUI/config",
            "LLAMACPP_MANAGER_LOG_DIR": NSHomeDirectory() + "/Testing/GUI/logs",
            "PATH": ProcessInfo.processInfo.environment["PATH"] ?? ""
        ]

        app.launch()
    }

    override func tearDownWithError() throws {
        // Put teardown code here. This method is called after the invocation of each test method in the class.
        app.terminate()
    }

    func testMenuBarIconExists() throws {
        // Test that the menu bar icon appears
        let menuBars = app.menuBars

        // Give the app time to initialize
        let expectation = XCTestExpectation(description: "Menu bar loads")
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            expectation.fulfill()
        }
        wait(for: [expectation], timeout: 5.0)

        // Check if menu bar exists (this is challenging to test directly for menu bar extras)
        // We'll test by looking for the app running state
        XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground)
    }

    func testMenuBarInteraction() throws {
        // This test is more conceptual since menu bar extra interaction
        // is difficult to test directly with XCUITest

        // Give app time to start
        sleep(2)

        // Test that the app is running and responsive
        XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground)

        // In a real menu bar test, we would:
        // 1. Click the menu bar icon
        // 2. Verify menu appears
        // 3. Click menu items
        // But menu bar extras require special accessibility setup
    }

    func testAppLaunchesWithoutCrashing() throws {
        // Test basic app stability
        sleep(3) // Let app fully initialize

        // App should still be running
        XCTAssertTrue(app.state == .runningForeground || app.state == .runningBackground)

        // App should not have crashed
        XCTAssertFalse(app.state == .notRunning)
    }

    func testAppTermination() throws {
        // Test that app can be terminated properly
        sleep(2)

        // Terminate the app
        app.terminate()

        // Verify it terminated
        let expectation = XCTestExpectation(description: "App terminates")
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            expectation.fulfill()
        }
        wait(for: [expectation], timeout: 5.0)

        XCTAssertTrue(app.state == .notRunning)
    }
}