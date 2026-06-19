import SwiftUI

struct DisplayPreferencesView: View {
    @ObservedObject var preferences = PreferencesManager.shared

    var body: some View {
        Form {
            Section(header: Text("Visibility")) {
                Toggle("Show stopped models", isOn: $preferences.showStoppedModels)
                Toggle("Show infrastructure section", isOn: $preferences.showInfrastructure)
            }

            Section(header: Text("View Mode")) {
                Picker("Layout:", selection: $preferences.viewMode) {
                    ForEach(ViewMode.allCases, id: \.self) { mode in
                        Text(mode.displayName).tag(mode)
                    }
                }
                .pickerStyle(.segmented)

                Text(preferences.viewMode == .compact
                    ? "Single line per model"
                    : "Multi-line with health indicators")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Section(header: Text("Status Indicators")) {
                Toggle("Show uptime", isOn: $preferences.showUptime)
                Toggle("Show port numbers", isOn: $preferences.showPortNumbers)
                Toggle("Show health status", isOn: $preferences.showHealthStatus)
                Toggle("Show version info", isOn: $preferences.showVersionInfo)
            }
        }
        .formStyle(.grouped)
    }
}
