# Testing & CI/CD

## Test Suite — 401 total tests across 5 suites

| Suite | File | Tests | Tool |
|-------|------|-------|------|
| Python unit | `api/test_app.py` | 61 | pytest (98% coverage) |
| Python integration | `api/test_integration.py` | 19 | pytest |
| JavaScript unit | `static/js/player.test.js` | 162 | Jest + jsdom (90% line threshold) |
| E2E | `tests/test_e2e.py` | 19 | pytest + requests (Docker prod stack) |
| Skills | `tests/test_skills.py` | 140 | pytest (validates all 17 slash commands) |

- Python unit tests use isolated `radiocalico_test` database (created/destroyed per test)
- Python fixtures: `client`, `registered_user`, `auth_token`, `auth_headers`
- Integration tests chain multiple API calls per test (user lifecycle, ratings workflow)
- JS uses Jest + jsdom with mocked `fetch`, `Hls.js`, `localStorage`, `window.open`
- E2E tests make real HTTP requests to nginx → gunicorn → MySQL (requires `make docker-prod`)

## Security Scanning (6 tools)

- **Bandit** (SAST): Python code, **Safety**: Python dependencies, **npm audit**: JS dependencies
- **Hadolint**: Dockerfile, **Trivy**: Docker image (HIGH/CRITICAL), **OWASP ZAP**: DAST baseline

## CI/CD — GitHub Actions (12 jobs)

Pipeline: `lint` → `[python-tests, integration-tests, js-tests, skills-tests]` → `[e2e-tests, zap]`
Parallel security: `bandit, safety, npm-audit, hadolint, trivy`

## Makefile Targets

| Target | Description |
| ------ | ----------- |
| `make test` | Run all tests (Python + JavaScript) |
| `make coverage` | Python tests + coverage (fails if <98%) |
| `make coverage-js` | JS tests + coverage (fails if <90% lines) |
| `make lint` | Run all linters (Ruff + ESLint + Stylelint + HTMLHint) |
| `make fix-py` | Auto-fix Python lint + format issues |
| `make security` | Bandit + Safety + npm audit |
| `make security-all` | All scans including Docker + DAST |
| `make ci` | Full pipeline: lint + coverage + security |
| `make test-integration` | API integration tests (requires MySQL) |
| `make test-skills` | Validate all 17 slash commands |
| `make test-e2e` | E2E tests (requires Docker prod running) |
| `make docker-e2e` | Start prod, run E2E, stop prod |