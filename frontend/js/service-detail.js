"use strict";

const params = new URLSearchParams(window.location.search);
const serviceName = params.get("service");

async function initServiceDetail() {
    await initLayout("/services");

    if (!serviceName) {
        window.location.href = "/services";
        return;
    }

    document.querySelectorAll("#detail-tabs .tab").forEach(tab => {
        tab.addEventListener("click", () => switchTab(tab.dataset.tab));
    });

    document.getElementById("refresh-logs").addEventListener("click", loadLogs);

    await loadDetail();
    await loadLogs();
}

function switchTab(tabName) {
    document.querySelectorAll("#detail-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tabName));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("active", p.id === `tab-${tabName}`));
}

async function loadDetail() {
    try {
        const detail = await getService(serviceName);
        renderDetail(detail);
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        document.getElementById("detail-name").textContent = "Error";
        document.getElementById("detail-description").textContent = error.message || "Failed to load service";
    }
}

function renderDetail(detail) {
    document.getElementById("detail-name").textContent = detail.name;
    document.getElementById("detail-description").textContent = detail.description || "No description";

    const statusClass = detail.active_state === "failed" ? "failed" :
        detail.active_state === "active" ? "running" : "stopped";
    const statusText = detail.active_state === "failed" ? "Failed" :
        detail.active_state === "active" ? "Running" : "Stopped";
    document.getElementById("detail-status-badge").innerHTML =
        `<span class="badge badge-${statusClass}"><span class="status-dot ${statusClass}"></span>${escapeHtml(statusText)}</span>`;

    const uptime = detail.state_change_timestamp && detail.active_state === "active"
        ? formatUptime(Math.floor((Date.now() - new Date(detail.state_change_timestamp).getTime()) / 1000))
        : "—";

    document.getElementById("overview-grid").innerHTML = `
        ${detailItem("State", detail.active_state)}
        ${detailItem("Sub-state", detail.sub_state)}
        ${detailItem("Enabled", detail.unit_file_state)}
        ${detailItem("Description", detail.description)}
        ${detailItem("Main PID", detail.main_pid || "—")}
        ${detailItem("Memory", formatBytes(detail.memory_current))}
        ${detailItem("CPU time", formatCpuTime(detail.cpu_usage_nsec))}
        ${detailItem("Tasks", detail.tasks_current || "—")}
        ${detailItem("Uptime", uptime)}
    `;

    document.getElementById("configuration-grid").innerHTML = `
        ${detailItem("Unit file", detail.fragment_path || "—")}
        ${detailItem("Source path", detail.source_path || "—")}
        ${detailItem("Drop-in files", formatList(detail.drop_in_paths, "No drop-in files"))}
        ${detailItem("User", detail.user || "—")}
        ${detailItem("Group", detail.group || "—")}
        ${detailItem("Restart policy", detail.restart || "—")}
    `;

    document.getElementById("dependencies-grid").innerHTML = `
        ${detailItem("Requires", formatList(detail.requires))}
        ${detailItem("Wants", formatList(detail.wants))}
        ${detailItem("BindsTo", formatList(detail.binds_to))}
        ${detailItem("PartOf", formatList(detail.part_of))}
        ${detailItem("Conflicts", formatList(detail.conflicts))}
        ${detailItem("Before", formatList(detail.before))}
        ${detailItem("After", formatList(detail.after))}
        ${detailItem("OnFailure", formatList(detail.on_failure))}
    `;

    const actionsEl = document.getElementById("detail-actions");
    actionsEl.innerHTML = "";
    const actions = [];
    if (detail.can_start && !detail.refuses_manual_start) actions.push(["start", "btn-primary"]);
    if (detail.can_stop && !detail.refuses_manual_stop && detail.active_state === "active") actions.push(["stop", "btn-danger"]);
    if (detail.can_restart) actions.push(["restart", "btn-ghost"]);
    if (detail.can_reload) actions.push(["reload", "btn-ghost"]);
    if (detail.unit_file_state === "disabled") actions.push(["enable", "btn-ghost"]);
    else if (detail.unit_file_state && detail.unit_file_state !== "static") actions.push(["disable", "btn-ghost"]);

    for (const [action, btnClass] of actions) {
        const btn = document.createElement("button");
        btn.className = `btn ${btnClass}`;
        btn.textContent = action.charAt(0).toUpperCase() + action.slice(1);
        btn.addEventListener("click", () => runAction(action));
        actionsEl.appendChild(btn);
    }
}

async function runAction(action) {
    const resultEl = document.getElementById("action-result");
    resultEl.textContent = `${action}...`;
    try {
        const result = await serviceAction(serviceName, action);
        resultEl.textContent = `${result.action} ${result.success ? "succeeded" : "failed"}: ${result.message}`;
        resultEl.style.color = result.success ? "var(--success)" : "var(--danger)";
        await loadDetail();
        await loadLogs();
    } catch (error) {
        if (error.status === 403) {
            resultEl.textContent = "Admin mode required. Enable it from the top bar.";
        } else {
            resultEl.textContent = `Error: ${error.message}`;
        }
        resultEl.style.color = "var(--danger)";
    }
}

async function loadLogs() {
    const viewer = document.getElementById("log-viewer");
    const empty = document.getElementById("logs-empty");
    try {
        const data = await getLogs(serviceName, { limit: 250 });
        if (data.entries.length === 0) {
            viewer.style.display = "none";
            empty.style.display = "block";
            return;
        }
        viewer.style.display = "block";
        empty.style.display = "none";
        viewer.innerHTML = data.entries.map(entry => `
            <div class="log-entry priority-${entry.priority}">
                <span class="log-time">${escapeHtml(entry.timestamp ? entry.timestamp.replace("T", " ").split(".")[0] : "—")}</span>
                <span class="log-priority">${escapeHtml(entry.priority_name)}</span>
                <span>${escapeHtml(entry.message)}</span>
            </div>
        `).join("");
        viewer.scrollTop = viewer.scrollHeight;
    } catch (error) {
        viewer.textContent = `Error loading logs: ${error.message}`;
    }
}

function detailItem(label, value) {
    return `
        <div class="detail-item">
            <dt>${escapeHtml(label)}</dt>
            <dd>${value}</dd>
        </div>
    `;
}

function formatList(items, emptyText = "—") {
    if (!items || items.length === 0) return emptyText;
    return `<ul class="code-list">${items.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`;
}

function formatCpuTime(nsec) {
    if (nsec == null) return "—";
    const ms = nsec / 1_000_000;
    if (ms < 1000) return `${ms.toFixed(0)} ms`;
    return `${(ms / 1000).toFixed(2)} s`;
}

function formatBytes(bytes) {
    if (bytes == null || bytes === 0) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatUptime(seconds) {
    if (seconds == null || seconds < 0) return "—";
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const parts = [];
    if (days) parts.push(`${days}d`);
    if (hours) parts.push(`${hours}h`);
    if (minutes) parts.push(`${minutes}m`);
    if (!parts.length) parts.push(`${seconds}s`);
    return parts.join(" ");
}

function escapeHtml(text) {
    if (text == null) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

initServiceDetail();
