# Radio Calico - Claude Code Guidelines

> Detailed rules are in `.claude/rules/`: `architecture.md`, `testing.md`, `database.md`, `style-guide.md`.

## Project Overview

Radio Calico is a live audio streaming web player with a Flask backend for ratings, user accounts, and feedback. Streams HLS audio from CloudFront (FLAC lossless or AAC Hi-Fi), displays track metadata, fetches artwork from iTunes, and lets users rate tracks, manage profiles, and submit feedback — all stored in MySQL.

## Architecture

- **Frontend**: Vanilla JS + HTML5 + CSS (no framework). Single-page app from `static/`.
- **Backend**: Python Flask API (`api/app.py`) on port 5000. MySQL 5.7 (local) or 8.0 (Docker).
- **Streaming**: HLS via CloudFront CDN, decoded by HLS.js (non-Safari) or native (Safari).
- **Metadata**: CloudFront `metadatav2.json` (not ID3 tags). Current track + 5 previous.
- **Artwork**: iTunes Search API (client-side, cached in localStorage 24h TTL).
- **Auth**: Token-based. PBKDF2 (260k iterations). Tokens in `localStorage`.
- **Logging**: Structured JSON — Python (`python-json-logger`), nginx, JS (`log.info/warn/error`). X-Request-ID correlation.
- **Testing**: 401 tests (61 unit + 19 integration + 162 JS + 19 E2E + 140 skills). See `.claude/rules/testing.md`.
- **CI/CD**: GitHub Actions (12 jobs). Linting: Ruff, ESLint, Stylelint, HTMLHint.
- **Performance**: WebP images, dns-prefetch, iTunes cache, API pagination.

## Key URLs & Endpoints

### External

- **HLS Stream**: `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8`
- **Metadata JSON**: `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` (root, NOT `/hls/`)
- **iTunes Search**: `https://itunes.apple.com/search?term=...&entity=song&limit=1`

### Local API (Flask :5000, Docker :5050)

**Ratings** (no auth):
- `GET /api/ratings` — paginated list (`?limit=100&offset=0`, max 500). No IPs exposed.
- `GET /api/ratings/summary` — likes/dislikes by station
- `GET /api/ratings/check?station=...` — check if current IP rated
- `POST /api/ratings` — submit `{ station, score }` (score 0 or 1, 409 on duplicate)

**Auth**:
- `POST /api/register` — `{ username, password }` (8-128 chars, rate-limited 5/min)
- `POST /api/login` — `{ username, password }` → `{ token, username }` (rate-limited 5/min)
- `POST /api/logout` — invalidate token (requires Bearer token)

**Profile** (requires Bearer token):
- `GET /api/profile` — get profile (nickname, email, genres, about)
- `PUT /api/profile` — update profile

**Feedback** (requires Bearer token):
- `POST /api/feedback` — submit `{ message }` (stores with profile snapshot)

**Health** (nginx only): `GET /health` → `200 "ok"`

**IMPORTANT**: All API routes use the `/api` prefix.

## Common Tasks

```bash
# Local dev
cd api && source venv/bin/activate && python app.py  # http://127.0.0.1:5000
brew services start mysql@5.7

# Docker
make docker-dev    # Dev: Flask + hot reload + MySQL → http://127.0.0.1:5050
make docker-prod   # Prod: gunicorn + nginx + MySQL
make docker-down   # Stop and remove volumes

# Testing & CI
make test          # All unit tests: Python (61) + JS (162)
make lint          # All linters (Ruff + ESLint + Stylelint + HTMLHint)
make ci            # Full pipeline: lint + coverage + security
make test-integration  # 19 API integration tests
make test-e2e          # 19 E2E tests (Docker prod required)
make test-skills       # 140 skill validation tests

# Hard refresh after static file edits: Cmd+Shift+R
```

## Important Notes

- **Metadata from CloudFront JSON**, not ID3 tags. ID3 parser is fallback only.
- **DB credentials from env vars** via python-dotenv (`api/.env.example`).
- **Debug mode off by default**, controlled by `FLASK_DEBUG`.
- **Run `make ci` before merging**. CI runs on push/PR (12 GitHub Actions jobs).
- **iTunes API cached** in localStorage (24h TTL) via `fetchItunesCached()`.
- **Ratings are local only** — not sent to CloudFront host.
- **Cache issues** — hard refresh (`Cmd+Shift+R`) after editing static files.
- **Port 5000** (local) or **5050** (Docker). Do NOT use port 8080.
- **Docker** uses MySQL 8.0, non-root `appuser`, nginx → gunicorn (4 workers).

## Known Gotchas

1. **`/ratings/summary` 404**: Cached old JS. Hard refresh.
2. **Port 8080**: Old static server running. Kill it, use Flask on 5000/5050.
3. **Metadata 404**: Root `/metadatav2.json`, NOT `/hls/`.
4. **`audio.currentTime` wrong**: Use `Date.now() - songStartTime` instead.
5. **Metadata updates too early**: `pendingTrackUpdate` delay compensates. Do NOT remove.
6. **Shazam URLs don't work**: Use Spotify/YT Music/Amazon instead.
7. **Emoji in URL encoding**: Use plain text `[N likes / N unlikes]`.
8. **mailto: in `window.open`**: Use `window.location.href` instead.

## Slash Commands (18 total, all v1.0.0)

| Command | Purpose |
|---------|---------|
| `/start` | Launch dev environment |
| `/check-stream` | Check stream & server status |
| `/troubleshoot` | Diagnose common issues |
| `/test-ratings` | Test ratings API end-to-end |
| `/run-ci` | Run full CI pipeline |
| `/create-pr` | Branch, commit, push, create PR |
| `/docker-verify` | Rebuild + verify Docker prod stack |
| `/add-endpoint` | Scaffold new API route + tests |
| `/security-audit` | Run all 6 security tools |
| `/generate-diagrams` | Mermaid architecture diagrams |
| `/generate-tech-spec` | Full technical specification |
| `/generate-requirements` | Requirements documentation (FR/NFR) |
| `/generate-vv-plan` | V&V test plan with user test cases |
| `/update-readme-diagrams` | Sync diagrams to README |
| `/test-browser` | Run 37 Selenium browser tests (headless Chrome) |
| `/add-share-button` | Add new share platform |
| `/add-dark-style` | Add dark mode for new components |
| `/update-claude-md` | Refresh CLAUDE.md from codebase |

## Claude Code Configuration

- **Rules**: `.claude/rules/` — architecture, testing, database, style-guide (loaded on relevant topics)
- **Settings**: `.claude/settings.json` — auto-approved commands, denied destructive ops, lint hooks
- **Skills**: `.claude/skills/*/SKILL.md` — mirrored from commands for extended skill features
- **Hooks**: auto-lint Python/JS on file edit, context reminder on compaction
- **Ignore**: `.claudeignore` — excludes node_modules, venv, coverage, caches from context
