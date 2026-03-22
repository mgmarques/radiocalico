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
- **Testing**: 1002 tests (81 unit + 62 LLM + 19 integration + 238 JS + 24 E2E + 47 browser + 492 skills/agents + 39 script unit). See `.claude/rules/testing.md`.
- **CI/CD**: GitHub Actions (13 jobs). Linting: Ruff, ESLint, Stylelint, HTMLHint.
- **Performance**: WebP images, dns-prefetch, iTunes cache, API pagination, LLM response cache (24h TTL).

## Key URLs & Endpoints

> Full endpoint reference in `.claude/rules/endpoints.md`.

- **All API routes use the `/api` prefix**. Flask :5000 (local), :5050 (Docker).
- **HLS Stream**: `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8`
- **Metadata JSON**: `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` (root, NOT `/hls/`)

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
make test-skills       # 492 skill + agent validation tests
make test-browser      # 47 Selenium browser tests (Docker + Chrome)
make test-scripts      # 39 SBOM script unit tests

# Hard refresh after static file edits: Cmd+Shift+R
```

## Important Notes

- **Run `make ci` before merging**. CI runs on push/PR (13 GitHub Actions jobs).
- **Docker** uses MySQL 8.0, non-root `appuser`, nginx → gunicorn (4 workers).
- **DB credentials from env vars** via python-dotenv (`api/.env.example`).
- **Ratings are local only** — not sent to CloudFront host.

## Known Gotchas

> 10 common issues with fixes in `.claude/rules/gotchas.md`. Top 3:

1. **Cache issues** — hard refresh (`Cmd+Shift+R`) after editing static files.
2. **Port 5000** (local) or **5050** (Docker). Do NOT use port 8080.
3. **Metadata from CloudFront JSON** at root `/metadatav2.json`, NOT `/hls/`.

## Slash Commands (24 total, all v2.0.0)

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
| `/test-browser` | Run 47 Selenium browser tests (headless Chrome) | QA Engineer |
| `/add-share-button` | Add new share platform | — |
| `/add-dark-style` | Add dark mode for new components | — |
| `/update-claude-md` | Refresh CLAUDE.md from codebase | — |
| `/generate-sbom` | Generate SBOM.md with all packages + CVE status | Security Auditor |
| `/check-llm` | Diagnose Ollama/LLM connectivity and model availability | — |
| `/add-language` | Scaffold a new i18n language across all files | — |
| `/add-retro-button` | Add a new retro radio button + query type | — |
| `/verify-deploy` | Verify Docker containers match local files | — |
| `/claude-qa` | Audit all Claude Code components, fix violations, update docs | Claude Code Housekeeper |

## Custom Agents (11 total, all v2.0.0)

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
| Claude Code Housekeeper | `claude-code-housekeeper.md` | Audit .claude/ components, fix violations, update tests and docs |

## Claude Code Configuration

- **Rules**: `.claude/rules/` — architecture, testing, database, style-guide, security-baseline, i18n, llm, endpoints, gotchas, rebase-safety, deploy-verify (loaded on relevant topics)
- **Settings**: `.claude/settings.json` — auto-approved commands, denied destructive ops, lint hooks
- **Skills**: `.claude/skills/*/SKILL.md` — mirrored from commands for extended skill features
- **Agents**: `.claude/agents/*.md` — 11 task-specific AI agents with specialized workflows
- **Hooks**: auto-lint Python/JS/CSS/HTML on file edit, static file hard-refresh reminder, SBOM reminder on dependency changes, context reminder on compaction
- **Ignore**: `.claudeignore` — excludes node_modules, venv, coverage, caches from context

## Code Style & Conventions

> Full details in `.claude/rules/style-guide.md`.

- **JavaScript**: Vanilla ES2020, no framework, no build step. Always use `escHtml()` for innerHTML. `log.info/warn/error()` for structured logging.
- **Python**: Flask + PyMySQL. Parameterized SQL (`%s` placeholders, never f-strings). Ruff for format + lint.
- **CSS**: CSS custom properties (`--mint`, `--forest`, `--teal`, `--orange`, `--charcoal`). Dark/light via `data-theme`. Breakpoint: 700px.
- **i18n**: Use `data-i18n` attributes + `t(key)` helper. **Never translate song metadata** (artist, track, album). Quiz button always "Quiz".
- **Commits**: Conventional Commits. One sentence summary, details in body.
- **PRs**: Short title (<70 chars), `## Summary` + `## Test plan` in body. Run `make ci` before merging.
- **Linting**: `make lint` must pass (Ruff + ESLint + Stylelint + HTMLHint). `make fix-py` auto-fixes Python.

**Commit example:**

```text
feat: add quiz interactive game with 5-question chat UI

- POST /api/quiz/start and /api/quiz/answer endpoints
- Sarcastic scoring system (-5 to +5)
- Chat-style bubble UI in info panel
```

**PR example:**

```markdown
## Summary
- Add interactive quiz game triggered by the Quiz retro button
- 5 multiple-choice questions per song with sarcastic LLM scoring

## Test plan
- [ ] `make test` — 81 Python + 238 JS tests pass
- [ ] `make lint` — all linters clean
- [ ] Manual: press Quiz button, answer 5 questions, verify score summary
```

## Strict Accuracy Policy

- Only reference code, APIs, and patterns that are **verified to exist** in this codebase or well-known stable libraries.
- When referencing external libraries, only use features from their **official, versioned documentation**.
- If a solution is uncertain, say: "I'm not sure this exists — please verify."
- Never fabricate function names, config keys, or CLI flags.
