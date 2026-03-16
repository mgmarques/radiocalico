# Radio Calico - Claude Code Guidelines

## Project Overview

Radio Calico is a live audio streaming web player with a Flask backend for ratings, user accounts, and feedback. It streams lossless audio via HLS from AWS CloudFront, displays track metadata from a CloudFront JSON endpoint, fetches album artwork and duration from iTunes, and lets users rate tracks, manage profiles, and submit feedback (all stored locally in MySQL).

## Architecture

- **Frontend**: Vanilla JavaScript + HTML5 + CSS (no framework). Single-page app served from `static/`.
- **Backend**: Python Flask API (`api/app.py`) on port 5000 with MySQL 5.7 (Homebrew) for data storage.
- **Streaming**: HLS via CloudFront CDN, decoded by HLS.js (non-Safari) or native (Safari).
- **Metadata**: Fetched from CloudFront `metadatav2.json` (not ID3 tags). Provides current track + 5 previous tracks.
- **Artwork & Duration**: iTunes Search API (client-side). `trackTimeMillis` used for duration display.
- **Ratings**: Stored in local MySQL only. CloudFront host does NOT accept ratings.
- **Auth**: Token-based authentication. Passwords hashed with PBKDF2 (260k iterations) + random salt. Timing-safe comparison via hmac.compare_digest. Tokens stored in `localStorage`.
- **Testing**: pytest + pytest-cov (99% coverage). Security: bandit (SAST) + safety (dependency scan).

## File Tree

```text
radiocalico/
├── CLAUDE.md                       # Claude Code guidelines (this file)
├── Makefile                        # CI/CD automation (test, coverage, security)
├── design.md                       # Full architecture and design document
├── RadioCalico_Style_Guide.txt     # Brand colors, typography, component specs
├── RadioCalicoLayout.png           # UI layout reference image
├── RadioCalicoLogoTM.png           # Logo with trademark
├── SomeLikesSogs.txt               # Sample liked songs reference
├── stream_URL.txt                  # Stream URL reference
├── api/
│   ├── app.py                      # Flask REST API + static file serving
│   ├── .env.example                # Environment variable template
│   ├── requirements.txt            # Python deps (flask, flask-cors, pymysql, python-dotenv, flask-limiter)
│   ├── requirements-dev.txt        # Dev deps (pytest, pytest-cov, bandit, safety)
│   ├── conftest.py                 # Pytest fixtures (test DB, client, auth)
│   ├── test_app.py                 # 61 unit tests (99% coverage)
│   ├── pytest.ini                  # Pytest configuration
│   ├── .bandit                     # Bandit security scan config
│   └── venv/                       # Python virtual environment
├── static/
│   ├── index.html                  # Main entry point, all UI markup
│   ├── logo.png                    # Radio Calico logo (navbar + favicon)
│   ├── css/
│   │   └── player.css              # All styles, responsive layout, design tokens
│   └── js/
│       └── player.js               # Playback, metadata, artwork, ratings, auth, sharing
└── .claude/
    └── commands/
        ├── start.md                # /start — launch dev environment
        ├── check-stream.md         # /check-stream — check stream & server status
        ├── troubleshoot.md         # /troubleshoot — diagnose common issues
        ├── test-ratings.md         # /test-ratings — test ratings API end-to-end
        ├── add-share-button.md     # /add-share-button — add new share platform
        ├── add-dark-style.md       # /add-dark-style — add dark mode for new components
        ├── update-claude-md.md     # /update-claude-md — refresh CLAUDE.md from codebase
        └── run-ci.md              # /run-ci — run full CI pipeline (tests + security)
```

## Key Files

| File | Purpose |
|------|---------|
| `static/index.html` | Main entry point, all UI markup (player, drawer, forms) |
| `static/js/player.js` | Playback, metadata, artwork, ratings, auth, profile, sharing, feedback |
| `static/css/player.css` | All styles, responsive layout, design tokens, dark/light themes |
| `api/app.py` | Flask REST API: ratings, auth, profile, feedback + static file serving |
| `api/test_app.py` | 61 unit tests covering all endpoints (99% coverage) |
| `api/conftest.py` | Pytest fixtures: test DB setup/teardown, client, auth helpers |
| `api/.env.example` | Environment variable template (DB creds, Flask config, CORS) |
| `api/requirements.txt` | Python dependencies (flask, flask-cors, pymysql, python-dotenv, flask-limiter) |
| `api/requirements-dev.txt` | Dev dependencies (pytest, pytest-cov, bandit, safety) |
| `Makefile` | CI/CD targets: test, coverage, security, ci |
| `design.md` | Full architecture and design document |
| `RadioCalico_Style_Guide.txt` | Brand colors, typography, component specs |

