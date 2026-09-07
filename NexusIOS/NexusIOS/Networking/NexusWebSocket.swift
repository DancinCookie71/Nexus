import Foundation

protocol NexusWebSocketDelegate: AnyObject {
    func webSocketDidReceiveMessage(_ message: String)
    func webSocketDidDisconnect(error: Error?)
    func webSocketDidConnect()
}

final class NexusWebSocket: NSObject, URLSessionWebSocketDelegate {
    private var task: URLSessionWebSocketTask?
    private let url: URL
    private var session: URLSession?
    private var isConnected = false

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
        disconnect()
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        let session = URLSession(configuration: config, delegate: self, delegateQueue: .main)
        self.session = session
        let task = session.webSocketTask(with: url)
        self.task = task
        task.resume()
        listen()
    }

    func disconnect() {
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
        session = nil
        isConnected = false
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
                @unknown default:
                    break
                }
                self.listen()
            case .failure(let error):
                self.isConnected = false
                self.delegate?.webSocketDidDisconnect(error: error)
            }
        }
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        isConnected = true
        delegate?.webSocketDidConnect()
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        isConnected = false
        if let error = error {
            delegate?.webSocketDidDisconnect(error: error)
        }
    }
}
