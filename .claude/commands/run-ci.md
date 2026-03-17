Run the full Radio Calico CI pipeline (tests + coverage + security).

1. Ensure MySQL is running: `brew services list | grep mysql`
2. Run `make ci` from the project root
3. Report results:
   - Python tests passed/failed (61 tests, 98% coverage target)
   - JavaScript tests passed/failed (44 tests via Jest)
   - Bandit findings (expected: 0 issues)
   - Safety findings
4. If any tests fail, investigate and suggest fixes
5. If Python coverage drops below 98%, identify uncovered lines

The CI pipeline runs:
- `pytest` with `--cov=app --cov-fail-under=99` (Python backend)
- `jest` via `npx jest --verbose` (JavaScript frontend)
- `bandit` static security analysis
- `safety` dependency vulnerability check

Python tests use an isolated `radiocalico_test` database (auto-created/destroyed per test).
JavaScript tests use Jest + jsdom with mocked DOM, fetch, Hls.js, and localStorage.
