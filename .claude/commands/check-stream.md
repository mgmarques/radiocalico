---
name: check-stream
description: Check stream and server status
---
Check the current status of the Radio Calico stream and metadata.

Detect the environment: if Docker is running (`docker compose --profile dev ps` shows healthy containers), use port 5050. Otherwise use port 5000.

1. Fetch the metadata JSON from `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` and display the current track info (artist, title, album, quality)
2. Check if the HLS stream manifest is accessible at `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8`
3. Check if the Flask server is responding at the detected port
4. If local: check if MySQL is running (`brew services list | grep mysql`). If Docker: check container health.

Report the status of each component clearly.
