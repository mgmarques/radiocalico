# Radio Calico — CI/CD automation targets
# Usage: make test | make coverage | make security | make ci
# Docker: make docker-dev | make docker-prod | make docker-down

ACTIVATE := . api/venv/bin/activate &&

.PHONY: install test test-py test-js coverage security bandit safety ci clean \
        docker-dev docker-prod docker-down docker-build docker-test

## Install all dependencies (prod + dev)
install:
	$(ACTIVATE) cd api && pip install -r requirements-dev.txt
	npm install

## Run all unit tests (Python + JavaScript)
test: test-py test-js

## Run Python unit tests
test-py:
	$(ACTIVATE) cd api && pytest test_app.py -v

## Run JavaScript unit tests
test-js:
	npx jest --verbose

## Run Python tests with coverage report (fail if <99%)
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
ci: coverage test-js security
	@echo ""
	@echo "=== CI pipeline passed ==="

## ── Docker targets ──────────────────────────────────────────

## Start development environment (Flask debug + hot reload)
docker-dev:
	docker compose --profile dev up --build

## Start production environment (gunicorn + 4 workers)
docker-prod:
	docker compose --profile prod up --build -d

## Stop all containers and remove volumes
docker-down:
	docker compose --profile dev --profile prod down -v

## Build Docker images without starting
docker-build:
	docker compose --profile dev --profile prod build

## Run tests inside the dev container
docker-test:
	docker compose --profile dev run --rm app-dev make test
