import SwiftUI

struct UsersView: View {
    @StateObject private var viewModel = UsersViewModel()
    @EnvironmentObject var appState: AppState
    @State private var showCreateSheet = false
    @State private var passwordUser: UnixUserInfo?
    @State private var deleteConfirm: UnixUserInfo?
    @State private var adminToggleConfirm: (user: UnixUserInfo, grant: Bool)?

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        List {
            if let notice = viewModel.notice {
                Section {
                    Label(notice, systemImage: "checkmark.circle.fill")
                        .font(.footnote)
                        .foregroundColor(.green)
                }
            }

            if let error = viewModel.error {
                Section {
                    ErrorBanner(error: error) {
                        Task { await viewModel.load() }
                    }
                }
            }

            if viewModel.isLoading && viewModel.users.isEmpty {
                Section {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 120)
                }
            } else if viewModel.users.isEmpty {
                Section {
                    EmptyStateView(title: "No user accounts", systemImage: "person.3")
                }
            } else {
                Section("Local UNIX Accounts") {
                    ForEach(viewModel.users) { user in
                        Button {
                            passwordUser = user
                        } label: {
                            UserRow(user: user, isCurrentUser: user.username == appState.currentUser?.username)
                        }
                        .buttonStyle(.plain)
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            if isAdmin {
                                Button(role: .destructive) {
                                    deleteConfirm = user
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                                Button {
                                    adminToggleConfirm = (user, !user.isAdmin)
                                } label: {
                                    Label(user.isAdmin ? "Revoke Admin" : "Make Admin", systemImage: user.isAdmin ? "lock.open" : "crown")
                                }
                                .tint(user.isAdmin ? .orange : .indigo)
                            }
                        }
                        .disabled(!isAdmin)
                    }
                } footer: {
                    Text("Deleting an account keeps its home directory. You cannot delete the account you are operating as.")
                }
            }
        }
        .navigationTitle("Users")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await viewModel.load() }
        .task { await viewModel.load() }
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    showCreateSheet = true
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(!isAdmin)
            }
        }
        .sheet(isPresented: $showCreateSheet) {
            CreateUserSheet(viewModel: viewModel)
        }
        .sheet(item: $passwordUser) { user in
            SetPasswordSheet(viewModel: viewModel, user: user)
        }
        .alert(
            "Delete user?",
            isPresented: Binding(
                get: { deleteConfirm != nil },
                set: { if !$0 { deleteConfirm = nil } }
            )
        ) {
            Button("Cancel", role: .cancel) { deleteConfirm = nil }
            Button("Delete", role: .destructive) {
                guard let user = deleteConfirm else { return }
                deleteConfirm = nil
                Task {
                    if let message = await viewModel.delete(user) {
                        viewModel.notice = nil
                        viewModel.error = .apiError(message)
                    } else {
                        Haptics.medium()
                    }
                }
            }
        } message: {
            Text(deleteConfirm.map { "Delete account \"\($0.username)\"? This cannot be undone." } ?? "")
        }
        .confirmationDialog(
            adminToggleConfirm.map { "\($0.grant ? "Grant" : "Revoke") admin for \($0.user.username)?" } ?? "",
            isPresented: Binding(
                get: { adminToggleConfirm != nil },
                set: { if !$0 { adminToggleConfirm = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button(adminToggleConfirm?.grant == true ? "Grant Admin" : "Revoke Admin", role: adminToggleConfirm?.grant == true ? nil : .destructive) {
                guard let target = adminToggleConfirm else { return }
                adminToggleConfirm = nil
                Task {
                    if let message = await viewModel.setAdmin(target.user, admin: target.grant) {
                        viewModel.notice = nil
                        viewModel.error = .apiError(message)
                    } else {
                        Haptics.medium()
                    }
                }
            }
            Button("Cancel", role: .cancel) { adminToggleConfirm = nil }
        } message: {
            Text("Admin access is granted through the server's sudo group.")
        }
    }
}

struct UserRow: View {
    let user: UnixUserInfo
    let isCurrentUser: Bool

    var body: some View {
        HStack(spacing: 12) {
            Text(initial)
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundColor(.white)
                .frame(width: 36, height: 36)
                .background(Circle().fill(user.isAdmin ? Color.indigo : Color.gray.opacity(0.6)))
            VStack(alignment: .leading, spacing: 2) {
                Text(user.fullName.isEmpty ? user.username : user.fullName)
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.primary)
                Text(user.username)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
            if user.isAdmin {
                StatusBadge(text: "Admin", color: .indigo)
            }
            if isCurrentUser {
                StatusBadge(text: "You", color: .gray)
            }
        }
        .padding(.vertical, 2)
    }

    private var initial: String {
        String((user.fullName.isEmpty ? user.username : user.fullName).prefix(1)).uppercased()
    }
}

struct CreateUserSheet: View {
    @ObservedObject var viewModel: UsersViewModel
    @Environment(\.dismiss) var dismiss
    @State private var username = ""
    @State private var fullName = ""
    @State private var password = ""
    @State private var shell = "/bin/bash"
    @State private var isSubmitting = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Account") {
                    TextField("Username", text: $username)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                    TextField("Full name", text: $fullName)
                    TextField("Shell", text: $shell)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                }
                Section("Password") {
                    SecureField("At least 8 characters", text: $password)
                        .textContentType(.newPassword)
                }
                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .font(.footnote)
                            .foregroundColor(.red)
                    }
                }
            }
            .navigationTitle("Add User")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        Task {
                            isSubmitting = true
                            errorMessage = await viewModel.create(
                                username: username, fullName: fullName, password: password, shell: shell
                            )
                            isSubmitting = false
                            if errorMessage == nil { dismiss() }
                        }
                    }
                    .disabled(isSubmitting || username.isEmpty || password.count < 8)
                }
            }
        }
        .presentationDetents([.medium])
    }
}

struct SetPasswordSheet: View {
    @ObservedObject var viewModel: UsersViewModel
    let user: UnixUserInfo
    @Environment(\.dismiss) var dismiss
    @State private var password = ""
    @State private var isSubmitting = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    SecureField("New password (min 8 characters)", text: $password)
                        .textContentType(.newPassword)
                }
                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .font(.footnote)
                            .foregroundColor(.red)
                    }
                }
            }
            .navigationTitle("Password — \(user.username)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Set") {
                        Task {
                            isSubmitting = true
                            errorMessage = await viewModel.setPassword(user, password: password)
                            isSubmitting = false
                            if errorMessage == nil { dismiss() }
                        }
                    }
                    .disabled(isSubmitting || password.count < 8)
                }
            }
        }
        .presentationDetents([.medium])
    }
}
