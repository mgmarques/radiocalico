# Radio Calico - Claude Code Guidelines

## Project Overview

Radio Calico is a live audio streaming web player with a Flask backend for ratings, user accounts, and feedback. It streams audio via HLS from AWS CloudFront (48kHz FLAC lossless or AAC Hi-Fi 211 kbps, user-selectable), displays track metadata from a CloudFront JSON endpoint, fetches album artwork and duration from iTunes, and lets users rate tracks, manage profiles, and submit feedback (all stored locally in MySQL).

## Architecture

- **Frontend**: Vanilla JavaScript + HTML5 + CSS (no framework). Single-page app served from `static/`.
- **Backend**: Python Flask API (`api/app.py`) on port 5000 with MySQL 5.7 (local/Homebrew) or MySQL 8.0 (Docker) for data storage.
- **Streaming**: HLS via CloudFront CDN, decoded by HLS.js (non-Safari) or native (Safari).
- **Metadata**: Fetched from CloudFront `metadatav2.json` (not ID3 tags). Provides current track + 5 previous tracks.
- **Artwork & Duration**: iTunes Search API (client-side). `trackTimeMillis` used for duration display.
- **Ratings**: Stored in local MySQL only. CloudFront host does NOT accept ratings.
- **Auth**: Token-based authentication. Passwords hashed with PBKDF2 (260k iterations) + random salt. Timing-safe comparison via hmac.compare_digest. Tokens stored in `localStorage`.
- **Logging**: Structured JSON logs across all layers. Python: `python-json-logger` with request_id, method, path, status, duration_ms. nginx: JSON access log format with upstream timing. JS: `log.info/warn/error()` outputs JSON to browser console. X-Request-ID header for cross-layer correlation.
- **Testing**: Python: pytest + pytest-cov (98% coverage). JS: Jest + jsdom (162 tests, 90% line threshold, ~96% actual). Integration: 19 multi-step API workflow tests. E2E: 19 tests against Docker prod stack. Security: bandit (SAST) + safety (deps) + npm audit + hadolint (Dockerfile) + trivy (image scan) + OWASP ZAP (DAST). CI: GitHub Actions (11 jobs) on push/PR.
- **Linting**: Ruff (Python lint + format), ESLint (JS), Stylelint (CSS), HTMLHint (HTML). Run `make lint` before committing.
- **Performance**: WebP images (logo 50% smaller), dns-prefetch for CDN/API domains, iTunes API cached in localStorage (24h TTL), API pagination on ratings endpoint.

## File Tree

