// File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/ModelDownloaderView.swift
// Description: SwiftUI view for browsing and downloading models from Hugging Face
// Author: Libor Ballaty <libor@arionetworks.com>
// Created: 2025-10-10

import SwiftUI

struct ModelInfo: Identifiable, Codable {
    let id: String
    let name: String
    let repoId: String
    let filename: String
    let sizeGB: Double
    let ramGB: Int
    let useCase: String
    let description: String
    var isDownloaded: Bool = false

    enum CodingKeys: String, CodingKey {
        case name, repoId = "repo_id", filename
        case sizeGB = "size_gb", ramGB = "ram_gb"
        case useCase = "use_case", description
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.name = try container.decode(String.self, forKey: .name)
        self.id = self.name
        self.repoId = try container.decode(String.self, forKey: .repoId)
        self.filename = try container.decode(String.self, forKey: .filename)
        self.sizeGB = try container.decode(Double.self, forKey: .sizeGB)
        self.ramGB = try container.decode(Int.self, forKey: .ramGB)
        self.useCase = try container.decode(String.self, forKey: .useCase)
        self.description = try container.decode(String.self, forKey: .description)
        self.isDownloaded = false
    }

    init(name: String, repoId: String, filename: String, sizeGB: Double, ramGB: Int, useCase: String, description: String, isDownloaded: Bool = false) {
        self.id = name
        self.name = name
        self.repoId = repoId
        self.filename = filename
        self.sizeGB = sizeGB
        self.ramGB = ramGB
        self.useCase = useCase
        self.description = description
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

final class DownloadViewModel: ObservableObject {
    @Published var availableModels: [ModelInfo] = []
    @Published var downloads: [String: DownloadProgress] = [:]
    @Published var filterSize: String = "All Sizes"
    @Published var filterUseCase: String = "All Use Cases"
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?

    private let cliService: CLIService

    let sizeFilters = ["All Sizes", "Small (<10GB)", "Medium (10-20GB)", "Large (>20GB)"]
    let useCaseFilters = ["All Use Cases", "Agentic AI", "Coding", "Compliance", "General"]

    init(cliService: CLIService) {
        self.cliService = cliService
    }

    func fetchAvailableModels() {
        isLoading = true
        errorMessage = nil

        Task { @MainActor in
            do {
                let output = try await cliService.runAndCapture(["models", "list", "--available", "--json"])
                let data = output.data(using: .utf8) ?? Data()

                // Parse JSON array of models
                var models = try JSONDecoder().decode([ModelInfo].self, from: data)

                // Check which models are downloaded
                for i in 0..<models.count {
                    models[i].isDownloaded = await checkIfDownloaded(modelName: models[i].name)
                }

                self.availableModels = models
            } catch {
                self.errorMessage = "Failed to fetch models: \(error.localizedDescription)"
                self.availableModels = []
            }
            isLoading = false
        }
    }

    private func checkIfDownloaded(modelName: String) async -> Bool {
        // Check if model directory exists in ~/llms/
        let homeDir = FileManager.default.homeDirectoryForCurrentUser
        let modelDir = homeDir.appendingPathComponent("llms").appendingPathComponent(modelName)
        return FileManager.default.fileExists(atPath: modelDir.path)
    }

    func downloadModel(name: String) {
        // Initialize download progress
        downloads[name] = DownloadProgress(
            id: name,
            bytesDownloaded: 0,
            totalBytes: 0,
            speedMBps: 0.0,
            etaSeconds: 0,
            status: "Starting..."
        )

        Task {
            do {
                // Start download in background
                _ = try await cliService.run(["models", "download", name])

                // Update model as downloaded
                await MainActor.run {
                    if let index = availableModels.firstIndex(where: { $0.name == name }) {
                        availableModels[index].isDownloaded = true
                    }
                    downloads.removeValue(forKey: name)
                }
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to download \(name): \(error.localizedDescription)"
                    downloads.removeValue(forKey: name)
                }
            }
        }
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

    var filteredModels: [ModelInfo] {
        let filtered = availableModels.filter { model in
            let sizeMatch: Bool
            switch filterSize {
            case "Small (<10GB)":
                sizeMatch = model.sizeGB < 10
            case "Medium (10-20GB)":
                sizeMatch = model.sizeGB >= 10 && model.sizeGB <= 20
            case "Large (>20GB)":
                sizeMatch = model.sizeGB > 20
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

            let result = sizeMatch && useCaseMatch

            // Debug logging
            if !result {
                print("Filtered out model: \(model.name)")
                print("  Size: \(model.sizeGB) GB (filter: \(filterSize))")
                print("  Use Case: \(model.useCase) (filter: \(filterUseCase))")
                print("  Size Match: \(sizeMatch)")
                print("  Use Case Match: \(useCaseMatch)")
            }

            return result
        }

        // Log total count of filtered models
        print("Total filtered models: \(filtered.count)")

        return filtered
    }
}

struct ModelDownloaderView: View {
    @StateObject var viewModel: DownloadViewModel
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Model Downloader")
                    .font(.title2)
                    .fontWeight(.semibold)
                Spacer()
                Button("Close") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))

            // Filters
            HStack(spacing: 12) {
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

                Text("\(viewModel.filteredModels.count) models")
                    .foregroundColor(.secondary)
                    .font(.caption)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor).opacity(0.5))

            Divider()

            // Error message
            if let error = viewModel.errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle")
                        .foregroundColor(.orange)
                    Text(error)
                        .foregroundColor(.orange)
                        .font(.caption)
                    Spacer()
                    Button("Dismiss") {
                        viewModel.errorMessage = nil
                    }
                    .buttonStyle(.borderless)
                    .font(.caption)
                }
                .padding()
                .background(Color.orange.opacity(0.1))
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

            // Metadata
            HStack(spacing: 16) {
                Label("\(String(format: "%.2f", model.sizeGB)) GB", systemImage: "externaldrive")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Label("~\(model.ramGB) GB RAM", systemImage: "memorychip")
                    .font(.caption)
                    .foregroundColor(.secondary)
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
                        HStack {
                            ProgressView(value: progress.percentComplete)
                                .progressViewStyle(.linear)
                            Text("\(Int(progress.percentComplete * 100))%")
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .frame(width: 40, alignment: .trailing)
                        }

                        Text(progress.status)
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                } else {
                    Button("Download") {
                        viewModel.downloadModel(name: model.name)
                    }
                    .buttonStyle(.borderedProminent)

                    Button("Info") {
                        // TODO: Show detailed model info
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
