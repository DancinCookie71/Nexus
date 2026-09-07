# Third-Party Notices

Nexus Panel is licensed under the GNU AGPL-3.0 (see [LICENSE](LICENSE)). The following third-party components are used and remain under their own licenses.

## Backend (Python, via `backend/requirements.txt`)

| Package | License |
|---------|---------|
| FastAPI | MIT |
| Uvicorn | BSD-3-Clause |
| Pydantic / pydantic-settings | MIT |
| SQLAlchemy | MIT |
| argon2-cffi | MIT (bundled argon2: CC0 1.0 / Apache-2.0 dual) |
| psutil | BSD-3-Clause |
| python-multipart | Apache-2.0 |

## Frontend (loaded from CDN at runtime)

| Library | Version | License | Used by |
|---------|---------|---------|---------|
| xterm.js | 5.3.0 | MIT | `frontend/terminal.html` |
| xterm-addon-fit | 0.8.0 | MIT | `frontend/terminal.html` |
| Chart.js | 4.4.3 | MIT | `frontend/health.html` |

All are served with subresource-integrity hashes pinned to the exact versions above.

## iOS app (`NexusIOS/`)

- No third-party Swift package dependencies.
- All bundled assets (including the `os-logo` server icon) are original to this project.

## Example assets

- The code of conduct is the Contributor Covenant v2.1 (CC BY 4.0).
- The license text is the GNU Affero General Public License v3.0 (copyright the Free Software Foundation).
