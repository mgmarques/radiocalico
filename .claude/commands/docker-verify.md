<!-- Radio Calico Skill v1.0.0 -->
Rebuild and verify the Docker production stack.

### Steps

1. **Stop existing stack**: `docker compose --profile prod down`
2. **Rebuild and start**: `docker compose --profile prod up --build -d`
3. **Wait for healthy**: Check `docker compose --profile prod ps` — all 3 containers (db, app, nginx) must show "healthy"
4. **Health check**: `curl -sf http://127.0.0.1:5050/health`
5. **API check**: `curl -sf http://127.0.0.1:5050/api/ratings/summary | head -c 200`
6. **Security headers**: `curl -sI http://127.0.0.1:5050/ | grep -iE "x-content-type|x-frame|content-security|x-request-id"`
7. **Run E2E tests**: `source api/venv/bin/activate && E2E_BASE_URL=http://127.0.0.1:5050 pytest tests/test_e2e.py -v`
8. **Check logs**: `docker compose --profile prod logs app --tail 5` (verify structured JSON format)
9. **Report results**: Summarize which checks passed/failed

### Troubleshooting

- If containers fail to start: `docker compose --profile prod logs` for error details
- If health check fails: verify `.env` file exists with valid credentials
- If E2E tests fail: check if `requests` is installed (`pip install requests`)
- Port conflict on 5050: check `lsof -i :5050` and kill conflicting process

### Expected output

- 3 containers: `db` (MySQL 8.0), `app` (gunicorn), `nginx` (alpine)
- Health endpoint returns `200 ok`
- API returns JSON with ratings data
- All 19 E2E tests pass
- Structured JSON logs in app container