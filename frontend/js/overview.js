"use strict";

const REFRESH_INTERVAL_MS = 5000;
const OVERVIEW_HISTORY_MAX = 90;

let refreshTimer = null;
const overviewHistory = { cpu: [], memory: [], disk: [], temperature: [] };

async function initOverview() {
    await initLayout("/overview");
    await loadStats();
    refreshTimer = setInterval(loadStats, REFRESH_INTERVAL_MS);

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        } else if (!refreshTimer) {
            loadStats();
            refreshTimer = setInterval(loadStats, REFRESH_INTERVAL_MS);
        }
    });

    window.addEventListener("resize", debounce(drawOverviewSparklines, 200));
}

async function loadStats() {
    try {
        const stats = await getSystemStats();
        updateCpu(stats.cpu);
        updateMemory(stats.memory);
        updateDisk(stats.disk);
        updateTemperature(stats.temperature_celsius);
        updateInfo(stats);
        recordOverviewHistory(stats);
        drawOverviewSparklines();
        setLastUpdated(`Updated ${new Date().toLocaleTimeString()}`);
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        setLastUpdated("Connection lost, retrying…");
    }
}

function recordOverviewHistory(stats) {
    pushOverviewSample(overviewHistory.cpu, stats.cpu?.usage_percent ?? 0);
    pushOverviewSample(overviewHistory.memory, stats.memory?.usage_percent ?? 0);
    pushOverviewSample(overviewHistory.disk, stats.disk?.usage_percent ?? 0);
    pushOverviewSample(overviewHistory.temperature, stats.temperature_celsius ?? 0);
}

function pushOverviewSample(arr, value) {
    arr.push(value);
    if (arr.length > OVERVIEW_HISTORY_MAX) arr.shift();
}

function drawOverviewSparklines() {
    drawSparkline(document.getElementById("cpu-spark"), overviewHistory.cpu, "#6366f1", OVERVIEW_HISTORY_MAX);
    drawSparkline(document.getElementById("memory-spark"), overviewHistory.memory, "#06b6d4", OVERVIEW_HISTORY_MAX);
    drawSparkline(document.getElementById("disk-spark"), overviewHistory.disk, "#a78bfa", OVERVIEW_HISTORY_MAX);
    drawSparkline(document.getElementById("temperature-spark"), overviewHistory.temperature, "#f59e0b", OVERVIEW_HISTORY_MAX);
}

function setLastUpdated(text) {
    const el = document.getElementById("last-updated");
    if (el) el.textContent = text;
}

function updateCpu(cpu) {
    const percent = cpu.usage_percent ?? 0;
    document.getElementById("cpu-metric").textContent = `${percent.toFixed(1)}%`;
    document.getElementById("cpu-detail").textContent = `${cpu.cores ?? "--"} cores` +
        (cpu.frequency_mhz ? ` @ ${cpu.frequency_mhz.toFixed(0)} MHz` : "");
    document.getElementById("cpu-bar").style.width = `${Math.min(percent, 100)}%`;
}

function updateMemory(memory) {
    const percent = memory.usage_percent ?? 0;
    document.getElementById("memory-metric").textContent = `${percent.toFixed(1)}%`;
    document.getElementById("memory-detail").textContent =
        `${formatBytes(memory.used_bytes)} / ${formatBytes(memory.total_bytes)}`;
    document.getElementById("memory-bar").style.width = `${Math.min(percent, 100)}%`;
}

function updateDisk(disk) {
    const percent = disk.usage_percent ?? 0;
    document.getElementById("disk-metric").textContent = `${percent.toFixed(1)}%`;
    document.getElementById("disk-detail").textContent =
        `${formatBytes(disk.used_bytes)} / ${formatBytes(disk.total_bytes)}`;
    document.getElementById("disk-bar").style.width = `${Math.min(percent, 100)}%`;
}

function updateTemperature(temp) {
    const element = document.getElementById("temperature-metric");
    if (temp == null) {
        element.textContent = "--°C";
        return;
    }
    element.textContent = `${temp.toFixed(1)}°C`;
    element.classList.toggle("warn", temp >= 80);
}

function updateInfo(stats) {
    document.getElementById("hostname").textContent = stats.hostname || "Unknown host";
    document.getElementById("info-hostname").textContent = stats.hostname || "--";
    document.getElementById("info-os").textContent = stats.os || "--";
    document.getElementById("info-kernel").textContent = stats.kernel || "--";
    document.getElementById("info-arch").textContent = stats.architecture || "--";
    document.getElementById("info-uptime").textContent = formatUptime(stats.uptime_seconds);
}

initOverview();
