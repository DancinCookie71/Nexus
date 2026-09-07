import Foundation

@MainActor
final class FileEditorViewModel: ObservableObject {
    @Published var content = ""
    @Published var originalContent = ""
    @Published var isLoading = false
    @Published var error: NexusError?
    @Published var saveMessage: String?

    let path: String

    var hasUnsavedChanges: Bool { content != originalContent }

    init(path: String) {
        self.path = path
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await NexusAPI.shared.readFile(path: path)
            guard PathUtilities.isTextMIMEType(response.mimeType) else {
                error = .apiError("This file cannot be edited because it is binary (\(response.mimeType)).")
                return
            }
            content = response.content
            originalContent = response.content
            error = nil
        } catch let err as NexusError {
            error = err
        } catch {
            self.error = .networkError(error)
        }
    }

    func save() async {
        do {
            _ = try await NexusAPI.shared.writeFile(path: path, content: content)
            originalContent = content
            saveMessage = "Saved"
        } catch let err as NexusError {
            error = err
            saveMessage = nil
        } catch {
            self.error = .networkError(error)
            saveMessage = nil
        }
    }
}
