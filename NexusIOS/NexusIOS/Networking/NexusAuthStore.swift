import Foundation

final class NexusAuthStore: ObservableObject {
    static let shared = NexusAuthStore()
    private let tokenAccount = "nexus.access_token"
    private let tokenExpiryAccount = "nexus.token_expiry"
    private let serverAccount = "nexus.server_url"

    @Published private(set) var token: String?
    private var tokenExpiry: Date?

    @Published var serverURL: String

    private init() {
        self.token = (try? KeychainHelper.shared.read(account: tokenAccount)).flatMap { String(data: $0, encoding: .utf8) }
        if let expiryData = try? KeychainHelper.shared.read(account: tokenExpiryAccount),
           let string = String(data: expiryData, encoding: .utf8),
           let interval = TimeInterval(string) {
            self.tokenExpiry = Date(timeIntervalSince1970: interval)
        }
        self.serverURL = (try? KeychainHelper.shared.read(account: serverAccount)).flatMap { String(data: $0, encoding: .utf8) } ?? ""
    }

    var isLoggedIn: Bool {
        guard let token = token, !token.isEmpty, !serverURL.isEmpty else { return false }
        if let expiry = tokenExpiry, expiry <= Date() { return false }
        return true
    }

    func saveToken(_ token: String, expiresAt: Date? = nil) throws {
        guard let data = token.data(using: .utf8) else { return }
        try KeychainHelper.shared.save(data, account: tokenAccount)
        if let expiresAt = expiresAt {
            let expiryData = Data(String(expiresAt.timeIntervalSince1970).utf8)
            try KeychainHelper.shared.save(expiryData, account: tokenExpiryAccount)
            self.tokenExpiry = expiresAt
        }
        self.token = token
    }

    func clearToken() throws {
        try KeychainHelper.shared.delete(account: tokenAccount)
        try? KeychainHelper.shared.delete(account: tokenExpiryAccount)
        self.token = nil
        self.tokenExpiry = nil
    }

    func saveServerURL(_ url: String, remember: Bool = true) throws {
        self.serverURL = url
        if remember {
            guard let data = url.data(using: .utf8) else { return }
            try KeychainHelper.shared.save(data, account: serverAccount)
        } else {
            try? KeychainHelper.shared.delete(account: serverAccount)
        }
    }
}
