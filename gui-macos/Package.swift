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
        .testTarget(
            name: "llamacpp-guiTests",
            dependencies: ["llamacpp-gui"],
            path: "Tests"
        )
    ]
)

