# Deploy Verification

## After Rebuilding Docker Prod

Local files being correct does NOT mean the container has them. Always verify:

```bash
# 1. Force rebuild (no cache)
docker compose --profile prod build --no-cache app

# 2. Restart
docker compose --profile prod up -d app nginx

# 3. Verify key files inside the container match local
docker exec radiocalico-nginx-1 grep "KEY_PATTERN" /usr/share/nginx/html/css/player.css
docker exec radiocalico-nginx-1 grep "KEY_PATTERN" /usr/share/nginx/html/js/player.js
docker exec radiocalico-app-1 grep "KEY_PATTERN" /app/api/llm_service.py
```

## Quick Diff: Local vs Container

```bash
# CSS
diff <(docker exec radiocalico-nginx-1 cat /usr/share/nginx/html/css/player.css) static/css/player.css

# JS
diff <(docker exec radiocalico-nginx-1 cat /usr/share/nginx/html/js/player.js) static/js/player.js

# Python
diff <(docker exec radiocalico-app-1 cat /app/api/llm_service.py) api/llm_service.py
```

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| Container has old CSS/JS | `docker compose up` reused cached image | `docker compose build --no-cache app` |
| `docker compose up --build` didn't rebuild | No changes to Dockerfile or requirements.txt | Use `--no-cache` flag |
| `.env` changes not picked up | Container env is set at build/start time | `docker compose up -d app` (recreates container) |
| Ollama model missing after rebuild | Volume was removed | `docker exec radiocalico-ollama-1 ollama pull llama3.2` |