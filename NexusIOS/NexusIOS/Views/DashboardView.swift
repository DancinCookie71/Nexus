import SwiftUI

struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    if let error = viewModel.error {
                        ErrorBanner(error: error) {
                            Task { await viewModel.load() }
                        }
                    }

                    OverallStatusCard(snapshot: viewModel.snapshot)

                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                        MetricCard(
                            title: "CPU",
                            value: cpuText,
                            detail: viewModel.snapshot?.cpu.temperatureC.map { String(format: "%.1f °C", $0) } ?? "",
                            color: metricColor(for: viewModel.snapshot?.cpu.percent ?? 0, warning: 80, critical: 95)
                        )
                        MetricCard(
                            title: "Memory",
                            value: memoryText,
                            detail: Formatters.bytes(viewModel.snapshot?.memory.usedBytes ?? 0) + " used",
                            color: metricColor(for: viewModel.snapshot?.memory.percent ?? 0, warning: 80, critical: 90)
                        )
                    }

                    if let snapshot = viewModel.snapshot {
                        DisksCard(disks: snapshot.disks)
                        NetworkCard(network: snapshot.network)
                        if let gpus = snapshot.gpus, !gpus.isEmpty {
                            GpuCard(gpus: gpus)
                        }
                        SystemInfoCard(system: viewModel.system)
                    }
                }
                .padding()
            }
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

    private var cpuText: String {
        guard let cpu = viewModel.snapshot?.cpu else { return "--" }
        return String(format: "%.1f%%", cpu.percent)
    }

    private var memoryText: String {
        guard let mem = viewModel.snapshot?.memory else { return "--" }
        return String(format: "%.1f%%", mem.percent)
    }
}

struct OverallStatusCard: View {
    let snapshot: HealthSnapshot?

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: statusIcon)
                .font(.system(size: 32))
                .foregroundColor(statusColor)
            VStack(alignment: .leading, spacing: 4) {
                Text("Overall Status")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(snapshot?.overall.uppercased() ?? "UNKNOWN")
                    .font(.title2.weight(.bold))
                    .foregroundColor(statusColor)
                Text(summary)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
            Spacer()
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(statusColor.opacity(0.08))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(statusColor.opacity(0.2), lineWidth: 1)
        )
    }

    private var statusColor: Color {
        switch snapshot?.overall {
        case "healthy": return .green
        case "warning": return .orange
        case "critical": return .red
        default: return .gray
        }
    }

    private var statusIcon: String {
        switch snapshot?.overall {
        case "healthy": return "checkmark.circle.fill"
        case "warning": return "exclamationmark.triangle.fill"
        case "critical": return "xmark.octagon.fill"
        default: return "questionmark.circle.fill"
        }
    }

    private var summary: String {
        guard let snapshot = snapshot else { return "Loading..." }
        var parts: [String] = []
        if snapshot.failedServices.count > 0 { parts.append("\(snapshot.failedServices.count) failed services") }
        if snapshot.filesystemErrors.count > 0 { parts.append("\(snapshot.filesystemErrors.count) filesystem errors") }
        if snapshot.updateCount > 0 { parts.append("\(snapshot.updateCount) updates") }
        return parts.isEmpty ? "All systems operating normally" : parts.joined(separator: " · ")
    }
}

struct MetricCard: View {
    let title: String
    let value: String
    let detail: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
                .textCase(.uppercase)
                .tracking(0.5)
            Text(value)
                .font(.system(.title, design: .rounded, weight: .bold))
                .foregroundColor(color)
            Text(detail)
                .font(.caption2)
                .foregroundColor(.secondary)
                .lineLimit(1)
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
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
            Text("Storage")
                .font(.headline)
            ForEach(uniqueDisks, id: \.device) { disk in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(disk.mountpoint)
                            .font(.subheadline.weight(.semibold))
                        Text(Formatters.bytes(disk.usedBytes) + " / " + Formatters.bytes(disk.totalBytes))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Text(String(format: "%.1f%%", disk.percent))
                        .font(.system(.callout, design: .rounded, weight: .bold))
                        .foregroundColor(metricColor(for: disk.percent, warning: 85, critical: 95))
                }
                .padding(.vertical, 4)
            }
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}

struct NetworkCard: View {
    let network: NetworkSnapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Network")
                .font(.headline)
            HStack {
                NetworkMetric(label: "Upload", value: network.totalBytesSentPerSec)
                Spacer()
                NetworkMetric(label: "Download", value: network.totalBytesRecvPerSec)
            }
            if let latency = network.latencyMs {
                Text("Latency: \(String(format: "%.1f", latency)) ms")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}

struct NetworkMetric: View {
    let label: String
    let value: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Text(Formatters.bytesPerSecond(value))
                .font(.callout.weight(.semibold))
        }
    }
}

struct GpuCard: View {
    let gpus: [GpuSnapshot]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("GPU")
                .font(.headline)
            ForEach(gpus, id: \.name) { gpu in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(gpu.name)
                            .font(.subheadline.weight(.semibold))
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
        .padding()
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}

struct SystemInfoCard: View {
    let system: SystemStatsResponse?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("System")
                .font(.headline)
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
            LabeledValue(label: "Uptime", value: Formatters.uptime(system?.uptimeSeconds ?? 0))
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}

struct LabeledValue: View {
    let label: String
    let value: String?

    var body: some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Spacer()
            Text(value ?? "—")
                .font(.subheadline)
                .multilineTextAlignment(.trailing)
        }
        .padding(.vertical, 2)
    }
}

func metricColor(for value: Double, warning: Double, critical: Double) -> Color {
    if value >= critical { return .red }
    if value >= warning { return .orange }
    return .green
}
