// File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/ModelDownloaderView.swift
// Description: SwiftUI view for browsing and downloading models from Hugging Face
// Author: Libor Ballaty <libor@arionetworks.com>
// Created: 2025-10-10

import SwiftUI
import AppKit

struct ModelInfo: Identifiable, Codable {
    let id: String
    let name: String
    let repoId: String
    let filename: String?  // Optional for MLX models
    let sizeGB: Double
    let ramGB: Double  // Can be int or float (e.g., 13.5 for some MLX models)
    let useCase: String
    let description: String
    let format: String?  // "gguf" or "mlx"
    let version: String?
    let requires: String?  // Hardware requirements for MLX
    var isDownloaded: Bool = false

    enum CodingKeys: String, CodingKey {
        case name, repoId = "repo_id", filename
        case sizeGB = "size_gb", ramGB = "ram_gb"
        case useCase = "use_case", description
        case format, version, requires
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.name = try container.decode(String.self, forKey: .name)
        self.id = self.name
        self.repoId = try container.decode(String.self, forKey: .repoId)
        self.filename = try container.decodeIfPresent(String.self, forKey: .filename)
        self.sizeGB = try container.decode(Double.self, forKey: .sizeGB)
        self.ramGB = try container.decode(Double.self, forKey: .ramGB)
        self.useCase = try container.decode(String.self, forKey: .useCase)
        self.description = try container.decode(String.self, forKey: .description)
        self.format = try container.decodeIfPresent(String.self, forKey: .format)
        self.version = try container.decodeIfPresent(String.self, forKey: .version)
        self.requires = try container.decodeIfPresent(String.self, forKey: .requires)
        self.isDownloaded = false
    }

    init(name: String, repoId: String, filename: String?, sizeGB: Double, ramGB: Double, useCase: String, description: String, format: String? = nil, version: String? = nil, requires: String? = nil, isDownloaded: Bool = false) {
        self.id = name
        self.name = name
        self.repoId = repoId
        self.filename = filename
        self.sizeGB = sizeGB
        self.ramGB = ramGB
        self.useCase = useCase
        self.description = description
        self.format = format
        self.version = version
        self.requires = requires
        self.isDownloaded = isDownloaded
    }
}

struct DownloadProgress: Identifiable {
    let id: String
    var bytesDownloaded: Int64
    var totalBytes: Int64
    var speedMBps: Double
    var etaSeconds: Int
    var status: String

    var percentComplete: Double {
        guard totalBytes > 0 else { return 0.0 }
        return Double(bytesDownloaded) / Double(totalBytes)
    }
}

// Wrapper for catalog response with metadata
struct CatalogResponse: Codable {
    let models: [ModelInfo]
    let catalog_fetched_at: String?
    let catalog_source: String?

    enum CodingKeys: String, CodingKey {
        case models
        case catalog_fetched_at = "catalog_fetched_at"
        case catalog_source = "catalog_source"
    }
}

final class DownloadViewModel: ObservableObject {
    @Published var availableModels: [ModelInfo] = []
    @Published var downloads: [String: DownloadProgress] = [:]
    @Published var filterFormat: String = "All Formats"
    @Published var filterSize: String = "All Sizes"
    @Published var filterUseCase: String = "All Use Cases"
    @Published var searchText: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var catalogFetchedAt: String?
    @Published var catalogSource: String?

    private let cliService: CLIService

    let formatFilters = ["All Formats", "GGUF (llama.cpp)", "MLX (Apple Silicon)"]
    let sizeFilters = ["All Sizes", "Tiny (<2GB)", "Small (2-10GB)", "Medium (10-25GB)", "Large (25-50GB)", "Very Large (>50GB)"]
    let useCaseFilters = ["All Use Cases", "Agentic AI", "Coding", "Compliance", "General"]

    init(cliService: CLIService) {
        self.cliService = cliService
    }

