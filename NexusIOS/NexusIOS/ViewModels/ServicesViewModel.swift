import Foundation
import Combine

@MainActor
final class ServicesViewModel: ObservableObject {
    @Published var services: [ServiceSummary] = []
    @Published var isLoading = false
    @Published var error: NexusError?
    @Published var searchQuery = "" {
        didSet { searchSubject.send() }
    }
    @Published var showSystem = false

    let searchSubject = PassthroughSubject<Void, Never>()
    private var cancellables = Set<AnyCancellable>()

    init() {
        searchSubject
            .debounce(for: .milliseconds(300), scheduler: DispatchQueue.main)
            .sink { [weak self] in
                Task { @MainActor in
                    await self?.load()
                }
            }
            .store(in: &cancellables)
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await NexusAPI.shared.listServices(showSystem: showSystem, search: searchQuery)
            services = response.services
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }

    func performAction(_ service: ServiceSummary, action: String) async -> String? {
        do {
            let result = try await NexusAPI.shared.serviceAction(service.name, action: action)
            await load()
            return result.success ? nil : (result.message)
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }
}
