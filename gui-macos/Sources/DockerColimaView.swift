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
        AppLogger.log("ViewModel refresh: got \(dockerContainers.count) containers from running profiles", level: .debug)
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

    // Returns nil on success, or a human-readable error message on failure.
    // `onLine` is forwarded to the underlying streaming subprocess so the
    // form can show live progress while the new VM boots (30-60s).
    func createProfile(
        name: String,
        cpus: Int? = nil,
        memory: String? = nil,
        disk: String? = nil,
        runtime: String? = nil,
        arch: String? = nil,
        onLine: ((String) -> Void)? = nil
    ) async -> String? {
        let err = await dockerService.createColimaProfile(
            name: name,
            cpus: cpus,
            memory: memory,
            disk: disk,
            runtime: runtime,
            arch: arch,
            onLine: onLine
        )
        await refresh()
        return err
    }

    func deleteProfile(name: String) async {
        _ = await dockerService.deleteColimaProfile(name)
        await refresh()
    }
}

struct DockerColimaView: View {
    @StateObject private var viewModel = DockerColimaViewModel()
    // NOTE: SwiftUI modal presentations (.sheet / .confirmationDialog / .alert)
    // inside MenuBarExtra silently freeze the menu because the modal can't
    // cleanly steal focus from the menu's transient host window. Both the
    // create-profile flow and delete-profile flow are presented via native
    // AppKit primitives instead:
    //   - Create:  NSWindow + NSHostingController (see CreateProfileWindowController)
    //   - Delete:  NSAlert.runModal() (see confirmAndDeleteProfile)
    // Previously this struct held @State for showCreateSheet, showDeleteConfirm,
    // profileToDelete, newProfileName/Cpus/Memory/Disk — all removed.

    private var groupedContainers: [String: [DockerContainer]] {
        Dictionary(grouping: viewModel.dockerContainers) { $0.colimaProfile }
    }

    // Use NSAlert (the codebase's established imperative-dialog pattern) instead of
    // SwiftUI .confirmationDialog. .confirmationDialog inside a MenuBarExtra menu
    // was freezing the entire menu when the modal tried to present, because the
    // modal can't steal focus cleanly from the menu's transient host window.
    private func confirmAndDeleteProfile(name: String) {
        let alert = NSAlert()
        alert.messageText = "Delete Colima profile '\(name)'?"
        alert.informativeText = "This will destroy the VM and all containers inside it. This cannot be undone."
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Delete")
        alert.addButton(withTitle: "Cancel")
        // Activate the app so the alert window appears in front of everything.
        NSApp.activate(ignoringOtherApps: true)
        let response = alert.runModal()
        guard response == .alertFirstButtonReturn else { return }
        Task { await viewModel.deleteProfile(name: name) }
    }

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
                                    Button("SSH") {
                                        openSSHInTerminal(profile: profile.name)
                                    }
                                    .buttonStyle(.borderless)
                                    .font(.caption)

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

                                Button("Delete") {
                                    // Use NSAlert directly — SwiftUI .confirmationDialog
                                    // in a MenuBarExtra was freezing the menu's interaction.
                                    confirmAndDeleteProfile(name: profile.name)
                                }
                                .buttonStyle(.borderless)
                                .font(.caption)
                                .foregroundColor(.red)
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

