import Foundation

@MainActor
final class TerminalViewModel: ObservableObject {
    @Published var output = ""
    @Published var isConnected = false
    @Published var error: NexusError?

    private var webSocket: NexusWebSocket?

    func connect() {
        disconnect()
        webSocket = NexusWebSocket(path: "/api/v1/terminal/ws")
        webSocket?.delegate = self
        webSocket?.connect()
    }

    func disconnect() {
        webSocket?.disconnect()
        webSocket = nil
        isConnected = false
    }

    func sendInput(_ text: String) {
        let message = ["type": "input", "data": text] as [String: Any]
        if let data = try? JSONSerialization.data(withJSONObject: message),
           let string = String(data: data, encoding: .utf8) {
            webSocket?.send(string)
        }
    }

    func sendResize(rows: Int, cols: Int) {
        let message = ["type": "resize", "rows": rows, "cols": cols] as [String: Any]
        if let data = try? JSONSerialization.data(withJSONObject: message),
           let string = String(data: data, encoding: .utf8) {
            webSocket?.send(string)
        }
    }

    func append(_ text: String) {
        let cleaned = TerminalViewModel.stripAnsi(text)
        output.append(cleaned)
        if output.count > 50000 {
            let start = output.index(output.endIndex, offsetBy: -40000)
            output = String(output[start...])
        }
    }

    private static func stripAnsi(_ text: String) -> String {
        var result = text
        // ESC[ ... m (SGR colors/attributes)
        result = result.replacingOccurrences(of: "\u{1B}\\[[0-9;]*m", with: "", options: .regularExpression)
        // ESC[ ... H, ESC[ ... J, ESC[ ... K (cursor movement, clear)
        result = result.replacingOccurrences(of: "\u{1B}\\[[0-9;]*[A-HJKSTfn]", with: "", options: .regularExpression)
        // ESC[? ... h/l (mode set/reset like bracketed paste)
        result = result.replacingOccurrences(of: "\u{1B}\\[\\?[0-9;]*[hl]", with: "", options: .regularExpression)
        // ESC]0;...BEL (window title)
        result = result.replacingOccurrences(of: "\u{1B}]0;[^\u{0007}]*\u{0007}", with: "", options: .regularExpression)
        // ESC]...BEL (other OSC sequences)
        result = result.replacingOccurrences(of: "\u{1B}][^\u{0007}]*\u{0007}", with: "", options: .regularExpression)
        // ESC(B, ESC)0, ESC M (charset/scroll)
        result = result.replacingOccurrences(of: "\u{1B}[()][AB012]", with: "", options: .regularExpression)
        result = result.replacingOccurrences(of: "\u{1B}M", with: "", options: .regularExpression)
        // Generic: any remaining ESC + 1-2 chars
        result = result.replacingOccurrences(of: "\u{1B}.?", with: "", options: .regularExpression)
        return result
    }
}

extension TerminalViewModel: NexusWebSocketDelegate {
    nonisolated func webSocketDidReceiveMessage(_ message: String) {
        Task { @MainActor in
            append(message)
        }
    }

    nonisolated func webSocketDidConnect() {
        Task { @MainActor in
            isConnected = true
        }
    }

    nonisolated func webSocketDidDisconnect(error: Error?) {
        Task { @MainActor in
            isConnected = false
            if let error = error {
                self.error = .networkError(error)
            }
        }
    }
}
