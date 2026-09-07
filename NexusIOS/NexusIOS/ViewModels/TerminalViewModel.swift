import Foundation

@MainActor
final class TerminalViewModel: ObservableObject {
    @Published var isConnected = false
    var onOutput: ((String) -> Void)?
    var onDisconnect: ((Error?) -> Void)?

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
}

extension TerminalViewModel: NexusWebSocketDelegate {
    nonisolated func webSocketDidReceiveMessage(_ message: String) {
        Task { @MainActor in
            self.onOutput?(message)
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
            self.onDisconnect?(error)
        }
    }
}
