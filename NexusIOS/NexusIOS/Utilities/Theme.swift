import SwiftUI

enum NexusTheme {
    static let cardCornerRadius: CGFloat = 18
    static let accentGradient = LinearGradient(
        colors: [.indigo, .cyan],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    static let buttonGradient = LinearGradient(
        colors: [.indigo, .indigo.opacity(0.75)],
        startPoint: .leading,
        endPoint: .trailing
    )

    static func statusColor(_ status: String?) -> Color {
        switch status?.lowercased() {
        case "healthy", "active", "running", "ok", "passed": return .green
        case "warning", "degraded", "unknown": return .orange
        case "critical", "failed", "failing": return .red
        default: return .gray
        }
    }

    static func statusIcon(_ status: String?) -> String {
        switch status?.lowercased() {
        case "healthy", "active", "running", "ok", "passed": return "checkmark.circle.fill"
        case "warning", "degraded", "unknown": return "exclamationmark.triangle.fill"
        case "critical", "failed", "failing": return "xmark.octagon.fill"
        default: return "questionmark.circle.fill"
        }
    }

    static func metricColor(for value: Double, warning: Double, critical: Double) -> Color {
        if value >= critical { return .red }
        if value >= warning { return .orange }
        return .green
    }
}

struct CardBackground: ViewModifier {
    var cornerRadius: CGFloat = NexusTheme.cardCornerRadius

    func body(content: Content) -> some View {
        content
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(Color(.secondarySystemGroupedBackground))
            )
            .shadow(color: Color.black.opacity(0.06), radius: 8, x: 0, y: 3)
    }
}

extension View {
    func nexusCard(cornerRadius: CGFloat = NexusTheme.cardCornerRadius) -> some View {
        modifier(CardBackground(cornerRadius: cornerRadius))
    }
}

struct SectionHeader: View {
    let title: String
    var systemImage: String?

    var body: some View {
        HStack(spacing: 6) {
            if let systemImage {
                Image(systemName: systemImage)
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.indigo)
            }
            Text(title)
                .font(.subheadline.weight(.semibold))
                .textCase(.uppercase)
                .tracking(0.6)
                .foregroundColor(.secondary)
        }
    }
}

struct StatusBadge: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.caption2.weight(.bold))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Capsule().fill(color.opacity(0.15)))
            .foregroundColor(color)
    }
}

struct RingGauge: View {
    let title: String
    let percent: Double
    let detail: String
    let color: Color

    var body: some View {
        VStack(spacing: 10) {
            ZStack {
                Circle()
                    .stroke(color.opacity(0.15), lineWidth: 9)
                Circle()
                    .trim(from: 0, to: max(0.01, min(1, percent / 100)))
                    .stroke(
                        AngularGradient(
                            colors: [color.opacity(0.55), color],
                            center: .center,
                            startAngle: .degrees(-90),
                            endAngle: .degrees(270)
                        ),
                        style: StrokeStyle(lineWidth: 9, lineCap: .round)
                    )
                    .rotationEffect(.degrees(-90))
                VStack(spacing: 0) {
                    Text(String(format: "%.0f%%", percent))
                        .font(.system(.title3, design: .rounded, weight: .bold))
                        .foregroundColor(color)
                    Text(title)
                        .font(.caption2.weight(.semibold))
                        .foregroundColor(.secondary)
                }
            }
            .frame(width: 108, height: 108)
            Text(detail)
                .font(.caption2)
                .foregroundColor(.secondary)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity)
    }
}

struct Sparkline: View {
    let data: [Double]
    let color: Color

    var body: some View {
        GeometryReader { geometry in
            let maxValue = max(data.max() ?? 1, 10) * 1.15
            Path { path in
                guard data.count > 1 else { return }
                let step = geometry.size.width / CGFloat(max(data.count - 1, 1))
                for (index, value) in data.enumerated() {
                    let x = CGFloat(index) * step
                    let y = geometry.size.height * (1 - CGFloat(value / maxValue))
                    if index == 0 {
                        path.move(to: CGPoint(x: x, y: y))
                    } else {
                        path.addLine(to: CGPoint(x: x, y: y))
                    }
                }
            }
            .stroke(color, style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
            .shadow(color: color.opacity(0.35), radius: 2, x: 0, y: 1)
        }
    }
}

struct StatTile: View {
    let systemImage: String
    let title: String
    let value: String
    var detail: String = ""
    var color: Color = .indigo

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.system(size: 17, weight: .semibold))
                .foregroundColor(color)
                .frame(width: 38, height: 38)
                .background(Circle().fill(color.opacity(0.14)))
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption2.weight(.semibold))
                    .foregroundColor(.secondary)
                    .textCase(.uppercase)
                    .tracking(0.4)
                Text(value)
                    .font(.system(.callout, design: .rounded, weight: .bold))
                    .foregroundColor(.primary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                if !detail.isEmpty {
                    Text(detail)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
            }
            Spacer(minLength: 0)
        }
    }
}

struct LabeledProgressBar: View {
    let title: String
    let subtitle: String
    let percent: Double
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text(String(format: "%.1f%%", percent))
                    .font(.system(.callout, design: .rounded, weight: .bold))
                    .foregroundColor(color)
            }
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(color.opacity(0.14))
                    Capsule()
                        .fill(
                            LinearGradient(
                                colors: [color.opacity(0.7), color],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: max(4, geometry.size.width * min(1, percent / 100)))
                }
            }
            .frame(height: 8)
            Text(subtitle)
                .font(.caption2)
                .foregroundColor(.secondary)
                .lineLimit(1)
        }
        .padding(.vertical, 3)
    }
}

struct LabeledValue: View {
    let label: String
    let value: String?

    var body: some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundColor(.secondary)
            Spacer()
            Text(value ?? "—")
                .font(.subheadline.weight(.medium))
                .multilineTextAlignment(.trailing)
        }
        .padding(.vertical, 2)
    }
}
