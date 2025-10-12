import XCTest
@testable import llamacpp_gui

final class InfrastructureRowTests: XCTestCase {
    func testInfrastructureRowInitializer() {
        let row = InfrastructureRow(
            name: "test-infra",
            type: "controller",
            enabled: true,
            running: true,
            healthy: true,
            status: "active",
            health_status: "running",
            latency_ms: 25,
            details: ["key": AnyCodable("value")],
            uptime: "3d 4h"
        )

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
        XCTAssertTrue(row.details?.keys.contains("key") == true)
        XCTAssertEqual(row.details?["key"]?.value as? String, "value")
    }

    func testInfrastructureRowCodingKeys() {
        let codingKeys = InfrastructureRow.CodingKeys.allCases.map { $0.rawValue }

        let expectedKeys = [
            "name",
            "type",
            "enabled",
            "running",
            "healthy",
            "status",
            "health_status",
            "latency_ms",
            "details",
            "uptime"
        ]

        XCTAssertEqual(Set(codingKeys), Set(expectedKeys))
    }
}