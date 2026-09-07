"use strict";

async function initStorage() {
    await initLayout("/storage");
    document.getElementById("refresh-drives").addEventListener("click", loadDrives);
    await loadDrives();
}

async function loadDrives() {
    const loadingEl = document.getElementById("drives-loading");
    const tableContainer = document.getElementById("drives-table-container");
    const emptyEl = document.getElementById("drives-empty");
    const tbody = document.getElementById("drives-table-body");

    loadingEl.style.display = "block";
    tableContainer.style.display = "none";
    emptyEl.style.display = "none";
    tbody.innerHTML = "";

    try {
        const data = await getDrives();
        loadingEl.style.display = "none";

        if (!data.drives || data.drives.length === 0) {
            emptyEl.style.display = "block";
            return;
        }

        for (const drive of data.drives) {
            const tr = document.createElement("tr");
            tr.className = drive.status === "critical" ? "critical" : drive.status === "warning" ? "warning" : "";
            tr.innerHTML = `
                <td>${escapeHtml(drive.device)}</td>
                <td>${escapeHtml(drive.model)}</td>
                <td>${escapeHtml(drive.serial)}</td>
                <td>${escapeHtml(drive.size_human)}</td>
                <td>${drive.temperature_c != null ? drive.temperature_c + " °C" : "—"}</td>
                <td>${drive.power_on_hours != null ? drive.power_on_hours.toLocaleString() + " h" : "—"}</td>
                <td>${escapeHtml(drive.smart_status)}</td>
                <td><span class="badge badge-${drive.status}">${capitalize(drive.status)}</span></td>
                <td>
                    <a href="/drive-detail?device=${encodeURIComponent(drive.device)}" class="btn btn-sm btn-ghost">Examine</a>
                </td>
            `;
            tbody.appendChild(tr);
        }

        tableContainer.style.display = "block";
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        if (error.status === 403) {
            loadingEl.textContent = "Admin mode required. Enable it from the top bar to view drives.";
        } else {
            loadingEl.textContent = `Error: ${error.message}`;
        }
    }
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

initStorage();
