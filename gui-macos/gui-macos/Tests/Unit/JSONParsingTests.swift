import XCTest
@testable import llamacpp_gui

final class JSONParsingTests: XCTestCase {
    func testDecodeStatusRows() throws {
        let json = """
        [
          {"name":"m1","pid":123,"host":"127.0.0.1","port":8081,"up":true,"latency_ms":5,"http_status":200,"version":"llama.cpp","mode":"direct","log_path":"/tmp/m1.log"}
        ]
        """.data(using: .utf8)!
        let rows = try JSONDecoder().decode([StatusRow].self, from: json)
        XCTAssertEqual(rows.count, 1)
        XCTAssertEqual(rows[0].name, "m1")
        XCTAssertTrue(rows[0].up)
    }
}

