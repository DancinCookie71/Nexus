import SwiftUI

struct SettingsView: View {
    @StateObject private var viewModel = SettingsViewModel()
    @EnvironmentObject var appState: AppState

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        List {
            Section("Server") {
                HStack {
                    Text("Address")
                    Spacer()
                    Text(NexusAuthStore.shared.serverURL)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
                HStack {
                    Text("User")
                    Spacer()
                    Text(appState.currentUser?.username ?? "—")
                        .foregroundColor(.secondary)
                }
            }

            Section("Management") {
                NavigationLink {
                    UpdatesView()
                } label: {
                    Label {
                        HStack {
                            Text("Updates")
                            Spacer()
                            if let count = viewModel.updateCount, count > 0 {
                                StatusBadge(text: "\(count)", color: .orange)
                            }
                        }
                    } icon: {
                        Image(systemName: "arrow.down.circle")
                            .foregroundColor(.indigo)
                    }
                }
                NavigationLink {
                    UsersView()
                } label: {
                    Label("Users", systemImage: "person.2")
                        .foregroundColor(.primary)
                }
            } footer: {
                Text("Managing users and installing updates requires admin access.")
            }

                if let error = viewModel.error {
                    Section {
                        ErrorBanner(error: error) {
                            Task { await viewModel.load() }
                        }
                    }
                }

                if viewModel.saveMessage != nil {
                    Section {
                        HStack {
                            Spacer()
                            Text(viewModel.saveMessage ?? "")
                                .font(.caption.weight(.semibold))
                                .foregroundColor(.green)
                            Spacer()
                        }
                    }
                }

                if viewModel.isLoading && viewModel.categories.isEmpty {
                    Section {
                        ProgressView()
                            .frame(maxWidth: .infinity, minHeight: 120)
                    }
                } else if viewModel.categories.isEmpty {
                    Section {
                        EmptyStateView(title: "No settings", systemImage: "gear")
                    }
                } else {
                    ForEach(viewModel.categories.keys.sorted(), id: \.self) { category in
                        Section(header: Text(category.capitalized)) {
                            if let items = viewModel.categories[category] {
                                ForEach(items.keys.sorted(), id: \.self) { key in
                                    SettingRow(category: category, key: key, value: items[key] ?? "", viewModel: viewModel, isAdmin: isAdmin)
                                }
                            }
                        }
                    }
                }

                Section {
                    Button(role: .destructive, action: logout) {
                        HStack {
                            Spacer()
                            Text("Sign Out")
                            Spacer()
                        }
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .listStyle(.insetGrouped)
            .refreshable { await viewModel.load() }
            .task { await viewModel.load() }
    }

    private func logout() {
        Task { await appState.logout() }
    }
}

struct SettingRow: View {
    let category: String
    let key: String
    @State var value: String
    @ObservedObject var viewModel: SettingsViewModel
    @State private var isEditing = false
    @State private var draft = ""
    let isAdmin: Bool

    init(category: String, key: String, value: String, viewModel: SettingsViewModel, isAdmin: Bool) {
        self.category = category
        self.key = key
        self._value = State(initialValue: value)
        self.viewModel = viewModel
        self.isAdmin = isAdmin
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(keyDisplayName)
                    .font(.subheadline)
                Text(value)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            Button("Edit") {
                draft = value
                isEditing = true
            }
            .font(.caption)
            .disabled(!isAdmin)
        }
        .alert(keyDisplayName, isPresented: $isEditing) {
            TextField("Value", text: $draft)
            Button("Cancel", role: .cancel) {}
            Button("Save") {
                Task {
                    await viewModel.update(key: key, value: draft)
                    if viewModel.error == nil {
                        value = draft
                    }
                }
            }
            .disabled(!isAdmin)
        }
    }

    private var keyDisplayName: String {
        key.replacingOccurrences(of: "_", with: " ").capitalized
    }
}
