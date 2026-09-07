import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var appState: AppState
    @State private var showAdminSheet = false

    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "gauge.with.dots.needle.67percent") }
            ServicesView()
                .tabItem { Label("Services", systemImage: "gearshape.2") }
            FilesView()
                .tabItem { Label("Files", systemImage: "folder") }
            TerminalView()
                .tabItem { Label("Terminal", systemImage: "terminal") }
            LogsView()
                .tabItem { Label("Logs", systemImage: "doc.text") }
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gear") }
        }
        .safeAreaInset(edge: .top) {
            AdminBar(showAdminSheet: $showAdminSheet)
                .padding(.horizontal)
                .padding(.top, 8)
        }
        .sheet(isPresented: $showAdminSheet) {
            AdminModeView()
        }
    }
}

struct AdminBar: View {
    @EnvironmentObject var appState: AppState
    @Binding var showAdminSheet: Bool

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: appState.adminStatus?.isAdmin == true ? "lock.open.fill" : "lock.fill")
                .font(.caption)
            Text(appState.adminStatus?.isAdmin == true
                 ? "Admin: \(appState.adminStatus?.sudoUsername ?? appState.currentUser?.username ?? "—")"
                 : "User: \(appState.currentUser?.username ?? "—")")
                .font(.caption.weight(.semibold))
            Spacer()
            Button(action: { showAdminSheet = true }) {
                Text(appState.adminStatus?.isAdmin == true ? "Manage" : "Enable Admin")
                    .font(.caption.weight(.semibold))
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(appState.adminStatus?.isAdmin == true
                      ? Color.green.opacity(0.12)
                      : Color.indigo.opacity(0.12))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(
                    appState.adminStatus?.isAdmin == true
                    ? Color.green.opacity(0.25)
                    : Color.indigo.opacity(0.25),
                    lineWidth: 1
                )
        )
    }
}
