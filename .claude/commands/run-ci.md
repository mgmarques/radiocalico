Run the full Radio Calico CI pipeline (tests + coverage + security).

1. Ensure MySQL is running: `brew services list | grep mysql`
2. Run `make ci` from the project root
3. Report results:
   - Number of tests passed/failed
   - Coverage percentage
   - Bandit findings (expected: hardcoded password B105 + debug mode B201)
   - Safety findings
4. If any tests fail, investigate and suggest fixes
5. If coverage drops below 99%, identify uncovered lines

The CI pipeline runs:
- `pytest` with `--cov=app --cov-fail-under=99`
- `bandit` static security analysis
- `safety` dependency vulnerability check

Tests use an isolated `radiocalico_test` database (auto-created/destroyed per test).
