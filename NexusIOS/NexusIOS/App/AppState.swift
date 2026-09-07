import Foundation
import Combine

@MainActor
final class AppState: ObservableObject {
    static let shared = AppState()

    @Published var isAuthenticated = false
    @Published var isCheckingAuth = true
    @Published var currentUser: NexusUser?
    @Published var adminStatus: AdminStatusResponse?
    @Published var lastError: NexusError?

    private var timer: Timer?

    private init() {
        isAuthenticated = NexusAuthStore.shared.isLoggedIn
    }

    func checkAuth() async {
        isCheckingAuth = true
        defer { isCheckingAuth = false }
        guard NexusAuthStore.shared.isLoggedIn else {
            isAuthenticated = false
            currentUser = nil
            return
        }
        do {
            let user = try await NexusAPI.shared.me()
            currentUser = user
            isAuthenticated = true
            await refreshAdminStatus()
            startAdminPolling()
        } catch {
            isAuthenticated = false
            currentUser = nil
            _ = try? NexusAuthStore.shared.clearToken()
        }
    }

    func login(username: String, password: String, serverURL: String? = nil, rememberServer: Bool = true) async throws {
        if let serverURL {
            try NexusAuthStore.shared.saveServerURL(serverURL, remember: rememberServer)
        }
        let response = try await NexusAPI.shared.login(username: username, password: password)
        try NexusAuthStore.shared.saveToken(response.accessToken, expiresAt: response.expiresAt)
        currentUser = response.user
        isAuthenticated = true
        await refreshAdminStatus()
        startAdminPolling()
    }

    func logout() async {
        _ = try? await NexusAPI.shared.logout()
        try? NexusAuthStore.shared.clearToken()
        isAuthenticated = false
        currentUser = nil
        adminStatus = nil
        stopAdminPolling()
    }

    func refreshAdminStatus() async {
        do {
            adminStatus = try await NexusAPI.shared.adminStatus()
        } catch {
            adminStatus = nil
        }
    }

    func elevateAdmin(username: String, password: String) async throws {
        let status = try await NexusAPI.shared.elevateAdmin(username: username, password: password)
        adminStatus = status
    }

    func revokeAdmin() async {
        _ = try? await NexusAPI.shared.revokeAdmin()
        await refreshAdminStatus()
    }

    private func startAdminPolling() {
        stopAdminPolling()
        timer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.refreshAdminStatus()
            }
        }
    }

    private func stopAdminPolling() {
        timer?.invalidate()
        timer = nil
    }
}
