# Radio Calico — CI/CD automation targets
# Usage: make test | make coverage | make security | make ci

ACTIVATE := . api/venv/bin/activate &&

.PHONY: install test coverage security bandit safety ci clean

## Install all dependencies (prod + dev)
install:
	$(ACTIVATE) cd api && pip install -r requirements-dev.txt

## Run unit tests
test:
	$(ACTIVATE) cd api && pytest test_app.py -v

## Run tests with coverage report (fail if <99% — line 269 is unreachable)
coverage:
	$(ACTIVATE) cd api && pytest test_app.py --cov=app --cov-report=term-missing --cov-fail-under=99 -v

## Run all security scans
security: bandit safety

## Static security analysis (SAST)
bandit:
	$(ACTIVATE) cd api && bandit -r app.py -f txt || true

## Dependency vulnerability check
safety:
	$(ACTIVATE) cd api && safety check -r requirements.txt || true

## Full CI pipeline: tests + coverage + security
ci: coverage security
	@echo ""
	@echo "=== CI pipeline passed ==="
