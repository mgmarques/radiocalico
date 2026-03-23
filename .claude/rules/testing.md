# Testing & CI/CD

## Test Suite — 1055 total tests across 9 suites

| Suite | File | Tests | Tool |
|-------|------|-------|------|
| Python unit | `api/test_app.py` | 81 | pytest (95% coverage) |
| LLM service | `tests/test_llm_service.py` | 62 | pytest (mocked OpenAI SDK) |
| Python integration | `api/test_integration.py` | 19 | pytest |
| JavaScript unit | `static/js/player.test.js` | 253 | Jest + jsdom (95% statement, 97% line) |
| E2E | `tests/test_e2e.py` | 24 | pytest + requests (Docker prod stack) |
| Browser | `tests/test_browser.py` | 47 | Selenium + headless Chrome (Docker prod) |
| Playwright E2E | `tests/playwright/radio-calico.spec.js` | 18 | Playwright + Chromium (Docker prod required) |
| Skills + Agents | `tests/test_skills.py` | 492 | pytest (validates 24 commands + 11 agents + 10 delegations + YAML frontmatter) |
| Script unit | `tests/test_generate_sbom.py` | 39 | pytest (SBOM enrichment, policy compliance, OSV cache, multi-project, DB persistence) |

- Python unit tests use isolated `radiocalico_test` database (created/destroyed per test)
- Python fixtures: `client`, `registered_user`, `auth_token`, `auth_headers`
- Integration tests chain multiple API calls per test (user lifecycle, ratings workflow)
- JS uses Jest + jsdom with mocked `fetch`, `Hls.js`, `localStorage`, `window.open`
- E2E tests make real HTTP requests to nginx → gunicorn → MySQL (requires `make docker-prod`)
- Browser tests use real Chrome to verify UI, themes, auth, playback, responsive layout
- Playwright tests use Chromium for SSE streaming, network mocking (`page.route()`), and visual regression

## When to use which testing tool

| Tool | Best for |
|------|----------|
| Jest + jsdom | Unit tests, pure functions, DOM manipulation |
| pytest | API endpoints, Python logic, DB operations |
| Selenium | Existing browser automation (47 tests) |
| Playwright | SSE streaming, network mocking, visual regression, V&V manual test automation |

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
| `make test-skills` | Validate 24 slash commands + 11 agents |
| `make test-browser` | 47 Selenium browser tests (Docker + Chrome) |
| `make test-playwright` | 20 Playwright E2E tests (Docker + Chromium) |
| `make test-e2e` | E2E tests (requires Docker prod running) |
| `make docker-e2e` | Start prod, run E2E, stop prod |