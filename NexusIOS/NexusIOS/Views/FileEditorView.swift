import SwiftUI

struct FileEditorView: View {
    let path: String
    @StateObject private var viewModel: FileEditorViewModel
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @FocusState private var isEditing: Bool
    @State private var showUnsavedConfirmation = false

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    init(path: String) {
        self.path = path
        _viewModel = StateObject(wrappedValue: FileEditorViewModel(path: path))
    }

    var body: some View {
        NavigationStack {
            ZStack {
                if viewModel.isLoading {
                    ProgressView()
                } else if viewModel.error != nil {
                    EmptyStateView(title: "Unable to load file", systemImage: "exclamationmark.triangle")
                } else {
                    TextEditor(text: $viewModel.content)
                        .font(.system(.body, design: .monospaced))
                        .focused($isEditing)
                        .disabled(!isAdmin)
                }
            }
            .navigationTitle(URL(fileURLWithPath: path).lastPathComponent)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") {
                        if viewModel.hasUnsavedChanges {
                            showUnsavedConfirmation = true
                        } else {
                            dismiss()
                        }
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await viewModel.save() }
                    }
                    .disabled(!isAdmin || viewModel.isLoading || !viewModel.hasUnsavedChanges)
                }
            }
            .task { await viewModel.load() }
            .alert("Unsaved Changes", isPresented: $showUnsavedConfirmation) {
                Button("Discard", role: .destructive) { dismiss() }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("You have unsaved changes. Discard them?")
            }
            .alert("Error", isPresented: Binding(
                get: { viewModel.error != nil },
                set: { if !$0 { viewModel.error = nil } }
            )) {
                Button("OK") { viewModel.error = nil }
            } message: {
                Text(viewModel.error?.localizedDescription ?? "")
            }
            .overlay(alignment: .bottom) {
                if let message = viewModel.saveMessage {
                    Text(message)
                        .font(.caption.weight(.semibold))
                        .padding(8)
                        .background(Color.green.opacity(0.9))
                        .foregroundColor(.white)
                        .cornerRadius(8)
                        .padding(.bottom, 16)
                        .onAppear {
                            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                viewModel.saveMessage = nil
                            }
                        }
                }
            }
        }
    }
}
