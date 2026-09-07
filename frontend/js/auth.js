"use strict";

const NAV_ITEMS = [
    { path: "/overview", label: "Overview", icon: "◈" },
    { path: "/health", label: "Health", icon: "✚" },
    { path: "/services", label: "Services", icon: "⚙" },
    { path: "/processes", label: "Processes", icon: "≣", feature: "processes" },
    { path: "/users", label: "Users", icon: "◍", feature: "users" },
    { path: "/storage", label: "Storage", icon: "▤" },
    { path: "/files", label: "Files", icon: "❐" },
    { path: "/updates", label: "Updates", icon: "↻" },
    { path: "/terminal", label: "Terminal", icon: "⌘", feature: "terminal" },
];

const BOTTOM_ITEMS = [
    { path: "/settings", label: "Settings", icon: "◎" },
];

let cachedFeatures = null;
let adminState = { is_admin: false, expires_at: null, checking: false };
let currentPanelUser = null;
const ADMIN_UNLIMITED_MS = 10 * 365 * 24 * 60 * 60 * 1000;

async function requireAuth() {
    try {
        const user = await getCurrentUser();
        return user;
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
        }
        throw error;
    }
}

async function getCachedFeatures() {
    if (cachedFeatures === null) {
        try {
            cachedFeatures = await getFeatures();
        } catch (error) {
            cachedFeatures = { terminal: false, service_management: true, logs: true };
        }
    }
    return cachedFeatures;
}

function renderSidebar(activePath, features) {
    const container = document.getElementById("sidebar");
    if (!container) return;

    const visibleNav = NAV_ITEMS.filter(item =>
        !item.feature || features[item.feature] === true
    );

    const navHtml = visibleNav.map(item => `
        <a href="${item.path}" class="nav-item ${item.path === activePath ? "active" : ""}">
            <span class="icon">${item.icon}</span>
            <span>${item.label}</span>
        </a>
    `).join("");

    const bottomHtml = BOTTOM_ITEMS.map(item => `
        <a href="${item.path}" class="nav-item ${item.path === activePath ? "active" : ""}">
            <span class="icon">${item.icon}</span>
            <span>${item.label}</span>
        </a>
    `).join("");

    container.innerHTML = `
        <div class="sidebar-brand">
            <span class="brand-name">Nexus Panel</span>
        </div>
        <nav class="sidebar-nav" aria-label="Main navigation">
            ${navHtml}
        </nav>
        <div class="sidebar-divider"></div>
        <div class="sidebar-section">
            ${bottomHtml}
            <a href="#" class="nav-item" id="logout-link">
                <span class="icon">⏻</span>
                <span>Logout</span>
            </a>
        </div>
    `;

    document.getElementById("logout-link").addEventListener("click", async (event) => {
        event.preventDefault();
        try {
            await logout();
        } catch (error) {
            // Ignore errors and redirect anyway.
        }
        window.location.href = "/login";
    });

    const mobileToggle = document.getElementById("mobile-menu-toggle");
    if (mobileToggle) {
        mobileToggle.addEventListener("click", () => {
            container.classList.toggle("open");
        });
    }

    // Close sidebar when clicking a nav item on mobile.
    container.querySelectorAll(".nav-item").forEach(link => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 768) {
                container.classList.remove("open");
            }
        });
    });
}

function _adminModalHtml() {
    return `
        <div id="admin-modal" class="modal" style="display:none;">
            <div class="modal-content" style="max-width:420px;">
                <div class="modal-header">
                    <h2>Enable Admin Mode</h2>
                    <button class="close-modal" id="admin-modal-close">&times;</button>
                </div>
                <p class="modal-hint">Enter the password of a sudo-authorized system user to unlock privileged operations.</p>
                <form id="admin-form" class="form-stack">
                    <label>
                        System user
                        <input type="text" id="admin-username" autocomplete="username" required>
                    </label>
                    <label>
                        Password
                        <input type="password" id="admin-password" autocomplete="current-password" required>
                    </label>
                    <div id="admin-error" class="form-error" style="display:none;"></div>
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">Unlock Admin</button>
                    </div>
                </form>
            </div>
        </div>
    `;
}

