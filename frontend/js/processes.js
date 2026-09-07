"use strict";

const PROC_REFRESH_MS = 3000;
const PROC_HISTORY_MAX = 90;

let procData = [];
let procSort = { key: "cpu_percent", dir: -1 };
let procFilter = "";
let procTimer = null;
const procHistory = { cpu: [], memory: [] };

async function initProcesses() {
    await initLayout("/processes");

    document.querySelectorAll("th.sortable").forEach(th => {
        th.addEventListener("click", () => {
            const key = th.dataset.sort;
            if (procSort.key === key) {
                procSort.dir = -procSort.dir;
            } else {
                procSort = { key, dir: key === "name" || key === "username" || key === "status" ? 1 : -1 };
            }
            document.querySelectorAll("th.sortable").forEach(h => h.classList.remove("sorted-asc", "sorted-desc"));
            th.classList.add(procSort.dir === 1 ? "sorted-asc" : "sorted-desc");
            renderProcTable();
        });
    });

    document.getElementById("proc-search").addEventListener("input", debounce(e => {
        procFilter = e.target.value.trim().toLowerCase();
        renderProcTable();
    }, 200));

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            clearInterval(procTimer);
            procTimer = null;
        } else if (!procTimer) {
            loadProcesses();
            procTimer = setInterval(loadProcesses, PROC_REFRESH_MS);
        }
    });

    await loadProcesses();
    procTimer = setInterval(loadProcesses, PROC_REFRESH_MS);
}

async function loadProcesses() {
    try {
        const data = await getProcesses();
        procData = data.processes;
        updateProcTotals(data);
        pushProcHistory(data);
        renderProcTable();
        document.getElementById("proc-updated").textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        document.getElementById("proc-updated").textContent = "Connection lost, retrying…";
    }
}

function updateProcTotals(data) {
    document.getElementById("proc-total").textContent = String(data.total);
    document.getElementById("proc-states").textContent = `${data.running} running / ${data.sleeping} sleeping`;
    document.getElementById("proc-cpu").textContent = `${(data.cpu_percent ?? 0).toFixed(1)}%`;
    document.getElementById("proc-mem").textContent = `${(data.memory_percent ?? 0).toFixed(1)}%`;
    document.getElementById("proc-load").textContent = (data.load_average || []).join(" ");
}

function pushProcHistory(data) {
    pushHistory(procHistory.cpu, data.cpu_percent ?? 0);
    pushHistory(procHistory.memory, data.memory_percent ?? 0);
    drawSparkline(document.getElementById("cpu-sparkline"), procHistory.cpu, "#6366f1", PROC_HISTORY_MAX);
    drawSparkline(document.getElementById("mem-sparkline"), procHistory.memory, "#06b6d4", PROC_HISTORY_MAX);
}

function pushHistory(arr, value) {
    arr.push(value);
    if (arr.length > PROC_HISTORY_MAX) arr.shift();
}

function filteredProcesses() {
    if (!procFilter) return procData;
    return procData.filter(p =>
        p.name.toLowerCase().includes(procFilter) ||
        p.username.toLowerCase().includes(procFilter) ||
        p.command.toLowerCase().includes(procFilter) ||
        String(p.pid).includes(procFilter)
    );
}

function renderProcTable() {
    const tbody = document.getElementById("proc-table-body");
    const emptyEl = document.getElementById("proc-empty");
    tbody.innerHTML = "";

    const rows = filteredProcesses().slice().sort((a, b) => {
        const av = a[procSort.key];
        const bv = b[procSort.key];
        if (typeof av === "string") return procSort.dir * av.localeCompare(bv);
        return procSort.dir * (av - bv);
    });

    if (rows.length === 0) {
        emptyEl.style.display = "block";
        return;
    }
    emptyEl.style.display = "none";

    for (const proc of rows) {
        const tr = document.createElement("tr");
        tr.className = "file-row";
        tr.innerHTML = `
            <td class="file-name"><span class="file-icon">⚙</span><span>${escapeHtml(proc.name)}</span></td>
            <td class="col-size">${proc.pid}</td>
            <td class="col-owner">${escapeHtml(proc.username)}</td>
            <td class="col-size">${proc.cpu_percent.toFixed(1)}</td>
            <td class="col-size">${formatBytes(proc.memory_bytes)} (${proc.memory_percent.toFixed(1)}%)</td>
            <td class="col-size">${escapeHtml(proc.status)}</td>
            <td class="col-command"><code>${escapeHtml(proc.command)}</code></td>
            <td class="col-action"><button class="btn btn-danger btn-xs" data-pid="${proc.pid}" title="Stop process">✕</button></td>
        `;
        tr.querySelector(".btn-danger").addEventListener("click", () => killProcessPrompt(proc));
        tbody.appendChild(tr);
    }
}

async function killProcessPrompt(proc) {
    if (!adminState.is_admin) {
        alert("Enable Admin mode (top bar) to stop processes.");
        return;
    }
    const confirmed = confirm(`Send SIGTERM to ${proc.name} (PID ${proc.pid})?`);
    if (!confirmed) return;
    try {
        await killProcess(proc.pid, "TERM");
        await loadProcesses();
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        alert(`Failed to stop process: ${error.message}`);
    }
}

initProcesses();
