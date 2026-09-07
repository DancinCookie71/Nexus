"use strict";

let currentPath = "";
let selectedPath = "";
let showHidden = false;
let searchQuery = "";
let activeSudoUser = null;

async function initFiles() {
    await initLayout("/files");

    activeSudoUser = getActiveSudoUsername();
    renderContextBar();

    const params = new URLSearchParams(window.location.search);
    currentPath = params.get("path") || "";

    document.getElementById("btn-refresh").addEventListener("click", async () => {
        activeSudoUser = getActiveSudoUsername();
        renderContextBar();
        await loadFiles();
    });
    document.getElementById("btn-new").addEventListener("click", (e) => {
        e.stopPropagation();
        document.getElementById("new-dropdown-menu").classList.toggle("open");
    });
    document.getElementById("btn-upload").addEventListener("click", openUploadModal);

    document.getElementById("new-dropdown-menu").querySelectorAll("button").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            document.getElementById("new-dropdown-menu").classList.remove("open");
            const type = btn.dataset.type;
            if (type === "folder") promptNewFolder();
            else if (type === "other") promptNewFile("");
            else promptNewFile("." + type);
        });
    });

    document.addEventListener("click", () => {
        document.getElementById("new-dropdown-menu").classList.remove("open");
    });

    const hiddenToggle = document.getElementById("show-hidden");
    hiddenToggle.checked = showHidden;
    hiddenToggle.addEventListener("change", (e) => {
        showHidden = e.target.checked;
        loadFiles();
    });

    const searchInput = document.getElementById("file-search");
    searchInput.addEventListener("input", debounce(() => {
        searchQuery = searchInput.value.trim();
        loadFiles();
    }, 250));

    setupEditorModal();
    setupUploadModal();
    setupPromptModal();
    setupConfirmModal();
    setupContextMenu();

    document.addEventListener("click", () => hideContextMenu());

    await loadFiles();
}

function renderContextBar() {
    const bar = document.getElementById("file-context-bar");
    if (!bar) return;
    const user = activeSudoUser || currentPanelUser || "nexus";
    if (activeSudoUser) {
        bar.innerHTML = `Browsing as <strong>${escapeHtml(user)}</strong> (admin mode)`;
        bar.style.background = "rgba(34, 197, 94, 0.08)";
    } else {
        bar.innerHTML = `Browsing as <strong>${escapeHtml(user)}</strong>`;
        bar.style.background = "rgba(99, 102, 241, 0.08)";
    }
}

async function loadFiles() {
    const currentSudoUser = getActiveSudoUsername();
    if (currentSudoUser !== activeSudoUser) {
        activeSudoUser = currentSudoUser;
        renderContextBar();
        if (currentPath !== "") {
            currentPath = "";
            searchQuery = "";
            document.getElementById("file-search").value = "";
            updateUrl();
            renderBreadcrumb();
        }
    }

    const loadingEl = document.getElementById("files-loading");
    const tableWrapper = document.getElementById("files-table-wrapper");
    const emptyEl = document.getElementById("files-empty");
    const tbody = document.getElementById("files-table-body");

    loadingEl.style.display = "block";
    tableWrapper.style.display = "none";
    emptyEl.style.display = "none";
    tbody.innerHTML = "";

    try {
        let entries;
        if (searchQuery) {
            const data = await searchFiles(searchQuery, currentPath, showHidden);
            entries = data.entries || [];
        } else {
            const data = await listFiles(currentPath);
            currentPath = data.path;
            entries = data.entries || [];
            if (!showHidden) {
                entries = entries.filter(e => !e.name.startsWith("."));
            }
        }
        updateUrl();
        renderBreadcrumb();
        loadingEl.style.display = "none";

        if (entries.length === 0) {
            emptyEl.textContent = searchQuery ? "No matching files." : "This directory is empty.";
            emptyEl.style.display = "block";
            return;
        }

        for (const entry of entries) {
            tbody.appendChild(renderEntryRow(entry));
        }

        tableWrapper.style.display = "block";
        bindFileActions();
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/login";
            return;
        }
        loadingEl.textContent = `Error: ${error.message}`;
    }
}

