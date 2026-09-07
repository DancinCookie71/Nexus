import Foundation

// MARK: - Auth
struct LoginRequest: Codable {
    let username: String
    let password: String
}

struct LoginResponse: Codable {
    let accessToken: String
    let tokenType: String
    let expiresAt: Date?
    let user: NexusUser

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case expiresAt = "expires_at"
        case user
    }
}

struct NexusUser: Codable, Identifiable {
    let id: String
    let username: String
    let createdAt: Date?
    let updatedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id, username
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct AdminStatusResponse: Codable {
    let isAdmin: Bool
    let expiresAt: Date?
    let username: String?
    let sudoUsername: String?

    enum CodingKeys: String, CodingKey {
        case isAdmin = "is_admin"
        case expiresAt = "expires_at"
        case username
        case sudoUsername = "sudo_username"
    }
}

struct AdminElevateRequest: Codable {
    let username: String
    let password: String
}

// MARK: - Common
struct MessageResponse: Codable {
    let message: String
}

// MARK: - System
struct SystemStatsResponse: Codable {
    let hostname: String?
    let os: String?
    let osVersion: String?
    let kernel: String?
    let architecture: String?
    let uptimeSeconds: Double?
    let cpuCount: Int?
    let memoryTotalBytes: Int64?
    let diskTotalBytes: Int64?
    let diskUsedBytes: Int64?
    let cpu: SystemCpuInfo?
    let temperatureCelsius: Double?

    enum CodingKeys: String, CodingKey {
        case hostname, os, kernel, architecture, cpu
        case osVersion = "os_version"
        case uptimeSeconds = "uptime_seconds"
        case cpuCount = "cpu_count"
        case memoryTotalBytes = "memory_total_bytes"
        case diskTotalBytes = "disk_total_bytes"
        case diskUsedBytes = "disk_used_bytes"
        case temperatureCelsius = "temperature_celsius"
    }
}

struct SystemCpuInfo: Codable {
    let usagePercent: Double?
    let cores: Int?
    let frequencyMhz: Double?

    enum CodingKeys: String, CodingKey {
        case usagePercent = "usage_percent"
        case cores
        case frequencyMhz = "frequency_mhz"
    }
}

// MARK: - Health
struct HealthSnapshot: Codable {
    let timestamp: TimeInterval
    let overall: String
    let cpu: CpuSnapshot
    let memory: MemorySnapshot
    let disks: [DiskSnapshot]
    let drives: [DriveHealthSummary]?
    let network: NetworkSnapshot
    let gpus: [GpuSnapshot]?
    let uptimeSeconds: Double
    let failedServices: [String]
    let filesystemErrors: [String]
    let updateCount: Int
    let sensors: [SensorReading]?

    enum CodingKeys: String, CodingKey {
        case timestamp, overall, cpu, memory, disks, drives, network, gpus
        case uptimeSeconds = "uptime_seconds"
        case failedServices = "failed_services"
        case filesystemErrors = "filesystem_errors"
        case updateCount = "update_count"
        case sensors
    }
}

struct CpuSnapshot: Codable {
    let percent: Double
    let perCpu: [Double]?
    let load1: Double
    let load5: Double
    let load15: Double
    let frequencyMhz: Double?
    let temperatureC: Double?

    enum CodingKeys: String, CodingKey {
        case percent
        case perCpu = "per_cpu"
        case load1 = "load_1"
        case load5 = "load_5"
        case load15 = "load_15"
        case frequencyMhz = "frequency_mhz"
        case temperatureC = "temperature_c"
    }
}

struct MemorySnapshot: Codable {
    let totalBytes: Int64
    let usedBytes: Int64
    let availableBytes: Int64
    let percent: Double
    let swapTotalBytes: Int64
    let swapUsedBytes: Int64
    let swapPercent: Double

