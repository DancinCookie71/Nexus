import Foundation

protocol NexusWebSocketDelegate: AnyObject {
    func webSocketDidReceiveMessage(_ message: String)
    func webSocketDidDisconnect(error: Error?)
    func webSocketDidConnect()
}

final class NexusWebSocket: NSObject, URLSessionWebSocketDelegate {
    private var task: URLSessionWebSocketTask?
    private var session: URLSession?
    private let url: URL
    private var isConnected = false
    private var shouldStayConnected = false
    private var reconnectAttempts = 0

    weak var delegate: NexusWebSocketDelegate?

    init(path: String) {
        let base = NexusAuthStore.shared.serverURL.trimmingCharacters(in: .whitespacesAndNewlines)
        var components = URLComponents(string: base)
        let isSecure = components?.scheme == "https"
        components?.scheme = isSecure ? "wss" : "ws"
        components?.path = path
        if let token = NexusAuthStore.shared.token {
            components?.queryItems = [URLQueryItem(name: "token", value: token)]
        }
        self.url = components?.url ?? URL(string: "ws://localhost")!
        super.init()
    }

    func connect() {
        shouldStayConnected = true
        reconnectAttempts = 0
        openConnection()
    }

    func disconnect() {
        shouldStayConnected = false
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
        session?.invalidateAndCancel()
        session = nil
        isConnected = false
    }

    private func openConnection() {
        task?.cancel(with: .goingAway, reason: nil)
        session?.invalidateAndCancel()
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        let session = URLSession(configuration: config, delegate: self, delegateQueue: .main)
        self.session = session
        let task = session.webSocketTask(with: url)
        self.task = task
        task.resume()
        listen()
    }

    private func scheduleReconnect() {
        guard shouldStayConnected else { return }
        reconnectAttempts += 1
        let delay = TimeInterval(min(30, pow(2, Double(min(reconnectAttempts, 5)))))
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self = self, self.shouldStayConnected, !self.isConnected else { return }
            self.openConnection()
        }
    }

    func send(_ text: String) {
        task?.send(.string(text)) { _ in }
    }

    private func listen() {
        task?.receive { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self.delegate?.webSocketDidReceiveMessage(text)
                case .data:
                    break
                case .binary(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self.delegate?.webSocketDidReceiveMessage(text)
                    }
                @unknown default:
                    break
                }
                self.listen()
            case .failure(let error):
                let wasConnected = self.isConnected
                self.isConnected = false
                if wasConnected {
                    self.delegate?.webSocketDidDisconnect(error: error)
                }
                self.scheduleReconnect()
            }
        }
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        isConnected = true
        reconnectAttempts = 0
        delegate?.webSocketDidConnect()
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        let wasConnected = isConnected
        isConnected = false
        if wasConnected {
            delegate?.webSocketDidDisconnect(error: error)
        }
        if error != nil {
            scheduleReconnect()
        }
    }
}
