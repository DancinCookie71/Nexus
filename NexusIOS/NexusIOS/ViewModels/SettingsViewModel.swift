import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var categories: [String: [String: String]] = [:]
    @Published var isLoading = false
    @Published var error: NexusError?
    @Published var saveMessage: String?
    @Published var updateCount: Int?

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await NexusAPI.shared.settings()
            categories = response.categories
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
        await loadUpdateCount()
    }

    private func loadUpdateCount() async {
        do {
            let info = try await NexusAPI.shared.updateInfo()
            updateCount = info.supported ? info.updateCount : nil
        } catch NexusError.forbidden {
            updateCount = nil
        } catch {
            updateCount = nil
        }
    }

    func update(key: String, value: String) async {
        do {
            _ = try await NexusAPI.shared.updateSetting(key: key, value: value)
            saveMessage = "Saved"
            await load()
        } catch let err as NexusError {
            error = err
            saveMessage = nil
        } catch {
            self.error = .networkError(error)
            saveMessage = nil
        }
    }
}
