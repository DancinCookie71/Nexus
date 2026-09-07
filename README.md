# Nexus Panel

A self-hosted server administration panel for Linux — a lightweight, privacy-friendly alternative to Cockpit and Webmin, with a web interface and a native iOS client.

Nexus Panel manages a single server over an authenticated web UI and REST/WebSocket API: live health metrics, systemd services, processes, local user accounts, package updates, a file manager with a sandboxed editor, drive health (SMART), and an interactive web terminal. It is designed to run on small hardware (a Raspberry Pi handles it comfortably) and to operate through your existing UNIX accounts rather than a parallel user database.

## Features

- **System overview** — CPU, memory, load, disk, temperature, uptime, and network throughput with live sparklines and a 2-second WebSocket stream.
- **Health page** — per-disk SMART status and temperatures, filesystem error scan, network interface diagnostics, GPU/sensor readings, and a reboot-required banner.
- **Services** — list, inspect, start/stop/restart/reload/enable/disable systemd services, restricted to a configurable allowlist, with an audit log.
- **Processes** — live process table with CPU/memory detail; the panel can signal only its own service user's processes.
- **Users** — Cockpit-style local UNIX account management: create users, set passwords, grant/revoke sudo-group membership, delete accounts (admin only).
- **Files** — a browser file manager scoped to a sandbox root: browse, search, upload/download, edit text files, copy/move/rename/delete, and traversal-safe archive extract/compress (tar/tar.gz/tgz/zip).
- **Updates** — detect and apply apt or dnf package updates (admin only), with reboot scheduling.
- **Terminal** — an interactive PTY terminal over WebSocket (xterm.js), running as the logged-in UNIX user. Can be disabled or admin-gated.
- **Storage** — physical drive discovery and SMART attribute analysis.
- **Settings** — persisted feature flags and options with an admin-gated editor.
- **iOS app** — a native SwiftUI client (`NexusIOS/`) that speaks the same API, including the terminal and admin mode.

## Platform support

- **Server:** Linux with systemd. Tested on Debian/Raspberry Pi OS; apt and dnf are supported for the updates feature.
- **Web UI:** any modern browser (vanilla HTML/CSS/JS; xterm.js and Chart.js are the only frontend libraries).
- **Mobile:** iOS 16+ via the SwiftUI client. No Android client exists yet.

## Architecture

```text
 ┌───────────────┐        ┌──────────────────┐
 │  Web browser  │        │  iOS app (Swift) │
 └───────┬───────┘        └────────┬─────────┘
         │  HTTP/WS (cookie)       │  HTTP/WS (bearer)
         ▼                         ▼
 ┌─────────────────────────────────────────┐
 │        Nexus API — FastAPI/uvicorn      │
 │  sessions · auth · feature routes       │
 └───────┬──────────────┬──────────────────┘
         │              │
         ▼              ▼
     SQLite DB     Linux system
  (users, tokens,  systemctl · journalctl · smartctl ·
   settings,       apt/dnf · psutil · file ops
   audit log)
```

- **Backend** (`backend/`): Python 3.11+, FastAPI, SQLAlchemy + SQLite, Pydantic-validated inputs, Argon2id hashing.
- **Frontend** (`frontend/`): server-served static HTML/CSS/JS, no build step.
- **iOS** (`NexusIOS/`): SwiftUI app defined by an XcodeGen `project.yml`.

Both clients consume the same `/api/v1/` endpoints.

## Authentication model

Nexus Panel uses your machine's existing UNIX accounts — there is no parallel password database to leak.

- Login verifies the account against the local system via `su(1)`; nothing about the password is stored. Only "real" human accounts can log in (UID >= 1000 with a login shell; `root`, `nexus`, `admin`, and system accounts can never log in).
- Panel users are provisioned automatically on first login (`auth_source="unix"`).
- Sessions are 32-byte random tokens; only a SHA-256 hash is stored. Clients authenticate with `Authorization: Bearer <token>` (iOS) or an `HttpOnly` `nexus_session` cookie (web).
- UNIX users in the `sudo` or `wheel` group are treated as admins automatically (Cockpit-style). Any user can also unlock **admin mode** explicitly by proving a sudo account's password; privileged operations then run as that account. Local (break-glass) Argon2id panel users can be created via `create_user.py` or the first-run setup endpoint.
- Privileged actions (updates, storage detail, logs, service actions, user management, process kill) require admin mode. The file manager normally operates as your own account; admin mode lets you browse as the elevated account, subject to that account's file permissions.
- Login and admin-elevation attempts are rate-limited (5 failures per 5 minutes).
- The interactive terminal is enabled by default and runs `sudo -u <you> bash -l` under the hood; it can be disabled (`NEXUS_TERMINAL_ENABLED=false`) or restricted to admin mode in settings.

