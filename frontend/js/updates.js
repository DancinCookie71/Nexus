"use strict";

async function initUpdates() {
    await initLayout("/updates");
    document.getElementById("refresh-updates").addEventListener("click", loadUpdates);
    document.getElementById("install-updates").addEventListener("click", installUpdates);
    await loadUpdates();
}

async function installUpdates() {
    const statusEl = document.getElementById("updates-status");
    const button = document.getElementById("install-updates");
    const rebootAfter = document.getElementById("reboot-after").checked;
    const count = document.getElementById("update-count").textContent;

    if (!adminState.is_admin) {
        statusEl.style.display = "block";
        statusEl.style.color = "var(--warn)";
        statusEl.textContent = "Enable Admin mode (top bar) to install updates.";
        return;
    }
    if (!confirm(`Install ${count}? This upgrades every upgradable package and can take a long time.${rebootAfter ? " The system will reboot afterwards." : ""}`)) {
        return;
    }

    button.disabled = true;
    document.getElementById("refresh-updates").disabled = true;
    statusEl.style.display = "block";
    statusEl.style.color = "var(--text-muted)";
    statusEl.textContent = "Installing updates… this can take several minutes. Do not close this page.";

    try {
        const result = await apiRequest("POST", "/updates", { reboot: rebootAfter });
        statusEl.style.color = "var(--success)";
        statusEl.textContent = result.message;
        if (!rebootAfter) {
            await loadUpdates();
        }
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        statusEl.style.color = "var(--danger)";
        statusEl.textContent = `Install failed: ${error.message}`;
    } finally {
        button.disabled = false;
        document.getElementById("refresh-updates").disabled = false;
    }
}

async function loadUpdates() {
    const countEl = document.getElementById("update-count");
    const managerEl = document.getElementById("update-manager");
    const listEl = document.getElementById("package-list");
    const errorEl = document.getElementById("updates-error");
    const unsupportedEl = document.getElementById("updates-unsupported");

    countEl.textContent = "Checking...";
    errorEl.textContent = "";
    listEl.innerHTML = "";
    unsupportedEl.style.display = "none";
    document.getElementById("reboot-banner").style.display = "none";

    try {
        const data = await getUpdates();

        if (data.reboot_required) {
            document.getElementById("reboot-banner").style.display = "block";
        }

        if (!data.supported) {
            countEl.textContent = "Not supported";
            unsupportedEl.textContent = data.error || "Update detection is not supported on this system.";
            unsupportedEl.style.display = "block";
            return;
        }

        countEl.textContent = `${data.update_count} update${data.update_count === 1 ? "" : "s"} available`;
        managerEl.textContent = data.package_manager ? `Package manager: ${data.package_manager}` : "";

        if (data.error) {
            errorEl.textContent = data.error;
        }

        if (data.packages.length === 0) {
            listEl.innerHTML = "<li>System is up to date</li>";
        } else {
            for (const pkg of data.packages) {
                const li = document.createElement("li");
                li.textContent = pkg;
                listEl.appendChild(li);
            }
        }
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        countEl.textContent = "Error";
        errorEl.textContent = error.message || "Failed to check for updates";
    }
}

initUpdates();
