<!-- Radio Calico Skill v2.0.0 -->
Diagnose LLM/Ollama connectivity and model availability.

Run the following checks in order and report results:

1. **Ollama process**: Check if Ollama is running locally (`curl -s http://localhost:11434/api/tags`). If not, check Docker (`docker exec ollama ollama list` or `docker compose ps ollama`).

2. **Model availability**: Verify `llama3.2` model is available in the Ollama instance. Parse the response from step 1 for the model name.

3. **Health endpoint**: Test the Flask health endpoint `curl -s http://127.0.0.1:5000/api/song-info/health` (local) or `http://127.0.0.1:5050/api/song-info/health` (Docker). Report the JSON response.

4. **Environment variables**: Check if `OLLAMA_BASE_URL` and `OLLAMA_FALLBACK_URL` are set in the environment or in `api/.env`. Report their values.

5. **Report status**:
   - **OK**: Ollama running, model available, health endpoint returns `{ "ok": true }`
   - **Model missing**: Ollama running but `llama3.2` not found — suggest `ollama pull llama3.2`
   - **Ollama down**: Neither local nor Docker Ollama responding — suggest `ollama serve` or `docker compose up ollama`
   - **Connection error**: Health endpoint fails but Ollama is running — check `OLLAMA_BASE_URL` configuration

Detect environment (Docker vs local) the same way as `/check-stream`: if Docker containers are healthy, use port 5050, otherwise use port 5000.