```text
radiocalico/
├── CLAUDE.md                       # Claude Code guidelines (this file)
├── Makefile                        # CI/CD automation (local + Docker)
├── Dockerfile                      # Multi-stage: dev (Flask) + prod (gunicorn)
├── docker-compose.yml              # Dev/prod profiles with MySQL + nginx
├── .dockerignore                   # Docker build exclusions
├── package.json                    # Node.js config (Jest for JS tests)
├── jest.config.js                  # Jest configuration
├── design.md                       # Full architecture and design document
├── RadioCalico_Style_Guide.txt     # Brand colors, typography, component specs
├── RadioCalicoLayout.png           # UI layout reference image
├── RadioCalicoLogoTM.png           # Logo with trademark
├── SomeLikesSogs.txt               # Sample liked songs reference
├── stream_URL.txt                  # Stream URL reference
├── db/
│   └── init.sql                    # Database schema (auto-run by Docker MySQL)
├── nginx/
│   └── nginx.conf                  # Reverse proxy: static files + /api proxy (prod)
├── api/
│   ├── app.py                      # Flask REST API + static file serving
│   ├── .env.example                # Environment variable template
│   ├── requirements.txt            # Python deps (flask, flask-cors, pymysql, python-dotenv, flask-limiter)
│   ├── requirements-dev.txt        # Dev deps (pytest, pytest-cov, bandit, safety, ruff)
│   ├── conftest.py                 # Pytest fixtures (test DB, client, auth)
│   ├── test_app.py                 # 61 unit tests (98% coverage)
│   ├── test_integration.py         # 19 integration tests (multi-step workflows)
│   ├── pytest.ini                  # Pytest configuration
│   ├── .bandit                     # Bandit security scan config
│   └── venv/                       # Python virtual environment
├── static/
│   ├── index.html                  # Main entry point, all UI markup
│   ├── logo.png                    # Radio Calico logo (PNG fallback)
│   ├── logo.webp                   # Radio Calico logo (WebP, 50% smaller)
│   ├── favicon.webp                # Favicon (1.1 KB WebP)
│   ├── css/
│   │   └── player.css              # All styles, responsive layout, design tokens
│   └── js/
│       ├── player.js               # Playback, metadata, artwork, ratings, auth, sharing
│       └── player.test.js          # 162 JavaScript unit tests (Jest + jsdom, 90% line threshold, ~96% actual)
├── tests/
│   ├── conftest.py                 # E2E test fixtures (base_url)
│   └── test_e2e.py                 # 19 E2E tests (nginx → gunicorn → MySQL)
├── pyproject.toml                  # Ruff linter configuration
├── eslint.config.js                # ESLint configuration
├── .stylelintrc.json               # Stylelint configuration
├── .htmlhintrc                     # HTMLHint configuration
├── VERSION                         # Project version (semver)
└── .claude/
    └── commands/                   # Claude Code slash commands (all v1.0.0)
        ├── start.md                # /start — launch dev environment
        ├── check-stream.md         # /check-stream — check stream & server status
        ├── troubleshoot.md         # /troubleshoot — diagnose common issues
        ├── test-ratings.md         # /test-ratings — test ratings API end-to-end
        ├── run-ci.md               # /run-ci — run full CI pipeline
        ├── create-pr.md            # /create-pr — branch, commit, push, create PR
        ├── docker-verify.md        # /docker-verify — rebuild + verify Docker prod stack
        ├── add-endpoint.md         # /add-endpoint — scaffold new API route + tests
        ├── security-audit.md       # /security-audit — run all 6 security tools
        ├── generate-diagrams.md     # /generate-diagrams — Mermaid architecture diagrams
        ├── generate-tech-spec.md   # /generate-tech-spec — full technical specification
        ├── generate-requirements.md # /generate-requirements — requirements documentation (FR/NFR)
        ├── generate-vv-plan.md     # /generate-vv-plan — V&V test plan with user test cases
        ├── update-readme-diagrams.md # /update-readme-diagrams — sync diagrams to README
        ├── add-share-button.md     # /add-share-button — add new share platform
        ├── add-dark-style.md       # /add-dark-style — add dark mode for new components
        └── update-claude-md.md     # /update-claude-md — refresh CLAUDE.md from codebase
```

## Key Files

| File | Purpose |
|------|---------|
| `static/index.html` | Main entry point, all UI markup (player, drawer, forms) |
| `static/js/player.js` | Playback, metadata, artwork, ratings, auth, profile, sharing, feedback |
| `static/css/player.css` | All styles, responsive layout, design tokens, dark/light themes |
| `api/app.py` | Flask REST API: ratings, auth, profile, feedback + static file serving |
| `api/test_app.py` | 61 Python unit tests covering all endpoints (98% coverage) |
| `api/test_integration.py` | 19 integration tests: user lifecycle, ratings, sessions, auth edge cases |
| `static/js/player.test.js` | 162 JavaScript unit tests (Jest + jsdom, 90% line threshold, ~96% actual) |
| `tests/test_e2e.py` | 19 E2E tests: static files, security headers, API proxy, error handling |
| `api/conftest.py` | Pytest fixtures: test DB setup/teardown, client, auth helpers |
| `api/.env.example` | Environment variable template (DB creds, Flask config, CORS) |
| `api/requirements.txt` | Python deps (flask, flask-cors, pymysql, python-dotenv, flask-limiter, python-json-logger) |
| `api/requirements-dev.txt` | Dev deps (pytest, pytest-cov, bandit, safety, ruff) |
| `pyproject.toml` | Ruff linter configuration (Python lint + format) |
| `eslint.config.js` | ESLint configuration (JS lint with browser/HLS.js globals) |
| `.github/workflows/ci.yml` | GitHub Actions CI: 11 jobs (lint, tests, security, E2E, ZAP) |
| `Makefile` | CI/CD targets: test, coverage, security, ci, Docker |
| `Dockerfile` | Multi-stage build: dev (Flask debug) + prod (gunicorn 4 workers) |
| `docker-compose.yml` | Dev/prod profiles with MySQL 8.0 + nginx (prod) |
| `nginx/nginx.conf` | Nginx reverse proxy config: static files + /api proxy |
| `db/init.sql` | Database schema (auto-run on first Docker MySQL startup) |
| `design.md` | Full architecture and design document |
| `RadioCalico_Style_Guide.txt` | Brand colors, typography, component specs |

## Key URLs & Endpoints

### External (read-only)

