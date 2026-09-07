import SwiftUI
import UniformTypeIdentifiers

struct FilesView: View {
    @StateObject private var viewModel = FilesViewModel()
    @EnvironmentObject var appState: AppState
    @State private var selectedEntry: FileEntry?
    @State private var editorPath: String?
    @State private var newFolderName = ""
    @State private var showNewFolder = false
    @State private var showNewFile = false
    @State private var newFileName = ""
    @State private var newFileTemplate = ""
    @State private var showNewOther = false
    @State private var otherFileName = ""
    @State private var showUpload = false
    @State private var showOptions: FileEntry?
    @State private var showDeleteConfirmation: FileEntry?
    @State private var actionError: String?
    @State private var showActionError = false
    @State private var pendingCreateName: String?
    @State private var pendingUploadData: Data?
    @State private var pendingUploadName: String?
    @State private var showOverwriteConfirmation = false

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Toggle("Show hidden", isOn: $viewModel.showHidden)
                        .accessibilityIdentifier("Show hidden")
                }

                if !viewModel.currentPath.isEmpty {
                    Button("⬆ Parent") {
                        Task { await viewModel.load(path: parentPath) }
                    }
                }

                if let error = viewModel.error {
                    Section {
                        ErrorBanner(error: error) {
                            Task { await viewModel.load() }
                        }
                    }
                }

                if viewModel.isLoading && viewModel.entries.isEmpty {
                    Section {
                        ProgressView()
                            .frame(maxWidth: .infinity, minHeight: 120)
                    }
                } else if viewModel.visibleEntries.isEmpty {
                    Section {
                        EmptyStateView(title: "No files", systemImage: "folder")
                    }
                } else {
                    ForEach(viewModel.visibleEntries) { entry in
                        Button {
                            if entry.isDirectory {
                                Task { await viewModel.load(path: entry.path) }
                            } else {
                                editorPath = entry.path
                            }
                        } label: {
                            FileRow(entry: entry)
                        }
                        .buttonStyle(.plain)
                        .contextMenu {
                            Button("Open") {
                                if entry.isDirectory {
                                    Task { await viewModel.load(path: entry.path) }
                                } else {
                                    editorPath = entry.path
                                }
                            }
                            if entry.isFile {
                                Button("Edit") { editorPath = entry.path }
                                Button("Download") { download(entry: entry) }
                            }
                            if isAdmin {
                                Button("Rename") { showOptions = entry }
                                Button("Copy") {
                                    Task {
                                        _ = await viewModel.copy(entry: entry, to: suggestedCopyName(for: entry.name))
                                    }
                                }
                                Button("Delete", role: .destructive) { showDeleteConfirmation = entry }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Files")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Text(viewModel.currentPath.isEmpty ? "/" : viewModel.currentPath)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        if isAdmin {
                            Button {
                                showNewFolder = true
                            } label: {
                                Label("Folder", systemImage: "folder.badge.plus")
                            }
                            Menu {
                                Button("Text (.txt)") { startNewFile(template: ".txt") }
                                Button("Shell Script (.sh)") { startNewFile(template: ".sh") }
                                Button("Python (.py)") { startNewFile(template: ".py") }
                                Button("JSON (.json)") { startNewFile(template: ".json") }
                                Button("Markdown (.md)") { startNewFile(template: ".md") }
                                Divider()
                                Button("Other...") {
                                    otherFileName = ""
                                    showNewOther = true
                                }
                            } label: {
                                Label("File", systemImage: "doc.badge.plus")
                            }
                            Divider()
                            Button {
                                showUpload = true
                            } label: {
                                Label("Upload", systemImage: "arrow.up.circle")
                            }
                        } else {
                            Text("Admin mode required")
                        }
                    } label: {
                        Image(systemName: "plus")
                            .accessibilityLabel("Add file or folder")
                    }
                    .disabled(!isAdmin)
                }
            }
            .refreshable { await viewModel.load() }
            .task { await viewModel.load() }
            .searchable(text: $viewModel.searchQuery, placement: .navigationBarDrawer(displayMode: .always))
            .onChange(of: viewModel.searchQuery) { _ in
                Task { await viewModel.search() }
            }
            .onChange(of: viewModel.showHidden) { _ in
                if viewModel.searchQuery.isEmpty {
                    // Local filtering only; no server round-trip needed
                } else {
                    Task { await viewModel.search() }
                }
            }
            .sheet(isPresented: Binding(
                get: { editorPath != nil },
                set: { if !$0 { editorPath = nil } }
            )) {
                if let path = editorPath {
                    FileEditorView(path: path)
                }
            }
            .alert("New Folder", isPresented: $showNewFolder) {
                TextField("Name", text: $newFolderName)
                Button("Cancel", role: .cancel) { newFolderName = "" }
                Button("Create") {
                    createDirectory(name: newFolderName)
                }
            }
            .alert("New File", isPresented: $showNewFile) {
                TextField("File name", text: $newFileName)
                Button("Cancel", role: .cancel) { resetNewFile() }
                Button("Create") {
                    let finalName = PathUtilities.normalizedFileName(newFileName, templateExtension: newFileTemplate)
                    createFile(name: finalName)
                }
            }
            .alert("New File", isPresented: $showNewOther) {
                TextField("filename.ext", text: $otherFileName)
                Button("Cancel", role: .cancel) { otherFileName = "" }
                Button("Create") {
                    createFile(name: otherFileName)
                }
            }
            .sheet(isPresented: $showUpload) {
                FileUploadSheet(viewModel: viewModel, isAdmin: isAdmin)
            }
            .sheet(item: $showOptions) { entry in
                FileOptionsSheet(entry: entry, viewModel: viewModel)
            }
            .alert("Delete?", isPresented: Binding(
                get: { showDeleteConfirmation != nil },
                set: { if !$0 { showDeleteConfirmation = nil } }
            )) {
                Button("Cancel", role: .cancel) { showDeleteConfirmation = nil }
                Button("Delete", role: .destructive) {
                    if let entry = showDeleteConfirmation {
                        performDestructive { await viewModel.delete(entry: entry) }
                    }
                    showDeleteConfirmation = nil
                }
            } message: {
                Text("Are you sure you want to delete \(showDeleteConfirmation?.name ?? "")?")
            }
            .alert("Overwrite?", isPresented: $showOverwriteConfirmation) {
                Button("Cancel", role: .cancel) {
                    pendingCreateName = nil
                    pendingUploadData = nil
                    pendingUploadName = nil
                }
                Button("Overwrite", role: .destructive) {
                    if let name = pendingCreateName {
                        pendingCreateName = nil
                        Task { await writeNewFile(name: name) }
                    } else if let data = pendingUploadData, let name = pendingUploadName {
                        pendingUploadData = nil
                        pendingUploadName = nil
                        Task { await finalizeUpload(data: data, name: name) }
                    }
                }
            } message: {
                Text("A file with that name already exists. Overwrite it?")
            }
            .alert("Error", isPresented: $showActionError) {
                Button("OK") { actionError = nil }
            } message: {
                Text(actionError ?? "")
            }
        }
    }

    private var parentPath: String {
        let parts = viewModel.currentPath.split(separator: "/")
        guard parts.count > 1 else { return "" }
        return "/" + parts.dropLast().joined(separator: "/")
    }

    private func startNewFile(template: String) {
        newFileTemplate = template
        newFileName = ""
        showNewFile = true
    }

    private func resetNewFile() {
        newFileName = ""
        newFileTemplate = ""
    }

    private func createDirectory(name: String) {
        newFolderName = ""
        perform { await viewModel.createDirectory(name: name) }
    }

    private func createFile(name: String) {
        resetNewFile()
        otherFileName = ""
        if viewModel.entryExists(name: name) {
            pendingCreateName = name
            showOverwriteConfirmation = true
            return
        }
        Task { await writeNewFile(name: name) }
    }

    private func writeNewFile(name: String) async {
        let path = PathUtilities.join(viewModel.currentPath, name)
        if let error = await viewModel.writeFile(path: path, content: "") {
            actionError = error
            showActionError = true
        }
    }

    func confirmUpload(data: Data, name: String) {
        if viewModel.entryExists(name: name) {
            pendingUploadData = data
            pendingUploadName = name
            showOverwriteConfirmation = true
            return
        }
        Task { await finalizeUpload(data: data, name: name) }
    }

    private func finalizeUpload(data: Data, name: String) async {
        if let error = await viewModel.upload(data: data, filename: name) {
            actionError = error
            showActionError = true
        }
    }

    private func download(entry: FileEntry) {
        Task {
            let result = await viewModel.download(entry: entry)
            switch result {
            case .success(let data):
                share(data: data, filename: entry.name)
            case .failure(let error):
                actionError = error.localizedDescription
                showActionError = true
            }
        }
    }

    private func share(data: Data, filename: String) {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(filename)
        try? data.write(to: url)
        let activity = UIActivityViewController(activityItems: [url], applicationActivities: nil)
        if let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let root = scene.windows.first?.rootViewController {
            root.present(activity, animated: true)
        }
    }

    private func perform(_ operation: @escaping () async -> String?) {
        Task {
            if let error = await operation() {
                actionError = error
                showActionError = true
            }
        }
    }

    private func performDestructive(_ operation: @escaping () async -> String?) {
        Haptics.heavy()
        perform(operation)
    }

    private func suggestedCopyName(for name: String) -> String {
        let url = URL(fileURLWithPath: name)
        let base = url.deletingPathExtension().lastPathComponent
        let ext = url.pathExtension
        let suffix = ext.isEmpty ? "_copy" : "_copy.\(ext)"
        return base + suffix
    }
}

