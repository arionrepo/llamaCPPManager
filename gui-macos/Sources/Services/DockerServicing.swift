//
//  DockerServicing.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Services/DockerServicing.swift
//  Description: Protocol seam over DockerService so callers can be unit-tested with mocks. Method signatures mirror the public surface of DockerService that DockerColimaView actually calls (Phase 6 inventory). No behavior change.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-24
//

import Foundation

/// Test seam for `DockerService`. Callers depend on this protocol so unit
/// tests can substitute a fake without spawning colima/docker subprocesses.
/// The concrete `DockerService` satisfies this protocol unchanged via the
/// extension at the bottom of this file.
protocol DockerServicing {
    func getColimaProfiles() async -> [ColimaProfile]
    func startColimaProfile(_ profile: String) async -> Bool
    func stopColimaProfile(_ profile: String) async -> Bool
    func restartColima() async -> Bool
    func createColimaProfile(
        name: String,
        cpus: Int?,
        memory: String?,
        disk: String?,
        runtime: String?,
        arch: String?,
        onLine: ((String) -> Void)?
    ) async -> String?
    func deleteColimaProfile(_ profile: String) async -> Bool
    func getDockerContainers() async -> [DockerContainer]
    func startDockerContainer(_ containerName: String, profile: String) async -> Bool
    func stopDockerContainer(_ containerName: String, profile: String) async -> Bool
    func restartDockerContainer(_ containerName: String, profile: String) async -> Bool
    func getContainerStats() async -> [String: (cpu: Double, memory: String)]
}

extension DockerService: DockerServicing {}
