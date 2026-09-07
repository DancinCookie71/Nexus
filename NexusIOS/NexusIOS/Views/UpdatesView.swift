import SwiftUI

struct UpdatesView: View {
    @StateObject private var viewModel = UpdatesViewModel()
    @EnvironmentObject var appState: AppState
    @State private var showInstallConfirm = false
    @State private var showRebootConfirm = false

    private var isAdmin: Bool { appState.adminStatus?.isAdmin == true }

    var body: some View {
        List {
            if let info = viewModel.info, info.rebootRequired {
                Section {
                    Label("System restart required. Updates are waiting to take effect.", systemImage: "arrow.counterclockwise.circle.fill")
                        .font(.footnote.weight(.medium))
                        .foregroundColor(.orange)
                }
            }

            if let error = viewModel.error {
                Section {
                    ErrorBanner(error: error) {
                        Task { await viewModel.load() }
                    }
                }
            }

            if let info = viewModel.info {
                Section {
                    StatTile(
                        systemImage: "arrow.down.circle.fill",
                        title: "Available",
                        value: info.supported ? "\(info.updateCount)" : "Not supported",
                        detail: info.packageManager.map { "via \($0)" } ?? "",
                        color: info.updateCount > 0 ? .orange : .green
                    )
                    .listRowInsets(EdgeInsets(top: 10, leading: 14, bottom: 10, trailing: 14))
                    if let checked = info.lastChecked {
                        LabeledValue(label: "Last checked", value: Formatters.shortDate(checked))
                    }
                }

                if !info.supported {
                    Section {
                        Text(info.error ?? "Update detection is not supported on this system.")
                            .font(.footnote)
                            .foregroundColor(.secondary)
                    }
                } else if info.packages.isEmpty {
                    Section {
                        EmptyStateView(title: "System is up to date", systemImage: "checkmark.seal.fill")
                    }
                } else {
                    Section("Packages") {
                        ForEach(info.packages, id: \.self) { package in
                            Text(package)
                                .font(.footnote.monospaced())
                        }
                    }
                }

                if info.supported && isAdmin {
                    Section {
                        Toggle("Reboot after installing", isOn: $viewModel.rebootAfter)
                        Button {
                            showInstallConfirm = true
                        } label: {
                            HStack {
                                Spacer()
                                if viewModel.isInstalling {
                                    Text("Installing… this can take a while")
                                        .font(.subheadline.weight(.semibold))
                                    ProgressView()
                                } else {
                                    Text("Install \(info.updateCount) Update\(info.updateCount == 1 ? "" : "s")")
                                        .font(.subheadline.weight(.semibold))
                                }
                                Spacer()
                            }
                        }
                        .disabled(viewModel.isInstalling || info.updateCount == 0)
                    } footer: {
                        Text("Upgrades every package on the server. Do not close the app while installing.")
                    }
                } else if info.supported && !isAdmin {
                    Section {
                        Text("Enable Admin mode to install updates.")
                            .font(.footnote)
                            .foregroundColor(.secondary)
                    }
                }
            } else if viewModel.isLoading {
                Section {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 120)
                }
            }

            if let message = viewModel.resultMessage {
                Section {
                    Label(message, systemImage: viewModel.resultIsError ? "exclamationmark.triangle.fill" : "checkmark.circle.fill")
                        .font(.footnote)
                        .foregroundColor(viewModel.resultIsError ? .red : .green)
                }
            }

            if isAdmin {
                Section("Danger Zone") {
                    Button(role: .destructive) {
                        showRebootConfirm = true
                    } label: {
                        HStack {
                            Spacer()
                            Text("Reboot Server")
                            Spacer()
                        }
                    }
                }
            }
        }
        .navigationTitle("Updates")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await viewModel.load() }
        .task { await viewModel.load() }
        .confirmationDialog(
            "Install all updates?",
            isPresented: $showInstallConfirm,
            titleVisibility: .visible
        ) {
            Button("Install \(viewModel.info?.updateCount ?? 0) updates", role: .destructive) {
                Task { await viewModel.install() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text(viewModel.rebootAfter
                 ? "The server will reboot automatically when finished."
                 : "This upgrades every package and can take a long time.")
        }
        .alert("Reboot the server now?", isPresented: $showRebootConfirm) {
            Button("Cancel", role: .cancel) {}
            Button("Reboot", role: .destructive) {
                Task {
                    if let message = await viewModel.rebootNow() {
                        viewModel.resultMessage = message
                        viewModel.resultIsError = false
                    }
                }
            }
        } message: {
            Text("The panel will be unreachable until the server comes back up.")
        }
    }
}