async function refreshAdminState() {
    try {
        adminState.checking = true;
        adminState = await getAdminStatus();
    } catch (error) {
        adminState = { is_admin: false, expires_at: null };
    } finally {
        adminState.checking = false;
    }
    _renderAdminBadge();
}

function _formatTimeRemaining(isoDate) {
    if (!isoDate) return "";
    const ms = new Date(isoDate) - Date.now();
    if (ms <= 0) return "expired";
    if (ms >= ADMIN_UNLIMITED_MS) return "";
    const minutes = Math.ceil(ms / 60000);
    return `${minutes}m`;
}

function _renderAdminBadge() {
    const badge = document.getElementById("admin-badge");
    if (!badge) return;
    if (adminState.is_admin) {
        const remaining = _formatTimeRemaining(adminState.expires_at);
        const user = adminState.sudo_username || "admin";
        badge.className = "admin-badge admin-on";
        badge.innerHTML = `● ${user}${remaining ? ` <span class="admin-timer">${remaining}</span>` : ""}`;
        badge.title = remaining
            ? `Operating as ${user}. Admin mode expires ${new Date(adminState.expires_at).toLocaleTimeString()}. Click to disable.`
            : `Operating as ${user}. Admin mode has no expiry. Click to disable.`;
    } else {
        badge.className = "admin-badge admin-off";
        badge.innerHTML = `○ nexus`;
        badge.title = "Operating as nexus. Click to enable admin mode";
    }
}

function getActiveSudoUsername() {
    return adminState.is_admin ? adminState.sudo_username || null : null;
}

function _attachAdminEvents() {
    const badge = document.getElementById("admin-badge");
    if (!badge) return;
    badge.addEventListener("click", () => {
        if (adminState.is_admin) {
            if (confirm("Disable admin mode and return to unprivileged user mode?")) {
                revokeAdmin().then(() => refreshAdminState()).catch(() => {});
            }
        } else {
            const userInput = document.getElementById("admin-username");
            if (userInput && currentPanelUser) userInput.value = currentPanelUser;
            const modal = document.getElementById("admin-modal");
            if (modal) modal.style.display = "flex";
        }
    });

    const modal = document.getElementById("admin-modal");
    const close = document.getElementById("admin-modal-close");
    if (close && modal) {
        close.addEventListener("click", () => { modal.style.display = "none"; });
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.style.display = "none";
        });
    }

    const form = document.getElementById("admin-form");
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("admin-username").value.trim();
            const password = document.getElementById("admin-password").value;
            const errorEl = document.getElementById("admin-error");
            errorEl.style.display = "none";
            try {
                await elevateAdmin(username, password);
                document.getElementById("admin-password").value = "";
                if (modal) modal.style.display = "none";
                await refreshAdminState();
            } catch (error) {
                errorEl.textContent = error.message || "Authentication failed";
                errorEl.style.display = "block";
            }
        });
    }
}

function renderAdminControls() {
    const menu = document.querySelector(".user-menu");
    if (!menu) return;
    if (!document.getElementById("admin-modal")) {
        const div = document.createElement("div");
        div.innerHTML = _adminModalHtml();
        document.body.appendChild(div.firstElementChild);
    }
    let badge = document.getElementById("admin-badge");
    if (!badge) {
        badge = document.createElement("button");
        badge.id = "admin-badge";
        badge.className = "admin-badge admin-off";
        menu.insertBefore(badge, menu.firstChild);
    }
    _attachAdminEvents();
    _renderAdminBadge();
}

async function initLayout(activePath) {
    const user = await requireAuth();
    currentPanelUser = user.username;
    const features = await getCachedFeatures();
    renderSidebar(activePath, features);
    renderAdminControls();

    const userEl = document.getElementById("current-user");
    if (userEl) userEl.textContent = user.username;

    await refreshAdminState();
    // Periodically refresh the timer display and check expiration.
    setInterval(() => {
        refreshAdminState();
    }, 60000);
}
