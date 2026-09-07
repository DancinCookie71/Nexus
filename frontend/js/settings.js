"use strict";

const CATEGORY_LABELS = {
    nexus: "Nexus",
    server: "Server",
    security: "Security",
    ui: "User Interface",
    logging: "Logging",
    notifications: "Notifications",
};

const CATEGORY_ORDER = ["nexus", "server", "security", "ui", "logging", "notifications"];

const SETTING_LABELS = {
    app_name: "Application name",
    session_lifetime_minutes: "Session lifetime (minutes)",
    admin_session_lifetime_minutes: "Admin mode timeout (minutes, 0 = never)",
    terminal_enabled: "Interactive terminal enabled",
    terminal_max_sessions_per_user: "Max terminal sessions per user",
    terminal_shell: "Terminal shell path",
    files_root: "File manager root directory",
    service_allowlist: "Service allowlist",
    host: "Bind host",
    port: "Bind port",
    require_admin_for_terminal: "Require admin mode for terminal",
    require_admin_for_files_writes: "Require admin mode for file writes",
    max_login_attempts: "Max failed login attempts",
    login_lockout_minutes: "Login lockout duration (minutes)",
    theme: "Theme",
    page_title: "Page title",
    refresh_interval_seconds: "Live refresh interval (seconds)",
    log_level: "Log level",
    audit_log_retention_days: "Audit log retention (days)",
    email_alerts_enabled: "Email alerts enabled",
    alert_email: "Alert email address",
};

const SETTING_TYPES = {
    terminal_enabled: "checkbox",
    require_admin_for_terminal: "checkbox",
    require_admin_for_files_writes: "checkbox",
    email_alerts_enabled: "checkbox",
    session_lifetime_minutes: "number",
    admin_session_lifetime_minutes: "number",
    terminal_max_sessions_per_user: "number",
    port: "number",
    max_login_attempts: "number",
    login_lockout_minutes: "number",
    refresh_interval_seconds: "number",
    audit_log_retention_days: "number",
};

let settingsData = { categories: {} };
let canEdit = false;

function _renderNotice(message, type = "info") {
    const el = document.getElementById("settings-notice");
    if (!el) return;
    el.textContent = message;
    el.className = `notice notice-${type}`;
    el.style.display = "block";
    setTimeout(() => { el.style.display = "none"; }, 5000);
}

function _inputType(key) {
    return SETTING_TYPES[key] || "text";
}

function _renderSetting(key, value) {
    const type = _inputType(key);
    const label = SETTING_LABELS[key] || key.replace(/_/g, " ");
    const disabledAttr = canEdit ? "" : "disabled";
    if (type === "checkbox") {
        const checked = value === "true" || value === "1" || value === "yes" ? "checked" : "";
        return `
            <div class="setting-row">
                <label class="setting-toggle">
                    <input type="checkbox" data-key="${key}" data-type="checkbox" ${checked} ${disabledAttr}>
                    <span>${label}</span>
                </label>
            </div>
        `;
    }
    return `
        <div class="setting-row">
            <label for="setting-${key}">${label}</label>
            <input type="${type}" id="setting-${key}" data-key="${key}" value="${escapeHtml(value)}" ${disabledAttr}>
        </div>
    `;
}

function _renderCategory(category, items) {
    const title = CATEGORY_LABELS[category] || category;
    const rows = Object.entries(items)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([key, value]) => _renderSetting(key, value))
        .join("");
    return `
        <article class="card settings-card">
            <h2>${escapeHtml(title)}</h2>
            <div class="settings-form">
                ${rows}
            </div>
        </article>
    `;
}

function renderSettings() {
    const container = document.getElementById("settings-container");
    if (!container) return;
    const categories = settingsData.categories || {};
    const ordered = CATEGORY_ORDER.filter(c => categories[c] && Object.keys(categories[c]).length > 0);
    // Also include any unexpected categories.
    for (const c of Object.keys(categories)) {
        if (!ordered.includes(c)) ordered.push(c);
    }
    container.innerHTML = ordered.map(c => _renderCategory(c, categories[c])).join("");

    if (!canEdit) {
        const hint = document.createElement("p");
        hint.className = "text-muted";
        hint.textContent = "Enable Admin mode to edit settings.";
        container.appendChild(hint);
    }

    container.querySelectorAll("input[data-key]").forEach(input => {
        input.addEventListener("change", handleSettingChange);
    });
}

async function handleSettingChange(event) {
    if (!canEdit) {
        _renderNotice("Admin mode is required to edit settings.", "warning");
        return;
    }
    const input = event.target;
    const key = input.dataset.key;
    const type = input.dataset.type;
    let value;
    if (type === "checkbox") {
        value = input.checked ? "true" : "false";
    } else {
        value = input.value;
    }
    try {
        await updateSetting(key, value);
        _renderNotice(`${SETTING_LABELS[key] || key} updated.`, "success");
    } catch (error) {
        _renderNotice(error.message || "Failed to update setting.", "error");
        // Revert visual state roughly by reloading.
        loadSettings();
    }
}

async function loadSettings() {
    try {
        settingsData = await getSettings();
        renderSettings();
    } catch (error) {
        const container = document.getElementById("settings-container");
        if (container) container.innerHTML = `<p class="text-danger">Failed to load settings: ${escapeHtml(error.message)}</p>`;
    }
}

async function init() {
    await initLayout("/settings");
    adminState = await getAdminStatus().catch(() => ({ is_admin: false }));
    canEdit = adminState.is_admin === true;
    await loadSettings();

    // Re-evaluate editability when admin state changes.
    const checkAdmin = setInterval(async () => {
        adminState = await getAdminStatus().catch(() => ({ is_admin: false }));
        const newCanEdit = adminState.is_admin === true;
        if (newCanEdit !== canEdit) {
            canEdit = newCanEdit;
            renderSettings();
        }
    }, 10000);
}

function escapeHtml(text) {
    if (text == null) return "";
    const div = document.createElement("div");
    div.textContent = String(text);
    return div.innerHTML;
}

init().catch(console.error);
