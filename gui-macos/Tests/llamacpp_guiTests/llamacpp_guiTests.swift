import XCTest
@testable import llamacpp_gui

final class LlamaCPPManagerTests: XCTestCase {
    func testStatusRowDecoding() {
        // Test the JSON decoding of StatusRow
        let jsonString = """
        {
            "name": "test-model",
            "pid": 1234,
            "host": "localhost",
            "port": 8080,
            "up": true,
            "latency_ms": 50,
            "http_status": 200,
            "version": "1.0.0",
            "mode": "chat",
            "log_path": "/path/to/log",
            "health_state": "ok",
            "uptime": "1d 2h"
        }
        """

        guard let jsonData = jsonString.data(using: .utf8) else {
            XCTFail("Failed to convert JSON string to data")
            return
        }

        do {
            let decoder = JSONDecoder()
            let row = try decoder.decode(StatusRow.self, from: jsonData)

            XCTAssertEqual(row.name, "test-model")
            XCTAssertEqual(row.pid, 1234)
            XCTAssertEqual(row.host, "localhost")
            XCTAssertEqual(row.port, 8080)
            XCTAssertEqual(row.up, true)
            XCTAssertEqual(row.latency_ms, 50)
            XCTAssertEqual(row.http_status, 200)
            XCTAssertEqual(row.version, "1.0.0")
            XCTAssertEqual(row.mode, "chat")
            XCTAssertEqual(row.log_path, "/path/to/log")
            XCTAssertEqual(row.health_state, "ok")
            XCTAssertEqual(row.uptime, "1d 2h")
        } catch {
            XCTFail("Failed to decode StatusRow: \(error)")
        }
    }

    func testInfrastructureRowDecoding() {
        // Test the JSON decoding of InfrastructureRow
        let jsonString = """
        {
            "name": "test-infra",
            "type": "controller",
            "enabled": true,
            "running": true,
            "healthy": true,
            "status": "active",
            "health_status": "running",
            "latency_ms": 25,
            "details": {"key": "value"},
            "uptime": "3d 4h"
        }
        """

        guard let jsonData = jsonString.data(using: .utf8) else {
            XCTFail("Failed to convert JSON string to data")
            return
        }

        do {
            let decoder = JSONDecoder()
            let row = try decoder.decode(InfrastructureRow.self, from: jsonData)

            XCTAssertEqual(row.name, "test-infra")
            XCTAssertEqual(row.type, "controller")
            XCTAssertEqual(row.enabled, true)
            XCTAssertEqual(row.running, true)
            XCTAssertEqual(row.healthy, true)
            XCTAssertEqual(row.status, "active")
            XCTAssertEqual(row.health_status, "running")
            XCTAssertEqual(row.latency_ms, 25)
            XCTAssertEqual(row.uptime, "3d 4h")

            // Verify details
            XCTAssertNotNil(row.details)

            // Check the details dictionary directly
            XCTAssertTrue(row.details?.keys.contains("key") == true)
            XCTAssertEqual(row.details?["key"]?.value as? String, "value")
        } catch {
            XCTFail("Failed to decode InfrastructureRow: \(error)")
        }
    }
}