# Security Policy

Nexus Panel is a privileged server administration panel: it holds sudo powers on the machine it manages. We treat security reports with corresponding seriousness.

## Supported versions

| Version | Supported |
|---------|-----------|
| latest `main` | yes |
| older tags/commits | no |

Please update to the latest `main` before reporting — most fixes land quickly.

## Reporting a vulnerability

**Do not open a public GitHub issue for security problems.**

Use GitHub's private vulnerability reporting: on the repository page, go to **Security → Report a vulnerability** (or "Private vulnerability reporting" under the Security tab). This reaches the maintainers privately and creates a tracked advisory draft.

Please include:

- What component is affected (backend route/service, frontend page, iOS client, systemd/sudoers example).
- Steps or a proof of concept to reproduce.
- The impact you believe is achievable, and any preconditions (e.g. requires a logged-in non-admin user).
- Your environment (OS, Python version) if relevant.

## What NOT to disclose publicly

- Details of unpatched vulnerabilities.
- Any deployment's real hostnames, IPs, credentials, or configuration secrets.
- Exploit code targeting default deployments.

We will credit reporters in the advisory unless you prefer to remain anonymous.

## Deployment security expectations

Nexus Panel is *designed* to hold significant power over its host. Operators should understand the following model:

- The service user holds passwordless sudo for a **fixed allowlist** of commands (`systemctl` actions, `smartctl`, apt/dnf update commands, `bash -l`, the file-worker helper, and user-management commands). That sudoers file is the effective security boundary — review it, keep it exact, and validate it with `visudo -cf` after every edit.
- Anyone who can authenticate as a UNIX account in the `sudo`/`wheel` group (or who can prove such an account's password) effectively controls the machine through the panel. Only expose the panel to networks/users you trust.
- UNIX users with ordinary (non-sudo) accounts can log in, browse files within their own permissions, and open terminal sessions as themselves. Set `NEXUS_TERMINAL_ENABLED=false` and/or `require_admin_for_terminal` / `require_admin_for_files_writes` in settings if you want a more restricted panel.
- The first-run setup endpoint (`POST /api/v1/auth/setup`) can create a break-glass local admin **only while no users exist**. On a fresh install, the first person to reach it wins — install and configure promptly, or pre-create the user with `create_user.py` before exposing the service.
- Login rate limiting is per-process and in-memory; run a single uvicorn worker (the default in the provided service file) so limits are effective.
- Serve the panel behind TLS. The session cookie is marked `Secure` automatically when the request arrives over HTTPS.
- The bundled sudoers examples intentionally allow `bash -l` so the terminal can operate as the logged-in user. If you do not need the terminal, remove `NEXUS_TERMINAL_SUDO`/`NEXUS_BASH` from your sudoers and set `NEXUS_TERMINAL_ENABLED=false`.

## Known design trade-offs

- WebSocket endpoints accept the session token as a query parameter (needed by native clients that cannot attach cookies). Tokens in URLs can appear in proxy logs — prefer TLS-terminating proxies you control, and prefer cookie auth for browsers.
- The health WebSocket validates the session at connect time; long-lived streams are not re-validated mid-stream.
- Process listing is visible to any authenticated user (like a shared `ps`); killing is restricted to the panel service user's own processes and requires admin.
