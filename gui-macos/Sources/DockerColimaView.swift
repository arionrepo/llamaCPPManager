// File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/DockerColimaView.swift
// Description: SwiftUI view for Docker and Colima management
// Author: Libor Ballaty <libor@arionetworks.com>
// Created: 2026-03-25

import SwiftUI

@MainActor
class DockerColimaViewModel: ObservableObject {
    @Published var colimaProfiles: [ColimaProfile] = []
    @Published var dockerContainers: [DockerContainer] = []
    @Published var containerStats: [String: (cpu: Double, memory: String)] = [:]
    @Published var isLoading = false

    private let dockerService = DockerService()
    private var refreshTask: Task<Void, Never>?

    func startPolling() {
        refreshTask?.cancel()
        refreshTask = Task {
            while !Task.isCancelled {
                await refresh()
                try? await Task.sleep(for: .seconds(5))
            }
        }
    }

    func stopPolling() {
        refreshTask?.cancel()
    }

    func refresh() async {
        isLoading = true
        async let profiles = dockerService.getColimaProfiles()
        async let containers = dockerService.getDockerContainers()
        async let stats = dockerService.getContainerStats()

        colimaProfiles = await profiles
        dockerContainers = await containers
        containerStats = await stats
        isLoading = false
    }

    func startColima(profile: String) async {
        _ = await dockerService.startColimaProfile(profile)
        await refresh()
    }

    func stopColima(profile: String) async {
        _ = await dockerService.stopColimaProfile(profile)
        await refresh()
    }

    func restartColima() async {
        _ = await dockerService.restartColima()
        await refresh()
    }

    func startContainer(name: String, profile: String) async {
        _ = await dockerService.startDockerContainer(name, profile: profile)
        await refresh()
    }

    func stopContainer(name: String, profile: String) async {
        _ = await dockerService.stopDockerContainer(name, profile: profile)
        await refresh()
    }

    func restartContainer(name: String, profile: String) async {
        _ = await dockerService.restartDockerContainer(name, profile: profile)
        await refresh()
    }
}

struct DockerColimaView: View {
    @StateObject private var viewModel = DockerColimaViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                // MARK: - Colima Profiles Section
                Text("COLIMA PROFILES")
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(.primary)

                if viewModel.colimaProfiles.isEmpty {
                    Text("No Colima profiles found")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.leading, 8)
                } else {
                    ForEach(viewModel.colimaProfiles) { profile in
                        HStack(spacing: 8) {
                            Circle()
                                .fill(profile.isRunning ? Color.blue : Color.gray)
                                .frame(width: 8, height: 8)

                            VStack(alignment: .leading, spacing: 2) {
                                Text(profile.name)
                                    .font(.system(.body, design: .monospaced))
                                    .fontWeight(.medium)

                                Text("\(profile.cpus) CPU, \(profile.memory)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }

                            Spacer()

                            Text(profile.status)
                                .font(.caption)
                                .foregroundColor(profile.isRunning ? .blue : .secondary)
                                .frame(minWidth: 60, alignment: .trailing)

                            HStack(spacing: 4) {
                                if profile.isRunning {
                                    Button("Stop") {
                                        Task { await viewModel.stopColima(profile: profile.name) }
                                    }
                                    .buttonStyle(.borderless)
                                    .font(.caption)
                                } else {
                                    Button("Start") {
                                        Task { await viewModel.startColima(profile: profile.name) }
                                    }
                                    .buttonStyle(.borderless)
                                    .font(.caption)
                                }
                            }
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                    }
                }

                HStack(spacing: 8) {
                    Button("Restart Active") {
                        Task { await viewModel.restartColima() }
                    }
                    .buttonStyle(.bordered)
                    .font(.caption)

                    Button("Refresh") {
                        Task { await viewModel.refresh() }
                    }
                    .buttonStyle(.bordered)
                    .font(.caption)
                }
                .padding(.horizontal, 8)

                Divider()

                // MARK: - Docker Containers Section
                Text("DOCKER CONTAINERS")
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(.primary)

                if viewModel.dockerContainers.isEmpty {
                    Text("No containers found")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.leading, 8)
                } else {
                    // Group containers by Colima profile
                    let groupedContainers = Dictionary(grouping: viewModel.dockerContainers) { $0.colimaProfile }

                    ForEach(groupedContainers.keys.sorted(), id: \.self) { profile in
                        Text(profile.uppercased())
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.primary)
                            .padding(.leading, 8)
                            .padding(.top, 4)

                        ForEach(groupedContainers[profile] ?? []) { container in
                        HStack(spacing: 8) {
                            Circle()
                                .fill(container.isRunning ? Color.blue : Color.gray)
                                .frame(width: 8, height: 8)

                            VStack(alignment: .leading, spacing: 2) {
                                Text(container.name)
                                    .font(.system(.body, design: .monospaced))
                                    .fontWeight(.medium)

                                Text(container.image)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)

                                if let stats = viewModel.containerStats[container.name] {
                                    Text("CPU: \(stats.cpu, specifier: "%.1f")% | MEM: \(stats.memory)")
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                }
                            }

                            Spacer()

                            Text(container.isRunning ? "Running" : "Stopped")
                                .font(.caption)
                                .foregroundColor(container.isRunning ? .blue : .secondary)
                                .frame(minWidth: 60, alignment: .trailing)

                            HStack(spacing: 4) {
                                if container.isRunning {
                                    Button("Stop") {
                                        Task { await viewModel.stopContainer(name: container.name, profile: container.colimaProfile) }
                                    }
                                    .buttonStyle(.borderless)
                                    .font(.caption)

                                    Button("Restart") {
                                        Task { await viewModel.restartContainer(name: container.name, profile: container.colimaProfile) }
                                    }
                                    .buttonStyle(.borderless)
                                    .font(.caption)
                                } else {
                                    Button("Start") {
                                        Task { await viewModel.startContainer(name: container.name, profile: container.colimaProfile) }
                                    }
                                    .buttonStyle(.borderless)
                                    .font(.caption)
                                }
                            }
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                    }
                    }
                }

                if viewModel.isLoading {
                    HStack {
                        ProgressView()
                            .scaleEffect(0.7)
                        Text("Loading...")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(8)
                }
            }
            .padding(6)
        }
        .frame(minWidth: 400, minHeight: 300)
        .task {
            await viewModel.refresh()
            viewModel.startPolling()
        }
        .onDisappear {
            viewModel.stopPolling()
        }
    }
}