    enum CodingKeys: String, CodingKey {
        case percent
        case totalBytes = "total_bytes"
        case usedBytes = "used_bytes"
        case availableBytes = "available_bytes"
        case swapTotalBytes = "swap_total_bytes"
        case swapUsedBytes = "swap_used_bytes"
        case swapPercent = "swap_percent"
    }
}

struct DiskSnapshot: Codable {
    let device: String
    let mountpoint: String
    let fstype: String
    let totalBytes: Int64
    let usedBytes: Int64
    let freeBytes: Int64
    let percent: Double
    let smartStatus: String?
    let smartFailing: Bool?
    let temperatureC: Double?

    enum CodingKeys: String, CodingKey {
        case device, mountpoint, fstype, percent
        case totalBytes = "total_bytes"
        case usedBytes = "used_bytes"
        case freeBytes = "free_bytes"
        case smartStatus = "smart_status"
        case smartFailing = "smart_failing"
        case temperatureC = "temperature_c"
    }
}

struct DriveHealthSummary: Codable {
    let device: String
    let status: String
    let smartStatus: String
    let temperatureC: Double?

    enum CodingKeys: String, CodingKey {
        case device, status
        case smartStatus = "smart_status"
        case temperatureC = "temperature_c"
    }
}

struct NetworkSnapshot: Codable {
    let totalBytesSentPerSec: Double
    let totalBytesRecvPerSec: Double
    let latencyMs: Double?
    let interfaces: [NetworkInterfaceSnapshot]

    enum CodingKeys: String, CodingKey {
        case latencyMs = "latency_ms"
        case interfaces
        case totalBytesSentPerSec = "total_bytes_sent_per_sec"
        case totalBytesRecvPerSec = "total_bytes_recv_per_sec"
    }
}

struct NetworkInterfaceSnapshot: Codable {
    let name: String
    let isUp: Bool
    let speedMbps: Double?
    let bytesSentPerSec: Double
    let bytesRecvPerSec: Double

    enum CodingKeys: String, CodingKey {
        case name
        case isUp = "is_up"
        case speedMbps = "speed_mbps"
        case bytesSentPerSec = "bytes_sent_per_sec"
        case bytesRecvPerSec = "bytes_recv_per_sec"
    }
}

struct GpuSnapshot: Codable {
    let name: String
    let utilizationPercent: Double?
    let temperatureC: Double?
    let memoryTotalBytes: Int64?
    let memoryUsedBytes: Int64?

    enum CodingKeys: String, CodingKey {
        case name
        case utilizationPercent = "utilization_percent"
        case temperatureC = "temperature_c"
        case memoryTotalBytes = "memory_total_bytes"
        case memoryUsedBytes = "memory_used_bytes"
    }
}

struct SensorReading: Codable {
    let label: String
    let value: Double?
    let unit: String
}

// MARK: - Services
struct ServiceListResponse: Codable {
    let services: [ServiceSummary]
    let total: Int
}

struct ServiceSummary: Codable, Identifiable {
    var id: String { name }
    let name: String
    let description: String?
    let loadState: String?
    let activeState: String?
    let subState: String?
    let unitFileState: String?
    let mainPid: Int?
    let memoryCurrent: Int64?
    let cpuUsageNsec: Int64?
    let isSystemService: Bool?

    enum CodingKeys: String, CodingKey {
        case name, description
        case loadState = "load_state"
        case activeState = "active_state"
        case subState = "sub_state"
        case unitFileState = "unit_file_state"
        case mainPid = "main_pid"
        case memoryCurrent = "memory_current"
        case cpuUsageNsec = "cpu_usage_nsec"
        case isSystemService = "is_system_service"
    }
}

struct ServiceDetail: Codable {
    let name: String
    let description: String?
    let activeState: String?
    let subState: String?
    let unitFileState: String?
    let mainPid: Int?
    let memoryCurrent: Int64?
    let cpuUsageNsec: Int64?
    let user: String?
    let group: String?
    let restart: String?
    let fragmentPath: String?
    let canStart: Bool?
    let canStop: Bool?
    let canRestart: Bool?
    let canReload: Bool?

