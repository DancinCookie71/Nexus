import Foundation
import Combine

struct MetricSample: Identifiable, Equatable {
    let date: Date
    let value: Double
    var id: Date { date }
}

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published var snapshot: HealthSnapshot?
    @Published var system: SystemStatsResponse?
    @Published var updateInfo: UpdateInfoResponse?
    @Published var isLoading = false
    @Published var error: NexusError?

    @Published private(set) var cpuHistory: [MetricSample] = []
    @Published private(set) var memoryHistory: [MetricSample] = []
    @Published private(set) var historyCount = 0

    static let historyCapacity = 90

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
            async let updates = NexusAPI.shared.updateInfo()
            applySnapshot(try await health)
            system = try await systemStats
            updateInfo = try await updates
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

    private func applySnapshot(_ newSnapshot: HealthSnapshot) {
        snapshot = newSnapshot
        let now = Date()
        append(sample: MetricSample(date: now, value: newSnapshot.cpu.percent), to: &cpuHistory)
        append(sample: MetricSample(date: now, value: newSnapshot.memory.percent), to: &memoryHistory)
        historyCount = cpuHistory.count
    }

    private func append(sample: MetricSample, to array: inout [MetricSample]) {
        array.append(sample)
        if array.count > DashboardViewModel.historyCapacity {
            array.removeFirst(array.count - DashboardViewModel.historyCapacity)
        }
    }
}

extension DashboardViewModel: NexusWebSocketDelegate {
    nonisolated func webSocketDidReceiveMessage(_ message: String) {
        Task { @MainActor in
            do {
                let data = message.data(using: .utf8) ?? Data()
                self.applySnapshot(try self.decoder.decode(HealthSnapshot.self, from: data))
            } catch {
            }
        }
    }

    nonisolated func webSocketDidDisconnect(error: Error?) {}
    nonisolated func webSocketDidConnect() {}
}
