"use strict";

async function initTerminal() {
    await initLayout("/terminal");

    const statusEl = document.getElementById("terminal-status");
    const terminalEl = document.getElementById("terminal");

    const term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        theme: {
            background: '#000000',
            foreground: '#e8e9ed',
        },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalEl);
    fitAddon.fit();

    let socket = null;
    let reconnectDelay = 1000;
    const maxReconnectDelay = 30000;

    function connect() {
        const wsUrl = getWebSocketUrl("/api/v1/terminal/ws");
        socket = new WebSocket(wsUrl);

        socket.addEventListener("open", () => {
            statusEl.textContent = "Connected";
            statusEl.style.color = "var(--success)";
            reconnectDelay = 1000;

            const dims = fitAddon.proposeDimensions();
            socket.send(JSON.stringify({
                type: "resize",
                rows: dims.rows,
                cols: dims.cols,
            }));
        });

        socket.addEventListener("message", (event) => {
            term.write(event.data);
        });

        socket.addEventListener("close", () => {
            statusEl.textContent = "Disconnected";
            statusEl.style.color = "var(--danger)";
            term.writeln("\r\nConnection closed. Reconnecting...");
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
        });

        socket.addEventListener("error", () => {
            statusEl.textContent = "Connection error";
            statusEl.style.color = "var(--danger)";
        });
    }

    connect();

    term.onData((data) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "input", data }));
        }
    });

    let resizeTimeout;
    window.addEventListener("resize", () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            fitAddon.fit();
            const dims = fitAddon.proposeDimensions();
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: "resize",
                    rows: dims.rows,
                    cols: dims.cols,
                }));
            }
        }, 100);
    });
}

initTerminal();
