# Testing & CI/CD

## Test Suite — 843 total tests across 8 suites

| Suite | File | Tests | Tool |
|-------|------|-------|------|
| Python unit | `api/test_app.py` | 81 | pytest (95% coverage) |
| LLM service | `tests/test_llm_service.py` | 62 | pytest (mocked OpenAI SDK) |
| Python integration | `api/test_integration.py` | 19 | pytest |
| JavaScript unit | `static/js/player.test.js` | 238 | Jest + jsdom (95% statement, 97% line) |
| E2E | `tests/test_e2e.py` | 24 | pytest + requests (Docker prod stack) |
| Browser | `tests/test_browser.py` | 47 | Selenium + headless Chrome (Docker prod) |
| Skills + Agents | `tests/test_skills.py` | 333 | pytest (validates 19 commands + 10 agents + 9 agent delegations) |
| Script unit | `tests/test_generate_sbom.py` | 39 | pytest (SBOM enrichment, policy compliance, OSV cache, multi-project, DB persistence) |

- Python unit tests use isolated `radiocalico_test` database (created/destroyed per test)
- Python fixtures: `client`, `registered_user`, `auth_token`, `auth_headers`
- Integration tests chain multiple API calls per test (user lifecycle, ratings workflow)
- JS uses Jest + jsdom with mocked `fetch`, `Hls.js`, `localStorage`, `window.open`
- E2E tests make real HTTP requests to nginx → gunicorn → MySQL (requires `make docker-prod`)
- Browser tests use real Chrome to verify UI, themes, auth, playback, responsive layout

## Security Scanning (6 tools)

- **Bandit** (SAST): Python code, **Safety**: Python dependencies, **npm audit**: JS dependencies
- **Hadolint**: Dockerfile, **Trivy**: Docker image (HIGH/CRITICAL), **OWASP ZAP**: DAST baseline

## CI/CD — GitHub Actions (13 jobs)

Pipeline: `lint` → `[python-tests, integration-tests, js-tests, skills-tests]` → `[e2e-tests, browser-tests, zap]`
Parallel security: `bandit, safety, npm-audit, hadolint, trivy`

## Makefile Targets

| Target | Description |
| ------ | ----------- |
| `make test` | Run all tests (Python + JavaScript + scripts) |
| `make test-scripts` | Script unit tests (generate_sbom ecosystem functions) |
| `make coverage` | Python tests + coverage (fails if <95%) |
| `make coverage-js` | JS tests + coverage (fails if <90% lines) |
| `make lint` | Run all linters (Ruff + ESLint + Stylelint + HTMLHint) |
| `make fix-py` | Auto-fix Python lint + format issues |
| `make security` | Bandit + Safety + npm audit |
| `make security-all` | All scans including Docker + DAST |
| `make ci` | Full pipeline: lint + coverage + security |
| `make test-integration` | API integration tests (requires MySQL) |
| `make test-skills` | Validate 19 slash commands + 10 agents |
| `make test-browser` | 47 Selenium browser tests (Docker + Chrome) |
| `make test-e2e` | E2E tests (requires Docker prod running) |
| `make docker-e2e` | Start prod, run E2E, stop prod |