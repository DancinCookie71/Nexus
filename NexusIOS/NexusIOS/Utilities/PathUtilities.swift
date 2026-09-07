import Foundation

enum PathUtilities {
    static func join(_ base: String, _ name: String) -> String {
        let trimmedBase = base.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let trimmedName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmedBase.isEmpty { return "/" + trimmedName }
        return "/" + trimmedBase + "/" + trimmedName
    }

    static func sanitizeName(_ name: String) -> String {
        name.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "//", with: "/")
    }

    static func validateName(_ name: String) -> String? {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "Name cannot be empty." }
        guard !trimmed.contains("/") else { return "Name cannot contain slashes." }
        guard trimmed != ".", trimmed != ".." else { return "Invalid name." }
        guard !trimmed.hasPrefix("../"), !trimmed.contains("/../") else { return "Path traversal is not allowed." }
        return nil
    }

    static func normalizedFileName(_ name: String, templateExtension: String?) -> String {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let ext = templateExtension, !ext.isEmpty else { return trimmed }
        if trimmed.lowercased().hasSuffix(ext.lowercased()) { return trimmed }
        return trimmed + ext
    }

    static func isTextMIMEType(_ mime: String) -> Bool {
        let lower = mime.lowercased()
        if lower.hasPrefix("text/") { return true }
        let textTypes: [String] = [
            "application/json", "application/javascript", "application/xml",
            "application/x-sh", "application/x-httpd-php", "application/x-python-code",
            "application/x-yaml", "application/toml", "application/x-www-form-urlencoded"
        ]
        if textTypes.contains(lower) { return true }
        if lower.hasSuffix("+json") || lower.hasSuffix("+xml") || lower.hasSuffix("+yaml") { return true }
        return false
    }
}
