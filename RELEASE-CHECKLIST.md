# First Public Release Checklist

Work through every item before making the repository public. Do not perform the release itself from this list — this is the review gate.

## 1. Git history

- [ ] Decide on history strategy. The current history is private and contains:
  - a personal author email on most commits,
  - `AGENTS.md` (private working notes) in every commit,
  - a screenshot containing a private LAN IP (`NexusIOS/screenshot2.png`),
  - personal usernames/domains/IPs in older versions of `README.md`, `systemd/*`, `.env.example`, iOS defaults, and backend tests.
- [ ] Recommended: publish a **fresh orphan branch** (single initial commit of the sanitized tree) or run `git filter-repo` to strip `AGENTS.md`, `NexusIOS/screenshot2.png`, and rewrite the author identity. Deleting files in the working tree does NOT remove them from history.
- [ ] Delete or ignore the stale `origin/ios-redesign-wip` ref (it points into main history; a fresh push of a new history makes it irrelevant).
- [ ] After any history rewrite: re-clone fresh, re-run the full scans below on the rewritten history (`git grep` across all commits), and force-push only after verification.
- [ ] Remove the private remote before public push if you keep the old history in the private repo.

## 2. Secrets

- [ ] `grep`-based secret scan across the tree AND all history (API keys, tokens, private keys, `.env` files, keystores, signing material). Current status: clean — no secrets were ever committed.
- [ ] Confirm `.env` is gitignored and `backend/.env.example` contains only placeholders.
- [ ] Confirm no real signing credentials exist for the iOS app (the project builds unsigned only; keep it that way unless a distribution plan adds managed signing).

## 3. Personal data

- [ ] Repo-wide scan for: personal usernames, hostnames, `/home/<user>` paths, private IPs (RFC1918), personal domains, SSH details, machine names. Current status: sanitized in the working tree; **history still contains them** (see §1).
- [ ] Screenshots/documentation show only example values (`192.0.2.x`, `example.com`).

## 4. AI / development remnants

- [ ] Scan for AI tooling state (`.opencode/`, `.claude/`, session logs, prompt files) — none exist in the repo; keep it that way and rely on `.gitignore` entries.
- [ ] `AGENTS.md` stays **private** (it is excluded from this tree; do not copy it into the public repo).

## 5. Dependencies and licenses

- [ ] `backend/requirements.txt` (runtime) and `requirements-dev.txt` reviewed; unused deps removed.
- [ ] THIRD-PARTY-NOTICES.md matches actual dependency versions (update the table when bumping xterm/Chart.js/FastAPI).
- [ ] LICENSE = AGPL-3.0 verbatim; README/CONTRIBUTING reference it.

## 6. Build and test verification

- [ ] Fresh clone: `python3 -m venv`, `pip install -r requirements-dev.txt`, `pytest -q` — all green.
- [ ] `uvicorn app.main:app` boots against a scratch `NEXUS_DATABASE_URL`; login works.
- [ ] Frontend loads on a clean browser profile (no console errors); terminal page works with cookies.
- [ ] iOS: `xcodegen generate` regenerates the project cleanly; CI IPA build is green; artifact sideloads via Xcode/AltStore.
- [ ] CI workflow (`.github/workflows/ipa.yml`) uses only public infrastructure.

## 7. Security review

- [ ] Re-read `SECURITY.md` claims against the code (admin gating, rate limits, file sandbox).
- [ ] Sudoers example matches the actual commands the code invokes; validate with `visudo -cf`.
- [ ] Confirm no debug endpoints, no permissive CORS, production mode disables API docs.
- [ ] Enable GitHub secret scanning + push protection on the public repo.

## 8. Final manual review

- [ ] `git status` clean; nothing untracked that should be committed; nothing tracked that should not be.
- [ ] Browse every file in the final tree once, personally.
- [ ] Repo description, topics, and About text set on GitHub.