struct FileRow: View {
    let entry: FileEntry

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: iconName)
                .font(.title3)
                .foregroundColor(entry.isDirectory ? .blue : .primary)
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.name)
                    .font(.subheadline.weight(.semibold))
                Text("\(entry.owner ?? "—"):\(entry.group ?? "—") · \(entry.mode ?? "—")")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(entry.isDirectory ? "—" : Formatters.bytes(entry.size))
                    .font(.caption)
                Text(Formatters.shortDate(entry.modifiedAt))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 2)
    }

    private var iconName: String {
        if entry.isSymlinkValue { return "link" }
        if entry.isDirectory { return "folder.fill" }
        return "doc.text"
    }
}

struct FileOptionsSheet: View {
    let entry: FileEntry
    @ObservedObject var viewModel: FilesViewModel
    @Environment(\.dismiss) var dismiss
    @State private var newName = ""
    @State private var actionError: String?
    @State private var showActionError = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("New name", text: $newName)
                }
                Section {
                    Button("Rename") {
                        Task {
                            if let error = await viewModel.rename(entry: entry, to: newName) {
                                actionError = error
                                showActionError = true
                            } else {
                                dismiss()
                            }
                        }
                    }
                    Button("Copy") {
                        Task {
                            if let error = await viewModel.copy(entry: entry, to: newName) {
                                actionError = error
                                showActionError = true
                            } else {
                                dismiss()
                            }
                        }
                    }
                }
            }
            .navigationTitle(entry.name)
            .navigationBarTitleDisplayMode(.inline)
            .onAppear { newName = entry.name }
            .alert("Error", isPresented: $showActionError) {
                Button("OK") { actionError = nil }
            } message: {
                Text(actionError ?? "")
            }
        }
    }
}

