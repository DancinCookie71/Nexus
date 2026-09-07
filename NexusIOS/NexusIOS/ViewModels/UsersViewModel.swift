import Foundation

@MainActor
final class UsersViewModel: ObservableObject {
    @Published var users: [UnixUserInfo] = []
    @Published var isLoading = false
    @Published var error: NexusError?
    @Published var notice: String?

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            users = try await NexusAPI.shared.unixUsers()
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }

    func create(username: String, fullName: String, password: String, shell: String) async -> String? {
        do {
            try await NexusAPI.shared.createUnixUser(
                username: username.trimmingCharacters(in: .whitespaces),
                fullName: fullName.trimmingCharacters(in: .whitespaces),
                password: password,
                shell: shell
            )
            notice = "User \(username) created"
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func setPassword(_ user: UnixUserInfo, password: String) async -> String? {
        do {
            try await NexusAPI.shared.setUnixPassword(username: user.username, password: password)
            notice = "Password updated for \(user.username)"
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func setAdmin(_ user: UnixUserInfo, admin: Bool) async -> String? {
        do {
            try await NexusAPI.shared.setUnixUserAdmin(username: user.username, admin: admin)
            notice = "\(user.username) admin access \(admin ? "granted" : "removed")"
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func delete(_ user: UnixUserInfo) async -> String? {
        do {
            try await NexusAPI.shared.deleteUnixUser(username: user.username)
            notice = "User \(user.username) deleted"
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }
}
