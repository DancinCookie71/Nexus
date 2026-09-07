import Foundation

enum NexusError: Error, LocalizedError, Equatable {
    case invalidURL
    case invalidServerURL
    case unauthorized
    case forbidden
    case notFound
    case serverError(Int)
    case decodingError(Error)
    case networkError(Error)
    case apiError(String)
    case unknown

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid URL."
        case .invalidServerURL: return "Server address is missing or invalid. Check Settings."
        case .unauthorized: return "Session expired. Please sign in again."
        case .forbidden: return "Admin privileges required."
        case .notFound: return "Resource not found."
        case .serverError(let code): return "Server error \(code)."
        case .decodingError: return "Unexpected response from server."
        case .networkError: return "Network connection failed."
        case .apiError(let msg): return msg
        case .unknown: return "An unknown error occurred."
        }
    }

    static func == (lhs: NexusError, rhs: NexusError) -> Bool {
        switch (lhs, rhs) {
        case (.invalidURL, .invalidURL), (.invalidServerURL, .invalidServerURL),
             (.unauthorized, .unauthorized), (.forbidden, .forbidden),
             (.notFound, .notFound), (.unknown, .unknown):
            return true
        case (.serverError(let a), .serverError(let b)): return a == b
        case (.apiError(let a), .apiError(let b)): return a == b
        default: return false
        }
    }
}