    func fetchAvailableModels(refresh: Bool = false) {
        isLoading = true
        errorMessage = nil

        Task { @MainActor in
            do {
                var args = ["models", "list", "--available", "--json"]
                if refresh {
                    args.append("--refresh")
                }

                let output = try await cliService.runAndCapture(args)
                let data = output.data(using: .utf8) ?? Data()
                do {
                    // Try to decode as new format first (with metadata)
                    if let catalogResponse = try? JSONDecoder().decode(CatalogResponse.self, from: data) {
                        var models = catalogResponse.models
                        for i in 0..<models.count {
                            models[i].isDownloaded = await checkIfDownloaded(modelName: models[i].name)
                        }
                        self.availableModels = models
                        self.catalogFetchedAt = catalogResponse.catalog_fetched_at
                        self.catalogSource = catalogResponse.catalog_source
                    } else {
                        // Fallback to old format (array only)
                        var models = try JSONDecoder().decode([ModelInfo].self, from: data)
                        for i in 0..<models.count {
                            models[i].isDownloaded = await checkIfDownloaded(modelName: models[i].name)
                        }
                        self.availableModels = models
                    }
                } catch {
                    throw CLIError.parseError(cmd: "models list --available --json", raw: output)
                }
            } catch CLIError.notFound {
                self.errorMessage = "CLI not found. Install with: pip install -e . in the llamaCPPManager directory."
            } catch CLIError.commandFailed(let cmd, let exitCode, let stderr) {
                let detail = stderr.isEmpty ? "no stderr output" : stderr
                self.errorMessage = "Command failed (exit \(exitCode)): \(detail)"
                AppLogger.log("fetchAvailableModels commandFailed [\(cmd)] exit=\(exitCode): \(stderr)", level: .error)
            } catch CLIError.parseError(_, let raw) {
                self.errorMessage = "CLI returned unexpected output. Check Console.app → com.llamacpp.manager for details. Raw: \(raw.prefix(200))"
                AppLogger.log("fetchAvailableModels parseError — raw output: \(raw.prefix(500))", level: .error)
            } catch {
                self.errorMessage = "Unexpected error: \(error.localizedDescription)"
                AppLogger.log("fetchAvailableModels error: \(error)", level: .error)
            }
            isLoading = false
        }
    }

    private func checkIfDownloaded(modelName: String) async -> Bool {
        // Check if model directory exists and contains at least one .gguf file
        let homeDir = FileManager.default.homeDirectoryForCurrentUser
        let modelDir = homeDir.appendingPathComponent("llms").appendingPathComponent(modelName)

        // First check if directory exists
        var isDir: ObjCBool = false
        guard FileManager.default.fileExists(atPath: modelDir.path, isDirectory: &isDir),
              isDir.boolValue else {
            return false
        }

        // Then check for .gguf files in the directory
        do {
            let contents = try FileManager.default.contentsOfDirectory(atPath: modelDir.path)
            return contents.contains { $0.lowercased().hasSuffix(".gguf") }
        } catch {
            return false
        }
    }

