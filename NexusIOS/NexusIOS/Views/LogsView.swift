import SwiftUI

struct LogsView: View {
    @StateObject private var viewModel = LogsViewModel()
    @EnvironmentObject var appState: AppState

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        List {
            Section {
                TextField("Service", text: $viewModel.serviceName)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                    .disabled(!isAdmin)
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
            } else if viewModel.entries.isEmpty {
                Section {
                    EmptyStateView(title: "No log entries", systemImage: "doc.text")
                }
            } else {
                ForEach(viewModel.entries) { entry in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(entry.timestamp?.replacingOccurrences(of: "T", with: " ").prefix(19) ?? "—")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                            Spacer()
                            StatusBadge(text: entry.priorityName, color: priorityColor(entry.priority))
                        }
                        Text(entry.message)
                            .font(.caption)
                            .textSelection(.enabled)
                    }
                    .padding(.vertical, 2)
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Logs")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await viewModel.load() }
        .task { await viewModel.load() }
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button("Load") {
                    Task { await viewModel.load() }
                }
                .disabled(!isAdmin)
            }
        }
    }

    private func priorityColor(_ priority: Int) -> Color {
        switch priority {
        case 0...2: return .red
        case 3: return .orange
        case 4: return .yellow
        default: return .secondary
        }
    }
}
