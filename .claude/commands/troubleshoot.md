Diagnose common Radio Calico issues by running through the debugging checklist.

Run these checks in order and report results:

1. **MySQL**: `brew services list | grep mysql` — is mysql@5.7 running?
2. **Flask server**: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000` — is it responding?
3. **Port conflict**: `lsof -i :8080 | head -5` — is an old static server running on 8080? If so, warn the user.
4. **API prefix**: `curl -s http://127.0.0.1:5000/api/ratings/summary` — does the API respond with JSON?
5. **Metadata URL**: Fetch `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` — is it accessible and returning valid JSON?
6. **HLS stream**: Fetch `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8` — does the manifest load?

After all checks, provide a summary of what's working and what's broken.

Always remind the user:
- If static file changes aren't showing: **Cmd+Shift+R** to hard refresh
- If the app loads on port 8080: kill that process and use port 5000
- If `/ratings/summary` returns 404: browser is serving cached old JS — hard refresh
- If metadata shows wrong song: `pendingTrackUpdate` delay is working as designed — wait for HLS latency to catch up
