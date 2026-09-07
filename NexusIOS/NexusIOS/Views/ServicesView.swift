import SwiftUI
import Combine

struct ServicesView: View {
    @StateObject private var viewModel = ServicesViewModel()
    @EnvironmentObject var appState: AppState
    @State private var selectedService: ServiceSummary?

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Toggle("Show system services", isOn: $viewModel.showSystem)
                }

                if let error = viewModel.error {
                    Section {
                        ErrorBanner(error: error) {
                            Task { await viewModel.load() }
                        }
                    }
                }

                if viewModel.isLoading && viewModel.services.isEmpty {
                    Section {
                        ProgressView()
                            .frame(maxWidth: .infinity, minHeight: 120)
                    }
                } else if viewModel.services.isEmpty {
                    Section {
                        EmptyStateView(title: "No services", systemImage: "gearshape.2")
                    }
                } else {
                    ForEach(viewModel.services) { service in
                        Button {
                            selectedService = service
                        } label: {
                            ServiceRow(service: service)
                        }
                        .buttonStyle(.plain)
                        .swipeActions(edge: .trailing) {
                            if isAdmin {
                                if service.activeState == "active" {
                                    Button("Restart") {
                                        Task { await viewModel.performAction(service, action: "restart") }
                                    }
                                    .tint(.blue)
                                    Button("Stop", role: .destructive) {
                                        Haptics.heavy()
                                        Task { await viewModel.performAction(service, action: "stop") }
                                    }
                                } else {
                                    Button("Start") {
                                        Task { await viewModel.performAction(service, action: "start") }
                                    }
                                    .tint(.green)
                                }
                            }
                        }
                        .disabled(!isAdmin)
                    }
                }
            }
            .navigationTitle("Services")
            .searchable(text: $viewModel.searchQuery, placement: .navigationBarDrawer(displayMode: .always))
            .onChange(of: viewModel.showSystem) { _ in Task { await viewModel.load() } }
            .refreshable { await viewModel.load() }
            .task { await viewModel.load() }
            .sheet(item: $selectedService) { service in
                ServiceDetailSheet(service: service, viewModel: viewModel)
            }
        }
    }
}

struct ServiceRow: View {
    let service: ServiceSummary

    var body: some View {
        HStack {
            Image(systemName: statusIcon)
                .foregroundColor(statusColor)
            VStack(alignment: .leading, spacing: 2) {
                Text(service.name)
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.primary)
                Text(service.description ?? service.subState ?? "")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            StatusBadge(text: service.activeState?.capitalized ?? "—", color: statusColor)
        }
        .padding(.vertical, 4)
    }

    private var statusColor: Color {
        NexusTheme.statusColor(service.activeState)
    }

    private var statusIcon: String {
        NexusTheme.statusIcon(service.activeState)
    }
}

struct ServiceDetailSheet: View {
    let service: ServiceSummary
    @ObservedObject var viewModel: ServicesViewModel
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @State private var isLoading = false
    @State private var message: String?
    @State private var error: NexusError?
    @State private var showError = false

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        NavigationStack {
            Form {
                Section("Status") {
                    LabeledValue(label: "State", value: service.activeState)
                    LabeledValue(label: "Sub-state", value: service.subState)
                    LabeledValue(label: "Enabled", value: service.unitFileState)
                    LabeledValue(label: "PID", value: service.mainPid.map { $0 == 0 ? "—" : String($0) })
                    LabeledValue(label: "Memory", value: Formatters.bytes(service.memoryCurrent ?? 0))
                }

                if !isAdmin {
                    Section {
                        Text("Admin mode is required to perform service actions.")
                            .foregroundColor(.secondary)
                            .font(.footnote)
                    }
                }

                Section("Actions") {
                    ServiceActionButton(title: "Start", isLoading: isLoading, enabled: isAdmin && service.activeState != "active") { action("start") }
                    ServiceActionButton(title: "Stop", isDestructive: true, isLoading: isLoading, enabled: isAdmin && service.activeState == "active") { action("stop") }
                    ServiceActionButton(title: "Restart", isLoading: isLoading, enabled: isAdmin) { action("restart") }
                    ServiceActionButton(title: "Reload", isLoading: isLoading, enabled: isAdmin) { action("reload") }
                    ServiceActionButton(title: "Enable", isLoading: isLoading, enabled: isAdmin) { action("enable") }
                    ServiceActionButton(title: "Disable", isLoading: isLoading, enabled: isAdmin) { action("disable") }
                }

                if let message = message {
                    Section {
                        Text(message)
                            .foregroundColor(.secondary)
                            .font(.footnote)
                    }
                }
            }
            .navigationTitle(service.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") { error = nil }
            } message: {
                Text(error?.localizedDescription ?? "")
            }
        }
    }

    private func action(_ name: String) {
        Task {
            isLoading = true
            if let result = await viewModel.performAction(service, action: name) {
                error = .apiError(result)
                showError = true
            }
            isLoading = false
        }
    }
}

struct ServiceActionButton: View {
    let title: String
    var isDestructive = false
    let isLoading: Bool
    let enabled: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Text(title)
                Spacer()
                if isLoading { ProgressView() }
            }
        }
        .foregroundColor(isDestructive ? .red : .primary)
        .disabled(!enabled || isLoading)
    }
}
