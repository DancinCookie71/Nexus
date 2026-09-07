import Foundation
import Combine

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published var snapshot: HealthSnapshot?
    @Published var system: SystemStatsResponse?
    @Published var isLoading = false
    @Published var error: NexusError?

    private var webSocket: NexusWebSocket?
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            async let health = NexusAPI.shared.healthSnapshot()
            async let systemStats = NexusAPI.shared.systemStats()
            snapshot = try await health
            system = try await systemStats
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }

    func startLiveUpdates() {
        stopLiveUpdates()
        webSocket = NexusWebSocket(path: "/api/v1/health/live/ws")
        webSocket?.delegate = self
        webSocket?.connect()
    }

    func stopLiveUpdates() {
        webSocket?.disconnect()
        webSocket = nil
    }
}

extension DashboardViewModel: NexusWebSocketDelegate {
    nonisolated func webSocketDidReceiveMessage(_ message: String) {
        Task { @MainActor in
            do {
                let data = message.data(using: .utf8) ?? Data()
                self.snapshot = try self.decoder.decode(HealthSnapshot.self, from: data)
            } catch {
                // Ignore malformed frames
            }
        }
    }

    nonisolated func webSocketDidDisconnect(error: Error?) {}
    nonisolated func webSocketDidConnect() {}
}