    func downloadModel(name: String) {
        // Find expected size from catalog
        let expectedGB = availableModels.first(where: { $0.name == name })?.sizeGB ?? 0
        let expectedBytes = Int64(expectedGB * 1_073_741_824)  // GB -> bytes

        downloads[name] = DownloadProgress(
            id: name,
            bytesDownloaded: 0,
            totalBytes: expectedBytes,
            speedMBps: 0.0,
            etaSeconds: 0,
            status: "Starting download..."
        )

        let modelDir = "\(NSHomeDirectory())/llms/\(name)"

        // Background polling task — monitors directory size while download runs
        let pollTask = Task { @MainActor in
            var lastBytes: Int64 = 0
            var lastTime = Date()

            while !Task.isCancelled && downloads[name] != nil {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard !Task.isCancelled else { break }

                let bytes = directorySize(path: modelDir)
                let now = Date()
                let elapsed = now.timeIntervalSince(lastTime)
                let speedBps = elapsed > 0 ? Double(bytes - lastBytes) / elapsed : 0
                let speedMBps = speedBps / 1_048_576.0

                let etaSec: Int
                if speedBps > 0 && expectedBytes > bytes {
                    etaSec = Int(Double(expectedBytes - bytes) / speedBps)
                } else {
                    etaSec = 0
                }

                let status: String
                if bytes == 0 {
                    status = "Connecting to HuggingFace..."
                } else if expectedBytes > 0 && bytes >= expectedBytes {
                    status = "Finalizing..."
                } else {
                    status = "Downloading..."
                }

                if var prog = self.downloads[name] {
                    prog.bytesDownloaded = bytes
                    prog.speedMBps = speedMBps
                    prog.etaSeconds = etaSec
                    prog.status = status
                    self.downloads[name] = prog
                }

                lastBytes = bytes
                lastTime = now
            }
        }

        // Main download task — runs the CLI and waits for completion
        Task {
            do {
                _ = try await cliService.runAndCapture(["models", "download", name])
                pollTask.cancel()

                await MainActor.run {
                    if let index = availableModels.firstIndex(where: { $0.name == name }) {
                        availableModels[index].isDownloaded = true
                    }
                    downloads.removeValue(forKey: name)
                }

                // Configure the model after download
                _ = try? await cliService.runAndCapture(["config", "add", name, "~/llms/\(name)/", "--port", "auto"])
            } catch CLIError.commandFailed(_, let exitCode, let stderr) {
                pollTask.cancel()
                await MainActor.run {
                    errorMessage = friendlyDownloadError(name: name, exitCode: exitCode, stderr: stderr)
                    downloads.removeValue(forKey: name)
                }
            } catch {
                pollTask.cancel()
                await MainActor.run {
                    errorMessage = "Failed to download \(name): \(error.localizedDescription)"
                    downloads.removeValue(forKey: name)
                }
            }
        }
    }

    private func friendlyDownloadError(name: String, exitCode: Int32, stderr: String) -> String {
        let lower = stderr.lowercased()

        if lower.contains("404") || lower.contains("entrynotfound") || lower.contains("not found") {
            return "❌ \(name): File not found on HuggingFace. The model entry in the catalog may be incorrect or the model was removed. Try refreshing the catalog or check the HuggingFace page directly."
        }
        if lower.contains("401") || lower.contains("403") || lower.contains("unauthorized") || lower.contains("gated") {
            return "🔒 \(name): This model requires authentication. Set HF_TOKEN environment variable with a HuggingFace token that has access to this model."
        }
        if lower.contains("connection") || lower.contains("timeout") || lower.contains("network") {
            return "🌐 \(name): Network error. Check your internet connection and try again."
        }
        if lower.contains("no space") || lower.contains("disk full") {
            return "💾 \(name): Not enough disk space. Free up space and try again."
        }
        if lower.contains("permission") || lower.contains("denied") {
            return "🚫 \(name): Permission denied. Check write access to ~/llms/."
        }

        // Generic with last line of stderr as hint
        let lastLine = stderr.split(separator: "\n").last.map(String.init) ?? ""
        let detail = lastLine.isEmpty ? "" : "\nDetail: \(lastLine.prefix(200))"
        return "Failed to download \(name) (exit \(exitCode))\(detail)"
    }