- **HLS Stream**: `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8`
- **Metadata JSON**: `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` (root path, NOT `/hls/`)
- **iTunes Search API**: `https://itunes.apple.com/search?term=...&entity=song&limit=1`

### Local API (Flask on port 5000)

When running via Docker, access the app at the port configured by `APP_PORT` (default: 5050).

#### Ratings (no auth required)

- `GET /api/ratings` — ratings list with pagination (`?limit=100&offset=0`, max 500). IPs not exposed.
- `GET /api/ratings/summary` — likes/dislikes grouped by station
- `GET /api/ratings/check?station=...` — check if current IP already rated
- `POST /api/ratings` — submit rating `{ station, score }` where score must be 0 or 1 (409 on duplicate)

#### Authentication

- `POST /api/register` — create account `{ username, password }` (409 on duplicate). Password: min 8 chars, max 128 chars. Rate-limited to 5 requests/minute.
- `POST /api/login` — authenticate `{ username, password }` → `{ token, username }`. Rate-limited to 5 requests/minute.
- `POST /api/logout` — invalidate token (requires `Authorization: Bearer <token>`)

#### Profile (requires `Authorization: Bearer <token>`)

- `GET /api/profile` — get user profile (nickname, email, genres, about)
- `PUT /api/profile` — update profile `{ nickname, email, genres, about }`

#### Feedback (requires `Authorization: Bearer <token>`)

