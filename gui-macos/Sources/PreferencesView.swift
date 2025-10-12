import SwiftUI

struct PreferencesView: View {
    @ObservedObject var preferences = PreferencesManager.shared
    @State private var selectedTab: PreferencesTab = .general

    var body: some View {
        TabView(selection: $selectedTab) {
            GeneralPreferencesView()
                .tabItem {
                    Label("General", systemImage: "gear")
                }
                .tag(PreferencesTab.general)

            DisplayPreferencesView()
                .tabItem {
                    Label("Display", systemImage: "eye")
                }
                .tag(PreferencesTab.display)

            AdvancedPreferencesView()
                .tabItem {
                    Label("Advanced", systemImage: "wrench.and.screwdriver")
                }
                .tag(PreferencesTab.advanced)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

enum PreferencesTab {
    case general
    case display
    case advanced
}
