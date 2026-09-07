import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var categories: [String: [String: String]] = [:]
    @Published var isLoading = false
    @Published var error: NexusError?
    @Published var saveMessage: String?

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
