"use strict";

const API_BASE = "/api/v1";

/**
 * Generic API request helper.
 */
async function apiRequest(method, endpoint, body = null) {
    const url = `${API_BASE}${endpoint}`;
    const options = {
        method,
        headers: {
            Accept: "application/json",
        },
        credentials: "include",
    };

    if (body !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        data = await response.json();
    }

    if (!response.ok) {
        const error = new Error(data?.detail || `Request failed: ${response.status}`);
        error.status = response.status;
        error.data = data;
        throw error;
    }

    return data;
}

async function login(username, password) {
    return apiRequest("POST", "/auth/login", { username, password });
}

async function logout() {
    return apiRequest("POST", "/auth/logout");
}

async function getCurrentUser() {
    return apiRequest("GET", "/auth/me");
}

async function getSystemStats() {
    return apiRequest("GET", "/system");
}

async function getServices(params = {}) {
    const qs = new URLSearchParams();
    if (params.showSystem) qs.set("show_system", "true");
    if (params.stateFilter) qs.set("state_filter", params.stateFilter);
    if (params.search) qs.set("search", params.search);
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return apiRequest("GET", `/services${query}`);
}

async function getService(service) {
    return apiRequest("GET", `/services/${encodeURIComponent(service)}`);
}

async function serviceAction(service, action) {
    return apiRequest("POST", `/services/${encodeURIComponent(service)}/${encodeURIComponent(action)}`);
}

async function getLogs(service, params = {}) {
    const qs = new URLSearchParams();
    qs.set("limit", params.limit || 200);
    if (params.since) qs.set("since", params.since);
    if (params.until) qs.set("until", params.until);
    if (params.priority != null) qs.set("priority", params.priority);
    return apiRequest("GET", `/logs/${encodeURIComponent(service)}?${qs.toString()}`);
}

async function getUpdates() {
    return apiRequest("GET", "/updates");
}

async function getProcesses(limit = 200) {
    return apiRequest("GET", `/processes?limit=${limit}`);
}

async function killProcess(pid, sig = "TERM") {
    return apiRequest("POST", `/processes/${encodeURIComponent(pid)}/kill`, { signal: sig });
}

async function extractFile(path) {
    return apiRequest("POST", "/files/extract", { path });
}

async function createArchive(paths, name) {
    return apiRequest("POST", "/files/archive", { paths, name });
}

async function getUnixUsers() {
    return apiRequest("GET", "/users");
}

async function createUnixUser(username, fullName, password, shell = "/bin/bash") {
    return apiRequest("POST", "/users", { username, full_name: fullName, password, shell });
}

async function setUnixPassword(username, password) {
    return apiRequest("POST", `/users/${encodeURIComponent(username)}/password`, { password });
}

async function setUnixUserAdmin(username, admin) {
    return apiRequest("POST", `/users/${encodeURIComponent(username)}/admin`, { admin });
}

async function deleteUnixUser(username) {
    return apiRequest("DELETE", `/users/${encodeURIComponent(username)}`);
}

async function getDrives() {
    return apiRequest("GET", "/storage/drives");
}

async function getDrive(device) {
    return apiRequest("GET", `/storage/drives/${encodeURIComponent(device)}`);
}

async function listFiles(path = "") {
    return apiRequest("GET", `/files?path=${encodeURIComponent(path)}`);
}

async function getFileContent(path) {
    return apiRequest("GET", `/files/content?path=${encodeURIComponent(path)}`);
}

async function saveFileContent(path, content) {
    return apiRequest("POST", "/files/content", { path, content });
}

async function createDirectory(path) {
    return apiRequest("POST", "/files/mkdir", { path });
}

async function renameFile(source, target) {
    return apiRequest("POST", "/files/rename", { source, target });
}

async function copyFile(source, target) {
    return apiRequest("POST", "/files/copy", { source, target });
}

async function deleteFile(path, recursive = false) {
    return apiRequest("DELETE", `/files?path=${encodeURIComponent(path)}&recursive=${recursive}`);
}

async function searchFiles(query, path = "", showHidden = false) {
    const qs = new URLSearchParams();
    qs.set("query", query);
    if (path) qs.set("path", path);
    if (showHidden) qs.set("show_hidden", "true");
    return apiRequest("GET", `/files/search?${qs.toString()}`);
}

async function uploadFile(path, file) {
    const formData = new FormData();
    formData.append("path", path);
    formData.append("file", file);
    const response = await fetch(`${API_BASE}/files/upload`, {
        method: "POST",
        body: formData,
        credentials: "include",
    });
    const data = await response.json();
    if (!response.ok) {
        const error = new Error(data?.detail || `Upload failed: ${response.status}`);
        error.status = response.status;
        throw error;
    }
    return data;
}

async function getFeatures() {
    return apiRequest("GET", "/settings/features");
}

async function getAdminStatus() {
    return apiRequest("GET", "/auth/admin");
}

async function elevateAdmin(username, password) {
    return apiRequest("POST", "/auth/admin", { username, password });
}

async function revokeAdmin() {
    return apiRequest("DELETE", "/auth/admin");
}

async function getSettings() {
    return apiRequest("GET", "/settings");
}

async function updateSetting(key, value) {
    return apiRequest("PUT", `/settings/${encodeURIComponent(key)}`, { value });
}

function formatBytes(bytes) {
    if (bytes == null || isNaN(bytes)) return "--";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    let value = bytes;
    while (value >= 1024 && i < units.length - 1) {
        value /= 1024;
        i++;
    }
    return `${value.toFixed(2)} ${units[i]}`;
}

function formatUptime(seconds) {
    if (seconds == null || isNaN(seconds)) return "--";
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0 || parts.length === 0) parts.push(`${minutes}m`);
    return parts.join(" ");
}

function getWebSocketUrl(path) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}${path}`;
}

function escapeHtml(text) {
    if (text == null) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function debounce(fn, wait) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), wait);
    };
}

function drawSparkline(canvas, data, color, capacity) {
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth || (canvas.parentElement ? canvas.parentElement.clientWidth : 200) || 200;
    const height = 40;
    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
    }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    if (data.length < 2) return;

    const cap = capacity || 90;
    const max = Math.max(...data, 10) * 1.15;
    const step = width / (cap - 1);
    const offset = (cap - data.length) * step;

    ctx.beginPath();
    ctx.moveTo(offset, height - 2 - (data[0] / max) * (height - 6));
    for (let i = 1; i < data.length; i++) {
        ctx.lineTo(offset + i * step, height - 2 - (data[i] / max) * (height - 6));
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.lineTo(offset + (data.length - 1) * step, height);
    ctx.lineTo(offset, height);
    ctx.closePath();
    ctx.fillStyle = `${color}22`;
    ctx.fill();
}
