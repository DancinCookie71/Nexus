import Foundation

@MainActor
final class ProcessesViewModel: ObservableObject {
    @Published var processes: [ProcessInfo] = []
    @Published var total = 0
    @Published var running = 0
    @Published var sleeping = 0
    @Published var cpuPercent: Double = 0
    @Published var memoryPercent: Double = 0
    @Published var loadAverage: [Double] = []
    @Published var isLoading = false
    @Published var error: NexusError?
    @Published var filter = ""
    @Published var sortKey: ProcessSortKey = .cpu
    @Published var sortAscending = false
    @Published var lastUpdated: Date?

    enum ProcessSortKey: String, CaseIterable, Identifiable {
        case name, pid, user, cpu, memory
        var id: String { rawValue }

        var label: String {
            switch self {
            case .name: return "Name"
            case .pid: return "PID"
            case .user: return "User"
            case .cpu: return "CPU"
            case .memory: return "Memory"
            }
        }
    }

    var filteredProcesses: [ProcessInfo] {
        let needle = filter.lowercased()
        let base = needle.isEmpty
            ? processes
            : processes.filter {
                $0.name.lowercased().contains(needle)
                    || $0.username.lowercased().contains(needle)
                    || $0.command.lowercased().contains(needle)
                    || String($0.pid).contains(needle)
            }
        return base.sorted { a, b in
            let result: Bool
            switch sortKey {
            case .name: result = a.name.localizedCaseInsensitiveCompare(b.name) == .orderedAscending
            case .pid: result = a.pid < b.pid
            case .user: result = a.username.localizedCaseInsensitiveCompare(b.username) == .orderedAscending
            case .cpu: result = a.cpuPercent < b.cpuPercent
            case .memory: result = a.memoryBytes < b.memoryBytes
            }
            return sortAscending ? result : !result
        }
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await NexusAPI.shared.processes()
            processes = response.processes
            total = response.total
            running = response.running
            sleeping = response.sleeping
            cpuPercent = response.cpuPercent
            memoryPercent = response.memoryPercent
            loadAverage = response.loadAverage
            lastUpdated = Date()
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }

    func kill(_ process: ProcessInfo, force: Bool = false) async -> String? {
        do {
            try await NexusAPI.shared.killProcess(pid: process.pid, signalName: force ? "KILL" : "TERM")
            Haptics.medium()
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }
}