                    Button("New Profile") {
                        // SwiftUI .sheet inside MenuBarExtra steals focus only
                        // partially, leaving the form's text fields inert.
                        // Present in a real NSWindow instead (same pattern as
                        // the Model Downloader window).
                        showCreateProfileWindow()
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

                if viewModel.colimaProfiles.isEmpty {
                    Text("No Colima profiles found")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.leading, 8)
                } else {
                    // Show all profiles
                    ForEach(viewModel.colimaProfiles.sorted { $0.name < $1.name }) { profile in
                        HStack {
                            Text(profile.name.uppercased())
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.primary)

                            Spacer()

                            Text("\(groupedContainers[profile.name]?.count ?? 0) containers")
                                .font(.caption2)
                                .foregroundColor(profile.isRunning ? .secondary : .orange)
                        }
                        .padding(.leading, 8)
                        .padding(.top, 8)
                        .padding(.trailing, 8)

                        let profileContainers = groupedContainers[profile.name] ?? []
                        if !profile.isRunning {
                            Text("Profile is not running")
                                .font(.caption)
                                .foregroundColor(.orange)
                                .padding(.leading, 16)
                                .padding(.vertical, 4)
                        } else if profileContainers.isEmpty {
                            Text("No containers configured in this profile")
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .padding(.leading, 16)
                                .padding(.vertical, 4)
                        } else {
                            ForEach(profileContainers) { container in
                                HStack(spacing: 8) {
                                    Circle()
                                        .fill(container.isRunning ? Color.blue : Color.gray)
                                        .frame(width: 8, height: 8)

                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(container.name)
                                            .font(.system(.body, design: .monospaced))
                                            .fontWeight(.medium)

                                        Text("\(container.image) [ID: \(container.id.prefix(12))]")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                            .lineLimit(1)

                                        // Port info: show actual ports, or "no port" in gray if empty
                                        let portText = container.ports.trimmingCharacters(in: .whitespaces)
                                        HStack(spacing: 4) {
                                            Image(systemName: portText.isEmpty ? "minus.circle" : "network")
                                                .font(.caption2)
                                                .foregroundColor(portText.isEmpty ? .secondary : .blue)
                                            Text(portText.isEmpty ? "no port" : portText)
                                                .font(.caption2)
                                                .foregroundColor(portText.isEmpty ? .secondary : .secondary)
                                                .lineLimit(1)
                                        }

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
        // No SwiftUI .sheet — the create form is presented in a real NSWindow
        // (see showCreateProfileWindow / CreateProfileForm below).
    }

    // MARK: - Create Profile Window (NSWindow-hosted to avoid MenuBarExtra .sheet freeze)

    // Open Terminal.app in a new window and run `colima ssh -p <profile>`.
    // Profile names are validated by Colima itself, but we additionally escape
    // any double quotes to keep the AppleScript string well-formed.
    private func openSSHInTerminal(profile: String) {
        let safe = profile.replacingOccurrences(of: "\"", with: "\\\"")
        let script = """
        tell application "Terminal"
            activate
            do script "colima ssh -p \(safe)"
        end tell
        """
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        task.arguments = ["-e", script]
        do {
            try task.run()
            AppLogger.log("Opened Terminal for SSH to colima profile: \(profile)", level: .info)
        } catch {
            AppLogger.log("Failed to open Terminal for SSH: \(error)", level: .error)
        }
    }

    private func showCreateProfileWindow() {
        // Reuse window if it's already open
        if let win = CreateProfileWindowController.shared.window {
            win.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }
        CreateProfileWindowController.shared.show(viewModel: viewModel)
    }
}

// MARK: - CreateProfileForm + window controller

private struct CreateProfileForm: View {
    @ObservedObject var viewModel: DockerColimaViewModel
    var onClose: () -> Void

    private static let sourceDefault = "— Colima defaults —"
    private static let runtimeOptions = ["docker", "containerd"]
    private static let archOptions = ["aarch64", "x86_64"]

    @State private var profileName = ""
    @State private var sourceProfile: String = sourceDefault
    @State private var cpus = ""
    @State private var memory = ""
    @State private var disk = ""
    @State private var runtime = "docker"
    @State private var arch = "aarch64"
    @State private var isSubmitting = false
    @State private var errorMessage: String?
    @State private var progressLines: [String] = []

    // Colima accepts memory as float GiB and disk as int GiB. Accept lenient
    // user input like "4G" / "4GiB" / "4 GB" and normalize to the bare number
    // that the colima CLI expects.
    private static func normalizeGiB(_ raw: String) -> String {
        let trimmed = raw.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return "" }
        let stripped = trimmed
            .replacingOccurrences(of: "GiB", with: "", options: .caseInsensitive)
            .replacingOccurrences(of: "GB", with: "", options: .caseInsensitive)
            .replacingOccurrences(of: "G", with: "", options: .caseInsensitive)
        return stripped.trimmingCharacters(in: .whitespaces)
    }

    // Apply the picked source profile's spec to the form fields. The new VM
    // gets independent data; only resource flags are copied.
    private func applySourceProfile(_ name: String) {
        guard name != Self.sourceDefault,
              let p = viewModel.colimaProfiles.first(where: { $0.name == name }) else {
            return
        }
        cpus = p.cpus > 0 ? String(p.cpus) : ""
        memory = Self.normalizeGiB(p.memory)
        disk = Self.normalizeGiB(p.disk)
        if Self.runtimeOptions.contains(p.runtime) { runtime = p.runtime }
        if Self.archOptions.contains(p.arch) { arch = p.arch }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Create Colima Profile")
                .font(.headline)

            VStack(alignment: .leading, spacing: 8) {
                Text("Profile Name").font(.caption).fontWeight(.semibold)
                TextField("e.g., my-profile", text: $profileName)
                    .textFieldStyle(.roundedBorder)
                    .disabled(isSubmitting)

                Text("Copy spec from (optional)").font(.caption).fontWeight(.semibold)
                Picker("", selection: $sourceProfile) {
                    Text(Self.sourceDefault).tag(Self.sourceDefault)
                    ForEach(viewModel.colimaProfiles.map { $0.name }, id: \.self) { name in
                        Text(name).tag(name)
                    }
                }
                .labelsHidden()
                .disabled(isSubmitting)
                .onChange(of: sourceProfile) { newValue in
                    applySourceProfile(newValue)
                }

                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("CPUs").font(.caption).fontWeight(.semibold)
                        TextField("2", text: $cpus)
                            .textFieldStyle(.roundedBorder)
                            .disabled(isSubmitting)
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Memory (GiB)").font(.caption).fontWeight(.semibold)
                        TextField("2", text: $memory)
                            .textFieldStyle(.roundedBorder)
                            .disabled(isSubmitting)
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Disk (GiB)").font(.caption).fontWeight(.semibold)
                        TextField("100", text: $disk)
                            .textFieldStyle(.roundedBorder)
                            .disabled(isSubmitting)
                    }
                }

                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Runtime").font(.caption).fontWeight(.semibold)
                        Picker("", selection: $runtime) {
                            ForEach(Self.runtimeOptions, id: \.self) { Text($0).tag($0) }
                        }
                        .labelsHidden()
                        .disabled(isSubmitting)
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Architecture").font(.caption).fontWeight(.semibold)
                        Picker("", selection: $arch) {
                            ForEach(Self.archOptions, id: \.self) { Text($0).tag($0) }
                        }
                        .labelsHidden()
                        .disabled(isSubmitting)
                    }
                }
            }

            if isSubmitting || !progressLines.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        if isSubmitting {
                            ProgressView().scaleEffect(0.6)
                        }
                        Text(isSubmitting ? "Creating VM (can take 30–60s)…" : "Output")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    ScrollViewReader { proxy in
                        ScrollView {
                            VStack(alignment: .leading, spacing: 1) {
                                ForEach(Array(progressLines.enumerated()), id: \.offset) { idx, line in
                                    Text(line)
                                        .font(.system(.caption2, design: .monospaced))
                                        .foregroundColor(.secondary)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .id(idx)
                                }
                            }
                            .padding(6)
                        }
                        .frame(height: 100)
                        .background(Color(NSColor.textBackgroundColor).opacity(0.5))
                        .cornerRadius(4)
                        .onChange(of: progressLines.count) { newCount in
                            if newCount > 0 {
                                proxy.scrollTo(newCount - 1, anchor: .bottom)
                            }
                        }
                    }
                }
            }

            if let errorMessage = errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundColor(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 12) {
                Button("Cancel") {
                    onClose()
                }
                .buttonStyle(.bordered)
                .disabled(isSubmitting)

                Button(isSubmitting ? "Creating…" : "Create") {
                    let cpusInt = Int(cpus.trimmingCharacters(in: .whitespaces))
                    let memoryArg = Self.normalizeGiB(memory)
                    let diskArg = Self.normalizeGiB(disk)
                    isSubmitting = true
                    errorMessage = nil
                    progressLines = []
                    Task {
                        let err = await viewModel.createProfile(
                            name: profileName.trimmingCharacters(in: .whitespaces),
                            cpus: cpusInt,
                            memory: memoryArg.isEmpty ? nil : memoryArg,
                            disk: diskArg.isEmpty ? nil : diskArg,
                            runtime: runtime,
                            arch: arch,
                            onLine: { line in
                                progressLines.append(line)
                            }
                        )
                        await MainActor.run {
                            isSubmitting = false
                            if let err = err {
                                errorMessage = err
                            } else {
                                onClose()
                            }
                        }
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(profileName.trimmingCharacters(in: .whitespaces).isEmpty || isSubmitting)
                .keyboardShortcut(.defaultAction)
            }
            .padding(.top, 8)

            Spacer()
        }
        .padding(16)
        .frame(width: 460, height: 560)
    }
}

private final class CreateProfileWindowController: NSObject, NSWindowDelegate {
    static let shared = CreateProfileWindowController()
    var window: NSWindow?

    func show(viewModel: DockerColimaViewModel) {
        let form = CreateProfileForm(viewModel: viewModel) { [weak self] in
            self?.close()
        }
        let hostingController = NSHostingController(rootView: form)
        let win = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 460, height: 560),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        win.title = "New Colima Profile"
        win.contentViewController = hostingController
        win.center()
        win.delegate = self
        win.isReleasedWhenClosed = false
        win.level = .floating
        win.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        self.window = win
    }

    func close() {
        window?.close()
    }

    func windowWillClose(_ notification: Notification) {
        self.window = nil
    }
}
