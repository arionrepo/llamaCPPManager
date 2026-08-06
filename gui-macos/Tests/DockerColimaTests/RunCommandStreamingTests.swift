// File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Tests/DockerColimaTests/RunCommandStreamingTests.swift
// Description: Unit tests for DockerService.runCommandStreaming — covers
//              success, failure, output streaming, and cancellation paths.
//              Uses standard Unix utilities as subprocess proxies (no colima
//              dependency); tests run in ~2s total.
// Author: Libor Ballaty <libor@arionetworks.com>
// Created: 2026-06-23

import XCTest
@testable import llamacpp_gui

final class RunCommandStreamingTests: XCTestCase {
    func testResolveExecutableUsesPreferredDirectoriesWhenPATHIsMinimal() {
        let service = DockerService(environment: ["PATH": "/usr/bin:/bin:/usr/sbin:/sbin"])
        let url = service.resolveExecutableURL(for: "colima")
        XCTAssertEqual(url?.path, "/opt/homebrew/bin/colima")
    }

    // Regression: 2026-08-06 "no colima profiles found". A GUI app launched via
    // LaunchServices with a minimal PATH (no /opt/homebrew/bin) located the
    // `colima` binary (via preferredDirs) but then handed colima that same
    // minimal PATH; `colima list` execs `limactl` via $PATH and failed with
    // "executable file not found in $PATH", so the Infra tab showed no profiles.
    // environmentWithToolPath() must guarantee the Homebrew/tool dirs are on the
    // PATH given to the subprocess.
    func testEnvironmentWithToolPathPrependsHomebrewWhenPATHIsMinimal() {
        let service = DockerService(environment: ["PATH": "/usr/bin:/bin:/usr/sbin:/sbin"])
        let path = service.environmentWithToolPath()["PATH"] ?? ""
        let dirs = path.split(separator: ":").map(String.init)
        XCTAssertTrue(dirs.contains("/opt/homebrew/bin"),
                      "Homebrew bin must be on PATH so colima can find limactl; got: \(path)")
        // Prepended, not appended — tool dirs take precedence.
        XCTAssertEqual(dirs.first, "/opt/homebrew/bin",
                       "Tool dirs should be prepended; got: \(path)")
        // Original entries preserved.
        XCTAssertTrue(dirs.contains("/usr/bin"), "Original PATH entries must be preserved; got: \(path)")
    }

    func testEnvironmentWithToolPathDeduplicatesExistingEntries() {
        let service = DockerService(environment: ["PATH": "/opt/homebrew/bin:/usr/bin"])
        let path = service.environmentWithToolPath()["PATH"] ?? ""
        let count = path.split(separator: ":").filter { $0 == "/opt/homebrew/bin" }.count
        XCTAssertEqual(count, 1, "PATH must not contain duplicate /opt/homebrew/bin; got: \(path)")
    }

    func testEnvironmentWithToolPathSuppliesPATHWhenAbsent() {
        let service = DockerService(environment: [:])
        let path = service.environmentWithToolPath()["PATH"] ?? ""
        XCTAssertTrue(path.contains("/opt/homebrew/bin"),
                      "Even with no inherited PATH, tool dirs must be present; got: \(path)")
    }

    // End-to-end integration proof for the 2026-08-06 fix: construct DockerService
    // with the exact minimal PATH a LaunchServices-launched app can inherit (no
    // Homebrew dir) and call the REAL getColimaProfiles(). Before the fix this
    // returned [] because colima could not exec limactl; after the fix the PATH
    // augmentation lets colima succeed. Skipped on machines without colima+limactl
    // installed (i.e. not a real regression environment).
    func testGetColimaProfilesSucceedsUnderMinimalPATH() async throws {
        let fm = FileManager.default
        guard fm.isExecutableFile(atPath: "/opt/homebrew/bin/colima"),
              fm.isExecutableFile(atPath: "/opt/homebrew/bin/limactl") else {
            throw XCTSkip("colima/limactl not installed at /opt/homebrew/bin — integration test not applicable")
        }
        // The failing condition: minimal PATH, homebrew absent.
        let service = DockerService(environment: ["PATH": "/usr/bin:/bin:/usr/sbin:/sbin"])
        let profiles = try await service.getColimaProfiles()
        XCTAssertFalse(profiles.isEmpty,
                       "getColimaProfiles() must return colima profiles even when the inherited " +
                       "PATH lacks /opt/homebrew/bin (regression: 'No Colima profiles found')")
    }

    func testResolveExecutableUsesInjectedPATHEntries() throws {
        let tempDir = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        let toolURL = tempDir.appendingPathComponent("demo-tool")
        try "#!/bin/sh\nexit 0\n".write(to: toolURL, atomically: true, encoding: .utf8)
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: toolURL.path)