function renderEntryRow(entry) {
    const tr = document.createElement("tr");
    tr.className = "file-row";
    tr.dataset.path = entry.path;
    tr.dataset.type = entry.type;
    tr.dataset.name = entry.name;
    const icon = entry.type === "directory" ? "📁" : entry.is_symlink ? "🔗" : "📄";
    const nameHtml = `<span class="file-icon">${icon}</span><span>${escapeHtml(entry.name)}${entry.is_symlink && entry.target ? ` → ${escapeHtml(entry.target)}` : ""}</span>`;

    tr.innerHTML = `
        <td class="col-name file-name">${nameHtml}</td>
        <td class="col-size">${entry.type === "directory" ? "—" : formatBytes(entry.size)}</td>
        <td class="col-modified">${formatDate(entry.modified_at)}</td>
        <td class="col-perms"><code>${escapeHtml(entry.mode)}</code></td>
        <td class="col-owner">${escapeHtml(entry.owner)}</td>
        <td class="col-group">${escapeHtml(entry.group)}</td>
    `;

    tr.addEventListener("click", (e) => {
        if (e.button !== 0) return;
        handleEntryClick(entry);
    });
    tr.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        showContextMenu(e, entry);
    });
    return tr;
}

function handleEntryClick(entry) {
    if (entry.type === "directory") {
        currentPath = entry.path;
        searchQuery = "";
        document.getElementById("file-search").value = "";
        loadFiles();
    } else {
        openEditor(entry.path);
    }
}

function bindFileActions() {
    // Actions are now bound per row and via context menu.
}

function renderBreadcrumb() {
    const container = document.getElementById("file-breadcrumb");
    const parts = currentPath.split("/").filter(Boolean);
    let html = `<span class="breadcrumb-item" data-path="">Home</span>`;
    let build = "";
    for (const part of parts) {
        build = build ? `${build}/${part}` : part;
        html += `<span class="breadcrumb-separator">/</span><span class="breadcrumb-item" data-path="${escapeHtml(build)}">${escapeHtml(part)}</span>`;
    }
    container.innerHTML = html;
    container.querySelectorAll(".breadcrumb-item").forEach(item => {
        item.addEventListener("click", () => {
            currentPath = item.dataset.path;
            searchQuery = "";
            document.getElementById("file-search").value = "";
            loadFiles();
        });
    });
}

function updateUrl() {
    const url = new URL(window.location.href);
    url.searchParams.set("path", currentPath);
    window.history.replaceState({}, "", url.toString());
}

async function promptNewFolder() {
    const name = await promptDialog("New Folder", "Enter name for the new folder:");
    if (!name) return;
    const path = currentPath ? `${currentPath}/${name}` : name;
    try {
        await createDirectory(path);
        await loadFiles();
    } catch (error) {
        alert(`Failed to create folder: ${error.message}`);
    }
}

async function promptNewFile(extension) {
    const defaultName = extension ? `file${extension}` : "";
    const message = extension
        ? `Enter file name (will add ${extension}):`
        : "Enter file name with extension:";
    const input = await promptDialog("New File", message, defaultName);
    if (!input) return;
    const name = extension && !input.endsWith(extension) ? input + extension : input;
    const path = currentPath ? `${currentPath}/${name}` : name;
    try {
        await saveFileContent(path, "");
        await loadFiles();
        openEditor(path);
    } catch (error) {
        alert(`Failed to create file: ${error.message}`);
    }
}

async function promptRename(entry) {
    const name = await promptDialog("Rename", "Enter new name:", entry.name);
    if (!name || name === entry.name) return;
    const target = currentPath ? `${currentPath}/${name}` : name;
    try {
        await renameFile(entry.path, target);
        await loadFiles();
    } catch (error) {
        alert(`Failed to rename: ${error.message}`);
    }
}

async function promptCopy(entry) {
    const defaultName = entry.type === "directory" ? `${entry.name}_copy` : entry.name;
    const name = await promptDialog("Copy", "Enter destination name:", defaultName);
    if (!name) return;
    const target = currentPath ? `${currentPath}/${name}` : name;
    try {
        await copyFile(entry.path, target);
        await loadFiles();
    } catch (error) {
        alert(`Failed to copy: ${error.message}`);
    }
}

