---
name: start
description: Launch the Radio Calico development environment
---
Start the Radio Calico development environment.

### Local development

1. Start MySQL: `brew services start mysql@5.7`
2. Start Flask in the background: `cd api && source venv/bin/activate && python app.py` (run in background, do NOT block)
3. Verify the server is responding at http://127.0.0.1:5000
4. Report the status to the user

IMPORTANT: Run the Flask server in the background. Never run it in the foreground as it will block.

### Alternative: Docker

1. Run `make docker-dev` (or `docker compose --profile dev up --build`)
2. Verify the server is responding at http://127.0.0.1:5050
3. Report the status to the user

Docker starts both Flask and MySQL 8.0 in containers. No local Python/MySQL setup needed.
