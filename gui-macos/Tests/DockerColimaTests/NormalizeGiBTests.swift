// File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Tests/DockerColimaTests/NormalizeGiBTests.swift
// Description: Unit tests for CreateProfileForm.normalizeGiB — the lenient
//              memory/disk input parser used by the New Colima Profile form.
// Author: Libor Ballaty <libor@arionetworks.com>
// Created: 2026-06-23

import XCTest
@testable import llamacpp_gui

final class NormalizeGiBTests: XCTestCase {

    func testBareIntegerPassesThrough() {
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4"), "4")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("100"), "100")
    }

    func testFloatPassesThrough() {
        // Colima accepts float for --memory; the normalizer should not mangle it.
        XCTAssertEqual(CreateProfileForm.normalizeGiB("2.5"), "2.5")
    }

    func testStripsTrailingG() {
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4G"), "4")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4g"), "4")
    }

    func testStripsTrailingGB() {
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4GB"), "4")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4gb"), "4")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4Gb"), "4")
    }

    func testStripsTrailingGiB() {
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4GiB"), "4")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4gib"), "4")
    }

    func testStripsTrailingSpaceBeforeUnit() {
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4 G"), "4")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4 GiB"), "4")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("4 GB"), "4")
    }

    func testStripsSurroundingWhitespace() {
        XCTAssertEqual(CreateProfileForm.normalizeGiB("  100  "), "100")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("\t60GiB\n"), "60")
    }

    func testEmptyInputReturnsEmpty() {
        XCTAssertEqual(CreateProfileForm.normalizeGiB(""), "")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("   "), "")
    }

    func testRealisticColimaListMemoryFormat() {
        // ColimaProfile.memory comes from `colima list` as e.g. "16GiB". The
        // Copy-spec-from dropdown feeds this into the form, where it must
        // normalize cleanly to "16" before re-submission to `colima start`.
        XCTAssertEqual(CreateProfileForm.normalizeGiB("16GiB"), "16")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("100GiB"), "100")
        XCTAssertEqual(CreateProfileForm.normalizeGiB("2GiB"), "2")
    }
}
