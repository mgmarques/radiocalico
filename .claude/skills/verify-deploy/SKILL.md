---
name: verify-deploy
description: Verify that running Docker containers match local file state
---
Verify that the running Docker prod containers have the same files as the local working tree.

## Steps

1. Check Docker containers are running:
   ```bash
   docker compose ps
   ```

2. Diff key files between container and local:
   ```bash
   diff <(docker exec radiocalico-nginx-1 cat /usr/share/nginx/html/css/player.css) static/css/player.css
   diff <(docker exec radiocalico-nginx-1 cat /usr/share/nginx/html/js/player.js) static/js/player.js
   diff <(docker exec radiocalico-app-1 cat /app/api/app.py) api/app.py
   diff <(docker exec radiocalico-app-1 cat /app/api/llm_service.py) api/llm_service.py
   ```

3. Check Ollama model availability:
   ```bash
   curl -sf http://localhost:11434/api/tags | python3 -c "import sys,json; models=[m['name'] for m in json.load(sys.stdin).get('models',[])]; print('Models:', models); assert any('llama3.2' in m for m in models), 'llama3.2 NOT FOUND'"
   ```

4. Check app health:
   ```bash
   curl -sf http://localhost:5050/health
   curl -sf http://localhost:5050/api/song-info/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d); assert d.get('ok'), 'LLM unhealthy'"
   ```

5. Report:
   - If all diffs are empty: "Deploy is in sync with local files"
   - If diffs found: list each file with a summary of what's different
   - If containers not running: "Prod stack is not running. Start with: `make docker-prod`"
   - Suggest `docker compose --profile prod build --no-cache app` if files are stale