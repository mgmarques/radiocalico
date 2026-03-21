# Radio Calico - Claude Code Guidelines

> Detailed rules are in `.claude/rules/`: `architecture.md`, `testing.md`, `database.md`, `style-guide.md`.

## Project Overview

Radio Calico is a live audio streaming web player with a Flask backend for ratings, user accounts, feedback, and AI-powered song information. Streams HLS audio from CloudFront (FLAC lossless or AAC Hi-Fi), displays track metadata, fetches artwork from iTunes, and lets users rate tracks, manage profiles, submit feedback, and explore song details via LLM — all stored in MySQL.

## Architecture

- **Frontend**: Vanilla JS + HTML5 + CSS (no framework). Single-page app from `static/`.
- **Backend**: Python Flask API (`api/app.py`) on port 5000. MySQL 5.7 (local) or 8.0 (Docker).
- **Streaming**: HLS via CloudFront CDN, decoded by HLS.js (non-Safari) or native (Safari).
- **Metadata**: CloudFront `metadatav2.json` (not ID3 tags). Current track + 5 previous.
- **Artwork**: iTunes Search API (client-side, cached in localStorage 24h TTL).
- **Auth**: Token-based. PBKDF2 (260k iterations). Tokens in `localStorage`.
- **Logging**: Structured JSON — Python (`python-json-logger`), nginx, JS (`log.info/warn/error`). X-Request-ID correlation.
- **LLM**: Ollama (Llama 3.2) via OpenAI SDK for song info (lyrics, details, facts, merchandise, jokes, quiz). Docker service with host GPU fallback. Response cache (24h TTL).
- **i18n**: English (default), Brazilian Portuguese, Spanish. UI labels translated; song metadata always in original language.
- **Testing**: 861 tests (81 unit + 62 LLM + 19 integration + 238 JS + 24 E2E + 47 browser + 351 skills/agents + 39 script unit). See `.claude/rules/testing.md`.
- **CI/CD**: GitHub Actions (13 jobs). Linting: Ruff, ESLint, Stylelint, HTMLHint.
- **Performance**: WebP images, dns-prefetch, iTunes cache, API pagination, LLM response cache (24h TTL).

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

**Song Info** (LLM, rate-limited 10/min):

- `POST /api/song-info` — `{ query_type, artist, track, album?, artwork_url?, language? }` → `{ ok, content }` (Markdown)
- `GET /api/song-info/health` — check Ollama + model availability

**Quiz** (LLM, rate-limited 10/min):

- `POST /api/quiz/start` — `{ artist, track, album?, language? }` → `{ ok, session_id, question, question_number, total_questions }`
- `POST /api/quiz/answer` — `{ session_id, answer }` → `{ ok, score, feedback, question?, summary? }`

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
make test          # All unit tests: Python (81) + JS (238)
make lint          # All linters (Ruff + ESLint + Stylelint + HTMLHint)
make ci            # Full pipeline: lint + coverage + security
make test-integration  # 19 API integration tests
make test-e2e          # 24 E2E tests (Docker prod required)
make test-skills       # 351 skill + agent validation tests
make test-browser      # 47 Selenium browser tests (Docker + Chrome)

# Hard refresh after static file edits: Cmd+Shift+R
```

## Important Notes

- **Metadata from CloudFront JSON**, not ID3 tags. ID3 parser is fallback only.
- **DB credentials from env vars** via python-dotenv (`api/.env.example`).
- **Debug mode off by default**, controlled by `FLASK_DEBUG`.
- **Run `make ci` before merging**. CI runs on push/PR (13 GitHub Actions jobs).
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

## Slash Commands (22 total, all v2.0.0)

9 heavy skills delegate to a specialized subagent (isolated context window).

| Command | Purpose | Delegated To |
| ------- | ------- | ------------ |
| `/start` | Launch dev environment | — |
| `/check-stream` | Check stream & server status | — |
| `/troubleshoot` | Diagnose common issues | — |
| `/test-ratings` | Test ratings API end-to-end | — |
| `/run-ci` | Run full CI pipeline | QA Engineer |
| `/create-pr` | Branch, commit, push, create PR | — |
| `/docker-verify` | Rebuild + verify Docker prod stack | DevOps |
| `/add-endpoint` | Scaffold new API route + tests | — |
| `/security-audit` | Run all 6 security tools | Security Auditor |
| `/generate-diagrams` | Mermaid architecture diagrams | Documentation Writer |
| `/generate-tech-spec` | Full technical specification | Documentation Writer |
| `/generate-requirements` | Requirements documentation (FR/NFR) | Documentation Writer |
| `/generate-vv-plan` | V&V test plan with user test cases | V&V Plan Updater |
| `/update-readme-diagrams` | Sync diagrams to README | — |
| `/test-browser` | Run 37 Selenium browser tests (headless Chrome) | QA Engineer |
| `/add-share-button` | Add new share platform | — |
| `/add-dark-style` | Add dark mode for new components | — |
| `/update-claude-md` | Refresh CLAUDE.md from codebase | — |
| `/generate-sbom` | Generate SBOM.md with all packages + CVE status | Security Auditor |
| `/check-llm` | Diagnose Ollama/LLM connectivity and model availability | — |
| `/add-language` | Scaffold a new i18n language across all files | — |
| `/add-retro-button` | Add a new retro radio button + query type | — |

## Custom Agents (10 total, all v2.0.0)

Task-specific AI personalities in `.claude/agents/` with specialized knowledge and workflows.

| Agent | File | Focus |
| ----- | ---- | ----- |
| QA Engineer | `qa-engineer.md` | Run tests, triage failures, check coverage thresholds |
| DBA | `dba.md` | MySQL queries, indexes, schema validation, migrations |
| Frontend Reviewer | `frontend-reviewer.md` | XSS prevention, theme consistency, responsiveness, a11y |
| DevOps | `devops.md` | Docker, nginx, CI/CD pipeline, deployment |
| API Designer | `api-designer.md` | REST conventions, auth patterns, endpoint consistency |
| Release Manager | `release-manager.md` | PR readiness, CI status, changelogs, version management |
| Security Auditor | `security-auditor.md` | 6 security tools, OWASP top 10, vulnerability triage |
| Performance Analyst | `performance-analyst.md` | Caching, CDN, pagination, resource optimization |
| Documentation Writer | `documentation-writer.md` | Docs generation, cross-document consistency, Mermaid diagrams |
| V&V Plan Updater | `vv-plan-updater.md` | Run all test suites, fill execution summary, detect coverage gaps |

## Claude Code Configuration

- **Rules**: `.claude/rules/` — architecture, testing, database, style-guide, security-baseline, i18n, llm (loaded on relevant topics)
- **Settings**: `.claude/settings.json` — auto-approved commands, denied destructive ops, lint hooks
- **Skills**: `.claude/skills/*/SKILL.md` — mirrored from commands for extended skill features
- **Agents**: `.claude/agents/*.md` — 10 task-specific AI agents with specialized workflows
- **Hooks**: auto-lint Python/JS/CSS/HTML on file edit, static file hard-refresh reminder, SBOM reminder on dependency changes, context reminder on compaction
- **Ignore**: `.claudeignore` — excludes node_modules, venv, coverage, caches from context

## Strict Accuracy Policy

- Only reference code, APIs, and patterns that are **verified to exist** in this codebase or well-known stable libraries.
- When referencing external libraries, only use features from their **official, versioned documentation**.
- If a solution is uncertain, say: "I'm not sure this exists — please verify."
- Never fabricate function names, config keys, or CLI flags.