    private func directorySize(path: String) -> Int64 {
        let url = URL(fileURLWithPath: path)
        guard let enumerator = FileManager.default.enumerator(
            at: url,
            includingPropertiesForKeys: [.fileSizeKey, .isRegularFileKey],
            options: [.skipsHiddenFiles]
        ) else { return 0 }

        var total: Int64 = 0
        for case let fileURL as URL in enumerator {
            if let values = try? fileURL.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey]),
               values.isRegularFile == true {
                total += Int64(values.fileSize ?? 0)
            }
        }
        return total
    }

    func configureDownloadedModel(name: String) {
        // TODO: Add model to configuration
        Task {
            do {
                _ = try await cliService.run(["config", "add", name, "~/llms/\(name)/", "--port", "auto"])
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to configure \(name): \(error.localizedDescription)"
                }
            }
        }
    }

    func showModelInfo(model: ModelInfo) {
        let downloadLocation = "\(NSHomeDirectory())/llms/\(model.name)/"
        let isDownloaded = model.isDownloaded ? "✅ Yes" : "❌ No"

        var infoText = """
        Model: \(model.name)

        Downloaded: \(isDownloaded)
        """

        if model.isDownloaded {
            infoText += "\nLocation: \(downloadLocation)"
        }

        infoText += """

        Repository: \(model.repoId)
        Filename: \(model.filename ?? "Auto-detected")
        Format: \(model.format?.uppercased() ?? "GGUF")
        Version: \(model.version ?? "N/A")
        """

        if let requires = model.requires {
            infoText += "\nRequires: \(requires)"
        }

        infoText += """

        Size: \(String(format: "%.1f", model.sizeGB)) GB
        RAM Required: \(model.ramGB) GB

        Use Case: \(model.useCase)

        Description:
        \(model.description)
        """

        let alert = NSAlert()
        alert.messageText = "Model Information"
        alert.informativeText = infoText
        alert.alertStyle = .informational
        alert.addButton(withTitle: "OK")

        // Create a window to display the alert at floating level
        if let window = NSApp.windows.first(where: { $0.title == "Model Downloader" }) {
            alert.beginSheetModal(for: window) { _ in }
        } else {
            // If no parent window, show as standalone
            let response = alert.runModal()
            _ = response
        }
    }

    var filteredModels: [ModelInfo] {
        let filtered = availableModels.filter { model in
            // Search filter (name or description)
            let searchMatch: Bool
            if searchText.trimmingCharacters(in: .whitespaces).isEmpty {
                searchMatch = true
            } else {
                let query = searchText.lowercased()
                searchMatch = model.name.lowercased().contains(query) ||
                              model.description.lowercased().contains(query) ||
                              model.useCase.lowercased().contains(query) ||
                              model.repoId.lowercased().contains(query)
            }
            if !searchMatch { return false }

            // Format filter
            let formatMatch: Bool
            switch filterFormat {
            case "GGUF (llama.cpp)":
                formatMatch = model.format == "gguf"
            case "MLX (Apple Silicon)":
                formatMatch = model.format == "mlx"
            default:
                formatMatch = true
            }

            // Size filter
            let sizeMatch: Bool
            switch filterSize {
            case "Tiny (<2GB)":
                sizeMatch = model.sizeGB < 2
            case "Small (2-10GB)":
                sizeMatch = model.sizeGB >= 2 && model.sizeGB < 10
            case "Medium (10-25GB)":
                sizeMatch = model.sizeGB >= 10 && model.sizeGB < 25
            case "Large (25-50GB)":
                sizeMatch = model.sizeGB >= 25 && model.sizeGB < 50
            case "Very Large (>50GB)":
                sizeMatch = model.sizeGB >= 50
            default:
                sizeMatch = true
            }

            let useCaseMatch: Bool
            switch filterUseCase {
            case "Agentic AI":
                useCaseMatch = model.useCase.lowercased().contains("agentic") ||
                               model.useCase.lowercased().contains("agent") ||
                               model.useCase.lowercased().contains("workflow")
            case "Coding":
                useCaseMatch = model.useCase.lowercased().contains("code") ||
                               model.useCase.lowercased().contains("coding") ||
                               model.description.lowercased().contains("code") ||
                               model.description.lowercased().contains("debugging")
            case "Compliance":
                useCaseMatch = model.useCase.lowercased().contains("compliance") ||
                               model.useCase.lowercased().contains("analysis") ||
                               model.description.lowercased().contains("report")
            case "General":
                useCaseMatch = !model.useCase.lowercased().contains("agentic") &&
                               !model.useCase.lowercased().contains("code") &&
                               !model.useCase.lowercased().contains("compliance")
            default:
                useCaseMatch = true
            }

            let result = formatMatch && sizeMatch && useCaseMatch

            if !result {
                AppLogger.log("Filter excluded '\(model.name)': size=\(model.sizeGB)GB filter=\(filterSize), useCase=\(model.useCase) filter=\(filterUseCase)", level: .debug)
            }

            return result
        }

        AppLogger.log("filteredModels count: \(filtered.count)", level: .debug)

        return filtered
    }
}