async function promptMove(entry) {
    const destination = await promptDialog("Move", "Enter destination path:", entry.path);
    if (!destination || destination === entry.path) return;
    try {
        await renameFile(entry.path, destination);
        await loadFiles();
    } catch (error) {
        alert(`Failed to move: ${error.message}`);
    }
}

async function promptDelete(entry) {
    const isDir = entry.type === "directory";
    const confirmed = await confirmDialog(
        "Confirm Delete",
        isDir
            ? `Delete folder "${entry.name}" and all its contents? This cannot be undone.`
            : `Delete file "${entry.name}"? This cannot be undone.`
    );
    if (!confirmed) return;
    try {
        await deleteFile(entry.path, isDir);
        await loadFiles();
    } catch (error) {
        alert(`Failed to delete: ${error.message}`);
    }
}

function setupEditorModal() {
    const modal = document.getElementById("editor-modal");
    const closeBtn = document.getElementById("editor-close");
    const saveBtn = document.getElementById("editor-save");
    const textarea = document.getElementById("editor-textarea");
    const statusEl = document.getElementById("editor-status");

    closeBtn.addEventListener("click", () => modal.style.display = "none");
    modal.querySelector(".modal-backdrop").addEventListener("click", () => modal.style.display = "none");

    saveBtn.addEventListener("click", async () => {
        statusEl.textContent = "Saving...";
        try {
            await saveFileContent(selectedPath, textarea.value);
            statusEl.textContent = "Saved";
            setTimeout(() => statusEl.textContent = "", 2000);
            await loadFiles();
        } catch (error) {
            statusEl.textContent = `Error: ${error.message}`;
        }
    });
}

async function openEditor(path) {
    const modal = document.getElementById("editor-modal");
    const title = document.getElementById("editor-title");
    const textarea = document.getElementById("editor-textarea");
    const statusEl = document.getElementById("editor-status");

    selectedPath = path;
    title.textContent = path;
    textarea.value = "";
    statusEl.textContent = "Loading...";
    modal.style.display = "flex";

    try {
        const data = await getFileContent(path);
        textarea.value = data.content;
        statusEl.textContent = `${formatBytes(data.size)} · ${data.mime_type}`;
    } catch (error) {
        statusEl.textContent = `Error: ${error.message}`;
    }
}

function setupUploadModal() {
    const modal = document.getElementById("upload-modal");
    const closeBtn = document.getElementById("upload-close");
    const submitBtn = document.getElementById("upload-submit");
    const input = document.getElementById("upload-input");
    const statusEl = document.getElementById("upload-status");

    closeBtn.addEventListener("click", () => modal.style.display = "none");
    modal.querySelector(".modal-backdrop").addEventListener("click", () => modal.style.display = "none");

    submitBtn.addEventListener("click", async () => {
        const file = input.files[0];
        if (!file) return;
        const path = currentPath ? `${currentPath}/${file.name}` : file.name;
        statusEl.textContent = "Uploading...";
        try {
            await uploadFile(path, file);
            modal.style.display = "none";
            input.value = "";
            await loadFiles();
        } catch (error) {
            statusEl.textContent = `Error: ${error.message}`;
        }
    });
}

function openUploadModal() {
    document.getElementById("upload-modal").style.display = "flex";
}

let promptResolve = null;

function setupPromptModal() {
    const modal = document.getElementById("prompt-modal");
    document.getElementById("prompt-close").addEventListener("click", () => closePrompt(null));
    document.getElementById("prompt-cancel").addEventListener("click", () => closePrompt(null));
    document.getElementById("prompt-ok").addEventListener("click", () => {
        const value = document.getElementById("prompt-input").value.trim();
        closePrompt(value);
    });
    modal.querySelector(".modal-backdrop").addEventListener("click", () => closePrompt(null));
    document.getElementById("prompt-input").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const value = e.target.value.trim();
            closePrompt(value);
        } else if (e.key === "Escape") {
            closePrompt(null);
        }
    });
}

