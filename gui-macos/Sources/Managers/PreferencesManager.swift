import Foundation
import Combine

final class PreferencesManager: ObservableObject {
    static let shared = PreferencesManager()

    private let defaults = UserDefaults.standard
    private let prefix = "com.llamacpp.manager."

    // MARK: - General Settings

    @Published var refreshInterval: Int {
        didSet { save(refreshInterval, forKey: "refreshInterval") }
    }

    @Published var autoStartModels: Bool {
        didSet { save(autoStartModels, forKey: "autoStartModels") }
    }

    @Published var showNotifications: Bool {
        didSet { save(showNotifications, forKey: "showNotifications") }
    }

    // MARK: - Display Settings

    @Published var showStoppedModels: Bool {
        didSet { save(showStoppedModels, forKey: "showStoppedModels") }
    }

    @Published var showInfrastructure: Bool {
        didSet { save(showInfrastructure, forKey: "showInfrastructure") }
    }

    @Published var viewMode: ViewMode {
        didSet { save(viewMode.rawValue, forKey: "viewMode") }
    }

    @Published var showUptime: Bool {
        didSet { save(showUptime, forKey: "showUptime") }
    }

    @Published var showPortNumbers: Bool {
        didSet { save(showPortNumbers, forKey: "showPortNumbers") }
    }

    @Published var showHealthStatus: Bool {
        didSet { save(showHealthStatus, forKey: "showHealthStatus") }
    }

    @Published var showVersionInfo: Bool {
        didSet { save(showVersionInfo, forKey: "showVersionInfo") }
    }

    // MARK: - Advanced Settings

    @Published var debugMode: Bool {
        didSet { save(debugMode, forKey: "debugMode") }
    }

    // MARK: - Computed Properties

    var cliExecutablePath: String {
        // Try to find the CLI executable
        let paths = [
            "/usr/local/bin/llamacpp-manager",
            "/opt/homebrew/bin/llamacpp-manager",
            "~/.local/bin/llamacpp-manager"
        ]

        for path in paths {
            let expandedPath = NSString(string: path).expandingTildeInPath
            if FileManager.default.fileExists(atPath: expandedPath) {
                return expandedPath
            }
        }

        return "Not found"
    }

    var configFilePath: String {
        return "~/.config/llamacpp/config.yaml"
    }

    var logDirectoryPath: String {
        return "~/Library/Logs/llamaCPPManager/"
    }

    // MARK: - Initialization

    private init() {
        // Load from UserDefaults or use defaults
        let refreshKey = prefix + "refreshInterval"
        let interval = defaults.integer(forKey: refreshKey)
        self.refreshInterval = interval == 0 ? 10 : interval

        self.autoStartModels = defaults.bool(forKey: prefix + "autoStartModels")
        self.showNotifications = defaults.object(forKey: prefix + "showNotifications") as? Bool ?? true
        self.showStoppedModels = defaults.object(forKey: prefix + "showStoppedModels") as? Bool ?? true
        self.showInfrastructure = defaults.object(forKey: prefix + "showInfrastructure") as? Bool ?? true

        let viewModeString = defaults.string(forKey: prefix + "viewMode") ?? "detailed"
        self.viewMode = ViewMode(rawValue: viewModeString) ?? .detailed

        self.showUptime = defaults.object(forKey: prefix + "showUptime") as? Bool ?? true
        self.showPortNumbers = defaults.object(forKey: prefix + "showPortNumbers") as? Bool ?? true
        self.showHealthStatus = defaults.object(forKey: prefix + "showHealthStatus") as? Bool ?? true
        self.showVersionInfo = defaults.object(forKey: prefix + "showVersionInfo") as? Bool ?? true
        self.debugMode = defaults.bool(forKey: prefix + "debugMode")
    }

    // MARK: - Methods

    func resetToDefaults() {
        refreshInterval = 10
        autoStartModels = false
        showNotifications = true
        showStoppedModels = true
        showInfrastructure = true
        viewMode = .detailed
        showUptime = true
        showPortNumbers = true
        showHealthStatus = true
        showVersionInfo = true
        debugMode = false
    }

    private func prefKey(_ key: String) -> String {
        return prefix + key
    }

    private func save<T>(_ value: T, forKey key: String) {
        defaults.set(value, forKey: prefKey(key))
    }
}

enum ViewMode: String, CaseIterable {
    case compact = "compact"
    case detailed = "detailed"

    var displayName: String {
        rawValue.capitalized
    }
}
