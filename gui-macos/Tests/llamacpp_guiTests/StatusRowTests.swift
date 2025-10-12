import XCTest
@testable import llamacpp_gui

final class StatusRowTests: XCTestCase {
    func testStatusRowInitializer() {
        let row = StatusRow(
            name: "test-model",
            pid: 1234,
            host: "localhost",
            port: 8080,
            up: true,
            latency_ms: 50,
            http_status: 200,
            version: "1.0.0",
            mode: "chat",
            log_path: "/path/to/log",
            health_state: "ok",
            uptime: "1d 2h"
        )

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
    }

    func testStatusRowCodingKeys() {
        let codingKeys = StatusRow.CodingKeys.allCases.map { $0.rawValue }

        let expectedKeys = [
            "name",
            "pid",
            "host",
            "port",
            "up",
            "latency_ms",
            "http_status",
            "version",
            "mode",
            "log_path",
            "health_state",
            "uptime"
        ]

        XCTAssertEqual(Set(codingKeys), Set(expectedKeys))
    }
}