import SwiftUI
import UIKit

struct TerminalView: View {
    @StateObject private var viewModel = TerminalViewModel()
    @State private var input = ""
    @State private var isAtBottom = true
    @State private var scrollToBottomRequest = false
    @State private var copiedFeedback = false
    @FocusState private var inputFocused: Bool

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
                    Button(action: { viewModel.connect() }) {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(viewModel.isConnected)
                }
                .padding(.horizontal)
                .padding(.vertical, 8)
                .background(Color(.systemGroupedBackground))

                ZStack(alignment: .bottomTrailing) {
                    ScrollViewReader { proxy in
                        ScrollView {
                            Text(viewModel.output)
                                .font(.system(.caption, design: .monospaced))
                                .textSelection(.enabled)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding()

                            Color.clear
                                .frame(height: 1)
                                .id("bottom")
                                .onAppear { isAtBottom = true }
                                .onDisappear { isAtBottom = false }
                        }
                        .background(Color.black)
                        .foregroundColor(.green)
                        .onChange(of: viewModel.output) { _ in
                            if isAtBottom {
                                proxy.scrollTo("bottom", anchor: .bottom)
                            }
                        }
                        .onChange(of: scrollToBottomRequest) { _ in
                            if scrollToBottomRequest {
                                withAnimation {
                                    proxy.scrollTo("bottom", anchor: .bottom)
                                }
                                isAtBottom = true
                                scrollToBottomRequest = false
                            }
                        }
                        .background(
                            GeometryReader { geo in
                                Color.clear
                                    .onAppear { updateTerminalSize(geo.size) }
                                    .onChange(of: geo.size) { _ in updateTerminalSize(geo.size) }
                            }
                        )
                    }

                    if !isAtBottom {
                        Button {
                            scrollToBottomRequest = true
                        } label: {
                            Image(systemName: "chevron.down")
                                .font(.caption.weight(.bold))
                                .padding(10)
                                .background(.ultraThinMaterial)
                                .foregroundColor(.green)
                                .clipShape(Circle())
                                .shadow(color: .black.opacity(0.3), radius: 4, y: 2)
                        }
                        .padding(12)
                    }
                }

                HStack {
                    TextField("Command", text: $input)
                        .textFieldStyle(.roundedBorder)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                        .focused($inputFocused)
                        .keyboardType(.asciiCapable)
                        .submitLabel(.send)
                        .onSubmit(send)
                    Button(action: send) {
                        Image(systemName: "return")
                    }
                    .disabled(input.isEmpty || !viewModel.isConnected)
                }
                .padding()
                .background(Color(.systemGroupedBackground))
            }
            .navigationTitle("Terminal")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: copyAll) {
                        Image(systemName: copiedFeedback ? "checkmark" : "doc.on.doc")
                    }
                    .disabled(viewModel.output.isEmpty)
                }
            }
            .onAppear {
                viewModel.connect()
                inputFocused = true
            }
            .onDisappear {
                viewModel.disconnect()
            }
        }
    }

    private func send() {
        guard !input.isEmpty else { return }
        viewModel.sendInput(input + "\n")
        input = ""
        if !isAtBottom {
            scrollToBottomRequest = true
        }
    }

    private func copyAll() {
        UIPasteboard.general.string = viewModel.output
        withAnimation { copiedFeedback = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            withAnimation { copiedFeedback = false }
        }
    }

    private func updateTerminalSize(_ size: CGSize) {
        let charWidth: CGFloat = 8.0
        let lineHeight: CGFloat = 14.0
        let cols = max(1, Int(size.width / charWidth))
        let rows = max(1, Int(size.height / lineHeight))
        viewModel.sendResize(rows: rows, cols: cols)
    }
}