- `POST /api/feedback` — submit feedback `{ message }` (stores with user's full profile data)

#### Health (nginx only, not proxied)

- `GET /health` — returns `200 "ok"` (used by Docker health checks and load balancers)

**IMPORTANT**: All API routes use the `/api` prefix. The frontend fetches `/api/ratings/...` — never `/ratings/...` without the prefix.

## Code Conventions

- **No frameworks** — vanilla JS, no build step, no bundler. Keep it simple.
- **CSS custom properties** for all colors: `--mint`, `--forest`, `--teal`, `--orange`, `--charcoal`, `--cream`, `--white`. Dark mode overrides these via `[data-theme="dark"]`.
- **Typography**: Montserrat for headings, Open Sans for body (loaded from Google Fonts).
- **HTML escaping**: Always use `escHtml()` when inserting user/metadata text into DOM via innerHTML.
- **Backend**: Pure Flask with PyMySQL. No ORM. Parameterized queries for SQL.
- **Auth**: Token-based. `localStorage` keys `rc-token` and `rc-user`. `Authorization: Bearer <token>` header.
- **Theme persistence**: `localStorage` key `rc-theme` stores `"light"` or `"dark"`. Default: dark.
- **Stream quality**: `localStorage` key `rc-stream-quality` stores `"flac"` or `"aac"`. Default: flac. Switching forces the HLS level to the matching codec.
- **Share buttons**: Use platform URL schemes (wa.me, x.com/intent, t.me/share/url, open.spotify.com/search, music.youtube.com/search, amazon.com/s with digital-music filter). Facebook removed (sharer doesn't support plain text sharing).
- **Logging**: Python uses `logger.info/warning/error()` with structured JSON (not `print()`). JS uses `log.info/warn/error(message, context)` (not bare `console.warn/error`). Business events should have descriptive names like `user_registered`, `rating_created`.
- **Linting**: `make lint` must pass before committing. Ruff for Python (lint + format), ESLint for JS, Stylelint for CSS, HTMLHint for HTML. `make fix-py` auto-fixes Python issues.
- **Testing**: All new API routes must have corresponding tests in `test_app.py`. New JS functions must be tested in `player.test.js`. Run `make ci` before merging.

## Common Tasks

### Run the backend (serves both API and frontend)

```bash
cd api
source venv/bin/activate
python app.py
# Runs on http://127.0.0.1:5000 — serves BOTH static files and API
```

### Start MySQL

```bash
brew services start mysql@5.7
```

### Access the app

Local dev: `http://127.0.0.1:5000`. Docker: `http://127.0.0.1:5050` (configurable via `APP_PORT`). Do NOT use port 8080 or any other static server — Flask serves everything.

### Hard refresh (clear cached JS/CSS in Chrome)

`Cmd+Shift+R` — required after editing static files since browser may cache aggressively.

### Run tests

```bash
make test      # Run all unit tests: Python (61) + JavaScript (162)
make test-py   # Run Python unit tests only
make test-js   # Run JavaScript unit tests only
make coverage  # Python tests + coverage (fails if <98%)
make coverage-js  # JS tests + coverage (fails if <90% lines)
make lint      # Run all linters (Ruff + ESLint + Stylelint + HTMLHint)
make security  # Bandit SAST + Safety + npm audit
make ci        # Full pipeline: lint + coverage + security
make test-integration  # 19 API integration tests (requires MySQL)
make test-e2e          # 19 E2E tests (requires Docker prod running)
```

### Docker

```bash
make docker-dev    # Dev: Flask debug + hot reload + MySQL
make docker-prod   # Prod: gunicorn (4 workers) + MySQL (detached)
make docker-down   # Stop all containers and remove volumes
make docker-test   # Run all tests inside the dev container
```

### Query feedback

```bash
/opt/homebrew/opt/mysql@5.7/bin/mysql -u root -pradiocalico radiocalico \
  -e "SELECT * FROM feedback ORDER BY created_at DESC;"
```

## Player.js Architecture

### Metadata Lifecycle

- **Not timer-based** — metadata fetches are triggered by HLS.js `FRAG_CHANGED` event
- `triggerMetadataFetch()` debounces calls (3s minimum interval via `METADATA_DEBOUNCE_MS`)
- One initial `fetchMetadata()` at boot so UI shows current track before playing
- Filter buttons and dropdown also trigger `fetchMetadata()` for fresh data

### History Accumulation

- CloudFront JSON only provides 5 previous tracks (`prev_artist_1` through `prev_artist_5`)
- History array accumulates up to 20 entries over time (merges fresh + older, deduped)
- Album names fetched from iTunes API for entries missing album info
- `renderHistory()` slices to `historyLimit` for display (dropdown: 5/10/15/20)

### Time Display

- Uses wall-clock time: `Date.now() - songStartTime` (not `audio.currentTime` which is HLS buffer position)
- Total duration from iTunes `trackTimeMillis`
- Format: `elapsed / total` or `elapsed / Live` if no duration

### Rating System

- IP-based deduplication (server-side unique constraint on `station + ip`)
- `station` key = `"Artist - Title"` string
- Frontend checks `/api/ratings/check` on track change, disables buttons if already rated
- Ratings summary shown as badges in Recently Played list

### Metadata Latency Compensation

- CloudFront metadata JSON updates **before** the HLS stream delivers the new song audio
- `fetchMetadata()` schedules track updates via `setTimeout` using `hls.latency` (fallback 6s)
- `pendingTrackKey` prevents repeated fetches from resetting the timer for the same track
- The delay ensures the UI (artist, title, artwork) changes when the listener actually hears the new song

### Dark/Light Theme

- Settings gear icon in navbar top-right opens a dropdown with Light / Dark (default) theme radio buttons and Stream Quality (FLAC / AAC) radio buttons
- Theme applied via `data-theme="dark"` attribute on `<html>`
- Dark mode overrides CSS custom properties (`--mint`, `--forest`, `--teal`, etc.) and adds `[data-theme="dark"]` selectors
- Navbar and footer text forced to white (`#FFFFFF`) in dark mode (not affected by token overrides)
- User choice persisted in `localStorage` key `rc-theme`

### Hamburger Menu & Side Drawer

- Hamburger icon (top-left navbar) opens a slide-out drawer from the left
- Drawer overlay dims the background; clicking overlay or X button closes drawer
- **Login/Register section**: username + password form. Register creates account, Login returns token.
- **Profile section** (shown when logged in): nickname, email, 16 music genre tags (checkboxes), "About You" textarea
- **Feedback section** (shown when logged in): message textarea + envelope icon (saves to DB with full profile), X/Twitter button, Telegram button
- Auth state stored in `localStorage`: `rc-token`, `rc-user`

### Social Share & Music Search Buttons

- **Now Playing share row**: circular icon buttons below the rating row
  - **Social sharing** (WhatsApp, X/Twitter, Telegram): opens share intent with track text via `getShareText()`
  - Share text format: `Listening to "Title" by Artist (Album) on Radio Calico!` followed by `Album cover: {artwork_url}` (300x300 iTunes image)
  - **Music search** (Spotify, YouTube Music, Amazon Music): opens search with `artist + title` query
- **Recently Played share row**: WhatsApp, X/Twitter buttons at the bottom of the widget
  - `getRecentlyPlayedText()` builds a numbered list from the currently filtered/displayed tracks
  - Format: `"N. Title by Artist (Album) [N likes / N unlikes]"`
  - Respects the active filter (All/Liked/Disliked) and track limit dropdown
  - Ratings shown as plain text `[N likes / N unlikes]` (emoji don't survive URL encoding on some platforms)
- All links open in new tab via `window.open(..., '_blank', 'noopener')`

### Sticky Navbar & Footer

- Navbar (`position: sticky; top: 0`) stays fixed at top when scrolling
- Footer bar (`position: sticky; bottom: 0`) stays fixed at bottom, same teal background as navbar
- Footer text: study case attribution in small font (0.6rem)

### Global Scale

- `html { zoom: 0.85; }` scales all UI to 85%
- Main content top padding reduced to 5px (minimal gap between navbar and content)

## Database

### MySQL 5.7 (Homebrew)

```sql
-- ratings table
CREATE TABLE ratings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  station VARCHAR(255) NOT NULL,
  score TINYINT NOT NULL,
  ip VARCHAR(45) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_rating (station, ip)
);

-- users table
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(64) NOT NULL,
  salt VARCHAR(32) NOT NULL,
  token VARCHAR(64) DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- profiles table
CREATE TABLE profiles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  nickname VARCHAR(100) DEFAULT '',
  email VARCHAR(255) DEFAULT '',
  genres VARCHAR(500) DEFAULT '',
  about TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- feedback table
CREATE TABLE feedback (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) DEFAULT '',
  message TEXT NOT NULL,
  ip VARCHAR(45) DEFAULT '',
  username VARCHAR(50) DEFAULT '',
  nickname VARCHAR(100) DEFAULT '',
  genres VARCHAR(500) DEFAULT '',
  about TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- `ratings.score`: 1 = thumbs up, 0 = thumbs down
- Unique constraint on `(station, ip)` prevents duplicate votes
- `users.token`: auth token set on login, used for Bearer auth
- `feedback`: stores message + full user profile snapshot (minus password)
- Credentials loaded from environment variables via python-dotenv (see `api/.env.example`)

## Testing & CI/CD

### Test Suite

**261 total tests** across 4 test suites:

| Suite | File | Tests | Tool |
|-------|------|-------|------|
| Python unit | `api/test_app.py` | 61 | pytest (98% coverage) |
| Python integration | `api/test_integration.py` | 19 | pytest |
| JavaScript unit | `static/js/player.test.js` | 162 | Jest + jsdom (90% line threshold, ~96% actual) |
| E2E | `tests/test_e2e.py` | 19 | pytest + requests (Docker prod stack) |
| Skills | `tests/test_skills.py` | 138 | pytest (validates all 17 slash commands) |

- Python unit tests use isolated `radiocalico_test` database (created/destroyed per test)
- Python fixtures: `client`, `registered_user`, `auth_token`, `auth_headers`
- Integration tests chain multiple API calls per test (user lifecycle, ratings workflow, session handling)
- JS uses Jest + jsdom with mocked `fetch`, `Hls.js`, `localStorage`, `window.open`
- E2E tests make real HTTP requests to nginx → gunicorn → MySQL (requires `make docker-prod`)

### Security Scanning

- **Bandit** (SAST): scans `app.py` for security issues. Reports 0 issues.
- **Safety**: checks `requirements.txt` for known vulnerabilities
- **npm audit**: checks `package.json` for known JS dependency vulnerabilities
- **Hadolint**: lints `Dockerfile` for best practices and security
- **Trivy**: scans Docker image for HIGH/CRITICAL OS and library vulnerabilities
- **OWASP ZAP**: dynamic application security testing (baseline scan against running app)

### Makefile Targets

| Target | Description |
| ------ | ----------- |
| `make install` | Install all dev dependencies (Python + npm) |
| `make test` | Run all tests (Python + JavaScript) |
| `make test-py` | Run Python unit tests only |
| `make test-js` | Run JavaScript unit tests only |
| `make coverage` | Python tests + coverage (fails if <98%) |
| `make lint` | Run all linters (Python + JS + CSS + HTML) |
| `make lint-py` | Ruff check + format check (Python) |
| `make lint-js` | ESLint (JavaScript) |
| `make lint-css` | Stylelint (CSS) |
| `make lint-html` | HTMLHint (HTML) |
| `make fix-py` | Auto-fix Python lint + format issues |
| `make security` | Bandit + Safety + npm audit |
| `make security-all` | All scans: security + hadolint + trivy + zap |
| `make hadolint` | Dockerfile best practices linting |
| `make trivy` | Docker image vulnerability scan (requires built image) |
| `make zap` | OWASP ZAP DAST baseline scan (requires running app) |
| `make docker-security` | Docker-specific scans: hadolint + trivy |
| `make test-integration` | API integration tests (requires MySQL) |
| `make test-skills` | Validate all 12 slash commands (structure, versions, refs) |
| `make test-e2e` | E2E tests against running Docker prod stack |
| `make docker-e2e` | Start prod, run E2E tests, stop prod |
| `make ci` | Full pipeline: lint + coverage + security |

## Important Notes

- **Metadata comes from CloudFront JSON**, not ID3 tags. The ID3 parser is implemented as fallback but the stream does not currently embed ID3 tags.
- **Database credentials are loaded from environment variables** via python-dotenv (`api/.env.example` provides the template). `CORS_ORIGIN` env var controls allowed CORS origins.
- **Debug mode is off by default**, controlled by `FLASK_DEBUG` env var.
- **Tests exist** — 399 tests: 61 Python unit + 19 integration + 162 JS unit + 19 E2E + 138 skills. Run `make ci` before merging. CI runs automatically on push/PR via GitHub Actions (11 jobs).
- **iTunes API** is cached client-side in localStorage (24h TTL) via `fetchItunesCached()`. No server-side proxy.
- **Ratings are local only** — not sent to the CloudFront/stream host.
- **Cache issues** — after editing static files, users must hard refresh (`Cmd+Shift+R`) to see changes.
- **Port conflicts** — do NOT run a separate static server. Flask on port 5000 (local) or 5050 (Docker) serves everything. Port 5000 on macOS may conflict with AirPlay Receiver.
- **Feedback is stored in DB** — no email sending configured. Query `feedback` table to read submissions.
- **Docker** uses MySQL 8.0 with `mysql_native_password` auth plugin for PyMySQL compatibility. Runs as non-root `appuser`. Production uses nginx (static files + reverse proxy) → gunicorn (4 workers, API only). Dev uses Flask directly. `FLASK_HOST=0.0.0.0` is set in Docker containers so Flask accepts external connections.

## Known Gotchas

1. **`/ratings/summary` 404**: If Flask logs show `/ratings/summary` without `/api` prefix, the browser is serving a cached old JS file. Fix: hard refresh.
2. **Port 8080 vs 5000/5050**: If the app appears on port 8080, an old static server is running. Kill it (`lsof -i :8080`) and use Flask on 5000 (local) or 5050 (Docker).
3. **Metadata 404**: The metadata JSON is at the root (`/metadatav2.json`), NOT under `/hls/`.
4. **`audio.currentTime` is wrong for elapsed**: It returns HLS buffer position, not actual song time. Use wall-clock `Date.now() - songStartTime`.
5. **Duplicate ratings in DB**: Before adding unique constraint, must delete existing duplicates first.
6. **Metadata updates too early**: CloudFront JSON updates before the HLS audio. The `pendingTrackUpdate` delay compensates — do NOT remove it or call `updateTrack()` directly from `fetchMetadata()`.
7. **Shazam search URLs don't work**: Shazam is an SPA with no direct search URL support. Use Spotify/YouTube Music/Amazon Music instead.
8. **Share shows wrong song**: Usually a browser cache issue. Hard refresh fixes it. The share function reads from DOM elements which reflect what's displayed.
9. **Emoji in URL encoding**: Emoji characters get corrupted in `encodeURIComponent` on some platforms (especially WhatsApp). Use plain text labels like `[N likes / N unlikes]`.
10. **mailto: links don't work in `window.open`**: Opens a blank tab instead of the email client. Use `window.location.href` or a server-side form instead.

## Style Guide Quick Reference

- Mint `#D8F2D5` — backgrounds, accents
- Forest Green `#1F4E23` — primary buttons, headings
- Teal `#38A29D` — navbar, footer, hover states
- Orange `#EFA63C` — call-to-action
- Charcoal `#231F20` — body text, player bar
- Breakpoint: 700px (single column below)
- Max width: 1200px, 24px gutters, 8px baseline grid
- Global zoom: 85% (`html { zoom: 0.85 }`)

## Recently Played Display Format

- List format: `"Title" by Artist (Album) 👍 N 👎 N` (emoji rendered via HTML entities in browser)
- Share text format: `"N. Title by Artist (Album) [N likes / N unlikes]"` (plain text, no emoji)
- Ratings use plain text `[N likes / N unlikes]` in shared messages (emoji break in URL encoding on WhatsApp)
- Now Playing share includes artwork URL at bottom: `Album cover: https://...300x300bb.jpg`