    enum CodingKeys: String, CodingKey {
        case name, description
        case activeState = "active_state"
        case subState = "sub_state"
        case unitFileState = "unit_file_state"
        case mainPid = "main_pid"
        case memoryCurrent = "memory_current"
        case cpuUsageNsec = "cpu_usage_nsec"
        case user, group, restart
        case fragmentPath = "fragment_path"
        case canStart = "can_start"
        case canStop = "can_stop"
        case canRestart = "can_restart"
        case canReload = "can_reload"
    }
}

struct ServiceActionResponse: Codable {
    let name: String
    let action: String
    let success: Bool
    let status: String
    let message: String
}

// MARK: - Storage
struct DriveListResponse: Codable {
    let drives: [DriveSummary]
    let total: Int
}

struct DriveSummary: Codable, Identifiable {
    var id: String { device }
    let device: String
    let model: String
    let serial: String
    let sizeHuman: String
    let isSsd: Bool
    let smartSupported: Bool
    let smartEnabled: Bool
    let smartStatus: String
    let temperatureC: Double?
    let powerOnHours: Int?
    let status: String

    enum CodingKeys: String, CodingKey {
        case device, model, serial
        case sizeHuman = "size_human"
        case isSsd = "is_ssd"
        case smartSupported = "smart_supported"
        case smartEnabled = "smart_enabled"
        case smartStatus = "smart_status"
        case temperatureC = "temperature_c"
        case powerOnHours = "power_on_hours"
        case status
    }
}

struct DriveDetail: Codable {
    let device: String
    let model: String
    let serial: String
    let firmware: String
    let sizeHuman: String
    let isSsd: Bool
    let smartSupported: Bool
    let smartEnabled: Bool
    let smartStatus: String
    let temperatureC: Double?
    let powerOnHours: Int?
    let status: String
    let attributes: [SmartAttribute]?
    let messages: [String]?
}

struct SmartAttribute: Codable {
    let id: Int
    let name: String
    let value: Int?
    let worst: Int?
    let threshold: Int?
    let type: String
    let whenFailed: String?
    let rawValue: String

    enum CodingKeys: String, CodingKey {
        case id, name, value, worst, threshold, type
        case whenFailed = "when_failed"
        case rawValue = "raw_value"
    }
}

// MARK: - Files
struct FileListResponse: Codable {
    let path: String
    let entries: [FileEntry]
}

struct FileSearchResponse: Codable {
    let query: String
    let path: String
    let includeHidden: Bool
    let total: Int
    let entries: [FileEntry]

    enum CodingKeys: String, CodingKey {
        case query, path, total, entries
        case includeHidden = "include_hidden"
    }
}

struct FileEntry: Codable, Identifiable {
    var id: String { path }
    let name: String
    let path: String
    let type: String
    let size: Int64
    let modifiedAt: String
    let mode: String?
    let owner: String?
    let group: String?
    let isSymlink: Bool?
    let target: String?

    enum CodingKeys: String, CodingKey {
        case name, path, type, size, mode, owner, group, target
        case modifiedAt = "modified_at"
        case isSymlink = "is_symlink"
    }

    var isDirectory: Bool { type == "directory" }
    var isFile: Bool { type == "file" }
    var isSymlinkValue: Bool { isSymlink ?? false }
}

struct FileContentResponse: Codable {
    let path: String
    let content: String
    let size: Int64
    let mimeType: String

    enum CodingKeys: String, CodingKey {
        case path, content, size
        case mimeType = "mime_type"
    }
}

struct FileWriteRequest: Codable {
    let path: String
    let content: String
}

struct FileRenameRequest: Codable {
    let source: String
    let target: String
}

struct FileCopyRequest: Codable {
    let source: String
    let target: String
}

struct FileMkdirRequest: Codable {
    let path: String
}

struct FileOperationResponse: Codable {
    let success: Bool
    let message: String
}

// MARK: - Logs
struct LogEntry: Codable, Identifiable {
    var id: String { "\(timestamp ?? "")-\(message)" }
    let timestamp: String?
    let priority: Int
    let priorityName: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case timestamp, priority, message
        case priorityName = "priority_name"
    }
}

