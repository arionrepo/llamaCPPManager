//
//  SliceD_StartStopTests.swift
//  llamacpp-gui — E2E vertical slice D.1
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Tests/E2E/SliceD_StartStopTests.swift
//  Description: Vertical-slice E2E for GUI start/stop against CLI status agreement. Builds an isolated one-model temp config from the user's real configuration, launches the installed app against that temp config, clicks Start and Stop from the GUI, and verifies `llamacpp-manager status --json` agrees after each transition.
//  Author: Codex
//  Created: 2026-06-25
//

import Testing
import Foundation

@Suite("E2E Slice D — GUI Start/Stop ↔ CLI Status Agreement")
struct SliceD_StartStopTests {

    @Test("GUI start then stop updates CLI status for one isolated native model")
    func guiStartStopMatchesCLIStatus() async throws {
        guard interactiveSlicesEnabled else {
            print(interactiveSkipMessage)
            return
        }

        let fixture = try makeIsolatedNativeFixture()
        let launchEnv = [
            "LLAMACPP_MANAGER_CONFIG_DIR": fixture.configDir.path,
            "LLAMACPP_MANAGER_LOG_DIR": fixture.logDir.path
        ]

        let proc = try launchApp(environment: launchEnv)
        defer {
            quitApp(proc)
            try? stopModel(name: fixture.modelName, env: launchEnv)
            try? FileManager.default.removeItem(at: fixture.rootDir)
        }

        let bootOffset = snapshotLogOffset()
        _ = try waitForLogEvent("ui.app.did_finish_launching",
                                after: bootOffset,
                                timeout: 15.0)
        _ = try waitForLogEvent("cli.status.fetched",
                                after: bootOffset,
                                timeout: 30.0)

        try clickStatusBarItem()
        try await Task.sleep(nanoseconds: 500_000_000)
        guard menuHasEnabledButton(named: "Start") else {
            print(menuAutomationSkipMessage)
            return
        }

        let preStart = snapshotLogOffset()
        try clickFirstEnabledButton(named: "Start")

        let started = try waitForLogEvent("ui.start.cli_result",
                                          after: preStart,
                                          timeout: 60.0)
        #expect(started["model"] as? String == fixture.modelName)
        #expect((started["exit_code"] as? Int) == 0)

        try waitForModelStatus(name: fixture.modelName, env: launchEnv, expectedUp: true, timeout: 90.0)

        try clickStatusBarItem()
        try await Task.sleep(nanoseconds: 500_000_000)

        let preStop = snapshotLogOffset()
        try clickFirstEnabledButton(named: "Stop")

        let stopped = try waitForLogEvent("ui.stop.cli_result",
                                          after: preStop,
                                          timeout: 30.0)
        #expect(stopped["model"] as? String == fixture.modelName)
        #expect((stopped["exit_code"] as? Int) == 0)

        try waitForModelStatus(name: fixture.modelName, env: launchEnv, expectedUp: false, timeout: 30.0)
    }
}

private struct NativeFixture {
    let rootDir: URL
    let configDir: URL
    let logDir: URL
    let modelName: String
}

private func makeIsolatedNativeFixture() throws -> NativeFixture {
    let rootDir = FileManager.default.temporaryDirectory.appendingPathComponent(
        "slice-d-\(UUID().uuidString)",
        isDirectory: true
    )
    let configDir = rootDir.appendingPathComponent("config", isDirectory: true)
    let logDir = rootDir.appendingPathComponent("logs", isDirectory: true)
    try FileManager.default.createDirectory(at: configDir, withIntermediateDirectories: true)
    try FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)

    let liveStatus = try cliJSON(["status", "--json"], env: [:])
    let liveConfig = try cliJSON(["config", "list", "--json"], env: [:])
    let model = try selectNativeCandidate(statusJSON: liveStatus, configJSON: liveConfig)

    let llamaServerPath = (liveConfig["llama_server_path"] as? String) ?? "/opt/homebrew/bin/llama-server"
    let yaml = renderFixtureConfigYAML(llamaServerPath: llamaServerPath, logDir: logDir.path, model: model)
    try yaml.write(to: configDir.appendingPathComponent("config.yaml"), atomically: true, encoding: .utf8)

    return NativeFixture(rootDir: rootDir, configDir: configDir, logDir: logDir, modelName: model.name)
}

private struct NativeModelSpec {
    let name: String
    let modelPath: String
    let host: String
    let port: Int
    let mode: String
    let deploymentType: String
    let args: [String]
    let env: [String: String]
    let autostart: Bool
    let ctxSize: Int?
    let nGpuLayers: Int?
}

