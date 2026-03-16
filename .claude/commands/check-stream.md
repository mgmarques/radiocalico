Check the current status of the Radio Calico stream and metadata.

1. Fetch the metadata JSON from `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` and display the current track info (artist, title, album, quality)
2. Check if the HLS stream manifest is accessible at `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8`
3. Check if the Flask server is responding at `http://127.0.0.1:5000`
4. Check if MySQL is running: `brew services list | grep mysql`

Report the status of each component clearly.
