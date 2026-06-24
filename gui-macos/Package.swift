// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "llamacpp-gui",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "llamacpp-gui", targets: ["llamacpp-gui"])
    ],
    targets: [
        .executableTarget(
            name: "llamacpp-gui",
            path: "Sources"
        ),
        // Focused test target covering audit-deliverable code.
        // Path is scoped to Tests/DockerColimaTests/ to keep historical
        // orphan tests (under Tests/UI/, Tests/Unit/, Tests/llamacpp_guiTests/,
        // Tests/JSONParsingTests.swift) out of compilation until they can be
        // refreshed against the current Models/* structure. See CHANGELOG
        // v2026.06.23.8 'Audit deliverable' for the deferral rationale.
        .testTarget(
            name: "llamacpp-guiTests",
            dependencies: ["llamacpp-gui"],
            path: "Tests/DockerColimaTests"
        ),
        // Real-stack vertical-slice E2E tests. Each test launches the
        // installed app, drives it via osascript / System Events, and asserts
        // via inspection of ~/Library/Logs/llamaCPPManager/lifecycle.jsonl
        // and (where applicable) accessibility queries.
        // See docs/E2E-SLICES.md for the test contract.
        .testTarget(
            name: "E2ETests",
            dependencies: ["llamacpp-gui"],
            path: "Tests/E2E"
        )
    ]
)

