"use strict";

let targetUser = null;
let confirmResolve = null;

async function initUsers() {
    await initLayout("/users");

    document.getElementById("btn-add-user").addEventListener("click", () => {
        document.getElementById("create-user-form").reset();
        document.getElementById("new-shell").value = "/bin/bash";
        hideError("create-user-error");
        document.getElementById("create-user-modal").style.display = "flex";
        setTimeout(() => document.getElementById("new-username").focus(), 50);
    });

    setupCreateUserModal();
    setupPasswordModal();
    setupConfirmModal();

    await refreshAdminState();
    await loadUsers();
}

async function loadUsers() {
    const loadingEl = document.getElementById("users-loading");
    const listEl = document.getElementById("users-list");
    loadingEl.style.display = "block";
    listEl.innerHTML = "";
    try {
        const users = await getUnixUsers();
        loadingEl.style.display = "none";
        renderUsers(users);
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        loadingEl.textContent = `Error: ${error.message}`;
    }
}

function renderUsers(users) {
    const listEl = document.getElementById("users-list");
    listEl.innerHTML = "";
    for (const user of users) {
        const card = document.createElement("article");
        card.className = "card user-card";
        const initial = (user.full_name || user.username).charAt(0).toUpperCase();
        const badges = [
            user.is_admin ? '<span class="badge badge-enabled">Admin</span>' : "",
            user.username === currentPanelUser ? '<span class="badge badge-neutral">You</span>' : "",
        ].join(" ");
        card.innerHTML = `
            <div class="user-avatar">${escapeHtml(initial)}</div>
            <div class="user-meta">
                <div class="user-name">
                    <strong>${escapeHtml(user.full_name || user.username)}</strong>
                    ${badges}
                </div>
                <div class="detail">${escapeHtml(user.username)} · UID ${user.uid} · ${escapeHtml(user.home)} · ${escapeHtml(user.shell)}</div>
            </div>
            <div class="user-actions">
                <button class="btn btn-ghost btn-xs" data-action="password">Set Password</button>
                <button class="btn btn-ghost btn-xs" data-action="toggle-admin">${user.is_admin ? "Remove Admin" : "Make Admin"}</button>
                <button class="btn btn-danger btn-xs" data-action="delete">Delete</button>
            </div>
        `;
        card.querySelectorAll("[data-action]").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const action = btn.dataset.action;
                if (action === "password") openPasswordModal(user);
                else if (action === "toggle-admin") promptToggleAdmin(user);
                else if (action === "delete") promptDeleteUser(user);
            });
        });
        listEl.appendChild(card);
    }
}

function setupCreateUserModal() {
    const modal = document.getElementById("create-user-modal");
    document.getElementById("create-user-close").addEventListener("click", () => modal.style.display = "none");
    modal.querySelector(".modal-content").addEventListener("click", e => e.stopPropagation());
    modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });
    document.getElementById("create-user-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        hideError("create-user-error");
        const username = document.getElementById("new-username").value.trim();
        const fullName = document.getElementById("new-fullname").value.trim();
        const password = document.getElementById("new-password").value;
        const shell = document.getElementById("new-shell").value.trim() || "/bin/bash";
        try {
            await createUnixUser(username, fullName, password, shell);
            modal.style.display = "none";
            showNotice(`User ${username} created`);
            await loadUsers();
        } catch (error) {
            showError("create-user-error", error.message);
        }
    });
}

function openPasswordModal(user) {
    targetUser = user;
    document.getElementById("password-modal-title").textContent = `Set Password — ${user.username}`;
    document.getElementById("password-form").reset();
    hideError("password-error");
    document.getElementById("password-modal").style.display = "flex";
    setTimeout(() => document.getElementById("password-input").focus(), 50);
}

function setupPasswordModal() {
    const modal = document.getElementById("password-modal");
    document.getElementById("password-close").addEventListener("click", () => modal.style.display = "none");
    modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });
    document.getElementById("password-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        hideError("password-error");
        try {
            await setUnixPassword(targetUser.username, document.getElementById("password-input").value);
            modal.style.display = "none";
            showNotice(`Password updated for ${targetUser.username}`);
        } catch (error) {
            showError("password-error", error.message);
        }
    });
}

async function promptToggleAdmin(user) {
    const verb = user.is_admin ? "Remove admin access from" : "Grant admin (sudo) access to";
    const confirmed = await confirmDialog("Confirm", `${verb} ${user.username}?`);
    if (!confirmed) return;
    try {
        await setUnixUserAdmin(user.username, !user.is_admin);
        showNotice(`${user.username} admin access ${user.is_admin ? "removed" : "granted"}`);
        await loadUsers();
    } catch (error) {
        alert(`Failed: ${error.message}`);
    }
}

async function promptDeleteUser(user) {
    const confirmed = await confirmDialog(
        "Delete User",
        `Delete account "${user.username}"? The home directory is kept. This cannot be undone.`
    );
    if (!confirmed) return;
    try {
        await deleteUnixUser(user.username);
        showNotice(`User ${user.username} deleted`);
        await loadUsers();
    } catch (error) {
        alert(`Failed to delete user: ${error.message}`);
    }
}

function setupConfirmModal() {
    const modal = document.getElementById("confirm-modal");
    document.getElementById("confirm-close").addEventListener("click", () => closeConfirm(false));
    document.getElementById("confirm-cancel").addEventListener("click", () => closeConfirm(false));
    document.getElementById("confirm-ok").addEventListener("click", () => closeConfirm(true));
    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeConfirm(false);
    });
}

function closeConfirm(value) {
    document.getElementById("confirm-modal").style.display = "none";
    if (confirmResolve) {
        confirmResolve(value);
        confirmResolve = null;
    }
}

function confirmDialog(title, message) {
    return new Promise((resolve) => {
        confirmResolve = resolve;
        document.getElementById("confirm-title").textContent = title;
        document.getElementById("confirm-message").textContent = message;
        document.getElementById("confirm-modal").style.display = "flex";
    });
}

function showNotice(message) {
    const el = document.getElementById("users-notice");
    el.textContent = message;
    el.className = "notice notice-success";
    el.style.display = "block";
    setTimeout(() => { el.style.display = "none"; }, 5000);
}

function showError(id, message) {
    const el = document.getElementById(id);
    el.textContent = message;
    el.style.display = "block";
}

function hideError(id) {
    document.getElementById(id).style.display = "none";
}

initUsers();