## Installation

### Requirements

- Linux with systemd, Python 3.11+, and `python3-venv`
- Optional: `smartmontools` (drive health), `policykit-1` (only if you use the optional polkit rule)

### 1. Get the code

```bash
sudo git clone https://github.com/<your-org>/nexus-panel.git /opt/nexus-panel
cd /opt/nexus-panel/backend
```

### 2. Configure

```bash
cp .env.example .env
# Set a strong secret:
openssl rand -hex 32
nano .env
```

### 3. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Create the service user and privileges

The recommended deployment runs the panel as a dedicated unprivileged user (example: `nexus`) with a narrowly-scoped sudoers file. Example files are provided:

```bash
sudo useradd -r -m -d /home/nexus -s /usr/sbin/nologin nexus
# Review and edit the aliases (paths, service user name) first:
sudo visudo -cf systemd/99-nexus-panel-nexus
sudo install -m 440 -o root -g root systemd/99-nexus-panel-nexus /etc/sudoers.d/99-nexus-panel-nexus
sudo install -m 440 -o root -g root systemd/99-nexus-panel-smartctl /etc/sudoers.d/99-nexus-panel-smartctl
```

The sudoers aliases authorize exactly the commands the panel invokes: scoped `systemctl` actions, `smartctl` reads, apt/dnf update commands, `bash -l` for the terminal, the file-worker helper script, and user-management commands. Nothing else.

### 5. Run as a systemd service

```bash
sudo cp ../systemd/nexus-panel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nexus-panel.service
```

Then visit `http://<server-ip>:8000` and log in with a UNIX account. The first login for any endpoint is created automatically; alternatively create a local break-glass admin first:

```bash
python create_user.py --username admin
```

### Reverse proxy (recommended)

Put nginx (or any TLS-terminating proxy) in front and serve only HTTPS publicly. The included unit already passes `--proxy-headers` trusting only localhost proxies, so client IPs and `Secure` cookies are handled correctly. Set `NEXUS_CORS_ORIGINS` to the origin users browse.

## Configuration

All settings are environment variables (prefix `NEXUS_`); see [backend/.env.example](backend/.env.example) for the full annotated list. Notable ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXUS_SECRET_KEY` | *(required)* | Session/token signing secret |
| `NEXUS_ENV` | `development` | `production` disables API docs and leaks |
| `NEXUS_SERVICE_ALLOWLIST` | `nginx,postgresql` | Manageable systemd services |
| `NEXUS_TERMINAL_ENABLED` | `true` | Interactive terminal on/off |
| `NEXUS_FILES_ROOT` | `/home/nexus` | File manager sandbox root |
| `NEXUS_CORS_ORIGINS` | `http://localhost:8000` | Allowed browser origins |

Runtime feature flags (admin-editable in the Settings page) include `require_admin_for_terminal`, `require_admin_for_files_writes`, and the service allowlist.

## Updating

Pull the latest code, restart the service:

```bash
cd /opt/nexus-panel
sudo -u nexus git pull
sudo systemctl restart nexus-panel
```

The panel can also apply OS package updates itself (Updates page, admin only).

## Development

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q              # full test suite
uvicorn app.main:app --reload   # run locally with hot reload
```

Interactive API docs at `/api/docs` when `NEXUS_ENV=development`.

### iOS app

```bash
cd NexusIOS
brew install xcodegen
xcodegen generate
open NexusIOS.xcodeproj   # build/run from Xcode on a Mac
```

CI builds unsigned IPAs on every push touching `NexusIOS/` (see `.github/workflows/ipa.yml`). Unsigned IPAs require sideloading (e.g. AltStore, Xcode) — they cannot be installed directly from a download like a signed App Store build.

## Security

- All privileged endpoints are admin-gated; the file manager enforces path containment and blocks archive traversal.
- Subprocess calls never use a shell and never interpolate user input; usernames, service names, and device paths are regex-validated.
- Passwords/tokens are never logged; the API returns generic errors in production.
- See [SECURITY.md](SECURITY.md) to report vulnerabilities, and it plus the deployment notes in this README for hardening recommendations.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Development happens on GitHub; pull requests are welcome.

## License

Nexus Panel is free software: licensed under the [GNU AGPL-3.0](LICENSE). Third-party components are covered by their own licenses — see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
