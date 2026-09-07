import Foundation

final class NexusAPI {
    static let shared = NexusAPI()
    private let session: URLSession
    private let decoder: JSONDecoder

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 300
        config.waitsForConnectivity = true
        self.session = URLSession(configuration: config)

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = formatter.date(from: dateString) {
                return date
            }
            formatter.formatOptions = [.withInternetDateTime]
            if let date = formatter.date(from: dateString) {
                return date
            }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Invalid date: \(dateString)")
        }
    }

    // MARK: - Base URL

    private func baseURL() throws -> URL {
        let raw = NexusAuthStore.shared.serverURL.trimmingCharacters(in: .whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard !raw.isEmpty, let url = URL(string: raw) else {
            throw NexusError.invalidServerURL
        }
        return url
    }

    private func url(for path: String, query: [String: String]? = nil) throws -> URL {
        var components = URLComponents(url: try baseURL().appendingPathComponent(path), resolvingAgainstBaseURL: false)
        if let query = query, !query.isEmpty {
            components?.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components?.url else { throw NexusError.invalidURL }
        return url
    }

    private func request(
        method: String,
        path: String,
        query: [String: String]? = nil,
        body: Encodable? = nil
    ) throws -> URLRequest {
        var request = URLRequest(url: try url(for: path, query: query))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token = NexusAuthStore.shared.token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body = body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(body)
        }
        return request
    }

    // MARK: - Request Execution

    func fetch<T: Decodable>(_ type: T.Type, request: URLRequest) async throws -> T {
        do {
            let (data, response) = try await session.data(for: request)
            return try handleResponse(data: data, response: response)
        } catch let error as NexusError {
            throw error
        } catch {
            throw NexusError.networkError(error)
        }
    }

    func fetchData(request: URLRequest) async throws -> Data {
        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw NexusError.unknown
            }
            switch httpResponse.statusCode {
            case 200...299: return data
            case 401: throw NexusError.unauthorized
            case 403: throw NexusError.forbidden
            case 404: throw NexusError.notFound
            case 500...599: throw NexusError.serverError(httpResponse.statusCode)
            default:
                let message = (try? decoder.decode(MessageResponse.self, from: data))?.message
                throw NexusError.apiError(message ?? "HTTP \(httpResponse.statusCode)")
            }
        } catch let error as NexusError {
            throw error
        } catch {
            throw NexusError.networkError(error)
        }
    }

    private func handleResponse<T: Decodable>(data: Data, response: URLResponse) throws -> T {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw NexusError.unknown
        }
        switch httpResponse.statusCode {
        case 200...299:
            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw NexusError.decodingError(error)
            }
        case 401: throw NexusError.unauthorized
        case 403: throw NexusError.forbidden
        case 404: throw NexusError.notFound
        case 500...599: throw NexusError.serverError(httpResponse.statusCode)
        default:
            let message = (try? decoder.decode(MessageResponse.self, from: data))?.message
            throw NexusError.apiError(message ?? "HTTP \(httpResponse.statusCode)")
        }
    }

    func upload(request: URLRequest) async throws -> FileOperationResponse {
        try await fetch(FileOperationResponse.self, request: request)
    }

    // MARK: - Auth

    func login(username: String, password: String) async throws -> LoginResponse {
        let request = try self.request(method: "POST", path: "api/v1/auth/login", body: LoginRequest(username: username, password: password))
        return try await fetch(LoginResponse.self, request: request)
    }

    func logout() async throws {
        let request = try self.request(method: "POST", path: "api/v1/auth/logout")
        _ = try? await fetchData(request: request)
    }

    func me() async throws -> NexusUser {
        let request = try self.request(method: "GET", path: "api/v1/auth/me")
        return try await fetch(NexusUser.self, request: request)
    }

    func adminStatus() async throws -> AdminStatusResponse {
        let request = try self.request(method: "GET", path: "api/v1/auth/admin")
        return try await fetch(AdminStatusResponse.self, request: request)
    }

    func elevateAdmin(username: String, password: String) async throws -> AdminStatusResponse {
        let request = try self.request(method: "POST", path: "api/v1/auth/admin", body: AdminElevateRequest(username: username, password: password))
        return try await fetch(AdminStatusResponse.self, request: request)
    }

    func revokeAdmin() async throws {
        let request = try self.request(method: "DELETE", path: "api/v1/auth/admin")
        _ = try? await fetchData(request: request)
    }

    // MARK: - System

    func systemStats() async throws -> SystemStatsResponse {
        let request = try self.request(method: "GET", path: "api/v1/system")
        return try await fetch(SystemStatsResponse.self, request: request)
    }

    // MARK: - Health

    func healthSnapshot() async throws -> HealthSnapshot {
        let request = try self.request(method: "GET", path: "api/v1/health/live")
        return try await fetch(HealthSnapshot.self, request: request)
    }

    // MARK: - Services

    func listServices(showSystem: Bool = false, stateFilter: String? = nil, search: String? = nil) async throws -> ServiceListResponse {
        var query: [String: String] = [:]
        if showSystem { query["show_system"] = "true" }
        if let stateFilter = stateFilter { query["state_filter"] = stateFilter }
        if let search = search, !search.isEmpty { query["search"] = search }
        let request = try self.request(method: "GET", path: "api/v1/services", query: query)
        return try await fetch(ServiceListResponse.self, request: request)
    }

    func serviceDetail(_ service: String) async throws -> ServiceDetail {
        let request = try self.request(method: "GET", path: "api/v1/services/\(service.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? service)")
        return try await fetch(ServiceDetail.self, request: request)
    }

    func serviceAction(_ service: String, action: String) async throws -> ServiceActionResponse {
        let encodedService = service.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? service
        let encodedAction = action.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? action
        let request = try self.request(method: "POST", path: "api/v1/services/\(encodedService)/\(encodedAction)")
        return try await fetch(ServiceActionResponse.self, request: request)
    }

    // MARK: - Storage

    func listDrives() async throws -> DriveListResponse {
        let request = try self.request(method: "GET", path: "api/v1/storage/drives")
        return try await fetch(DriveListResponse.self, request: request)
    }

    // MARK: - Files

    func listFiles(path: String = "") async throws -> FileListResponse {
        let request = try self.request(method: "GET", path: "api/v1/files", query: path.isEmpty ? nil : ["path": path])
        return try await fetch(FileListResponse.self, request: request)
    }

    func readFile(path: String) async throws -> FileContentResponse {
        let request = try self.request(method: "GET", path: "api/v1/files/content", query: ["path": path])
        return try await fetch(FileContentResponse.self, request: request)
    }

    func writeFile(path: String, content: String) async throws -> FileOperationResponse {
        let request = try self.request(method: "POST", path: "api/v1/files/content", body: FileWriteRequest(path: path, content: content))
        return try await fetch(FileOperationResponse.self, request: request)
    }

    func createDirectory(path: String) async throws -> FileOperationResponse {
        let request = try self.request(method: "POST", path: "api/v1/files/mkdir", body: FileMkdirRequest(path: path))
        return try await fetch(FileOperationResponse.self, request: request)
    }

    func renameFile(source: String, target: String) async throws -> FileOperationResponse {
        let request = try self.request(method: "POST", path: "api/v1/files/rename", body: FileRenameRequest(source: source, target: target))
        return try await fetch(FileOperationResponse.self, request: request)
    }

    func copyFile(source: String, target: String) async throws -> FileOperationResponse {
        let request = try self.request(method: "POST", path: "api/v1/files/copy", body: FileCopyRequest(source: source, target: target))
        return try await fetch(FileOperationResponse.self, request: request)
    }

    func deleteFile(path: String, recursive: Bool = false) async throws -> FileOperationResponse {
        let request = try self.request(method: "DELETE", path: "api/v1/files", query: ["path": path, "recursive": recursive ? "true" : "false"])
        return try await fetch(FileOperationResponse.self, request: request)
    }

    func searchFiles(query: String, path: String = "", showHidden: Bool = false) async throws -> FileSearchResponse {
        var queryItems: [String: String] = ["query": query]
        if !path.isEmpty { queryItems["path"] = path }
        if showHidden { queryItems["show_hidden"] = "true" }
        let request = try self.request(method: "GET", path: "api/v1/files/search", query: queryItems)
        return try await fetch(FileSearchResponse.self, request: request)
    }

    func downloadRequest(path: String) throws -> URLRequest {
        try self.request(method: "GET", path: "api/v1/files/download", query: ["path": path])
    }

    func uploadFile(path: String, data: Data) async throws -> FileOperationResponse {
        let url = try self.url(for: "api/v1/files/upload")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        if let token = NexusAuthStore.shared.token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"path\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(path)\r\n".data(using: .utf8)!)
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        let filename = URL(fileURLWithPath: path).lastPathComponent
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: application/octet-stream\r\n\r\n".data(using: .utf8)!)
        body.append(data)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body
        return try await upload(request: request)
    }

    // MARK: - Logs

    func logs(for service: String, limit: Int = 200) async throws -> LogsResponse {
        let encoded = service.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? service
        let request = try self.request(method: "GET", path: "api/v1/logs/\(encoded)", query: ["limit": String(limit)])
        return try await fetch(LogsResponse.self, request: request)
    }

    // MARK: - Updates

    func updateInfo() async throws -> UpdateInfoResponse {
        let request = try self.request(method: "GET", path: "api/v1/updates")
        return try await fetch(UpdateInfoResponse.self, request: request)
    }

    func runUpdates(reboot: Bool) async throws -> UpdateOperationResponse {
        let request = try self.request(method: "POST", path: "api/v1/updates", body: UpdatesRequest(reboot: reboot))
        return try await fetch(UpdateOperationResponse.self, request: request)
    }

    func reboot() async throws -> UpdateOperationResponse {
        let request = try self.request(method: "POST", path: "api/v1/updates/reboot")
        return try await fetch(UpdateOperationResponse.self, request: request)
    }

    // MARK: - Processes

    func processes(limit: Int = 500) async throws -> ProcessListResponse {
        let request = try self.request(method: "GET", path: "api/v1/processes", query: ["limit": String(limit)])
        return try await fetch(ProcessListResponse.self, request: request)
    }

    func killProcess(pid: Int, signalName: String = "TERM") async throws {
        let request = try self.request(
            method: "POST",
            path: "api/v1/processes/\(pid)/kill",
            body: ProcessKillRequest(signal: signalName)
        )
        _ = try await fetchData(request: request)
    }

    // MARK: - UNIX Users

    func unixUsers() async throws -> [UnixUserInfo] {
        let request = try self.request(method: "GET", path: "api/v1/users")
        return try await fetch([UnixUserInfo].self, request: request)
    }

    func createUnixUser(username: String, fullName: String, password: String, shell: String) async throws {
        let request = try self.request(
            method: "POST",
            path: "api/v1/users",
            body: UnixUserCreateRequest(username: username, fullName: fullName, password: password, shell: shell)
        )
        _ = try await fetchData(request: request)
    }

    func setUnixPassword(username: String, password: String) async throws {
        let encoded = username.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? username
        let request = try self.request(
            method: "POST",
            path: "api/v1/users/\(encoded)/password",
            body: UnixUserPasswordRequest(password: password)
        )
        _ = try await fetchData(request: request)
    }

    func setUnixUserAdmin(username: String, admin: Bool) async throws {
        let encoded = username.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? username
        let request = try self.request(
            method: "POST",
            path: "api/v1/users/\(encoded)/admin",
            body: UnixUserAdminRequest(admin: admin)
        )
        _ = try await fetchData(request: request)
    }

    func deleteUnixUser(username: String) async throws {
        let encoded = username.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? username
        let request = try self.request(method: "DELETE", path: "api/v1/users/\(encoded)")
        _ = try await fetchData(request: request)
    }

    // MARK: - File Archives

    func extractArchive(path: String) async throws -> FileOperationResponse {
        let request = try self.request(method: "POST", path: "api/v1/files/extract", body: FileExtractRequest(path: path))
        return try await fetch(FileOperationResponse.self, request: request)
    }

    func createArchive(paths: [String], name: String) async throws -> FileOperationResponse {
        let request = try self.request(method: "POST", path: "api/v1/files/archive", body: FileArchiveRequest(paths: paths, name: name))
        return try await fetch(FileOperationResponse.self, request: request)
    }

    // MARK: - Features

    func features() async throws -> FeaturesResponse {
        let request = try self.request(method: "GET", path: "api/v1/settings/features")
        return try await fetch(FeaturesResponse.self, request: request)
    }

    // MARK: - Settings

    func settings() async throws -> SettingsResponse {
        let request = try self.request(method: "GET", path: "api/v1/settings")
        return try await fetch(SettingsResponse.self, request: request)
    }

    func updateSetting(key: String, value: String) async throws -> SettingValue {
        let encoded = key.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? key
        let request = try self.request(method: "PUT", path: "api/v1/settings/\(encoded)", body: SettingUpdateRequest(value: value))
        return try await fetch(SettingValue.self, request: request)
    }
}
