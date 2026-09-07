import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @State private var serverURL = ""
    @State private var username = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Spacer()
                    .frame(height: 60)

                VStack(spacing: 8) {
                    Image("os-logo")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 64, height: 80)
                    Text("Nexus")
                        .font(.system(.largeTitle, design: .rounded, weight: .bold))
                    Text("Server Management")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .padding(.bottom, 40)

                Form {
                    Section("Server") {
                        TextField("https://nexus.example.com", text: $serverURL)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                            .keyboardType(.URL)
                            .textContentType(.URL)
                    }

                    Section("Credentials") {
                        TextField("Username", text: $username)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                            .textContentType(.username)
                        SecureField("Password", text: $password)
                            .textContentType(.password)
                    }

                    if let errorMessage = errorMessage {
                        Section {
                            Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                                .foregroundColor(.red)
                                .font(.footnote)
                        }
                    }

                    Section {
                        Button(action: signIn) {
                            HStack {
                                Spacer()
                                if isLoading {
                                    ProgressView()
                                        .tint(.white)
                                } else {
                                    Text("Sign In")
                                        .fontWeight(.semibold)
                                }
                                Spacer()
                            }
                        }
                        .listRowBackground(
                            LinearGradient(
                                colors: [.indigo, .purple],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .foregroundColor(.white)
                        .disabled(isLoading || serverURL.isEmpty || username.isEmpty || password.isEmpty)
                    }
                }
                .scrollContentBackground(.hidden)

                Spacer()
            }
            .background(
                LinearGradient(
                    colors: [Color(.systemGroupedBackground), Color(.secondarySystemGroupedBackground)],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .onAppear {
                serverURL = NexusAuthStore.shared.serverURL
            }
        }
    }

    private func signIn() {
        isLoading = true
        errorMessage = nil
        Task {
            do {
                try await appState.login(username: username, password: password, serverURL: serverURL)
            } catch let err as NexusError {
                errorMessage = err.localizedDescription
            } catch {
                errorMessage = error.localizedDescription
            }
            isLoading = false
        }
    }
}
