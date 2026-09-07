import SwiftUI

struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 14) {
                    if let error = viewModel.error {
                        ErrorBanner(error: error) {
                            Task { await viewModel.load() }
                        }
                    }

                    OverallStatusCard(snapshot: viewModel.snapshot, system: viewModel.system)

                    HStack(spacing: 12) {
                        RingGauge(
                            title: "CPU",
                            percent: viewModel.snapshot?.cpu.percent ?? 0,
                            detail: cpuDetail,
                            color: metricColor(for: viewModel.snapshot?.cpu.percent ?? 0, warning: 80, critical: 95)
                        )
                        .nexusCard()
                        RingGauge(
                            title: "Memory",
                            percent: viewModel.snapshot?.memory.percent ?? 0,
                            detail: memoryDetail,
                            color: metricColor(for: viewModel.snapshot?.memory.percent ?? 0, warning: 80, critical: 90)
                        )
                        .nexusCard()
                    }

                    if viewModel.historyCount >= 2 {
                        HistoryCard(cpu: viewModel.cpuHistory, memory: viewModel.memoryHistory)
                    }

                    if let info = viewModel.updateInfo, info.supported, info.updateCount > 0 {
                        NavigationLink {
                            UpdatesView()
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "arrow.down.circle.fill")
                                    .font(.system(size: 20))
                                    .foregroundColor(.orange)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("\(info.updateCount) update\(info.updateCount == 1 ? "" : "s") available")
                                        .font(.subheadline.weight(.semibold))
                                        .foregroundColor(.primary)
                                    Text("Tap to review and install")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.caption.weight(.bold))
                                    .foregroundColor(.secondary)
                            }
                        }
                        .buttonStyle(.plain)
                        .nexusCard()
                    }

                    if let snapshot = viewModel.snapshot {
                        if !snapshot.failedServices.isEmpty || !snapshot.filesystemErrors.isEmpty {
                            WarningCard(snapshot: snapshot)
                        }
                        DisksCard(disks: snapshot.disks)
                        NetworkCard(network: snapshot.network)
                        if let gpus = snapshot.gpus, !gpus.isEmpty {
                            GpuCard(gpus: gpus)
                        }
                        SystemInfoCard(system: viewModel.system)
                        QuickLinksCard()
                    }
                }
                .padding(.horizontal)
                .padding(.bottom, 24)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Dashboard")
            .refreshable { await viewModel.load() }
            .task {
                await viewModel.load()
                viewModel.startLiveUpdates()
            }
            .onDisappear {
                viewModel.stopLiveUpdates()
            }
        }
    }

    private var cpuDetail: String {
        guard let cpu = viewModel.snapshot?.cpu else { return "" }
        var parts: [String] = []
        parts.append("load \(String(format: "%.2f", cpu.load1))")
        if let temp = cpu.temperatureC {
            parts.append(String(format: "%.1f °C", temp))
        }
        return parts.joined(separator: " · ")
    }

    private var memoryDetail: String {
        guard let mem = viewModel.snapshot?.memory else { return "" }
        return Formatters.bytes(mem.usedBytes) + " of " + Formatters.bytes(mem.totalBytes)
    }
}

struct OverallStatusCard: View {
    let snapshot: HealthSnapshot?
    let system: SystemStatsResponse?

    private var statusColor: Color {
        NexusTheme.statusColor(snapshot?.overall)
    }

    private var summary: String {
        guard let snapshot = snapshot else { return "Loading..." }
        var parts: [String] = []
        if snapshot.failedServices.count > 0 { parts.append("\(snapshot.failedServices.count) failed services") }
        if snapshot.filesystemErrors.count > 0 { parts.append("\(snapshot.filesystemErrors.count) filesystem errors") }
        if snapshot.updateCount > 0 { parts.append("\(snapshot.updateCount) updates") }
        return parts.isEmpty ? "All systems operating normally" : parts.joined(separator: " · ")
    }

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: NexusTheme.statusIcon(snapshot?.overall))
                .font(.system(size: 30, weight: .semibold))
                .foregroundColor(.white)
                .frame(width: 56, height: 56)
                .background(Circle().fill(statusColor.opacity(0.9)))
            VStack(alignment: .leading, spacing: 4) {
                Text("Overall Status")
                    .font(.caption.weight(.semibold))
                    .foregroundColor(.white.opacity(0.85))
                    .textCase(.uppercase)
                    .tracking(0.6)
                Text(snapshot?.overall.capitalized ?? "Unknown")
                    .font(.system(.title2, design: .rounded, weight: .bold))
                    .foregroundColor(.white)
                Text(summary)
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.85))
                    .lineLimit(2)
                if let hostname = system?.hostname {
                    Text(hostname)
                        .font(.caption2.weight(.medium))
                        .foregroundColor(.white.opacity(0.7))
                        .lineLimit(1)
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                Text("UPTIME")
                    .font(.caption2.weight(.bold))
                    .foregroundColor(.white.opacity(0.7))
                Text(Formatters.uptime(snapshot?.uptimeSeconds ?? 0))
                    .font(.system(.callout, design: .rounded, weight: .bold))
                    .foregroundColor(.white)
            }
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: NexusTheme.cardCornerRadius, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [statusColor, statusColor.opacity(0.75)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
        )
        .shadow(color: statusColor.opacity(0.3), radius: 10, x: 0, y: 4)
    }
}