## Key URLs & Endpoints

### External (read-only)

- **HLS Stream**: `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8`
- **Metadata JSON**: `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` (root path, NOT `/hls/`)
- **iTunes Search API**: `https://itunes.apple.com/search?term=...&entity=song&limit=1`

### Local API (Flask on port 5000)

#### Ratings (no auth required)

- `GET /api/ratings` — all ratings (IP addresses are not exposed in response)
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

**IMPORTANT**: All API routes use the `/api` prefix. The frontend fetches `/api/ratings/...` — never `/ratings/...` without the prefix.

## Code Conventions

- **No frameworks** — vanilla JS, no build step, no bundler. Keep it simple.
- **CSS custom properties** for all colors: `--mint`, `--forest`, `--teal`, `--orange`, `--charcoal`, `--cream`, `--white`. Dark mode overrides these via `[data-theme="dark"]`.
- **Typography**: Montserrat for headings, Open Sans for body (loaded from Google Fonts).
- **HTML escaping**: Always use `escHtml()` when inserting user/metadata text into DOM via innerHTML.
- **Backend**: Pure Flask with PyMySQL. No ORM. Parameterized queries for SQL.
- **Auth**: Token-based. `localStorage` keys `rc-token` and `rc-user`. `Authorization: Bearer <token>` header.
- **Theme persistence**: `localStorage` key `rc-theme` stores `"light"` or `"dark"`. Default: dark.
- **Share buttons**: Use platform URL schemes (wa.me, x.com/intent, t.me/share/url, open.spotify.com/search, music.youtube.com/search, amazon.com/s with digital-music filter). Facebook removed (sharer doesn't support plain text sharing).
- **Testing**: All new API routes must have corresponding tests in `test_app.py`. Run `make ci` before merging.

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

Always use `http://127.0.0.1:5000`. Do NOT use port 8080 or any other static server — Flask serves everything.

### Hard refresh (clear cached JS/CSS in Chrome)

`Cmd+Shift+R` — required after editing static files since browser may cache aggressively.

### Run tests

```bash
make test      # Run all unit tests (61 tests)
make coverage  # Tests + coverage report (fails if <99%)
make security  # Bandit SAST + Safety dependency scan
make ci        # Full pipeline: coverage + security
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

- Settings gear icon in navbar top-right opens a dropdown with Light / Dark (default) radio buttons
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

- **61 unit tests** in `api/test_app.py` covering all endpoints and helper functions
- **99.47% code coverage** (only `app.run()` uncovered — unreachable in tests)
- Uses isolated `radiocalico_test` database (created/destroyed per test via `conftest.py`)
- Fixtures: `client`, `registered_user`, `auth_token`, `auth_headers`

### Security Scanning

- **Bandit** (SAST): scans `app.py` for security issues. Reports 0 issues (B105 and B201 previously found are now fixed).
- **Safety**: checks `requirements.txt` for known vulnerabilities

### Makefile Targets

| Target | Description |
| ------ | ----------- |
| `make install` | Install all dev dependencies |
| `make test` | Run all unit tests |
| `make coverage` | Tests + coverage (fails if <99%) |
| `make security` | Bandit + Safety scans |
| `make ci` | Full pipeline: coverage + security |

## Important Notes

- **Metadata comes from CloudFront JSON**, not ID3 tags. The ID3 parser is implemented as fallback but the stream does not currently embed ID3 tags.
- **Database credentials are loaded from environment variables** via python-dotenv (`api/.env.example` provides the template). `CORS_ORIGIN` env var controls allowed CORS origins.
- **Debug mode is off by default**, controlled by `FLASK_DEBUG` env var.
- **Tests exist** — 61 tests with 99% coverage. Run `make ci` before merging changes. Add tests for new endpoints.
- **iTunes API** is called client-side for artwork — no proxy or caching layer yet.
- **Ratings are local only** — not sent to the CloudFront/stream host.
- **Cache issues** — after editing static files, users must hard refresh (`Cmd+Shift+R`) to see changes.
- **Port conflicts** — do NOT run a separate static server. Flask on port 5000 serves everything.
- **Feedback is stored in DB** — no email sending configured. Query `feedback` table to read submissions.

## Known Gotchas

1. **`/ratings/summary` 404**: If Flask logs show `/ratings/summary` without `/api` prefix, the browser is serving a cached old JS file. Fix: hard refresh.
2. **Port 8080 vs 5000**: If the app appears on port 8080, an old static server is running. Kill it (`lsof -i :8080`) and use Flask on 5000.
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
