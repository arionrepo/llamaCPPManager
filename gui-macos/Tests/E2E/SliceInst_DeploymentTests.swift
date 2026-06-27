//
//  SliceInst_DeploymentTests.swift
//  llamacpp-gui — E2E vertical slice Inst
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Tests/E2E/SliceInst_DeploymentTests.swift
//  Description: Real-shell deployment/install tests for gui-macos/install_gui.sh.
//               Uses env overrides to exercise the real installer logic against
//               temp app bundles and temp install locations without writing into
//               /Applications during the test run.
//

import Testing
import Foundation

@Suite("E2E Slice Inst — GUI Installer")
struct SliceInst_DeploymentTests {

    @Test("install-gui --no-launch installs to override path")
    func installGuiNoLaunch() async throws {
        let harness = try InstallGuiHarness()
        try harness.createBuildArtifact(version: "2026.06.25.1", contents: "build-a")

        let result = try harness.run(["--no-rebuild", "--no-launch"])

        #expect(result.status == 0, "stdout:\n\(result.stdout)\nstderr:\n\(result.stderr)")
        #expect(FileManager.default.fileExists(atPath: harness.installedExecutable.path))
        #expect(result.stdout.contains("Installed:"))
        #expect(result.stdout.contains("(skipping launch per --no-launch)"))
    }

    @Test("install-gui --no-rebuild does not invoke build script")
    func installGuiNoRebuildSkipsBuildScript() async throws {
        let harness = try InstallGuiHarness()
        try harness.createBuildArtifact(version: "2026.06.25.1", contents: "build-b")
        try harness.installMarker.write(to: harness.buildScriptMarker, atomically: true, encoding: .utf8)
        try FileManager.default.removeItem(at: harness.buildScriptMarker)

        let result = try harness.run(["--no-rebuild", "--no-launch"])

        #expect(result.status == 0, "stdout:\n\(result.stdout)\nstderr:\n\(result.stderr)")
        #expect(!FileManager.default.fileExists(atPath: harness.buildScriptMarker.path))
    }

    @Test("install-gui --force invokes build script")
    func installGuiForceRebuilds() async throws {
        let harness = try InstallGuiHarness()
        try harness.createBuildArtifact(version: "2026.06.25.1", contents: "old-build")
        try harness.writeBuildScript(rebuildVersion: "2026.06.25.2", contents: "rebuilt")

        let result = try harness.run(["--force", "--no-launch"])

        #expect(result.status == 0, "stdout:\n\(result.stdout)\nstderr:\n\(result.stderr)")
        #expect(FileManager.default.fileExists(atPath: harness.buildScriptMarker.path))
        let installed = try String(contentsOf: harness.installedExecutable)
        #expect(installed == "rebuilt")
    }

    @Test("install-gui auto rebuilds when VERSION is newer than built binary")
    func installGuiDetectsStaleBuildViaVersionMtime() async throws {
        let harness = try InstallGuiHarness()
        try harness.createBuildArtifact(version: "2026.06.25.1", contents: "stale-build")
        try harness.writeBuildScript(rebuildVersion: "2026.06.25.3", contents: "fresh-build")

        let builtBin = harness.buildExecutable
        let oldDate = Date(timeIntervalSinceNow: -3600)
        try FileManager.default.setAttributes([.modificationDate: oldDate], ofItemAtPath: builtBin.path)
        try FileManager.default.setAttributes([.modificationDate: oldDate], ofItemAtPath: harness.sourceDir.appendingPathComponent("Placeholder.swift").path)
        let newDate = Date()
        try FileManager.default.setAttributes([.modificationDate: newDate], ofItemAtPath: harness.versionFile.path)

        let result = try harness.run(["--no-launch"])

        #expect(result.status == 0, "stdout:\n\(result.stdout)\nstderr:\n\(result.stderr)")
        #expect(FileManager.default.fileExists(atPath: harness.buildScriptMarker.path))
        #expect(result.stdout.contains("VERSION newer than built binary; will rebuild"))
    }
}

