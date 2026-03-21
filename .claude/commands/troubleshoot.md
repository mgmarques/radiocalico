<!-- Radio Calico Skill v2.0.0 -->
Diagnose common Radio Calico issues by running through the debugging checklist.

### Local development checks

Run these checks in order and report results:

1. **MySQL**: `brew services list | grep mysql` — is mysql@5.7 running?
2. **Flask server**: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000` — is it responding?
3. **Port conflict**: `lsof -i :8080 | head -5` — is an old static server running on 8080? If so, warn the user.
4. **API prefix**: `curl -s http://127.0.0.1:5000/api/ratings/summary` — does the API respond with JSON?
5. **Metadata URL**: Fetch `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` — is it accessible and returning valid JSON?
6. **HLS stream**: Fetch `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8` — does the manifest load?

### Docker checks

If using Docker instead of local dev:

1. **Containers**: `docker compose --profile dev ps` — are `db` and `app-dev` healthy?
2. **App**: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5050` — Docker app runs on port 5050
3. **Logs**: `docker compose --profile dev logs app-dev --tail=20` — check for errors
4. **DB**: `docker compose --profile dev logs db --tail=20` — check MySQL started OK

### Common reminders

- If static file changes aren't showing: **Cmd+Shift+R** to hard refresh
- If the app loads on port 8080: kill that process and use port 5000 (local) or 5050 (Docker)
- If `/ratings/summary` returns 404: browser is serving cached old JS — hard refresh
- If metadata shows wrong song: `pendingTrackUpdate` delay is working as designed — wait for HLS latency to catch up
- Port 5000 on macOS may conflict with AirPlay Receiver — Docker uses 5050 to avoid this
