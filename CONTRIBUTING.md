# Contributing to Nexus Panel

Thank you for considering a contribution! Nexus Panel is an AGPL-3.0 licensed, self-hosted server administration panel, and all contributions are welcome under the same license.

## Getting started

1. Fork the repository and clone your fork:

   ```bash
   git clone https://github.com/<you>/nexus-panel.git
   cd nexus-panel
   ```

2. Install development prerequisites:

   - Linux with systemd and Python 3.11+
   - `python3 -m venv backend/.venv`
   - `pip install -r backend/requirements-dev.txt` (this includes the runtime requirements)

3. Run the backend locally:

   ```bash
   cd backend
   source .venv/bin/activate
   cp .env.example .env   # then set NEXUS_SECRET_KEY
   uvicorn app.main:app --reload
   ```

   Interactive API docs are available at `/api/docs` in development mode.

4. Run the tests before you start changing things, so you know your baseline:

   ```bash
   cd backend
   .venv/bin/pytest -q
   ```

## Project layout

| Path | What lives there |
|------|------------------|
| `backend/app/routes/` | FastAPI route modules — one file per feature area |
| `backend/app/services/` | Business logic that touches the system (systemd, files, updates, ...) |
| `backend/app/schemas/` | Pydantic request/response models |
| `backend/tests/` | pytest suite (TestClient-based, fully hermetic — no real system calls in CI) |
| `frontend/` | Static web UI: one HTML page per screen, a JS module per page, shared `api.js`/`auth.js` |
| `NexusIOS/` | SwiftUI iOS client (XcodeGen project) |
| `systemd/` | Example service unit, sudoers, and polkit rules |

## Where to add features

- **A new API feature:** add a route module in `backend/app/routes/`, a schema module in `backend/app/schemas/`, and the system-touching logic in `backend/app/services/`. Wire the router into `app/main.py`. Anything requiring elevated privileges must depend on `require_admin` and use the existing list-form `subprocess` helpers — never a shell string.
- **A new web page:** add `frontend/<page>.html`, `frontend/js/<page>.js`, and a `FileResponse` route in `app/main.py`. Reuse `api.js` helpers and the `escapeHtml` utility for anything rendered from API data.
- **An iOS feature:** add to `NexusIOS/NexusIOS/` and keep the project definition in `project.yml` (run `xcodegen generate` after changing it; commit the regenerated `.xcodeproj`).
- **Settings/flags:** register defaults in `backend/app/services/settings.py::DEFAULT_SETTINGS`.

## Coding conventions

- **Python:** type-annotated, Pydantic-validated inputs, no raw SQL, no shell string interpolation, docstrings on public functions.
- **Security-sensitive code** (anything that runs subprocesses, touches files, or changes privileges) must be covered by tests, including rejection paths.
- **JavaScript:** plain ES modules loaded per page; escape all API-derived content before inserting into HTML.
- **Swift:** SwiftUI, no third-party dependencies unless discussed first.

## Tests

The backend test suite is hermetic: system interactions are mocked, so it runs on any Linux (and mostly on macOS). If your change touches `services/`, add or extend tests in `backend/tests/`. Run:

```bash
cd backend && .venv/bin/pytest -q
```

## Commit and pull request expectations

- Short, imperative commit messages (e.g. `Add rate limit to files search`).
- One logical change per pull request; include the reasoning in the description.
- Ensure `pytest -q` passes and mention any manual testing you did.
- Do not include personal data (usernames, hostnames, IPs, domains) in commits, screenshots, or sample configs — use the documented example placeholders (`192.0.2.x`, `example.com`, `youruser`).

## Reporting issues

For bugs and feature requests, open a GitHub issue. For security vulnerabilities, **do not** open a public issue — see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the GNU AGPL-3.0 (see [LICENSE](LICENSE)).
