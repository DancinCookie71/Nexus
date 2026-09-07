import SwiftUI

struct AdminModeView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @State private var username = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }
    private var isImplicitAdmin: Bool {
        isAdmin
            && appState.adminStatus?.expiresAt == nil
            && appState.adminStatus?.sudoUsername == appState.currentUser?.username
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Current context") {
                    HStack {
                        Text("Operating as")
                        Spacer()
                        Text(appState.adminStatus?.sudoUsername ?? appState.currentUser?.username ?? "—")
                            .fontWeight(.semibold)
                            .foregroundColor(isAdmin ? .green : .indigo)
                    }
                    if isAdmin {
                        HStack {
                            Text("Expires")
                            Spacer()
                            Text(expiryText)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    if isImplicitAdmin {
                        Text("You have full access through your UNIX account on the server.")
                            .font(.footnote)
                            .foregroundColor(.secondary)
                    }
                }

                if !isAdmin {
                    Section {
                        TextField("System user", text: $username)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                        SecureField("Password", text: $password)
                    } header: {
                        Text("Elevate as a different sudo user")
                    } footer: {
                        Text("Your UNIX account is already admin if it is in the server's sudo group. Use this only to operate as another sudo user.")
                    }
                }

                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .foregroundColor(.red)
                            .font(.footnote)
                    }
                }

                if isAdmin && !isImplicitAdmin {
                    Section {
                        Button(role: .destructive, action: revoke) {
                            HStack {
                                Spacer()
                                if isLoading { ProgressView() } else { Text("Return to Personal Context") }
                                Spacer()
                            }
                        }
                    }
                } else if !isAdmin {
                    Section {
                        Button(action: enable) {
                            HStack {
                                Spacer()
                                if isLoading { ProgressView() } else { Text("Enable Admin Mode") }
                                Spacer()
                            }
                        }
                        .disabled(isLoading || username.isEmpty || password.isEmpty)
                    }
                }
            }
            .navigationTitle("Admin Access")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium, .large])
    }

    private var expiryText: String {
        guard let expiresAt = appState.adminStatus?.expiresAt else { return "No expiry" }
        if expiresAt.timeIntervalSinceNow > 5 * 365 * 24 * 3600 {
            return "No expiry"
        }
        return expiresAt.formatted(.relative(presentation: .named))
    }

    private func enable() {
        isLoading = true
        errorMessage = nil
        Task {
            do {
                try await appState.elevateAdmin(username: username, password: password)
                Haptics.medium()
                dismiss()
            } catch let err as NexusError {
                errorMessage = err.localizedDescription
                Haptics.error()
            } catch {
                errorMessage = error.localizedDescription
                Haptics.error()
            }
            isLoading = false
        }
    }

    private func revoke() {
        isLoading = true
        Task {
            await appState.revokeAdmin()
            isLoading = false
            dismiss()
        }
    }
}
