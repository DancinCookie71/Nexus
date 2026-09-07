import SwiftUI

struct AdminModeView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @State private var username = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Text("Current context")
                        Spacer()
                        Text(appState.adminStatus?.isAdmin == true
                             ? appState.adminStatus?.sudoUsername ?? "admin"
                             : "nexus")
                            .fontWeight(.semibold)
                            .foregroundColor(appState.adminStatus?.isAdmin == true ? .green : .blue)
                    }
                    if appState.adminStatus?.isAdmin == true, let expiresAt = appState.adminStatus?.expiresAt {
                        HStack {
                            Text("Expires")
                            Spacer()
                            Text(expiresAt, style: .relative)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }

                if appState.adminStatus?.isAdmin != true {
                    Section("Authenticate") {
                        TextField("System user", text: $username)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                        SecureField("Password", text: $password)
                    }
                }

                if let errorMessage = errorMessage {
                    Section {
                        Text(errorMessage)
                            .foregroundColor(.red)
                            .font(.footnote)
                    }
                }

                Section {
                    if appState.adminStatus?.isAdmin == true {
                        Button(role: .destructive, action: revoke) {
                            HStack {
                                Spacer()
                                if isLoading { ProgressView() } else { Text("Disable Admin Mode") }
                                Spacer()
                            }
                        }
                    } else {
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
            .navigationTitle("Admin Mode")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private func enable() {
        isLoading = true
        errorMessage = nil
        Task {
            do {
                try await appState.elevateAdmin(username: username, password: password)
                dismiss()
            } catch let err as NexusError {
                errorMessage = err.localizedDescription
            } catch {
                errorMessage = error.localizedDescription
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
