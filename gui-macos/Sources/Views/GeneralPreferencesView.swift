import SwiftUI

struct GeneralPreferencesView: View {
    @ObservedObject var preferences = PreferencesManager.shared

    var body: some View {
        Form {
            Section(header: Text("Status Updates")) {
                Picker("Refresh Interval:", selection: $preferences.refreshInterval) {
                    Text("5 seconds").tag(5)
                    Text("10 seconds").tag(10)
                    Text("30 seconds").tag(30)
                    Text("1 minute").tag(60)
                    Text("Manual").tag(0)
                }
                .pickerStyle(.menu)

                Text("Controls how often the app checks model status")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Section(header: Text("Behavior")) {
                Toggle("Auto-start models on launch", isOn: $preferences.autoStartModels)
                    .help("Start models marked as 'autostart' when the app launches")

                Toggle("Show notifications", isOn: $preferences.showNotifications)
                    .help("Display system notifications for status changes")
            }

            Spacer()

            HStack {
                Spacer()
                Button("Reset to Defaults") {
                    confirmReset()
                }
                .buttonStyle(.bordered)
            }
        }
        .formStyle(.grouped)
    }

    private func confirmReset() {
        let alert = NSAlert()
        alert.messageText = "Reset All Preferences?"
        alert.informativeText = "This will restore all settings to their default values."
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Reset")
        alert.addButton(withTitle: "Cancel")

        if alert.runModal() == .alertFirstButtonReturn {
            preferences.resetToDefaults()
        }
    }
}
