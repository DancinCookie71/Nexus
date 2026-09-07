import SwiftUI
import SwiftTerm
import UIKit

struct TerminalView: View {
    @StateObject private var viewModel = TerminalViewModel()
    @State private var reconnectTick = 0

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                HStack {
                    Circle()
                        .fill(viewModel.isConnected ? Color.green : Color.red)
                        .frame(width: 8, height: 8)
                    Text(viewModel.isConnected ? "Connected" : "Disconnected")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    Button(action: reconnect) {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(viewModel.isConnected)
                }
                .padding(.horizontal)
                .padding(.vertical, 8)
                .background(Color(.systemGroupedBackground))

                TerminalHostView(viewModel: viewModel)
                    .accessibilityIdentifier("terminal-host")
            }
            .navigationTitle("Terminal")
            .onAppear {
                viewModel.connect()
            }
            .onDisappear {
                viewModel.disconnect()
            }
        }
    }

    private func reconnect() {
        Haptics.light()
        viewModel.disconnect()
        viewModel.connect()
    }
}

struct TerminalHostView: UIViewRepresentable {
    @ObservedObject var viewModel: TerminalViewModel

    func makeUIView(context: Context) -> SwiftTerm.TerminalView {
        let terminal = SwiftTerm.TerminalView(frame: .zero)
        terminal.terminalDelegate = context.coordinator
        terminal.font = UIFont.monospacedSystemFont(ofSize: 13, weight: .regular)
        terminal.backgroundColor = UIColor.black
        terminal.nativeBackgroundColor = UIColor.black
        terminal.nativeForegroundColor = UIColor(red: 0.3, green: 0.85, blue: 0.4, alpha: 1)
        viewModel.onOutput = { [weak terminal] text in
            terminal?.feed(byteSource: Array(text.utf8)[...])
        }
        return terminal
    }

    func updateUIView(_ uiView: SwiftTerm.TerminalView, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(viewModel: viewModel)
    }

    final class Coordinator: NSObject, TerminalViewDelegate {
        private let viewModel: TerminalViewModel

        init(viewModel: TerminalViewModel) {
            self.viewModel = viewModel
        }

        func send(source: SwiftTerm.TerminalView, data: ArraySlice<UInt8>) {
            let bytes = Array(data)
            if let text = String(bytes: bytes, encoding: .utf8) {
                viewModel.sendInput(text)
            }
        }

        func terminalView(_ view: SwiftTerm.TerminalView, didChangeTerminalSize size: CGSize, source: SwiftTerm.TerminalView) {
            viewModel.sendResize(rows: Int(size.height), cols: Int(size.width))
        }

        func terminalView(_ view: SwiftTerm.TerminalView, setTerminalIconTitle source: SwiftTerm.TerminalView, title: String) {}

        func terminalView(_ view: SwiftTerm.TerminalView, rangeChanged range: Range<String.Index>, source: SwiftTerm.TerminalView) {}

        func scrolled(source: SwiftTerm.TerminalView, position: Double) {}
    }
}
