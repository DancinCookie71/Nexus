"use strict";

const MAX_HISTORY = 60;

let ws = null;
let reconnectTimer = null;
let token = null;

const charts = {};
const history = {
    cpu: [],
    memory: [],
    networkSent: [],
    networkRecv: [],
};

async function initHealth() {
    await initLayout("/health");
    initCharts();
    const authed = await checkAuth();
    if (!authed) {
        window.location.href = "/login";
        return;
    }
    connectWebSocket();
}

async function checkAuth() {
    try {
        const response = await fetch("/api/v1/auth/me", { credentials: "include" });
        return response.ok;
    } catch (error) {
        return false;
    }
}

function connectWebSocket() {
    if (ws) {
        try { ws.close(); } catch (e) {}
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/api/v1/health/live/ws`;
    ws = new WebSocket(url);

    ws.onopen = () => {
        updateConnectionStatus(true);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleSnapshot(data);
        } catch (e) {
            console.error("Failed to parse health snapshot", e);
        }
    };

    ws.onclose = () => {
        updateConnectionStatus(false);
        scheduleReconnect();
    };

    ws.onerror = (error) => {
        console.error("Health WebSocket error", error);
    };
}

function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWebSocket();
    }, 3000);
}

function updateConnectionStatus(connected) {
    // Could show a small indicator; for now keep it minimal.
}

function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { display: false },
            y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" } },
        },
        elements: { point: { radius: 0 } },
    };

    charts.cpu = new Chart(document.getElementById("cpu-chart"), {
        type: "line",
        data: {
            labels: Array(MAX_HISTORY).fill(""),
            datasets: [{
                data: Array(MAX_HISTORY).fill(0),
                borderColor: "var(--primary)",
                backgroundColor: "rgba(59, 130, 246, 0.1)",
                fill: true,
                tension: 0.3,
            }],
        },
        options: { ...commonOptions, scales: { ...commonOptions.scales, y: { min: 0, max: 100, display: false } } },
    });

    charts.memory = new Chart(document.getElementById("memory-chart"), {
        type: "line",
        data: {
            labels: Array(MAX_HISTORY).fill(""),
            datasets: [{
                data: Array(MAX_HISTORY).fill(0),
                borderColor: "#8b5cf6",
                backgroundColor: "rgba(139, 92, 246, 0.1)",
                fill: true,
                tension: 0.3,
            }],
        },
        options: { ...commonOptions, scales: { ...commonOptions.scales, y: { min: 0, max: 100, display: false } } },
    });

    charts.network = new Chart(document.getElementById("network-chart"), {
        type: "line",
        data: {
            labels: Array(MAX_HISTORY).fill(""),
            datasets: [
                {
                    label: "Up",
                    data: Array(MAX_HISTORY).fill(0),
                    borderColor: "#10b981",
                    backgroundColor: "rgba(16, 185, 129, 0.1)",
                    fill: true,
                    tension: 0.3,
                },
                {
                    label: "Down",
                    data: Array(MAX_HISTORY).fill(0),
                    borderColor: "#3b82f6",
                    backgroundColor: "rgba(59, 130, 246, 0.1)",
                    fill: true,
                    tension: 0.3,
                },
            ],
        },
        options: commonOptions,
    });
}

function pushHistory(arr, value) {
    arr.push(value);
    if (arr.length > MAX_HISTORY) arr.shift();
}

function updateChart(chart, datasets) {
    if (!chart) return;
    datasets.forEach((dataset, index) => {
        if (chart.data.datasets[index]) {
            chart.data.datasets[index].data = dataset;
        }
    });
    chart.update("none");
}

function handleSnapshot(data) {
    updateOverall(data);
    updateCpu(data.cpu);
    updateMemory(data.memory);
    updateDisks(data.disks, data.drives || []);
    updateNetwork(data.network);
    updateSystem(data);
    updateGpu(data.gpus);
    updateSensors(data.sensors);
}

function updateOverall(data) {
    const overallEl = document.getElementById("health-overall");
    const statusText = document.getElementById("overall-status");
    const summaryText = document.getElementById("overall-summary");

    overallEl.classList.remove("healthy", "warning", "critical");
    overallEl.classList.add(data.overall);

    statusText.textContent = data.overall.toUpperCase();

    const warnings = [];
    if (data.cpu.percent >= 80) warnings.push(`CPU ${data.cpu.percent.toFixed(0)}%`);
    if (data.memory.percent >= 80) warnings.push(`Memory ${data.memory.percent.toFixed(0)}%`);
    data.disks.forEach(d => {
        if (d.percent >= 85) warnings.push(`${d.device} ${d.percent.toFixed(0)}% full`);
        if (d.smart_failing) warnings.push(`${d.device} SMART failing`);
    });
    (data.drives || []).forEach(d => {
        if (d.status === "critical") warnings.push(`${d.device} SMART critical`);
        else if (d.status === "warning") warnings.push(`${d.device} SMART warning`);
    });
    if (data.failed_services.length) warnings.push(`${data.failed_services.length} failed services`);
    if (data.filesystem_errors.length) warnings.push(`${data.filesystem_errors.length} filesystem errors`);

    if (warnings.length === 0) {
        summaryText.textContent = "All systems operating normally";
    } else {
        summaryText.textContent = warnings.slice(0, 3).join(" · ");
    }
}

function componentStatus(el, status) {
    el.classList.remove("healthy", "warning", "critical");
    el.classList.add(status);
    el.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

function updateCpu(cpu) {
    const status = cpu.percent >= 95 || (cpu.temperature_c && cpu.temperature_c >= 90) ? "critical" :
        cpu.percent >= 80 || (cpu.temperature_c && cpu.temperature_c >= 75) ? "warning" : "healthy";
    componentStatus(document.getElementById("cpu-status"), status);

    document.getElementById("cpu-percent").textContent = `${cpu.percent.toFixed(1)}%`;
    document.getElementById("cpu-details").innerHTML = `
        <div class="detail-grid compact">
            <div class="detail-item"><dt>Load 1m</dt><dd>${cpu.load_1.toFixed(2)}</dd></div>
            <div class="detail-item"><dt>Load 5m</dt><dd>${cpu.load_5.toFixed(2)}</dd></div>
            <div class="detail-item"><dt>Load 15m</dt><dd>${cpu.load_15.toFixed(2)}</dd></div>
            <div class="detail-item"><dt>Frequency</dt><dd>${cpu.frequency_mhz ? cpu.frequency_mhz.toFixed(0) + " MHz" : "—"}</dd></div>
            <div class="detail-item"><dt>Temperature</dt><dd>${cpu.temperature_c ? cpu.temperature_c.toFixed(1) + " °C" : "—"}</dd></div>
            <div class="detail-item"><dt>Cores</dt><dd>${cpu.per_cpu.length}</dd></div>
        </div>
    `;

    pushHistory(history.cpu, cpu.percent);
    updateChart(charts.cpu, [history.cpu]);
}

function updateMemory(memory) {
    const status = memory.percent >= 90 ? "critical" : memory.percent >= 80 ? "warning" : "healthy";
    componentStatus(document.getElementById("memory-status"), status);

    document.getElementById("memory-percent").textContent = `${memory.percent.toFixed(1)}%`;
    document.getElementById("memory-details").innerHTML = `
        <div class="detail-grid compact">
            <div class="detail-item"><dt>Used</dt><dd>${formatBytes(memory.used_bytes)}</dd></div>
            <div class="detail-item"><dt>Total</dt><dd>${formatBytes(memory.total_bytes)}</dd></div>
            <div class="detail-item"><dt>Available</dt><dd>${formatBytes(memory.available_bytes)}</dd></div>
            <div class="detail-item"><dt>Swap used</dt><dd>${formatBytes(memory.swap_used_bytes)} / ${formatBytes(memory.swap_total_bytes)}</dd></div>
        </div>
    `;

    pushHistory(history.memory, memory.percent);
    updateChart(charts.memory, [history.memory]);
}

function updateDisks(disks, drives) {
    let worst = "healthy";
    disks.forEach(d => {
        if (d.smart_failing || d.percent >= 95 || d.errors.length) worst = "critical";
        else if (d.percent >= 85 && worst !== "critical") worst = "warning";
    });
    (drives || []).forEach(d => {
        if (d.status === "critical") worst = "critical";
        else if (d.status === "warning" && worst !== "critical") worst = "warning";
    });
    componentStatus(document.getElementById("disks-status"), worst);

    if (disks.length === 0 && (!drives || drives.length === 0)) {
        document.getElementById("disks-details").innerHTML = "<p class='detail'>No disk data available.</p>";
        return;
    }

    const driveSmartMarkup = drives && drives.length ? `
        <h4 style="margin:1rem 0 0.5rem;">SMART Health</h4>
        <table class="data-table">
            <thead><tr><th>Drive</th><th>Status</th><th>SMART</th><th>Temperature</th><th></th></tr></thead>
            <tbody>
                ${drives.map(d => `
                    <tr class="${d.status === "critical" ? "critical" : d.status === "warning" ? "warning" : ""}">
                        <td>${escapeHtml(d.device)}</td>
                        <td><span class="badge badge-${d.status}">${escapeHtml(d.status)}</span></td>
                        <td>${escapeHtml(d.smart_status)}</td>
                        <td>${d.temperature_c != null ? d.temperature_c.toFixed(1) + " °C" : "—"}</td>
                        <td><a class="btn btn-sm btn-ghost" href="/drive-detail?device=${encodeURIComponent(d.device)}">Examine</a></td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    ` : `<p class="detail" style="margin-top:0.75rem;">Enable <strong>Admin mode</strong> to see SMART drive health.</p>`;

    document.getElementById("disks-details").innerHTML = `
        ${disks.length ? `<table class="data-table">
            <thead>
                <tr>
                    <th>Device</th>
                    <th>Mount</th>
                    <th>Usage</th>
                    <th>Read</th>
                    <th>Write</th>
                    <th>IOPS</th>
                    <th>Temp</th>
                    <th>SMART</th>
                </tr>
            </thead>
            <tbody>
                ${disks.map(d => `
                    <tr class="${d.smart_failing || d.percent >= 95 ? "critical" : d.percent >= 85 ? "warning" : ""}">
                        <td>${escapeHtml(d.device)}</td>
                        <td>${escapeHtml(d.mountpoint)}</td>
                        <td>${d.percent.toFixed(1)}% <span class="detail">${formatBytes(d.used_bytes)} / ${formatBytes(d.total_bytes)}</span></td>
                        <td>${formatBytes(d.read_bytes_per_sec)}/s</td>
                        <td>${formatBytes(d.write_bytes_per_sec)}/s</td>
                        <td>${d.iops.toFixed(1)}</td>
                        <td>${d.temperature_c ? d.temperature_c.toFixed(1) + " °C" : "—"}</td>
                        <td>${d.smart_status}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>` : ""}
        ${driveSmartMarkup}
    `;
}

function updateNetwork(network) {
    // Mirror the backend thresholds: down interfaces have historical counters,
    // errors are always significant, lifetime drops only above 1000.
    const ifaceHasProblems = i => i.is_up && (i.errin || i.errout || (i.dropin + i.dropout) > 1000);
    const hasErrors = network.interfaces.some(ifaceHasProblems);
    const status = hasErrors ? "warning" : "healthy";
    componentStatus(document.getElementById("network-status"), status);

    const totalBps = network.total_bytes_sent_per_sec + network.total_bytes_recv_per_sec;
    document.getElementById("network-total").textContent = `${formatBytes(totalBps)}/s`;

    document.getElementById("network-details").innerHTML = `
        <div class="detail-grid compact">
            <div class="detail-item"><dt>Upload</dt><dd>${formatBytes(network.total_bytes_sent_per_sec)}/s</dd></div>
            <div class="detail-item"><dt>Download</dt><dd>${formatBytes(network.total_bytes_recv_per_sec)}/s</dd></div>
            <div class="detail-item"><dt>Latency</dt><dd>${network.latency_ms ? network.latency_ms.toFixed(1) + " ms" : "—"}</dd></div>
            <div class="detail-item"><dt>Interfaces</dt><dd>${network.interfaces.length}</dd></div>
        </div>
        ${network.interfaces.length ? `
        <table class="data-table" style="margin-top:0.75rem;">
            <thead>
                <tr><th>Interface</th><th>Up</th><th>Speed</th><th>Sent</th><th>Recv</th><th>Errors</th><th>Drops</th></tr>
            </thead>
            <tbody>
                ${network.interfaces.map(i => `
                    <tr class="${ifaceHasProblems(i) ? "warning" : ""}">
                        <td>${escapeHtml(i.name)}</td>
                        <td>${i.is_up ? "Yes" : "No"}</td>
                        <td>${i.speed_mbps ? i.speed_mbps + " Mbps" : "—"}</td>
                        <td>${formatBytes(i.bytes_sent_per_sec)}/s</td>
                        <td>${formatBytes(i.bytes_recv_per_sec)}/s</td>
                        <td>${i.errin + i.errout}</td>
                        <td>${i.dropin + i.dropout}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
        ` : ""}
    `;

    pushHistory(history.networkSent, network.total_bytes_sent_per_sec);
    pushHistory(history.networkRecv, network.total_bytes_recv_per_sec);
    updateChart(charts.network, [history.networkSent, history.networkRecv]);
}

function updateSystem(data) {
    const hasFailed = data.failed_services.length > 0;
    const hasFsErrors = data.filesystem_errors.length > 0;
    const hasUpdates = data.update_count > 50;
    const status = hasFsErrors ? "critical" : (hasFailed || hasUpdates) ? "warning" : "healthy";
    componentStatus(document.getElementById("system-status"), status);

    document.getElementById("system-details").innerHTML = `
        <div class="detail-grid compact">
            <div class="detail-item"><dt>Uptime</dt><dd>${formatUptime(data.uptime_seconds)}</dd></div>
            <div class="detail-item"><dt>Failed services</dt><dd>${data.failed_services.length ? `<span class="text-danger">${data.failed_services.length}</span>` : "0"}</dd></div>
            <div class="detail-item"><dt>FS errors</dt><dd>${data.filesystem_errors.length ? `<span class="text-danger">${data.filesystem_errors.length}</span>` : "0"}</dd></div>
            <div class="detail-item"><dt>Updates</dt><dd>${data.update_count}</dd></div>
        </div>
        ${data.failed_services.length ? `<p class="detail text-danger" style="margin-top:0.5rem;">${data.failed_services.map(escapeHtml).join(", ")}</p>` : ""}
        ${data.filesystem_errors.length ? `<ul class="code-list" style="margin-top:0.5rem;">${data.filesystem_errors.slice(0, 5).map(e => `<li>${escapeHtml(e)}</li>`).join("")}</ul>` : ""}
    `;
}

function updateGpu(gpus) {
    const card = document.getElementById("gpu-card");
    if (!gpus || gpus.length === 0) {
        card.style.display = "none";
        return;
    }
    card.style.display = "";

    let worst = "healthy";
    gpus.forEach(g => {
        if (g.temperature_c && g.temperature_c >= 90) worst = "critical";
        else if (g.temperature_c && g.temperature_c >= 80 && worst !== "critical") worst = "warning";
    });
    componentStatus(document.getElementById("gpu-status"), worst);

    document.getElementById("gpu-details").innerHTML = `
        <div class="detail-grid compact">
            ${gpus.map(g => `
                <div class="detail-item"><dt>${escapeHtml(g.name)}</dt><dd>${g.utilization_percent != null ? g.utilization_percent.toFixed(0) + "%" : "—"}</dd></div>
                <div class="detail-item"><dt>Temp</dt><dd>${g.temperature_c ? g.temperature_c.toFixed(1) + " °C" : "—"}</dd></div>
                <div class="detail-item"><dt>Memory</dt><dd>${g.memory_used_bytes != null ? formatBytes(g.memory_used_bytes) + " / " + formatBytes(g.memory_total_bytes) : "—"}</dd></div>
            `).join("")}
        </div>
    `;
}

function updateSensors(sensors) {
    const container = document.getElementById("sensors-details");
    if (!sensors || sensors.length === 0) {
        container.innerHTML = "<p class='detail'>No sensor data available.</p>";
        return;
    }
    container.innerHTML = `
        <div class="sensor-grid">
            ${sensors.map(s => `
                <div class="sensor-item">
                    <span class="sensor-label">${escapeHtml(s.label)}</span>
                    <span class="sensor-value">${s.value != null ? s.value.toFixed(1) + " " + escapeHtml(s.unit) : "—"}</span>
                </div>
            `).join("")}
        </div>
    `;
}

function escapeHtml(text) {
    if (text == null) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

initHealth();
