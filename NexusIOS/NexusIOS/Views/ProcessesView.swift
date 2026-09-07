import SwiftUI

struct ProcessesView: View {
    @StateObject private var viewModel = ProcessesViewModel()
    @EnvironmentObject var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    @State private var selectedProcess: ProcessInfo?
    @State private var confirmKill: ProcessInfo?
    @State private var actionMessage: String?

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        List {
            Section {
                HStack(spacing: 12) {
                    StatTile(
                        systemImage: "cpu.fill",
                        title: "CPU",
                        value: String(format: "%.0f%%", viewModel.cpuPercent),
                        color: metricColor(for: viewModel.cpuPercent, warning: 80, critical: 95)
                    )
                    StatTile(
                        systemImage: "memorychip",
                        title: "Memory",
                        value: String(format: "%.0f%%", viewModel.memoryPercent),
                        color: metricColor(for: viewModel.memoryPercent, warning: 80, critical: 90)
                    )
                    StatTile(
                        systemImage: "bolt.horizontal.fill",
                        title: "Load",
                        value: viewModel.loadAverage.map { String(format: "%.2f", $0) }.joined(separator: " "),
                        color: .indigo
                    )
                    StatTile(
                        systemImage: "play.circle.fill",
                        title: "Running",
                        value: "\(viewModel.running)",
                        color: .green
                    )
                }
                .listRowInsets(EdgeInsets(top: 10, leading: 14, bottom: 10, trailing: 14))
            }

            if let actionMessage {
                Section {
                    Text(actionMessage)
                        .font(.footnote)
                        .foregroundColor(.secondary)
                }
            }

            if let error = viewModel.error {
                Section {
                    ErrorBanner(error: error) {
                        Task { await viewModel.load() }
                    }
                }
            }

            if viewModel.isLoading && viewModel.processes.isEmpty {
                Section {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 120)
                }
            } else if viewModel.filteredProcesses.isEmpty {
                Section {
                    EmptyStateView(title: "No matching processes", systemImage: "square.stack.3d.up.slash")
                }
            } else {
                Section {
                    ForEach(viewModel.filteredProcesses) { process in
                        Button {
                            selectedProcess = process
                        } label: {
                            ProcessRow(process: process)
                        }
                        .buttonStyle(.plain)
                    }
                } header: {
                    Text("\(viewModel.filteredProcesses.count) of \(viewModel.total) processes")
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Processes")
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $viewModel.filter, placement: .navigationBarDrawer(displayMode: .always), prompt: "Name, user, or command")
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Menu {
                    Picker("Sort by", selection: $viewModel.sortKey) {
                        ForEach(ProcessesViewModel.ProcessSortKey.allCases) { key in
                            Text(key.label).tag(key)
                        }
                    }
                    Button(action: { viewModel.sortAscending.toggle() }) {
                        Label(
                            viewModel.sortAscending ? "Descending" : "Ascending",
                            systemImage: viewModel.sortAscending ? "arrow.down" : "arrow.up"
                        )
                    }
                } label: {
                    Image(systemName: "arrow.up.arrow.down")
                }
            }
        }
        .refreshable { await viewModel.load() }
        .task {
            await viewModel.load()
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 5_000_000_000)
                guard !Task.isCancelled, scenePhase == .active else { continue }
                await viewModel.load()
            }
        }
        .sheet(item: $selectedProcess) { process in
            ProcessDetailSheet(process: process, viewModel: viewModel)
        }
        .alert(
            "Stop process?",
            isPresented: Binding(
                get: { confirmKill != nil },
                set: { if !$0 { confirmKill = nil } }
            )
        ) {
            Button("Cancel", role: .cancel) { confirmKill = nil }
            Button("Stop", role: .destructive) {
                guard let process = confirmKill else { return }
                confirmKill = nil
                Task {
                    if let message = await viewModel.kill(process) {
                        actionMessage = message
                    }
                }
            }
        } message: {
            Text(confirmKill.map { "Send SIGTERM to \($0.name) (PID \($0.pid))?" } ?? "")
        }
    }
}

struct ProcessRow: View {
    let process: ProcessInfo

    var body: some View {
        HStack(spacing: 12) {
            Text(String(format: "%.0f", process.cpuPercent))
                .font(.system(.callout, design: .rounded, weight: .bold))
                .foregroundColor(process.cpuPercent >= 50 ? .red : .secondary)
                .frame(width: 42, alignment: .trailing)
            VStack(alignment: .leading, spacing: 2) {
                Text(process.name)
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.primary)
                    .lineLimit(1)
                Text("\(process.username) · \(Formatters.bytes(process.memoryBytes))")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            StatusBadge(text: process.status.capitalized, color: NexusTheme.statusColor(process.status == "sleeping" ? "sleeping" : process.status))
        }
        .padding(.vertical, 2)
    }
}

struct ProcessDetailSheet: View {
    let process: ProcessInfo
    @ObservedObject var viewModel: ProcessesViewModel
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @State private var isLoading = false
    @State private var message: String?

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        NavigationStack {
            Form {
                Section("Process") {
                    LabeledValue(label: "Name", value: process.name)
                    LabeledValue(label: "PID", value: String(process.pid))
                    LabeledValue(label: "User", value: process.username)
                    LabeledValue(label: "State", value: process.status.capitalized)
                    LabeledValue(label: "CPU", value: String(format: "%.1f%%", process.cpuPercent))
                    LabeledValue(label: "Memory", value: Formatters.bytes(process.memoryBytes))
                }

                Section("Command") {
                    Text(process.command)
                        .font(.caption.monospaced())
                        .textSelection(.enabled)
                }

                if let message {
                    Section {
                        Text(message)
                            .font(.footnote)
                            .foregroundColor(.secondary)
                    }
                }

                if !isAdmin {
                    Section {
                        Text("Admin mode is required to stop processes.")
                            .font(.footnote)
                            .foregroundColor(.secondary)
                    }
                }

                Section {
                    Button(role: .destructive) {
                        Task {
                            isLoading = true
                            message = await viewModel.kill(process)
                            isLoading = false
                            if message == nil { dismiss() }
                        }
                    } label: {
                        HStack {
                            Text("Send SIGTERM")
                            Spacer()
                            if isLoading { ProgressView() }
                        }
                    }
                    .disabled(isLoading || !isAdmin)
                }
            }
            .navigationTitle(process.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }
}
