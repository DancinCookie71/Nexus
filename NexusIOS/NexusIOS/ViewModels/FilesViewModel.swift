import Foundation

@MainActor
final class FilesViewModel: ObservableObject {
    @Published var entries: [FileEntry] = []
    @Published var currentPath: String = ""
    @Published var isLoading = false
    @Published var error: NexusError?
    @Published var searchQuery = ""
    @Published var showHidden = false
    @Published var isSearching = false

    var visibleEntries: [FileEntry] {
        if showHidden { return entries }
        return entries.filter { !$0.name.hasPrefix(".") }
    }

    func load(path: String? = nil) async {
        let target = path ?? currentPath
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await NexusAPI.shared.listFiles(path: target)
            currentPath = response.path
            entries = response.entries
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }

    func search() async {
        guard !searchQuery.isEmpty else {
            isSearching = false
            await load()
            return
        }
        isSearching = true
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await NexusAPI.shared.searchFiles(query: searchQuery, path: currentPath, showHidden: showHidden)
            entries = response.entries
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }

    func entryExists(name: String) -> Bool {
        visibleEntries.contains { $0.name == name }
    }

    func createDirectory(name: String) async -> String? {
        if let validationError = PathUtilities.validateName(name) {
            return validationError
        }
        let path = PathUtilities.join(currentPath, name)
        do {
            _ = try await NexusAPI.shared.createDirectory(path: path)
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func rename(entry: FileEntry, to newName: String) async -> String? {
        if let validationError = PathUtilities.validateName(newName) {
            return validationError
        }
        let target = PathUtilities.join(currentPath, newName)
        do {
            _ = try await NexusAPI.shared.renameFile(source: entry.path, target: target)
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func copy(entry: FileEntry, to newName: String) async -> String? {
        if let validationError = PathUtilities.validateName(newName) {
            return validationError
        }
        let target = PathUtilities.join(currentPath, newName)
        do {
            _ = try await NexusAPI.shared.copyFile(source: entry.path, target: target)
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func delete(entry: FileEntry) async -> String? {
        do {
            _ = try await NexusAPI.shared.deleteFile(path: entry.path, recursive: entry.isDirectory)
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func upload(data: Data, filename: String) async -> String? {
        if let validationError = PathUtilities.validateName(filename) {
            return validationError
        }
        let path = PathUtilities.join(currentPath, filename)
        do {
            _ = try await NexusAPI.shared.uploadFile(path: path, data: data)
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func writeFile(path: String, content: String) async -> String? {
        do {
            _ = try await NexusAPI.shared.writeFile(path: path, content: content)
            await load()
            return nil
        } catch let err as NexusError {
            return err.localizedDescription
        } catch {
            return NexusError.networkError(error).localizedDescription
        }
    }

    func download(entry: FileEntry) async -> Result<Data, NexusError> {
        do {
            let request = try NexusAPI.shared.downloadRequest(path: entry.path)
            let data = try await NexusAPI.shared.fetchData(request: request)
            return .success(data)
        } catch let err as NexusError {
            return .failure(err)
        } catch {
            return .failure(.networkError(error))
        }
    }
}
