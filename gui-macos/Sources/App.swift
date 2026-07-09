import SwiftUI
import AppKit
import Combine

@main
struct LlamaCPPManagerApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var vm = StatusViewModel()

    var body: some Scene {
        MenuBarExtra {
            VStack(alignment: .leading, spacing: 6) {
                // Version header
                Text("llamaCPP Manager v\(APP_VERSION)")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.top, 4)

                // MARK: - Error banner (start failures, etc.)
                if let error = vm.errorMessage {
                    HStack(alignment: .top, spacing: 6) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                            .accessibilityHidden(true)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                            .textSelection(.enabled)
                            .lineLimit(4)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        Button(action: { vm.errorMessage = nil }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.secondary)
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Dismiss error")
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 6)
                    .background(Color.red.opacity(0.08))
                }

                // MARK: - Active Downloads + Loading (pinned at top so always visible)
                let totalActive = vm.downloadViewModel.downloads.count + vm.startupProgress.count
                if totalActive > 0 {
                    Divider()
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.down.circle.fill")
                            .foregroundColor(.blue)
                            .accessibilityHidden(true)
                        Text("Active Downloads & Loading (\(totalActive))")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.blue)
                        Spacer()
                    }
                    .padding(.horizontal, 8)
                    .padding(.top, 2)

                    // Models being loaded / lazy-downloaded by their server processes
                    ForEach(Array(vm.startupProgress.keys.sorted()), id: \.self) { name in
                        if let prog = vm.startupProgress[name] {
                            VStack(alignment: .leading, spacing: 2) {
                                HStack(spacing: 6) {
                                    ProgressView()
                                        .scaleEffect(0.5)
                                        .frame(width: 12, height: 12)
                                    Text(name)
                                        .font(.caption)
                                        .fontWeight(.medium)
                                        .lineLimit(1)
                                    Spacer()
                                    if let pct = prog.progress {
                                        Text("\(Int(pct * 100))%")
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                    }
                                }
                                if let pct = prog.progress {
                                    ProgressView(value: pct)
                                        .progressViewStyle(.linear)
                                        .frame(height: 4)
                                }
                                HStack {
                                    Text(prog.status)
                                        .font(.caption2)
                                        .foregroundColor(.blue)
                                    Spacer()
                                    if let detail = prog.detail {
                                        Text(detail)
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                        }
                    }

                    ForEach(Array(vm.downloadViewModel.downloads.keys.sorted()), id: \.self) { name in
                        if let progress = vm.downloadViewModel.downloads[name] {
                            VStack(alignment: .leading, spacing: 2) {
                                HStack(spacing: 6) {
                                    ProgressView()
                                        .scaleEffect(0.5)
                                        .frame(width: 12, height: 12)
                                    Text(name)
                                        .font(.caption)
                                        .fontWeight(.medium)
                                        .lineLimit(1)
                                    Spacer()
                                    Text("\(Int(progress.percentComplete * 100))%")
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                }
                                ProgressView(value: progress.percentComplete)
                                    .progressViewStyle(.linear)
                                    .frame(height: 4)
                                HStack {
                                    Text(progress.status)
                                        .font(.caption2)
                                        .foregroundColor(.blue)
                                    Spacer()
                                    if progress.bytesDownloaded > 0 && progress.totalBytes > 0 {
                                        let dl = ByteCountFormatter.string(fromByteCount: progress.bytesDownloaded, countStyle: .file)
                                        let total = ByteCountFormatter.string(fromByteCount: progress.totalBytes, countStyle: .file)
                                        Text("\(dl) / \(total)")
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                    }
                                }
                                if progress.speedMBps > 0.1 {
                                    HStack {
                                        Text(String(format: "%.1f MB/s", progress.speedMBps))
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                        Spacer()
                                        if progress.etaSeconds > 0 {
                                            Text("ETA: " + formatDownloadETA(progress.etaSeconds))
                                                .font(.caption2)
                                                .foregroundColor(.secondary)
                                        }
                                    }
                                }
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                        }
                    }
                }

                Divider()

                // MARK: - Tabbed Interface
                TabView {
                    // MARK: - Infrastructure Tab
                    ScrollView {
                        VStack(alignment: .leading, spacing: 6) {
                            if !vm.infrastructureRows.isEmpty {
                    Text("Infrastructure")
                        .font(.headline)
                        .padding(.horizontal, 8)

                    ForEach(vm.infrastructureRows, id: \.name) { infra in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Circle()
                                    .fill(vm.healthColorInfra(for: infra))
                                    .frame(width: 10, height: 10)

                                VStack(alignment: .leading) {
                                    Text(infra.name)
                                        .font(.headline)
                                    Text(vm.healthStatusInfra(for: infra))
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }

                                Spacer()

                                VStack(alignment: .trailing) {
                                    Text(infra.type)
                                        .font(.caption)
                                    if infra.latency_ms > 0 {
                                        Text("\(infra.latency_ms) ms")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                    if let uptime = infra.uptime, !uptime.isEmpty {
                                        Text("up \(uptime)")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
                            .padding(.horizontal, 8)

                            HStack {
                                Button("Start") { vm.startInfra(name: infra.name) }
                                    .disabled(infra.running)
                                Button("Stop") { vm.stopInfra(name: infra.name) }
                                    .disabled(!infra.running)
                                Button("Restart") { vm.restartInfra(name: infra.name) }
                                Button("Logs") { vm.infraLogs(name: infra.name) }
                            }
                            .buttonStyle(.borderless)
                            .font(.caption)
                            .padding(.leading, 18)
                        }
                        Divider()
                    }
                }

                            // MARK: - Docker & Colima Section
                            Divider()
                            DockerColimaView()
                        }
                    }
                    .tabItem {
                        Label("Infrastructure", systemImage: "server.rack")
                    }

                    // MARK: - Native Models Tab
                    ScrollView {
                        VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text("Native Models")
                        .font(.headline)
                    Spacer()
                    if !vm.nativeSearchText.isEmpty {
                        Button(action: { vm.nativeSearchText = "" }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.secondary)
                                .font(.caption)
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Clear search")
                    }
                }
                .padding(.horizontal, 8)

                TextField("Search models…", text: $vm.nativeSearchText)
                    .textFieldStyle(.roundedBorder)
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.bottom, 2)

                if vm.rows.isEmpty {
                    Text("No native models configured")
                        .padding(.horizontal, 8)
                } else if vm.filteredNativeRows.isEmpty {
                    Text("No models match \"\(vm.nativeSearchText)\"")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 8)
                } else {
                    ForEach(vm.filteredNativeRows, id: \.name) { row in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                // Enhanced health indicator
                                Circle()
                                    .fill(vm.healthColor(for: row))
                                    .frame(width: 10, height: 10)

                                VStack(alignment: .leading, spacing: 2) {
                                    HStack(spacing: 6) {
                                        Text(row.name)
                                            .font(.headline)
                                        if let format = row.format {
                                            Text(format.uppercased())
                                                .font(.caption2)
                                                .padding(.horizontal, 6)
                                                .padding(.vertical, 2)
                                                .background(vm.formatBadgeColor(format))
                                                .foregroundColor(.white)
                                                .cornerRadius(3)
                                        }
                                        if let q = row.quantization {
                                            Text(q)
                                                .font(.caption2)
                                                .padding(.horizontal, 5)
                                                .padding(.vertical, 2)
                                                .background(Color.gray.opacity(0.25))
                                                .cornerRadius(3)
                                        }
                                        if let sz = row.file_size_gb, sz > 0 {
                                            Text(String(format: "%.1f GB", sz))
                                                .font(.caption2)
                                                .foregroundColor(.secondary)
                                        }
                                    }

                                    if let fn = row.model_filename, !fn.isEmpty {
                                        Text(fn)
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                            .lineLimit(1)
                                            .truncationMode(.middle)
                                    }

                                    Text(vm.healthStatus(for: row))
                                        .font(.caption)
                                        .foregroundColor(.secondary)

                                    if let desc = row.description, !desc.isEmpty {
                                        Text(desc)
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                            .italic()
                                            .lineLimit(2)
                                    }

                                    if row.up, let ram = row.ram_mb, ram > 0 {
                                        HStack(spacing: 8) {
                                            Text(String(format: "RAM: %.1f GB", ram / 1024.0))
                                                .font(.caption2)
                                                .foregroundColor(.secondary)
                                            if let cpu = row.cpu_percent {
                                                Text(String(format: "CPU: %.1f%%", cpu))
                                                    .font(.caption2)
                                                    .foregroundColor(.secondary)
                                            }
                                        }
                                    }
                                }

                                Spacer()

                                VStack(alignment: .trailing) {
                                    Text("\(row.host):\(row.port)")
                                        .font(.caption)
                                    if let ms = row.latency_ms, ms > 0 {
                                        Text("\(ms) ms")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                    if let uptime = row.uptime, !uptime.isEmpty {
                                        Text("up \(uptime)")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
                            .padding(.horizontal, 8)

                            // Startup progress (shows download / loading status)
                            if let progress = vm.startupProgress[row.name] {
                                VStack(alignment: .leading, spacing: 2) {
                                    HStack(spacing: 6) {
                                        ProgressView()
                                            .scaleEffect(0.6)
                                            .frame(width: 14, height: 14)
                                        Text(progress.status)
                                            .font(.caption)
                                            .foregroundColor(.blue)
                                        if let detail = progress.detail {
                                            Text("(\(detail))")
                                                .font(.caption2)
                                                .foregroundColor(.secondary)
                                        }
                                        Spacer()
                                    }
                                    if let pct = progress.progress {
                                        ProgressView(value: pct)
                                            .progressViewStyle(.linear)
                                            .frame(height: 4)
                                    }
                                }
                                .padding(.horizontal, 18)
                                .padding(.vertical, 4)
                            }

                            // Mode picker (show when stopped and not starting). Mode set is
                            // deployment-specific — llama.cpp gets basic/tools/performance/extended,
                            // MLX gets basic/think. See StatusViewModel.availableModes(for:).
                            if !row.up && vm.startupProgress[row.name] == nil {
                                let modes = vm.availableModes(for: row)
                                HStack(spacing: 4) {
                                    Text("Mode:")
                                        .font(.caption)
                                        .foregroundColor(.secondary)

                                    Picker("", selection: Binding(
                                        get: { vm.selectedModes[row.name] ?? "basic" },
                                        set: { newMode in
                                            vm.selectedModes[row.name] = newMode
                                            vm.saveMode(for: row.name, mode: newMode)
                                        }
                                    )) {
                                        ForEach(modes, id: \.tag) { mode in
                                            Text(mode.label).tag(mode.tag)
                                        }
                                    }
                                    .pickerStyle(.segmented)
                                    .labelsHidden()
                                }
                                .padding(.horizontal, 18)
                                .padding(.vertical, 4)
                            }

                            // Control buttons
                            HStack {
                                Button("Start") { vm.startWithScript(name: row.name, mode: vm.selectedModes[row.name]) }
                                    .disabled(row.up || vm.startupProgress[row.name] != nil)
                                Button("Stop") { vm.stop(name: row.name) }
                                    .disabled(!row.up)
                                Button("Restart") { vm.restart(name: row.name) }

                                if row.up {
                                    Button("Chat") { vm.openChat(name: row.name) }
                                }

                                Button("Monitor") { vm.toggleMonitoring(name: row.name) }
                                    .foregroundColor(vm.isMonitored(name: row.name) ? .orange : .blue)

                                Button("Logs") { vm.tailLogs(name: row.name) }
                            }
                            .buttonStyle(.plain)
                            .font(.caption)
                            .padding(.leading, 18)
                        }
                        Divider()
                    }
                }
                HStack {
                    Button(action: { vm.startAllModels() }) {
                        Text("Start All Native Models")
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                    }
                    .buttonStyle(.bordered)
                    .help("Start all native models")

                    Button(action: { vm.stopAllModels() }) {
                        Text("Stop All Native Models")
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                    }
                    .buttonStyle(.bordered)
                    .foregroundColor(.red)
                    .help("Stop all running native models")
                }
                        }
                    }
                    .tabItem {
                        Label("Native Models", systemImage: "desktopcomputer")
                    }

                    // MARK: - Docker Models Tab
                    ScrollView {
                        VStack(alignment: .leading, spacing: 6) {
                Text("Docker Models")
                    .font(.headline)
                    .padding(.horizontal, 8)

                if vm.dockerRows.isEmpty {
                    Text("No Docker models running")
                        .padding(.horizontal, 8)
                } else {
                    ForEach(vm.dockerRows, id: \.name) { row in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                // Enhanced health indicator
                                Circle()
                                    .fill(vm.healthColor(for: row))
                                    .frame(width: 10, height: 10)

                                VStack(alignment: .leading, spacing: 2) {
                                    HStack(spacing: 6) {
                                        Text(row.name)
                                            .font(.headline)
                                        if let format = row.format {
                                            Text(format.uppercased())
                                                .font(.caption2)
                                                .padding(.horizontal, 6)
                                                .padding(.vertical, 2)
                                                .background(vm.formatBadgeColor(format))
                                                .foregroundColor(.white)
                                                .cornerRadius(3)
                                        }
                                        if let q = row.quantization {
                                            Text(q)
                                                .font(.caption2)
                                                .padding(.horizontal, 5)
                                                .padding(.vertical, 2)
                                                .background(Color.gray.opacity(0.25))
                                                .cornerRadius(3)
                                        }
                                        if let sz = row.file_size_gb, sz > 0 {
                                            Text(String(format: "%.1f GB", sz))
                                                .font(.caption2)
                                                .foregroundColor(.secondary)
                                        }
                                    }

                                    if let fn = row.model_filename, !fn.isEmpty {
                                        Text(fn)
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                            .lineLimit(1)
                                            .truncationMode(.middle)
                                    }

                                    Text(vm.healthStatus(for: row))
                                        .font(.caption)
                                        .foregroundColor(.secondary)

                                    if let desc = row.description, !desc.isEmpty {
                                        Text(desc)
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                            .italic()
                                            .lineLimit(2)
                                    }

                                    if row.up, let ram = row.ram_mb, ram > 0 {
                                        HStack(spacing: 8) {
                                            Text(String(format: "RAM: %.1f GB", ram / 1024.0))
                                                .font(.caption2)
                                                .foregroundColor(.secondary)
                                            if let cpu = row.cpu_percent {
                                                Text(String(format: "CPU: %.1f%%", cpu))
                                                    .font(.caption2)
                                                    .foregroundColor(.secondary)
                                            }
                                        }
                                    }
                                }

                                Spacer()

                                VStack(alignment: .trailing) {
                                    Text("\(row.host):\(row.port)")
                                        .font(.caption)
                                    if let ms = row.latency_ms, ms > 0 {
                                        Text("\(ms) ms")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                    if let uptime = row.uptime, !uptime.isEmpty {
                                        Text("up \(uptime)")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
                            .padding(.horizontal, 8)

                            // Startup progress (shows download / loading status)
                            if let progress = vm.startupProgress[row.name] {
                                VStack(alignment: .leading, spacing: 2) {
                                    HStack(spacing: 6) {
                                        ProgressView()
                                            .scaleEffect(0.6)
                                            .frame(width: 14, height: 14)
                                        Text(progress.status)
                                            .font(.caption)
                                            .foregroundColor(.blue)
                                        if let detail = progress.detail {
                                            Text("(\(detail))")
                                                .font(.caption2)
                                                .foregroundColor(.secondary)
                                        }
                                        Spacer()
                                    }
                                    if let pct = progress.progress {
                                        ProgressView(value: pct)
                                            .progressViewStyle(.linear)
                                            .frame(height: 4)
                                    }
                                }
                                .padding(.horizontal, 18)
                                .padding(.vertical, 4)
                            }

                            // Mode selector (only shown when stopped and not starting).
                            // Uses availableModes(for:) so MLX rows get MLX-specific modes.
                            if !row.up && vm.startupProgress[row.name] == nil {
                                let modes = vm.availableModes(for: row)
                                HStack(spacing: 4) {
                                    Text("Mode:")
                                        .font(.caption)
                                        .foregroundColor(.secondary)

                                    Picker("", selection: Binding(
                                        get: { vm.selectedModes[row.name] ?? "basic" },
                                        set: { newMode in
                                            vm.selectedModes[row.name] = newMode
                                            vm.saveMode(for: row.name, mode: newMode)
                                        }
                                    )) {
                                        ForEach(modes, id: \.tag) { mode in
                                            Text(mode.label).tag(mode.tag)
                                        }
                                    }
                                    .pickerStyle(.segmented)
                                    .labelsHidden()
                                }
                                .padding(.horizontal, 18)
                                .padding(.vertical, 4)
                            }

                            // Control buttons (Docker version)
                            HStack {
                                Button("Start") { vm.startWithScript(name: row.name, isDocker: true) }
                                    .disabled(row.up || vm.startupProgress[row.name] != nil)
                                Button("Stop") { vm.stop(name: row.name, isDocker: true) }
                                    .disabled(!row.up)
                                Button("Restart") { vm.restart(name: row.name, isDocker: true) }

                                if row.up {
                                    Button("Chat") { vm.openChat(name: row.name) }
                                }

                                Button("Monitor") { vm.toggleMonitoring(name: row.name) }
                                    .foregroundColor(vm.isMonitored(name: row.name) ? .orange : .blue)

                                Button("Logs") { vm.tailLogs(name: row.name, isDocker: true) }
                            }
                            .buttonStyle(.plain)
                            .font(.caption)
                            .padding(.leading, 18)
                        }
                        Divider()
                    }
                }
                HStack {
                    Button(action: { vm.startAllModels(isDocker: true) }) {
                        Text("Start All Docker Models")
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                    }
                    .buttonStyle(.bordered)
                    .help("Start all Docker containers")

                    Button(action: { vm.stopAllModels(isDocker: true) }) {
                        Text("Stop All Docker Models")
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                    }
                    .buttonStyle(.bordered)
                    .foregroundColor(.red)
                    .help("Stop all Docker containers")
                }
                        }
                    }
                    .tabItem {
                        Label("Docker Models", systemImage: "shippingbox")
                    }
                }
                .frame(minHeight: 700, maxHeight: 900)

                Divider()

                // MARK: - Logging Section
                if let logging = vm.loggingConfig {
                    HStack {
                        Text("Logging")
                            .font(.headline)
                        Spacer()
                        Text(logging.enabled ? "ON" : "OFF")
                            .font(.caption)
                            .foregroundColor(logging.enabled ? .blue : .red)
                    }
                    .padding(.horizontal, 8)

                    HStack {
                        Button(logging.enabled ? "Disable Logs" : "Enable Logs") {
                            vm.toggleLogging()
                        }
                        Button(logging.timestamps ? "Timestamps: ON" : "Timestamps: OFF") {
                            vm.toggleTimestamps()
                        }
                        .foregroundColor(logging.timestamps ? .blue : .secondary)
                    }
                    .buttonStyle(.borderless)
                    .font(.caption)
                    .padding(.horizontal, 8)

                    Divider()
                }

                Button("Download Models") { vm.openModelDownloader() }
                Divider()
                Button("Refresh") { vm.refresh() }
                Button("Open Config") { vm.openConfig() }
                Button("Open CLI") { vm.openCLI() }
                Divider()
                Button("Preferences...") { vm.openPreferences() }
                    .keyboardShortcut(",", modifiers: .command)
                Divider()
                Button("Help") { vm.openHelp() }
                Button("About") { vm.openAbout() }
                Divider()
                Button("Quit") { NSApplication.shared.terminate(nil) }
            }
            .task { vm.startPolling() }
            .padding(6)
        } label: {
            HStack(spacing: 3) {
                Image(systemName: "brain.head.profile")
                    .accessibilityLabel("llamaCPPManager menu")
                    .accessibilityHint("Opens the model management menu")
                Circle()
                    .fill(vm.overallStatusColor)
                    .frame(width: 8, height: 8)
                    .overlay(
                        Circle()
                            .fill(vm.overallStatusColor)
                            .frame(width: 8, height: 8)
                            .opacity(vm.isAnyModelRunning ? 0.6 : 0)
                            .animation(
                                vm.isAnyModelRunning ?
                                Animation.easeInOut(duration: 1.0)
                                    .repeatForever(autoreverses: true) :
                                .default,
                                value: vm.isAnyModelRunning
                            )
                    )
            }
        }
        .menuBarExtraStyle(.window)
    }
}




