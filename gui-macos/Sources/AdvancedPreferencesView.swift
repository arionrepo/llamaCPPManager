import SwiftUI

struct AdvancedPreferencesView: View {
    @ObservedObject var preferences = PreferencesManager.shared

    var body: some View {
        Form {
            Section(header: Text("System Paths")) {
                PathRow(label: "CLI Executable:", path: preferences.cliExecutablePath)
                PathRow(label: "Config File:", path: preferences.configFilePath)
                PathRow(label: "Log Directory:", path: preferences.logDirectoryPath)
            }

            Section(header: Text("Debugging")) {
                Toggle("Debug mode", isOn: $preferences.debugMode)
                    .help("Enable verbose logging to Console.app")
            }

            Section(header: Text("Updates")) {
                Button("Check for Updates") {
                    checkForUpdates()
                }
                .buttonStyle(.bordered)
            }
        }
        .formStyle(.grouped)
    }

    private func checkForUpdates() {
        // Open GitHub releases page
        if let url = URL(string: "https://github.com/arionrepo/llamaCPPManager/releases") {
            NSWorkspace.shared.open(url)
        }
    }
}

struct PathRow: View {
    let label: String
    let path: String

    var body: some View {
        HStack {
            Text(label)
                .frame(width: 120, alignment: .trailing)
            Text(path)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
                .foregroundColor(.secondary)
            Spacer()
            Button("Reveal") {
                revealInFinder()
            }
            .buttonStyle(.borderless)
        }
    }

    private func revealInFinder() {
        let expandedPath = NSString(string: path).expandingTildeInPath
        let url = URL(fileURLWithPath: expandedPath)
        NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: url.deletingLastPathComponent().path)
    }
}