private struct InstallGuiHarness {
    let root: URL
    let buildApp: URL
    let buildExecutable: URL
    let installedApp: URL
    let installedExecutable: URL
    let buildScript: URL
    let buildScriptMarker: URL
    let sourceDir: URL
    let versionFile: URL
    let installMarker = "build-script-ran"

    init() throws {
        let fm = FileManager.default
        root = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        buildApp = root.appendingPathComponent("build/Test App.app")
        buildExecutable = buildApp.appendingPathComponent("Contents/MacOS/llamacpp-gui")
        installedApp = root.appendingPathComponent("Applications/Test App.app")
        installedExecutable = installedApp.appendingPathComponent("Contents/MacOS/llamacpp-gui")
        buildScript = root.appendingPathComponent("fake-build.sh")
        buildScriptMarker = root.appendingPathComponent("build-script-ran.txt")
        sourceDir = root.appendingPathComponent("Sources")
        versionFile = root.appendingPathComponent("VERSION")

        try fm.createDirectory(at: root, withIntermediateDirectories: true)
        try fm.createDirectory(at: sourceDir, withIntermediateDirectories: true)
        try "struct Placeholder {}".write(to: sourceDir.appendingPathComponent("Placeholder.swift"), atomically: true, encoding: .utf8)
        try "2026.06.25.1".write(to: versionFile, atomically: true, encoding: .utf8)
    }

    func createBuildArtifact(version: String, contents: String) throws {
        let fm = FileManager.default
        try fm.createDirectory(at: buildExecutable.deletingLastPathComponent(), withIntermediateDirectories: true)
        try contents.write(to: buildExecutable, atomically: true, encoding: .utf8)
        try fm.setAttributes([.posixPermissions: 0o755], ofItemAtPath: buildExecutable.path)
        let plist = buildApp.appendingPathComponent("Contents/Info.plist")
        let plistText = """
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0"><dict><key>CFBundleShortVersionString</key><string>\(version)</string></dict></plist>
        """
        try plistText.write(to: plist, atomically: true, encoding: .utf8)
    }

    func writeBuildScript(rebuildVersion: String, contents: String) throws {
        let script = """
        #!/bin/bash
        set -euo pipefail
        mkdir -p "\(buildExecutable.deletingLastPathComponent().path)"
        printf '%s' "\(contents)" > "\(buildExecutable.path)"
        chmod +x "\(buildExecutable.path)"
        cat > "\(buildApp.appendingPathComponent("Contents/Info.plist").path)" <<'EOF'
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0"><dict><key>CFBundleShortVersionString</key><string>\(rebuildVersion)</string></dict></plist>
        EOF
        printf '%s' "\(installMarker)" > "\(buildScriptMarker.path)"
        """
        try script.write(to: buildScript, atomically: true, encoding: .utf8)
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: buildScript.path)
    }

    func run(_ arguments: [String]) throws -> (status: Int32, stdout: String, stderr: String) {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/bin/bash")
        let installScript = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("install_gui.sh")
        proc.arguments = [installScript.path] + arguments
        var env = ProcessInfo.processInfo.environment
        env["INSTALL_GUI_APP_NAME"] = "Test App"
        env["INSTALL_GUI_BUILD_APP"] = buildApp.path
        env["INSTALL_GUI_INSTALL_APP"] = installedApp.path
        env["INSTALL_GUI_BUILD_SCRIPT"] = buildScript.path
        env["INSTALL_GUI_SOURCE_DIR"] = sourceDir.path
        env["INSTALL_GUI_VERSION_FILE"] = versionFile.path
        env["INSTALL_GUI_PROCESS_PATTERN"] = "definitely-not-a-real-process"
        env["INSTALL_GUI_SKIP_PROCESS_CLEANUP"] = "true"
        proc.environment = env
        proc.currentDirectoryURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)

        let out = Pipe()
        let err = Pipe()
        proc.standardOutput = out
        proc.standardError = err
        try proc.run()
        proc.waitUntilExit()
        let stdout = String(data: out.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let stderr = String(data: err.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        return (proc.terminationStatus, stdout, stderr)
    }
}
