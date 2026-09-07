import Foundation

@MainActor
final class LogsViewModel: ObservableObject {
    @Published var entries: [LogEntry] = []
    @Published var isLoading = false
    @Published var error: NexusError?
    @Published var serviceName = "nexus-panel.service"

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await NexusAPI.shared.logs(for: serviceName, limit: 200)
            entries = response.entries
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }
}
