<!-- Radio Calico Skill v1.0.0 -->
Run the full Radio Calico CI pipeline (lint + tests + coverage + security).

1. Ensure MySQL is running: `brew services list | grep mysql`
2. Run `make ci` from the project root
3. Report results:
   - Linting passed/failed (Ruff, ESLint, Stylelint, HTMLHint)
   - Python tests passed/failed (61 unit tests, 98% coverage target)
   - JavaScript tests passed/failed (162 tests via Jest, 90% line coverage target)
   - Bandit findings (expected: 0 issues)
   - Safety findings
   - npm audit findings
4. If any tests fail, investigate and suggest fixes
5. If Python coverage drops below 98%, identify uncovered lines

The CI pipeline runs:
- `ruff check` + `ruff format --check` (Python linting)
- `eslint` + `stylelint` + `htmlhint` (frontend linting)
- `pytest` with `--cov=app --cov-fail-under=98` (Python backend)
- `jest` with `--coverage` (JavaScript frontend, 90% line threshold)
- `bandit` static security analysis
- `safety` dependency vulnerability check
- `npm audit` JavaScript dependency scan

Additional test suites (not in `make ci`, run separately):
- `make test-integration` — 19 API integration tests (requires MySQL)
- `make test-e2e` — 19 E2E tests against Docker prod stack

Python tests use an isolated `radiocalico_test` database (auto-created/destroyed per test).
JavaScript tests use Jest + jsdom with mocked DOM, fetch, Hls.js, and localStorage.