struct FileUploadSheet: View {
    @ObservedObject var viewModel: FilesViewModel
    @Environment(\.dismiss) var dismiss
    @State private var selectedData: Data?
    @State private var selectedName = ""
    @State private var showPicker = false
    @State private var actionError: String?
    @State private var showActionError = false
    @State private var showOverwriteConfirmation = false
    let isAdmin: Bool

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    if !isAdmin {
                        Text("Admin mode is required to upload files.")
                            .foregroundColor(.secondary)
                    } else if let data = selectedData {
                        HStack {
                            Image(systemName: "doc.fill")
                            VStack(alignment: .leading) {
                                Text(selectedName)
                                    .font(.subheadline.weight(.semibold))
                                Text(Formatters.bytes(Int64(data.count)))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                            Button(role: .destructive) {
                                selectedData = nil
                                selectedName = ""
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .accessibilityLabel("Remove selected file")
                            }
                        }
                    } else {
                        Button("Select File") { showPicker = true }
                    }
                }
                Section {
                    Button("Upload") {
                        uploadIfConfirmed()
                    }
                    .disabled(!isAdmin || selectedData == nil || selectedName.isEmpty)
                }
            }
            .navigationTitle("Upload")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $showPicker) {
                DocumentPicker(selectedData: $selectedData, selectedName: $selectedName)
            }
            .alert("Overwrite?", isPresented: $showOverwriteConfirmation) {
                Button("Cancel", role: .cancel) {}
                Button("Overwrite", role: .destructive) {
                    Task { await upload() }
                }
            } message: {
                Text("A file with that name already exists. Overwrite it?")
            }
            .alert("Error", isPresented: $showActionError) {
                Button("OK") { actionError = nil }
            } message: {
                Text(actionError ?? "")
            }
        }
    }

    private func uploadIfConfirmed() {
        guard selectedData != nil else { return }
        if viewModel.entryExists(name: selectedName) {
            showOverwriteConfirmation = true
            return
        }
        Task { await upload() }
    }

    private func upload() async {
        guard let data = selectedData else { return }
        if let error = await viewModel.upload(data: data, filename: selectedName) {
            actionError = error
            showActionError = true
        } else {
            dismiss()
        }
    }
}

struct DocumentPicker: UIViewControllerRepresentable {
    @Binding var selectedData: Data?
    @Binding var selectedName: String
    @Environment(\.dismiss) var dismiss

    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: [.item])
        picker.delegate = context.coordinator
        picker.allowsMultipleSelection = false
        return picker
    }

    func updateUIViewController(_ uiViewController: UIDocumentPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    class Coordinator: NSObject, UIDocumentPickerDelegate {
        let parent: DocumentPicker
        init(_ parent: DocumentPicker) { self.parent = parent }

        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            guard let url = urls.first else { return }
            guard url.startAccessingSecurityScopedResource() else { return }
            defer { url.stopAccessingSecurityScopedResource() }
            parent.selectedData = try? Data(contentsOf: url)
            parent.selectedName = url.lastPathComponent
            parent.dismiss()
        }
    }
}
