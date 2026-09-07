import Foundation

@MainActor
final class UpdatesViewModel: ObservableObject {
    @Published var info: UpdateInfoResponse?
    @Published var isLoading = false
    @Published var isInstalling = false
    @Published var resultMessage: String?
    @Published var resultIsError = false
    @Published var rebootAfter = false
    @Published var error: NexusError?

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            info = try await NexusAPI.shared.updateInfo()
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }

    func install() async {
        isInstalling = true
        resultMessage = nil
        defer { isInstalling = false }
        do {
            let response = try await NexusAPI.shared.runUpdates(reboot: rebootAfter)
            resultMessage = response.message
            resultIsError = !response.success
            Haptics.medium()
            if !rebootAfter {
                await load()
            }
        } catch let err as NexusError {
            resultMessage = err.localizedDescription
            resultIsError = true
            Haptics.error()
        } catch {
            resultMessage = NexusError.networkError(error).localizedDescription
            resultIsError = true
            Haptics.error()
        }
    }

    func rebootNow() async -> String? {
        do {
            let response = try await NexusAPI.shared.reboot()
            return response.message
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }
}