function closePrompt(value) {
    document.getElementById("prompt-modal").style.display = "none";
    if (promptResolve) {
        promptResolve(value);
        promptResolve = null;
    }
}

function promptDialog(title, message, defaultValue = "") {
    return new Promise((resolve) => {
        promptResolve = resolve;
        document.getElementById("prompt-title").textContent = title;
        document.getElementById("prompt-message").textContent = message;
        const input = document.getElementById("prompt-input");
        input.value = defaultValue;
        document.getElementById("prompt-modal").style.display = "flex";
        setTimeout(() => input.focus(), 50);
    });
}

let confirmResolve = null;

function setupConfirmModal() {
    const modal = document.getElementById("confirm-modal");
    document.getElementById("confirm-close").addEventListener("click", () => closeConfirm(false));
    document.getElementById("confirm-cancel").addEventListener("click", () => closeConfirm(false));
    document.getElementById("confirm-ok").addEventListener("click", () => closeConfirm(true));
    modal.querySelector(".modal-backdrop").addEventListener("click", () => closeConfirm(false));
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

let contextEntry = null;

function setupContextMenu() {
    const menu = document.getElementById("context-menu");
    menu.querySelectorAll("button[data-action]").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const action = btn.dataset.action;
            const entry = contextEntry;
            hideContextMenu();
            if (!entry) return;
            if (action === "open" || action === "edit") handleEntryClick(entry);
            else if (action === "download") downloadFile(entry.path);
            else if (action === "extract") promptExtract(entry);
            else if (action === "compress") promptCompress(entry);
            else if (action === "copy") promptCopy(entry);
            else if (action === "move") promptMove(entry);
            else if (action === "rename") promptRename(entry);
            else if (action === "delete") promptDelete(entry);
        });
    });
}

function isArchiveName(name) {
    return /\.(zip|tar|tar\.gz|tgz)$/i.test(name || "");
}

async function promptExtract(entry) {
    const confirmed = await confirmDialog(
        "Extract Archive",
        `Extract "${entry.name}" into a new folder here?`
    );
    if (!confirmed) return;
    try {
        const result = await extractFile(entry.path);
        await loadFiles();
        const dest = result.message.replace(/^Extracted to /, "");
        if (dest) {
            currentPath = dest;
            searchQuery = "";
            document.getElementById("file-search").value = "";
            loadFiles();
        }
    } catch (error) {
        alert(`Failed to extract: ${error.message}`);
    }
}

async function promptCompress(entry) {
    const suggested = entry.type === "directory" ? `${entry.name}.tar.gz` : `${entry.name}.tar.gz`;
    let name = await promptDialog("Compress", "Archive name (.tar.gz, .tgz, or .zip):", suggested);
    if (!name) return;
    name = name.trim();
    if (!/\.(zip|tar\.gz|tgz)$/i.test(name)) name = `${name}.tar.gz`;
    try {
        await createArchive([entry.path], name);
        await loadFiles();
    } catch (error) {
        alert(`Failed to create archive: ${error.message}`);
    }
}

function showContextMenu(event, entry) {
    contextEntry = entry;
    const menu = document.getElementById("context-menu");
    const isFile = entry.type === "file";
    menu.querySelector('[data-action="edit"]').style.display = isFile ? "block" : "none";
    menu.querySelector('[data-action="download"]').style.display = isFile ? "block" : "none";
    menu.querySelector('[data-action="extract"]').style.display = isFile && isArchiveName(entry.name) ? "block" : "none";
    menu.querySelector('[data-action="compress"]').style.display = entry.path ? "block" : "none";

    menu.style.display = "block";
    const x = Math.min(event.pageX, window.innerWidth - menu.offsetWidth - 8);
    const y = Math.min(event.pageY, window.innerHeight - menu.offsetHeight - 8);
    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;
}

function hideContextMenu() {
    document.getElementById("context-menu").style.display = "none";
    contextEntry = null;
}

function downloadFile(path) {
    window.location.href = `/api/v1/files/download?path=${encodeURIComponent(path)}`;
}

function formatDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString();
}

initFiles();