struct ModelDownloaderView: View {
    @StateObject var viewModel: DownloadViewModel
    @Environment(\.dismiss) var dismiss

    private func formatRelativeTime(_ isoTimestamp: String) -> String {
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: isoTimestamp) else {
            return "unknown"
        }

        let now = Date()
        let seconds = now.timeIntervalSince(date)

        if seconds < 60 {
            return "just now"
        } else if seconds < 3600 {
            let minutes = Int(seconds / 60)
            return minutes == 1 ? "1 minute ago" : "\(minutes) minutes ago"
        } else if seconds < 86400 {
            let hours = Int(seconds / 3600)
            return hours == 1 ? "1 hour ago" : "\(hours) hours ago"
        } else {
            let days = Int(seconds / 86400)
            return days == 1 ? "1 day ago" : "\(days) days ago"
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Model Downloader")
                    .font(.title2)
                    .fontWeight(.semibold)
                Spacer()
                if viewModel.isLoading {
                    ProgressView()
                        .scaleEffect(0.75)
                }
                Button(action: {
                    viewModel.fetchAvailableModels(refresh: true)
                }) {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(.borderless)
                .help("Refresh catalog from HuggingFace")
                .disabled(viewModel.isLoading)
                Button("Close") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))

            // Search box
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                TextField("Search by name, description, or repo...", text: $viewModel.searchText)
                    .textFieldStyle(.roundedBorder)
                if !viewModel.searchText.isEmpty {
                    Button(action: { viewModel.searchText = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal)
            .padding(.top, 8)

            // Filters
            HStack(spacing: 12) {
                Picker("Format", selection: $viewModel.filterFormat) {
                    ForEach(viewModel.formatFilters, id: \.self) { filter in
                        Text(filter).tag(filter)
                    }
                }
                .pickerStyle(.menu)
                .frame(width: 200)

                Picker("Size", selection: $viewModel.filterSize) {
                    ForEach(viewModel.sizeFilters, id: \.self) { filter in
                        Text(filter).tag(filter)
                    }
                }
                .pickerStyle(.menu)
                .frame(width: 180)

                Picker("Use Case", selection: $viewModel.filterUseCase) {
                    ForEach(viewModel.useCaseFilters, id: \.self) { filter in
                        Text(filter).tag(filter)
                    }
                }
                .pickerStyle(.menu)
                .frame(width: 180)

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text("\(viewModel.filteredModels.count) models")
                        .foregroundColor(.secondary)
                        .font(.caption)

                    if let fetchedAt = viewModel.catalogFetchedAt {
                        Text("Updated: \(formatRelativeTime(fetchedAt))")
                            .foregroundColor(.secondary)
                            .font(.caption2)
                    }

                    if let source = viewModel.catalogSource {
                        Text("Source: \(source.uppercased())")
                            .foregroundColor(.secondary)
                            .font(.caption2)
                    }
                }
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor).opacity(0.5))

            Divider()

            // Error message
            if let error = viewModel.errorMessage {
                HStack(spacing: 8) {
                    Image(systemName: "exclamationmark.triangle")
                        .foregroundColor(.orange)
                    Text(error)
                        .foregroundColor(.orange)
                        .font(.caption)
                        .textSelection(.enabled)
                        .lineLimit(nil)
                    Spacer()
                    Button(action: {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(error, forType: .string)
                    }) {
                        Image(systemName: "doc.on.doc")
                            .font(.caption)
                    }
                    .buttonStyle(.borderless)
                    .help("Copy error message")
                    Button("Dismiss") {
                        viewModel.errorMessage = nil
                    }
                    .buttonStyle(.borderless)
                    .font(.caption)
                }
                .padding()
                .background(Color.orange.opacity(0.1))
                .cornerRadius(6)
            }