private func selectNativeCandidate(statusJSON: [String: Any], configJSON: [String: Any]) throws -> NativeModelSpec {
    guard let statusRows = statusJSON["models"] as? [[String: Any]],
          let configRows = configJSON["models"] as? [[String: Any]] else {
        throw E2EError.launchFailed("Could not parse live model inventory")
    }

    let configByName = Dictionary(uniqueKeysWithValues: configRows.compactMap { row in
        (row["name"] as? String).map { ($0, row) }
    })

    let candidates = statusRows.compactMap { row -> (Double, NativeModelSpec)? in
        guard let name = row["name"] as? String,
              let cfg = configByName[name],
              (row["deployment_type"] as? String)?.lowercased() == "native",
              (row["up"] as? Bool) == false,
              let modelPath = cfg["model_path"] as? String,
              let host = cfg["host"] as? String,
              let port = cfg["port"] as? Int else {
            return nil
        }

        let fileSize = row["file_size_gb"] as? Double ?? Double.greatestFiniteMagnitude
        let spec = NativeModelSpec(
            name: name,
            modelPath: modelPath,
            host: host,
            port: port,
            mode: (cfg["mode"] as? String) ?? "basic",
            deploymentType: (cfg["deployment_type"] as? String) ?? "native",
            args: (cfg["args"] as? [String]) ?? [],
            env: (cfg["env"] as? [String: String]) ?? [:],
            autostart: (cfg["autostart"] as? Bool) ?? false,
            ctxSize: cfg["ctx_size"] as? Int,
            nGpuLayers: cfg["n_gpu_layers"] as? Int
        )
        return (fileSize, spec)
    }
    .sorted { lhs, rhs in
        if lhs.0 == rhs.0 { return lhs.1.name < rhs.1.name }
        return lhs.0 < rhs.0
    }

    guard let selected = candidates.first?.1 else {
        throw E2EError.launchFailed("No stopped native model candidate available for Slice D.1")
    }
    return selected
}

private func renderFixtureConfigYAML(llamaServerPath: String, logDir: String, model: NativeModelSpec) -> String {
    var lines = [
        "llama_server_path: \(yamlScalar(llamaServerPath))",
        "log_dir: \(yamlScalar(logDir))",
        "infrastructure: {}",
        "monitoring:",
        "  enabled: false",
        "models:",
        "  - name: \(yamlScalar(model.name))",
        "    model_path: \(yamlScalar(model.modelPath))",
        "    host: \(yamlScalar(model.host))",
        "    port: \(model.port)",
        "    deployment_type: \(yamlScalar(model.deploymentType))",
        "    mode: \(yamlScalar(model.mode))",
        "    autostart: \(model.autostart ? "true" : "false")",
        "    args:"
    ]

    if model.args.isEmpty {
        lines.append("      []")
    } else {
        for arg in model.args {
            lines.append("      - \(yamlScalar(arg))")
        }
    }

    lines.append("    env:")
    if model.env.isEmpty {
        lines.append("      {}")
    } else {
        for key in model.env.keys.sorted() {
            lines.append("      \(key): \(yamlScalar(model.env[key] ?? ""))")
        }
    }

    if let ctxSize = model.ctxSize {
        lines.append("    ctx_size: \(ctxSize)")
    }
    if let nGpuLayers = model.nGpuLayers {
        lines.append("    n_gpu_layers: \(nGpuLayers)")
    }

    return lines.joined(separator: "\n") + "\n"
}

private func yamlScalar(_ value: String) -> String {
    let escaped = value.replacingOccurrences(of: "\\", with: "\\\\")
        .replacingOccurrences(of: "\"", with: "\\\"")
    return "\"\(escaped)\""
}

private func cliJSON(_ args: [String], env: [String: String]) throws -> [String: Any] {
    let output = try cliCapture(args, env: env)
    guard let data = output.data(using: .utf8),
          let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        throw E2EError.launchFailed("Failed to decode CLI JSON for args: \(args)")
    }
    return object
}

private func cliCapture(_ args: [String], env: [String: String]) throws -> String {
    let proc = Process()
    proc.executableURL = URL(fileURLWithPath: "/opt/homebrew/bin/llamacpp-manager")
    proc.arguments = args
    proc.environment = ProcessInfo.processInfo.environment.merging(env) { _, new in new }
    let stdout = Pipe()
    let stderr = Pipe()
    proc.standardOutput = stdout
    proc.standardError = stderr
    try proc.run()
    proc.waitUntilExit()

    let stdoutText = String(data: stdout.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
    let stderrText = String(data: stderr.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
    guard proc.terminationStatus == 0 else {
        throw E2EError.launchFailed("CLI failed (\(proc.terminationStatus)): \(args.joined(separator: " ")) :: \(stderrText)")
    }
    return stdoutText
}

private func waitForModelStatus(name: String,
                                env: [String: String],
                                expectedUp: Bool,
                                timeout: TimeInterval) throws {
    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        let status = try cliJSON(["status", "--json"], env: env)
        if let models = status["models"] as? [[String: Any]],
           let row = models.first(where: { ($0["name"] as? String) == name }),
           let up = row["up"] as? Bool,
           up == expectedUp {
            return
        }
        Thread.sleep(forTimeInterval: 1.0)
    }
    throw E2EError.logTimeout(event: "status \(name) up=\(expectedUp)", after: timeout)
}

private func stopModel(name: String, env: [String: String]) throws {
    _ = try cliCapture(["stop", name], env: env)
}
