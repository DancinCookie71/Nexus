"use strict";

let allServices = [];
let currentFilter = "all";
let showSystem = false;

async function initServices() {
    await initLayout("/services");

    document.getElementById("service-search").addEventListener("input", debounce(loadServices, 200));
    document.getElementById("show-system-services").addEventListener("change", (e) => {
        showSystem = e.target.checked;
        loadServices();
    });

    document.querySelectorAll("#service-filters .filter-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll("#service-filters .filter-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentFilter = tab.dataset.filter;
            applyFilters();
        });
    });

    await loadServices();
}

async function loadServices() {
    const loadingEl = document.getElementById("services-loading");
    const tableContainer = document.getElementById("services-table-container");
    const emptyEl = document.getElementById("services-empty");

    loadingEl.style.display = "block";
    tableContainer.style.display = "none";
    emptyEl.style.display = "none";

    const search = document.getElementById("service-search").value.trim();

    try {
        const data = await getServices({ showSystem, search });
        allServices = data.services || [];
        applyFilters();
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        loadingEl.textContent = `Error: ${error.message}`;
    }
}

function applyFilters() {
    const loadingEl = document.getElementById("services-loading");
    const tableContainer = document.getElementById("services-table-container");
    const emptyEl = document.getElementById("services-empty");

    let filtered = allServices;

    if (currentFilter === "applications") {
        filtered = filtered.filter(s => !s.is_system_service);
    } else if (currentFilter === "running") {
        filtered = filtered.filter(s => s.active_state === "active");
    } else if (currentFilter === "failed") {
        filtered = filtered.filter(s => s.active_state === "failed");
    } else if (currentFilter === "inactive") {
        filtered = filtered.filter(s => s.active_state === "inactive");
    }

    loadingEl.style.display = "none";

    if (filtered.length === 0) {
        tableContainer.style.display = "none";
        emptyEl.style.display = "block";
        return;
    }

    renderServices(filtered);
    tableContainer.style.display = "block";
    emptyEl.style.display = "none";
}

function renderServices(services) {
    const tbody = document.getElementById("services-table-body");
    tbody.innerHTML = "";

    for (const service of services) {
        const tr = document.createElement("tr");
        tr.addEventListener("click", () => {
            window.location.href = `/service-detail.html?service=${encodeURIComponent(service.name)}`;
        });

        const statusClass = service.active_state === "failed" ? "failed" :
            service.active_state === "active" ? "running" : "stopped";
        const statusText = service.active_state === "failed" ? "Failed" :
            service.active_state === "active" ? "Running" : "Stopped";

        const enabledBadge = service.unit_file_state && service.unit_file_state !== "disabled" ?
            '<span class="badge badge-enabled">Enabled</span>' :
            '<span class="badge badge-disabled">Disabled</span>';

        tr.innerHTML = `
            <td>
                <strong>${escapeHtml(service.name)}</strong>
                <div class="detail">${escapeHtml(service.description)}</div>
            </td>
            <td>
                <span class="badge badge-${statusClass}">
                    <span class="status-dot ${statusClass}"></span>${escapeHtml(statusText)}
                </span>
                <div class="detail">${escapeHtml(service.sub_state)}</div>
            </td>
            <td>${enabledBadge}</td>
            <td>${service.main_pid || "—"}</td>
            <td>${formatBytes(service.memory_current)}</td>
            <td>${formatCpuTime(service.cpu_usage_nsec)}</td>
        `;
        tbody.appendChild(tr);
    }
}

function formatCpuTime(nsec) {
    if (nsec == null) return "—";
    const ms = nsec / 1_000_000;
    if (ms < 1000) return `${ms.toFixed(0)} ms`;
    return `${(ms / 1000).toFixed(2)} s`;
}

function escapeHtml(text) {
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

initServices();