            // Models list
            if viewModel.isLoading {
                VStack {
                    Spacer()
                    ProgressView()
                    Text("Loading available models...")
                        .foregroundColor(.secondary)
                        .padding(.top)
                    Spacer()
                }
            } else if viewModel.filteredModels.isEmpty {
                VStack {
                    Spacer()
                    Image(systemName: "tray")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)
                    Text("No models found")
                        .foregroundColor(.secondary)
                        .padding(.top)
                    Spacer()
                }
            } else {
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(viewModel.filteredModels) { model in
                            ModelCard(model: model, viewModel: viewModel)
                        }
                    }
                    .padding()
                }
            }
        }
        .frame(minWidth: 700, minHeight: 600)
        .onAppear {
            viewModel.fetchAvailableModels()
        }
    }
}

// Helper to format ETA from seconds
private func formatETA(_ seconds: Int) -> String {
    if seconds < 60 { return "\(seconds)s" }
    if seconds < 3600 { return "\(seconds / 60)m \(seconds % 60)s" }
    let h = seconds / 3600
    let m = (seconds % 3600) / 60
    return "\(h)h \(m)m"
}

struct ModelCard: View {
    let model: ModelInfo
    @ObservedObject var viewModel: DownloadViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Header
            HStack {
                Image(systemName: "brain.head.profile")
                    .font(.title2)
                    .foregroundColor(.blue)

                VStack(alignment: .leading, spacing: 2) {
                    Text(model.name)
                        .font(.headline)
                    Text(model.description)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(2)
                }

                Spacer()

                // Status badge
                if model.isDownloaded {
                    HStack(spacing: 4) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text("Downloaded")
                            .font(.caption)
                            .foregroundColor(.green)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.green.opacity(0.1))
                    .cornerRadius(8)
                }
            }

            // Format and Version badges
            HStack(spacing: 8) {
                // Format badge
                if let format = model.format {
                    Text(format.uppercased())
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(format == "mlx" ? Color.purple.opacity(0.2) : Color.blue.opacity(0.2))
                        .foregroundColor(format == "mlx" ? .purple : .blue)
                        .cornerRadius(4)
                }

                // Version badge
                if let version = model.version {
                    Text("v\(version)")
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.gray.opacity(0.2))
                        .foregroundColor(.secondary)
                        .cornerRadius(4)
                }
            }

            // Metadata
            HStack(spacing: 16) {
                Label("\(String(format: "%.1f", model.sizeGB)) GB", systemImage: "externaldrive")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Label("~\(model.ramGB) GB RAM", systemImage: "memorychip")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            // Requirements (for MLX models)
            if let requires = model.requires {
                HStack(spacing: 4) {
                    Image(systemName: "cpu")
                    Text(requires)
                }
                .font(.caption2)
                .foregroundColor(.orange)
            }

            // Use case
            Text(model.useCase)
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.vertical, 4)

            // Actions
            HStack(spacing: 8) {
                if model.isDownloaded {
                    Button("Configure") {
                        viewModel.configureDownloadedModel(name: model.name)
                    }
                    .buttonStyle(.borderedProminent)

                    Button("Re-download") {
                        viewModel.downloadModel(name: model.name)
                    }
                    .buttonStyle(.bordered)
                } else if let progress = viewModel.downloads[model.name] {
                    // Show download progress
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(spacing: 8) {
                            ProgressView()
                                .scaleEffect(0.6)
                                .frame(width: 14, height: 14)
                            ProgressView(value: progress.percentComplete)
                                .progressViewStyle(.linear)
                            Text("\(Int(progress.percentComplete * 100))%")
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .frame(width: 40, alignment: .trailing)
                        }

                        HStack {
                            Text(progress.status)
                                .font(.caption2)
                                .foregroundColor(.blue)
                            Spacer()
                            if progress.bytesDownloaded > 0 {
                                let downloaded = ByteCountFormatter.string(fromByteCount: progress.bytesDownloaded, countStyle: .file)
                                let total = ByteCountFormatter.string(fromByteCount: progress.totalBytes, countStyle: .file)
                                Text("\(downloaded) / \(total)")
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
                                    Text("ETA: \(formatETA(progress.etaSeconds))")
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                    }
                } else {
                    Button("Download") {
                        viewModel.downloadModel(name: model.name)
                    }
                    .buttonStyle(.borderedProminent)

                    Button("Info") {
                        viewModel.showModelInfo(model: model)
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }
}
