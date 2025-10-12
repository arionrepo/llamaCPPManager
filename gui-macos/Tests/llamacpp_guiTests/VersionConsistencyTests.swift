import XCTest
@testable import llamacpp_gui

class VersionConsistencyTests: XCTestCase {
    func testAboutTextVersionMatchesGitTag() {
        // Get the latest git tag
        let process = Process()
        process.launchPath = "/usr/bin/git"
        process.arguments = ["describe", "--tags", "--abbrev=0"]

        let pipe = Pipe()
        process.standardOutput = pipe

        do {
            try process.run()
            process.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            guard let gitTag = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) else {
                XCTFail("Could not read git tag")
                return
            }

            // Remove the 'v' prefix if present
            let expectedVersion = gitTag.hasPrefix("v") ? String(gitTag.dropFirst()) : gitTag

            // Get the version from the AboutView constant
            let aboutText = """
                llamaCPP Manager v\(APP_VERSION)

                A toolkit for managing local llama.cpp server instances on macOS.

                Features:
                • Multiple model management
                • Menu bar integration
                • Built-in chat interface
                • CLI automation
                • Container & Kubernetes support

                GitHub: https://github.com/your-username/llamacpp-manager
                """

            // Extract version from aboutText
            let aboutTextVersion = APP_VERSION

            // Assert that the versions match
            XCTAssertEqual(
                aboutTextVersion,
                expectedVersion,
                "AboutView version (\(aboutTextVersion)) does not match the latest git tag (\(expectedVersion))"
            )

        } catch {
            XCTFail("Failed to run git command: \(error)")
        }
    }

    func testAppVersionMatchesGitTag() {
        // Similar to above, but checks the entire version string including 'v'
        let process = Process()
        process.launchPath = "/usr/bin/git"
        process.arguments = ["describe", "--tags", "--abbrev=0"]

        let pipe = Pipe()
        process.standardOutput = pipe

        do {
            try process.run()
            process.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            guard let gitTag = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) else {
                XCTFail("Could not read git tag")
                return
            }

            // Check Bundle version (from Info.plist)
            guard let infoPlist = Bundle.main.infoDictionary,
                  let bundleVersion = infoPlist["CFBundleShortVersionString"] as? String else {
                XCTFail("Could not read bundle version")
                return
            }

            // Assert that the versions match (removing 'v' if present)
            let cleanGitTag = gitTag.hasPrefix("v") ? String(gitTag.dropFirst()) : gitTag
            let cleanBundleVersion = bundleVersion.hasPrefix("v") ? String(bundleVersion.dropFirst()) : bundleVersion

            XCTAssertEqual(
                cleanBundleVersion,
                cleanGitTag,
                "Bundle version (\(bundleVersion)) does not match the latest git tag (\(gitTag))"
            )

        } catch {
            XCTFail("Failed to run git command: \(error)")
        }
    }
}