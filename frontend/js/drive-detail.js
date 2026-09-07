"use strict";

const params = new URLSearchParams(window.location.search);
const device = params.get("device");

async function initDriveDetail() {
    await initLayout("/storage");

    if (!device) {
        window.location.href = "/storage";
        return;
    }

    document.getElementById("drive-device").textContent = device;
    document.getElementById("refresh-drive").addEventListener("click", loadDrive);
    await loadDrive();
}

async function loadDrive() {
    const loadingEl = document.getElementById("drive-loading");
    const contentEl = document.getElementById("drive-content");

    loadingEl.style.display = "block";
    contentEl.style.display = "none";

    try {
        const drive = await getDrive(device);
        renderDrive(drive);
        loadingEl.style.display = "none";
        contentEl.style.display = "block";
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        if (error.status === 403) {
            loadingEl.textContent = "Admin mode required. Enable it from the top bar to examine drives.";
        } else {
            loadingEl.textContent = `Error: ${error.message}`;
        }
    }
}

function renderDrive(drive) {
    document.getElementById("drive-device").textContent = drive.device;
    document.getElementById("drive-model").textContent = drive.model || "Unknown model";

    const badge = document.getElementById("drive-status-badge");
    badge.innerHTML = `<span class="badge badge-${drive.status}">${capitalize(drive.status)}</span>`;

    document.getElementById("drive-info-grid").innerHTML = `
        ${detailItem("Model", drive.model)}
        ${detailItem("Serial", drive.serial)}
        ${detailItem("Firmware", drive.firmware)}
        ${detailItem("Size", drive.size_human)}
        ${detailItem("Type", drive.is_ssd ? "SSD" : drive.rotation_rate === 0 ? "SSD" : "HDD")}
        ${detailItem("SMART Status", drive.smart_status)}
        ${detailItem("Temperature", drive.temperature_c != null ? drive.temperature_c + " °C" : "—")}
        ${detailItem("Power On Hours", drive.power_on_hours != null ? drive.power_on_hours.toLocaleString() + " h" : "—")}
        ${detailItem("SMART Supported", drive.smart_supported ? "Yes" : "No")}
        ${detailItem("SMART Enabled", drive.smart_enabled ? "Yes" : "No")}
    `;

    const tbody = document.getElementById("drive-attributes-body");
    if (drive.attributes && drive.attributes.length) {
        tbody.innerHTML = drive.attributes.map(a => `
            <tr class="${a.when_failed && a.when_failed !== '-' ? 'critical' : ''}">
                <td>${a.id}</td>
                <td>${escapeHtml(a.name)}</td>
                <td>${a.value != null ? a.value : "—"}</td>
                <td>${a.worst != null ? a.worst : "—"}</td>
                <td>${a.threshold != null ? a.threshold : "—"}</td>
                <td>${escapeHtml(a.type)}</td>
                <td>${escapeHtml(a.when_failed && a.when_failed !== '-' ? a.when_failed : "OK")}</td>
                <td class="mono">${escapeHtml(a.raw_value)}</td>
            </tr>
        `).join("");
    } else {
        tbody.innerHTML = `<tr><td colspan="8" class="detail">No SMART attributes available.</td></tr>`;
    }

    const msgEl = document.getElementById("drive-messages");
    if (drive.messages && drive.messages.length) {
        msgEl.innerHTML = `<div class="alert alert-warning">${drive.messages.map(m => `<div>${escapeHtml(m)}</div>`).join("")}</div>`;
    } else {
        msgEl.innerHTML = "";
    }
}

function detailItem(label, value) {
    return `
        <div class="detail-item">
            <dt>${escapeHtml(label)}</dt>
            <dd>${value != null ? escapeHtml(String(value)) : "—"}</dd>
        </div>
    `;
}

function escapeHtml(text) {
    if (text == null) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function capitalize(text) {
    if (!text) return "";
    return text.charAt(0).toUpperCase() + text.slice(1);
}

initDriveDetail();
