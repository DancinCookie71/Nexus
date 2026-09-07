import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @FocusState private var focusedField: Field?
    @State private var serverURL = ""
    @State private var username = ""
    @State private var password = ""
    @State private var showPassword = false
    @State private var rememberServer = true
    @State private var isLoading = false
    @State private var errorMessage: String?

    private enum Field {
        case server, username, password
    }

    var body: some View {
        ZStack {
            backgroundGradient
            ScrollView {
                VStack(spacing: 28) {
                    Spacer()
                        .frame(height: 48)

                    brand

                    VStack(spacing: 16) {
                        if let notice = appState.sessionNotice {
                            infoPill(notice)
                        }
                        fieldStack
                        if let errorMessage {
                            errorPill(errorMessage)
                        }
                        signInButton
                    }
                    .padding(22)
                    .background(
                        RoundedRectangle(cornerRadius: 24, style: .continuous)
                            .fill(Color(.secondarySystemGroupedBackground))
                            .shadow(color: Color.black.opacity(0.18), radius: 18, x: 0, y: 8)
                    )
                    .padding(.horizontal, 24)

                    Text("Sign in with your server's UNIX account")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.65))

                    Spacer()
                        .frame(height: 32)
                }
            }
        }
        .onAppear {
            serverURL = NexusAuthStore.shared.serverURL
        }
    }

    private var backgroundGradient: some View {
        LinearGradient(
            colors: [
                Color(red: 0.25, green: 0.22, blue: 0.55),
                Color(red: 0.10, green: 0.16, blue: 0.38),
                Color(red: 0.05, green: 0.09, blue: 0.22)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .ignoresSafeArea()
    }

    private var brand: some View {
        VStack(spacing: 10) {
            Image("os-logo")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 58, height: 72)
            Text("Nexus")
                .font(.system(size: 40, weight: .bold, design: .rounded))
                .foregroundColor(.white)
            Text("Server Management")
                .font(.subheadline.weight(.medium))
                .foregroundColor(.white.opacity(0.7))
        }
    }

    private var fieldStack: some View {
        VStack(spacing: 14) {
            HStack(spacing: 10) {
                Image(systemName: "globe")
                    .foregroundColor(.secondary)
                    .frame(width: 22)
                TextField("https://nexus.example.com", text: $serverURL)
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textContentType(.URL)
                    .submitLabel(.next)
                    .focused($focusedField, equals: .server)
                    .onSubmit { focusedField = .username }
            }
            Divider()
            HStack(spacing: 10) {
                Image(systemName: "person.fill")
                    .foregroundColor(.secondary)
                    .frame(width: 22)
                TextField("Username", text: $username)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textContentType(.username)
                    .submitLabel(.next)
                    .focused($focusedField, equals: .username)
                    .onSubmit { focusedField = .password }
            }
            Divider()
            HStack(spacing: 10) {
                Image(systemName: "lock.fill")
                    .foregroundColor(.secondary)
                    .frame(width: 22)
                Group {
                    if showPassword {
                        TextField("Password", text: $password)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    } else {
                        SecureField("Password", text: $password)
                    }
                }
                .textContentType(.password)
                .submitLabel(.go)
                .focused($focusedField, equals: .password)
                .onSubmit(signIn)
                Button {
                    showPassword.toggle()
                } label: {
                    Image(systemName: showPassword ? "eye.slash.fill" : "eye.fill")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            Divider()
            HStack {
                Image(systemName: "square.and.arrow.down.fill")
                    .foregroundColor(.secondary)
                    .font(.caption)
                Toggle("Save server on every launch", isOn: $rememberServer)
                    .font(.footnote)
                    .tint(.indigo)
            }
        }
    }

    private func errorPill(_ message: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
            Text(message)
                .font(.footnote)
        }
        .foregroundColor(.red)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color.red.opacity(0.1)))
    }

    private func infoPill(_ message: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "clock.arrow.circlepath")
            Text(message)
                .font(.footnote)
        }
        .foregroundColor(.indigo)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color.indigo.opacity(0.1)))
    }

    private var signInButton: some View {
        Button(action: signIn) {
            HStack {
                Spacer()
                if isLoading {
                    ProgressView()
                        .tint(.white)
                } else {
                    Text("Sign In")
                        .font(.headline)
                }
                Spacer()
            }
            .padding(.vertical, 14)
            .background(NexusTheme.buttonGradient)
            .foregroundColor(.white)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(isLoading || serverURL.isEmpty || username.isEmpty || password.isEmpty)
        .opacity(isLoading || serverURL.isEmpty || username.isEmpty || password.isEmpty ? 0.6 : 1)
    }

    private func signIn() {
        focusedField = nil
        isLoading = true
        errorMessage = nil
        appState.sessionNotice = nil
        Task {
            do {
                try await appState.login(
                    username: username,
                    password: password,
                    serverURL: serverURL,
                    rememberServer: rememberServer
                )
                Haptics.medium()
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
}
