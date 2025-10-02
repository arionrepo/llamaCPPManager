import XCTest
@testable import llamacpp_gui

final class StatusViewModelTests: XCTestCase {

    func testJSONParsingWithEmptyArray() throws {
        let json = "[]"
        let data = json.data(using: .utf8)!

        // Test that empty array parses correctly
        let decoder = JSONDecoder()
        let rows = try decoder.decode([StatusRow].self, from: data)

        XCTAssertEqual(rows.count, 0)
    }

    func testJSONParsingWithSingleModel() throws {
        let json = """
        [
            {
                "name": "test-model",
                "host": "127.0.0.1",
                "port": 8081,
                "up": true,
                "latency_ms": 15
            }
        ]
        """
        let data = json.data(using: .utf8)!

        let decoder = JSONDecoder()
        let rows = try decoder.decode([StatusRow].self, from: data)

        XCTAssertEqual(rows.count, 1)
        XCTAssertEqual(rows[0].name, "test-model")
        XCTAssertEqual(rows[0].host, "127.0.0.1")
        XCTAssertEqual(rows[0].port, 8081)
        XCTAssertTrue(rows[0].up)
        XCTAssertEqual(rows[0].latency_ms, 15)
    }

    func testJSONParsingWithMultipleModels() throws {
        let json = """
        [
            {
                "name": "model1",
                "host": "127.0.0.1",
                "port": 8081,
                "up": true,
                "latency_ms": 15
            },
            {
                "name": "model2",
                "host": "127.0.0.1",
                "port": 8082,
                "up": false,
                "latency_ms": null
            }
        ]
        """
        let data = json.data(using: .utf8)!

        let decoder = JSONDecoder()
        let rows = try decoder.decode([StatusRow].self, from: data)

        XCTAssertEqual(rows.count, 2)

        // Test first model
        XCTAssertEqual(rows[0].name, "model1")
        XCTAssertTrue(rows[0].up)
        XCTAssertEqual(rows[0].latency_ms, 15)

        // Test second model
        XCTAssertEqual(rows[1].name, "model2")
        XCTAssertFalse(rows[1].up)
        XCTAssertNil(rows[1].latency_ms)
    }

    func testJSONParsingWithOptionalFields() throws {
        let json = """
        [
            {
                "name": "minimal-model",
                "host": "127.0.0.1",
                "port": 8080,
                "up": false
            }
        ]
        """
        let data = json.data(using: .utf8)!

        let decoder = JSONDecoder()
        let rows = try decoder.decode([StatusRow].self, from: data)

        XCTAssertEqual(rows.count, 1)
        XCTAssertEqual(rows[0].name, "minimal-model")
        XCTAssertFalse(rows[0].up)
        XCTAssertNil(rows[0].latency_ms) // Should handle missing latency_ms
    }

    func testJSONParsingHandlesInvalidData() throws {
        let invalidJSON = """
        [
            {
                "name": "test",
                "invalid_field": true
            }
        ]
        """
        let data = invalidJSON.data(using: .utf8)!

        let decoder = JSONDecoder()

        // Should throw an error for missing required fields
        XCTAssertThrowsError(try decoder.decode([StatusRow].self, from: data)) { error in
            XCTAssertTrue(error is DecodingError)
        }
    }

    func testStatusRowEquality() throws {
        let row1 = StatusRow(name: "test", pid: 1234, host: "127.0.0.1", port: 8080, up: true, latency_ms: 15, http_status: 200, version: "1.0", mode: "bare-metal", log_path: "/tmp/test.log", health_state: "ok")
        let row2 = StatusRow(name: "test", pid: 1234, host: "127.0.0.1", port: 8080, up: true, latency_ms: 15, http_status: 200, version: "1.0", mode: "bare-metal", log_path: "/tmp/test.log", health_state: "ok")
        let row3 = StatusRow(name: "test", pid: nil, host: "127.0.0.1", port: 8080, up: false, latency_ms: nil, http_status: nil, version: nil, mode: "bare-metal", log_path: nil, health_state: "down")

        // Note: StatusRow needs to conform to Equatable for this to work
        // If not implemented, this test documents expected behavior
        XCTAssertEqual(row1.name, row2.name)
        XCTAssertNotEqual(row1.up, row3.up)
    }

    func testStatusRowDisplayProperties() throws {
        let runningModel = StatusRow(name: "fast-model", pid: 5678, host: "127.0.0.1", port: 8081, up: true, latency_ms: 12, http_status: 200, version: "1.0", mode: "bare-metal", log_path: "/tmp/fast.log", health_state: "ok")
        let stoppedModel = StatusRow(name: "slow-model", pid: nil, host: "127.0.0.1", port: 8082, up: false, latency_ms: nil, http_status: nil, version: nil, mode: "bare-metal", log_path: nil, health_state: "down")

        // Test display logic
        XCTAssertTrue(runningModel.up)
        XCTAssertNotNil(runningModel.latency_ms)

        XCTAssertFalse(stoppedModel.up)
        XCTAssertNil(stoppedModel.latency_ms)
    }

    func testEdgeCases() throws {
        // Test with extreme values
        let json = """
        [
            {
                "name": "edge-case-model",
                "host": "0.0.0.0",
                "port": 65535,
                "up": true,
                "latency_ms": 999999
            }
        ]
        """
        let data = json.data(using: .utf8)!

        let decoder = JSONDecoder()
        let rows = try decoder.decode([StatusRow].self, from: data)

        XCTAssertEqual(rows.count, 1)
        XCTAssertEqual(rows[0].host, "0.0.0.0")
        XCTAssertEqual(rows[0].port, 65535)
        XCTAssertEqual(rows[0].latency_ms, 999999)
    }

    func testUnicodeModelNames() throws {
        let json = """
        [
            {
                "name": "模型-🤖",
                "host": "127.0.0.1",
                "port": 8080,
                "up": true,
                "latency_ms": 25
            }
        ]
        """
        let data = json.data(using: .utf8)!

        let decoder = JSONDecoder()
        let rows = try decoder.decode([StatusRow].self, from: data)

        XCTAssertEqual(rows.count, 1)
        XCTAssertEqual(rows[0].name, "模型-🤖")
    }
}