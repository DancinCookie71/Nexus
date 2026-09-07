import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var appState: AppState
    @State private var showAdminSheet = false

    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Status", systemImage: "waveform.path.ecg.rectangle.fill") }
            ServicesView()
                .tabItem { Label("Services", systemImage: "gearshape.2.fill") }
            FilesView()
                .tabItem { Label("Files", systemImage: "folder.fill") }
            TerminalView()
                .tabItem { Label("Terminal", systemImage: "terminal.fill") }
            MoreView()
                .tabItem { Label("More", systemImage: "ellipsis.circle.fill") }
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            AdminBar(showAdminSheet: $showAdminSheet)
                .padding(.horizontal)
                .padding(.top, 6)
        }
        .sheet(isPresented: $showAdminSheet) {
            AdminModeView()
        }
    }
}

struct MoreView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationStack {
            List {
                Section("Server") {
                    NavigationLink {
                        ProcessesView()
                    } label: {
                        MoreRow(title: "Processes", systemImage: "square.stack.3d.up", color: .blue)
                    }
                    NavigationLink {
                        UsersView()
                    } label: {
                        MoreRow(title: "Users", systemImage: "person.2.fill", color: .indigo)
                    }
                    NavigationLink {
                        UpdatesView()
                    } label: {
                        MoreRow(title: "Updates", systemImage: "arrow.down.circle.fill", color: .orange)
                    }
                    NavigationLink {
                        LogsView()
                    } label: {
                        MoreRow(title: "Logs", systemImage: "doc.text.fill", color: .teal)
                    }
                }
                Section("Panel") {
                    NavigationLink {
                        SettingsView()
                    } label: {
                        MoreRow(title: "Settings", systemImage: "gearshape.fill", color: .gray)
                    }
                }
            }
            .navigationTitle("More")
            .listStyle(.insetGrouped)
        }
    }
}

struct MoreRow: View {
    let title: String
    let systemImage: String
    let color: Color

    var body: some View {
        Label {
            Text(title).foregroundColor(.primary)
        } icon: {
            Image(systemName: systemImage)
                .foregroundColor(.white)
                .frame(width: 28, height: 28)
                .background(RoundedRectangle(cornerRadius: 7, style: .continuous).fill(color))
        }
    }
}

struct AdminBar: View {
    @EnvironmentObject var appState: AppState
    @Binding var showAdminSheet: Bool

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }
    private var activeName: String {
        appState.adminStatus?.sudoUsername ?? appState.currentUser?.username ?? "—"
    }

    var body: some View {
        Button {
            Haptics.light()
            showAdminSheet = true
        } label: {
            HStack(spacing: 8) {
                Image(systemName: isAdmin ? "lock.open.fill" : "lock.fill")
                    .font(.caption.weight(.bold))
                Text(isAdmin ? "Admin · \(activeName)" : "User · \(activeName)")
                    .font(.caption.weight(.semibold))
                Spacer()
                Text(isAdmin ? "Manage" : "Elevate")
                    .font(.caption2.weight(.bold))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Capsule().fill((isAdmin ? Color.green : Color.indigo).opacity(0.18)))
            }
            .foregroundColor(.primary)
            .padding(.horizontal, 14)
            .padding(.vertical, 9)
            .background(
                Capsule()
                    .fill(Color(.secondarySystemGroupedBackground))
                    .shadow(color: Color.black.opacity(0.08), radius: 6, x: 0, y: 2)
            )
            .overlay(
                Capsule()
                    .stroke((isAdmin ? Color.green : Color.indigo).opacity(0.35), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("admin-bar")
    }
}
