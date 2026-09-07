import SwiftUI

struct ErrorBanner: View {
    let error: NexusError
    let retry: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(error.localizedDescription)
                .foregroundColor(.red)
            if let retry = retry {
                Button("Retry", action: retry)
                    .font(.caption)
            }
        }
        .padding()
        .background(Color.red.opacity(0.1))
        .cornerRadius(8)
    }
}

struct ErrorAlert: ViewModifier {
    @Binding var error: NexusError?

    func body(content: Content) -> some View {
        content
            .alert("Error", isPresented: Binding(
                get: { error != nil },
                set: { if !$0 { error = nil } }
            )) {
                Button("OK") { error = nil }
            } message: {
                Text(error?.localizedDescription ?? "")
            }
    }
}

extension View {
    func errorAlert(error: Binding<NexusError?>) -> some View {
        modifier(ErrorAlert(error: error))
    }
}

struct EmptyStateView: View {
    let title: String
    let systemImage: String

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: systemImage)
                .font(.largeTitle)
                .foregroundColor(.secondary)
            Text(title)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 120)
    }
}