struct LogsResponse: Codable {
    let unit: String
    let entries: [LogEntry]
}

// MARK: - Settings
struct SettingsResponse: Codable {
    let categories: [String: [String: String]]
}

struct SettingValue: Codable {
    let key: String
    let value: String
    let category: String
    let updatedAt: Date?

    enum CodingKeys: String, CodingKey {
        case key, value, category
        case updatedAt = "updated_at"
    }
}

struct SettingUpdateRequest: Codable {
    let value: String
}

// MARK: - Updates
struct UpdatesRequest: Codable {
    let reboot: Bool
}

// MARK: - Features
struct FeaturesResponse: Codable {
    let terminal: Bool
    let serviceManagement: Bool
    let processes: Bool
    let users: Bool
    let logs: Bool

    enum CodingKeys: String, CodingKey {
        case terminal, processes, users, logs
        case serviceManagement = "service_management"
    }
}

// MARK: - Updates
struct UpdateInfoResponse: Codable {
    let supported: Bool
    let packageManager: String?
    let updateCount: Int
    let packages: [String]
    let error: String?
    let lastChecked: String?
    let rebootRequired: Bool

    enum CodingKeys: String, CodingKey {
        case supported, packages, error
        case packageManager = "package_manager"
        case updateCount = "update_count"
        case lastChecked = "last_checked"
        case rebootRequired = "reboot_required"
    }
}

struct UpdateOperationResponse: Codable {
    let success: Bool
    let message: String
    let rebootScheduled: Bool

    enum CodingKeys: String, CodingKey {
        case success, message
        case rebootScheduled = "reboot_scheduled"
    }
}

// MARK: - Processes
struct ProcessInfo: Codable, Identifiable {
    var id: Int { pid }
    let pid: Int
    let name: String
    let username: String
    let cpuPercent: Double
    let memoryPercent: Double
    let memoryBytes: Int64
    let status: String
    let command: String

    enum CodingKeys: String, CodingKey {
        case pid, name, username, status, command
        case cpuPercent = "cpu_percent"
        case memoryPercent = "memory_percent"
        case memoryBytes = "memory_bytes"
    }
}

struct ProcessListResponse: Codable {
    let processes: [ProcessInfo]
    let total: Int
    let running: Int
    let sleeping: Int
    let cpuPercent: Double
    let memoryPercent: Double
    let loadAverage: [Double]

    enum CodingKeys: String, CodingKey {
        case processes, total, running, sleeping
        case cpuPercent = "cpu_percent"
        case memoryPercent = "memory_percent"
        case loadAverage = "load_average"
    }
}

struct ProcessKillRequest: Codable {
    let signal: String
}

// MARK: - UNIX Users
struct UnixUserInfo: Codable, Identifiable {
    var id: String { username }
    let username: String
    let fullName: String
    let home: String
    let shell: String
    let uid: Int
    let isAdmin: Bool

    enum CodingKeys: String, CodingKey {
        case username, home, shell, uid
        case fullName = "full_name"
        case isAdmin = "is_admin"
    }
}

struct UnixUserCreateRequest: Codable {
    let username: String
    let fullName: String
    let password: String
    let shell: String

    enum CodingKeys: String, CodingKey {
        case username, password, shell
        case fullName = "full_name"
    }
}

struct UnixUserPasswordRequest: Codable {
    let password: String
}

struct UnixUserAdminRequest: Codable {
    let admin: Bool
}

// MARK: - File Archives
struct FileExtractRequest: Codable {
    let path: String
}

struct FileArchiveRequest: Codable {
    let paths: [String]
    let name: String
}
