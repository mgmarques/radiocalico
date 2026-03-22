# Known Gotchas

Common debugging issues and their fixes. Check here first when troubleshooting.

1. **`/ratings/summary` 404**: Cached old JS. Hard refresh (`Cmd+Shift+R`).
2. **Port 8080**: Old static server running. Kill it, use Flask on 5000/5050.
3. **Metadata 404**: Root `/metadatav2.json`, NOT `/hls/`.
4. **`audio.currentTime` wrong**: Use `Date.now() - songStartTime` instead (HLS buffer position ≠ wall clock).
5. **Metadata updates too early**: `pendingTrackUpdate` delay compensates for HLS latency. Do NOT remove.
6. **Shazam URLs don't work**: Shazam is a SPA — use Spotify/YT Music/Amazon search links instead.
7. **Emoji in URL encoding**: Emoji characters get corrupted in `encodeURIComponent` + share URLs. Use plain text labels (e.g., `[N likes / N unlikes]`).
8. **mailto: in `window.open`**: Use `window.location.href` instead — `window.open` blocks mailto on most browsers.
9. **Docker Ollama is slow on macOS**: No GPU passthrough in Docker Desktop. Set `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1` to use host Metal GPU (5-10x faster).
10. **Song metadata translated**: i18n must NEVER translate artist, track, or album names. Check `data-i18n` attributes and LLM system prompts.