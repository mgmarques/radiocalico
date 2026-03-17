# Radio Calico — CI/CD automation targets
# Usage: make test | make coverage | make security | make ci
# Lint: make lint | make lint-py | make lint-js | make lint-css | make lint-html
# Docker: make docker-dev | make docker-prod | make docker-down
# Security: make security | make security-all | make audit-npm | make hadolint
#           make trivy | make zap
# Integration: make test-integration | make test-e2e | make docker-e2e

ACTIVATE := . api/venv/bin/activate &&
IMAGE_NAME := radiocalico-app
ZAP_TARGET ?= http://host.docker.internal:5050
E2E_BASE_URL ?= http://127.0.0.1:5050

.PHONY: install test test-py test-js coverage coverage-js ci clean \
        lint lint-py lint-js lint-css lint-html fix-py \
        security security-all bandit safety audit-npm hadolint trivy zap \
        test-integration test-skills test-e2e docker-e2e \
        docker-dev docker-prod docker-down docker-build docker-test docker-security

## Install all dependencies (prod + dev)
install:
	$(ACTIVATE) cd api && pip install -r requirements-dev.txt
	npm install

## ── Unit tests ────────────────────────────────────────────────

## Run all unit tests (Python + JavaScript)
test: test-py test-js

## Run Python unit tests
test-py:
	$(ACTIVATE) cd api && pytest test_app.py -v

## Run JavaScript unit tests
test-js:
	npx jest --verbose

## Run JavaScript tests with coverage report (fail if below thresholds)
coverage-js:
	npx jest --coverage --verbose

## Run Python tests with coverage report (fail if <95%)
coverage:
	$(ACTIVATE) cd api && pytest test_app.py --cov=app --cov-report=term-missing --cov-fail-under=95 -v

## ── Linting targets ───────────────────────────────────────────

## Run all linters
lint: lint-py lint-js lint-css lint-html

## Python linting (ruff check + format check)
lint-py:
	@echo "=== Ruff (Python lint + format) ==="
	$(ACTIVATE) ruff check api/ && ruff format --check api/

## JavaScript linting
lint-js:
	@echo "=== ESLint (JavaScript) ==="
	npx eslint static/js/player.js

## CSS linting
lint-css:
	@echo "=== Stylelint (CSS) ==="
	npx stylelint "static/css/**/*.css"

## HTML linting
lint-html:
	@echo "=== HTMLHint (HTML) ==="
	npx htmlhint static/index.html

## Auto-fix Python lint and format issues
fix-py:
	$(ACTIVATE) ruff check --fix api/ && ruff format api/

## ── Security targets ────────────────────────────────────────

## Run core security scans (Python SAST + dependency checks)
security: bandit safety audit-npm

## Run all security scans including Docker and DAST (requires running app)
security-all: security hadolint trivy zap

## Python static security analysis (SAST)
bandit:
	@echo "=== Bandit (Python SAST) ==="
	$(ACTIVATE) cd api && bandit -r app.py -f txt || true

## Python dependency vulnerability check
safety:
	@echo "=== Safety (Python dependencies) ==="
	$(ACTIVATE) cd api && safety check -r requirements.txt || true

## Node.js dependency vulnerability check
audit-npm:
	@echo "=== npm audit (JS dependencies) ==="
	npm audit --omit=dev || true

## Dockerfile best practices linting
hadolint:
	@echo "=== Hadolint (Dockerfile linting) ==="
	@if command -v hadolint >/dev/null 2>&1; then \
		hadolint Dockerfile; \
	else \
		docker run --rm -i hadolint/hadolint < Dockerfile; \
	fi

## Docker image vulnerability scan (requires built image)
trivy:
	@echo "=== Trivy (Docker image scan) ==="
	@if command -v trivy >/dev/null 2>&1; then \
		trivy image --severity HIGH,CRITICAL $(IMAGE_NAME):latest; \
	else \
		docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
			aquasec/trivy image --severity HIGH,CRITICAL $(IMAGE_NAME):latest; \
	fi

## OWASP ZAP baseline scan (requires running app at ZAP_TARGET)
zap:
	@echo "=== OWASP ZAP (DAST baseline scan) ==="
	@echo "Target: $(ZAP_TARGET)"
	docker run --rm --add-host=host.docker.internal:host-gateway \
		ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
		-t $(ZAP_TARGET) -l WARN -I -j

## ── Integration & E2E tests ──────────────────────────────────

## Run API integration tests (requires MySQL running)
test-integration:
	$(ACTIVATE) cd api && pytest test_integration.py -v

## Validate all Claude Code slash commands (structure, versions, references)
test-skills:
	$(ACTIVATE) pytest tests/test_skills.py -v

## Run end-to-end tests against running Docker prod stack
test-e2e:
	E2E_BASE_URL=$(E2E_BASE_URL) $(ACTIVATE) pip install requests -q && pytest tests/test_e2e.py -v

## Full E2E: start prod stack, run e2e tests, stop stack
docker-e2e:
	docker compose --profile prod up --build -d
	@echo "Waiting for stack to be healthy..."
	@for i in $$(seq 1 30); do \
		if curl -sf $(E2E_BASE_URL)/health > /dev/null 2>&1; then \
			echo "Stack is healthy"; \
			break; \
		fi; \
		echo "Waiting... ($$i/30)"; \
		sleep 5; \
	done
	E2E_BASE_URL=$(E2E_BASE_URL) $(ACTIVATE) pip install requests -q && pytest tests/test_e2e.py -v || (docker compose --profile prod down -v && exit 1)
	docker compose --profile prod down -v

## Full CI pipeline: lint + tests + coverage + security
ci: lint coverage coverage-js security
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

## Run security scans in Docker context (image scan + Dockerfile lint)
docker-security: hadolint trivy