struct HistoryCard: View {
    let cpu: [MetricSample]
    let memory: [MetricSample]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Live Activity", systemImage: "chart.xyaxis.line")
            HStack(spacing: 16) {
                Sparkline(data: cpu.map { $0.value }, color: .indigo)
                    .frame(height: 44)
                Sparkline(data: memory.map { $0.value }, color: .cyan)
                    .frame(height: 44)
            }
            HStack {
                legend(color: .indigo, label: "CPU")
                Spacer()
                legend(color: .cyan, label: "Memory")
            }
        }
        .nexusCard()
    }

    private func legend(color: Color, label: String) -> some View {
        HStack(spacing: 5) {
            RoundedRectangle(cornerRadius: 2)
                .fill(color)
                .frame(width: 12, height: 4)
            Text(label)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
    }
}

struct WarningCard: View {
    let snapshot: HealthSnapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !snapshot.failedServices.isEmpty {
                Label("\(snapshot.failedServices.count) failed service\(snapshot.failedServices.count == 1 ? "" : "s")", systemImage: "xmark.octagon.fill")
                    .font(.footnote.weight(.semibold))
                    .foregroundColor(.red)
                Text(snapshot.failedServices.joined(separator: ", "))
                    .font(.caption2.monospaced())
                    .foregroundColor(.secondary)
                    .lineLimit(3)
            }
            if !snapshot.filesystemErrors.isEmpty {
                Label("\(snapshot.filesystemErrors.count) filesystem error\(snapshot.filesystemErrors.count == 1 ? "" : "s")", systemImage: "externaldrive.badge.exclamationmark")
                    .font(.footnote.weight(.semibold))
                    .foregroundColor(.orange)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .nexusCard()
    }
}

struct DisksCard: View {
    let disks: [DiskSnapshot]

    private var uniqueDisks: [DiskSnapshot] {
        var seen = Set<String>()
        return disks.filter { seen.insert($0.device).inserted }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Storage", systemImage: "internaldrive.fill")
            ForEach(uniqueDisks, id: \.device) { disk in
                LabeledProgressBar(
                    title: disk.mountpoint,
                    subtitle: Formatters.bytes(disk.usedBytes) + " of " + Formatters.bytes(disk.totalBytes)
                        + (disk.smartStatus.map { " · SMART \($0)" } ?? ""),
                    percent: disk.percent,
                    color: metricColor(for: disk.percent, warning: 85, critical: 95)
                )
            }
        }
        .nexusCard()
    }
}

struct NetworkCard: View {
    let network: NetworkSnapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Network", systemImage: "network")
            HStack(spacing: 12) {
                StatTile(
                    systemImage: "arrow.up",
                    title: "Upload",
                    value: Formatters.bytesPerSecond(network.totalBytesSentPerSec),
                    color: .indigo
                )
                StatTile(
                    systemImage: "arrow.down",
                    title: "Download",
                    value: Formatters.bytesPerSecond(network.totalBytesRecvPerSec),
                    color: .cyan
                )
            }
            if let latency = network.latencyMs {
                Text("Latency: \(String(format: "%.1f", latency)) ms")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .nexusCard()
    }
}

struct GpuCard: View {
    let gpus: [GpuSnapshot]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "GPU", systemImage: "cpu.fill")
            ForEach(gpus, id: \.name) { gpu in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(gpu.name)
                            .font(.subheadline.weight(.semibold))
                            .lineLimit(1)
                        if let temp = gpu.temperatureC {
                            Text(String(format: "%.1f °C", temp))
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    Spacer()
                    if let util = gpu.utilizationPercent {
                        Text(String(format: "%.0f%%", util))
                            .font(.system(.callout, design: .rounded, weight: .bold))
                            .foregroundColor(metricColor(for: util, warning: 80, critical: 95))
                    }
                }
                .padding(.vertical, 4)
            }
        }
        .nexusCard()
    }
}

struct SystemInfoCard: View {
    let system: SystemStatsResponse?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "System", systemImage: "server.rack")
            LabeledValue(label: "Hostname", value: system?.hostname)
            LabeledValue(label: "OS", value: system?.os)
            LabeledValue(label: "Kernel", value: system?.kernel)
            LabeledValue(label: "Architecture", value: system?.architecture)
            if let cores = system?.cpu?.cores {
                LabeledValue(label: "CPU Cores", value: "\(cores)")
            }
            if let temp = system?.temperatureCelsius {
                LabeledValue(label: "Temperature", value: String(format: "%.1f °C", temp))
            }
        }
        .nexusCard()
    }
}

struct QuickLinksCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionHeader(title: "Manage", systemImage: "slider.horizontal.3")
            NavigationLink {
                ProcessesView()
            } label: {
                MoreRow(title: "Processes", systemImage: "square.stack.3d.up", color: .blue)
                    .padding(.vertical, 4)
            }
            .buttonStyle(.plain)
            Divider()
            NavigationLink {
                UpdatesView()
            } label: {
                MoreRow(title: "Updates", systemImage: "arrow.down.circle.fill", color: .orange)
                    .padding(.vertical, 4)
            }
            .buttonStyle(.plain)
            Divider()
            NavigationLink {
                UsersView()
            } label: {
                MoreRow(title: "Users", systemImage: "person.2.fill", color: .indigo)
                    .padding(.vertical, 4)
            }
            .buttonStyle(.plain)
        }
        .nexusCard()
    }
}
