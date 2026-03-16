# ── Base target: shared dependencies ────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

# Create non-root user
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

# Install production dependencies
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir gunicorn==22.0.0 -r api/requirements.txt

# Copy application code
COPY api/app.py api/app.py
COPY static/ static/

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

EXPOSE 5000

# ── Production target ───────────────────────────────────────────
FROM base AS prod

ENV FLASK_DEBUG=false

USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--chdir", "api", "app:app"]

# ── Development target ──────────────────────────────────────────
FROM base AS dev

# Install dev dependencies (tests, security scanning)
COPY api/requirements-dev.txt api/requirements-dev.txt
RUN pip install --no-cache-dir -r api/requirements-dev.txt

# Install Node.js for JavaScript tests + curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm curl \
    && rm -rf /var/lib/apt/lists/*

# Copy test files and configs
COPY api/conftest.py api/conftest.py
COPY api/test_app.py api/test_app.py
COPY api/pytest.ini api/pytest.ini
COPY api/.bandit api/.bandit
COPY package.json jest.config.js ./
COPY static/js/player.test.js static/js/player.test.js
COPY Makefile ./

RUN npm install --ignore-scripts

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

ENV FLASK_DEBUG=true

USER appuser

CMD ["python", "api/app.py"]
