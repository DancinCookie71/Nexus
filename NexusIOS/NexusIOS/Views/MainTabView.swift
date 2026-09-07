import SwiftUI

enum MainSection: Hashable {
    case dashboard, services, files, terminal
    case processes, users, updates, logs, settings
}

struct MainTabView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @State private var showAdminSheet = false
    @State private var sidebarSelection: MainSection? = .dashboard

    var body: some View {
        Group {
            if horizontalSizeClass == .regular {
                iPadLayout
            } else {
                iPhoneLayout
            }
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

    private var iPhoneLayout: some View {
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
    }

    private var iPadLayout: some View {
        NavigationSplitView {
            List(selection: $sidebarSelection) {
                Section("Server") {
                    sidebarRow("Dashboard", icon: "waveform.path.ecg.rectangle.fill", color: .indigo, section: .dashboard)
                    sidebarRow("Services", icon: "gearshape.2.fill", color: .blue, section: .services)
                    sidebarRow("Processes", icon: "square.stack.3d.up", color: .teal, section: .processes)
                    sidebarRow("Users", icon: "person.2.fill", color: .indigo, section: .users)
                    sidebarRow("Updates", icon: "arrow.down.circle.fill", color: .orange, section: .updates)
                }
                Section("Workspaces") {
                    sidebarRow("Files", icon: "folder.fill", color: .yellow, section: .files)
                    sidebarRow("Terminal", icon: "terminal.fill", color: .green, section: .terminal)
                    sidebarRow("Logs", icon: "doc.text.fill", color: .gray, section: .logs)
                }
                Section("Panel") {
                    sidebarRow("Settings", icon: "gearshape.fill", color: .gray, section: .settings)
                }
            }
            .listStyle(.sidebar)
            .navigationTitle("Nexus")
        } detail: {
            detailView
        }
    }

    @ViewBuilder
    private func sidebarRow(_ title: String, icon: String, color: Color, section: MainSection) -> some View {
        Label {
            Text(title)
        } icon: {
            Image(systemName: icon)
                .foregroundColor(color)
        }
        .tag(section)
    }

    @ViewBuilder
    private var detailView: some View {
        switch sidebarSelection {
        case .services:
            ServicesView()
        case .files:
            FilesView()
        case .terminal:
            TerminalView()
        case .processes:
            ProcessesView()
        case .users:
            UsersView()
        case .updates:
            UpdatesView()
        case .logs:
            LogsView()
        case .settings:
            SettingsView()
        default:
            DashboardView()
        }
    }
}

struct MoreView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationStack {
            List {
                Section("Server") {
                    NavigationLink(value: MainSection.processes) {
                        MoreRow(title: "Processes", systemImage: "square.stack.3d.up", color: .blue)
                    }
                    NavigationLink(value: MainSection.users) {
                        MoreRow(title: "Users", systemImage: "person.2.fill", color: .indigo)
                    }
                    NavigationLink(value: MainSection.updates) {
                        MoreRow(title: "Updates", systemImage: "arrow.down.circle.fill", color: .orange)
                    }
                    NavigationLink(value: MainSection.logs) {
                        MoreRow(title: "Logs", systemImage: "doc.text.fill", color: .teal)
                    }
                }
                Section("Panel") {
                    NavigationLink(value: MainSection.settings) {
                        MoreRow(title: "Settings", systemImage: "gearshape.fill", color: .gray)
                    }
                }
            }
            .navigationTitle("More")
            .listStyle(.insetGrouped)
            .navigationDestination(for: MainSection.self) { section in
                switch section {
                case .processes: ProcessesView()
                case .users: UsersView()
                case .updates: UpdatesView()
                case .logs: LogsView()
                case .settings: SettingsView()
                default: EmptyView()
                }
            }
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