        let service = DockerService(environment: ["PATH": tempDir.path])
        let url = service.resolveExecutableURL(for: "demo-tool")

        XCTAssertEqual(url?.path, toolURL.path)
    }

    func testSuccessfulCommandReturnsOutput() async throws {
        let service = DockerService()
        let output = try await service.runCommandStreaming(
            "echo",
            args: ["hello", "world"],
            onLine: nil
        )
        XCTAssertTrue(output.contains("hello world"),
                      "Expected 'hello world' in output, got: \(output)")
    }

    func testFailingCommandThrowsNSError() async {
        let service = DockerService()
        do {
            _ = try await service.runCommandStreaming(
                "false",
                args: [],
                onLine: nil
            )
            XCTFail("Expected runCommandStreaming to throw on non-zero exit")
        } catch is CancellationError {
            XCTFail("Expected NSError, got CancellationError (this would mean " +
                    "the failure was misclassified as cancellation)")
        } catch {
            let nsErr = error as NSError
            XCTAssertEqual(nsErr.domain, "DockerService",
                           "Error domain should be DockerService, got: \(nsErr.domain)")
            XCTAssertEqual(nsErr.code, 1,
                           "/usr/bin/false exits with status 1, got: \(nsErr.code)")
        }
    }

    func testOnLineCallbackReceivesStreamedOutput() async throws {
        let service = DockerService()
        // Use a thread-safe collector since onLine is invoked on the main queue.
        let collector = LineCollector()
        _ = try await service.runCommandStreaming(
            "printf",
            args: [#"line-one\nline-two\nline-three\n"#],
            onLine: { line in
                collector.append(line)
            }
        )
        // Give the main queue one cycle to flush any pending onLine dispatches.
        await Task.yield()
        try await Task.sleep(nanoseconds: 50_000_000) // 50ms

        let lines = collector.allLines()
        XCTAssertEqual(lines, ["line-one", "line-two", "line-three"],
                       "Expected exactly three streamed lines, got: \(lines)")
    }

    func testCancellationTerminatesLongRunningSubprocess() async throws {
        let service = DockerService()
        // sleep 30 would otherwise tie up the test runner for 30s. We cancel
        // after 200ms and assert the call returns within ~1s.
        let started = Date()
        let task = Task<Result<String, Error>, Never> {
            do {
                let s = try await service.runCommandStreaming(
                    "sleep",
                    args: ["30"],
                    onLine: nil
                )
                return .success(s)
            } catch {
                return .failure(error)
            }
        }

        // Give the subprocess time to actually spawn before cancelling.
        try await Task.sleep(nanoseconds: 200_000_000) // 200ms

        task.cancel()
        let result = await task.value
        let elapsed = Date().timeIntervalSince(started)

        XCTAssertLessThan(elapsed, 2.0,
                          "Cancellation should propagate within ~1s; took \(elapsed)s")

        switch result {
        case .success:
            XCTFail("Expected CancellationError, got successful return")
        case .failure(let error):
            XCTAssertTrue(error is CancellationError,
                          "Expected CancellationError, got: \(type(of: error)) \(error)")
        }
    }

    func testCancellationBeforeRunResolvesCleanly() async {
        // Edge case: cancel the Task immediately, before the subprocess can
        // even spawn. The ProcessBox race-handling should resolve with
        // CancellationError without leaking processes.
        let service = DockerService()
        let task = Task<Result<String, Error>, Never> {
            do {
                let s = try await service.runCommandStreaming(
                    "sleep",
                    args: ["10"],
                    onLine: nil
                )
                return .success(s)
            } catch {
                return .failure(error)
            }
        }
        task.cancel()
        let result = await task.value
        switch result {
        case .success:
            XCTFail("Expected cancellation, got success")
        case .failure(let error):
            // Either CancellationError (race won by cancel) or NSError with
            // signal-based termination (race won by run, then SIGTERM). Both
            // are acceptable outcomes of an immediate-cancel.
            XCTAssertTrue(
                error is CancellationError
                    || (error as NSError).domain == "DockerService",
                "Unexpected error type: \(type(of: error)) \(error)"
            )
        }
    }
}

// Synchronous, NSLock-backed line collector. Important: append() must be
// synchronous so the test preserves the order in which the production code
// emits lines via the main-queue dispatch. An earlier actor-based version
// spawned independent Tasks per line and lost ordering (lines arrived
// 1, 3, 2 about a third of the time).
//
// SAFETY (@unchecked Sendable): all access is serialized through `lock`.
private final class LineCollector: @unchecked Sendable {
    private let lock = NSLock()
    private var lines: [String] = []

    func append(_ line: String) {
        lock.lock()
        defer { lock.unlock() }
        lines.append(line)
    }

    func allLines() -> [String] {
        lock.lock()
        defer { lock.unlock() }
        return lines
    }
}
