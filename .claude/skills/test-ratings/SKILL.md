<!-- Radio Calico Skill v2.0.0 -->
Test the Radio Calico ratings API end-to-end.

Detect the environment: if Docker is running (`docker compose --profile dev ps` shows healthy containers), use http://127.0.0.1:5050. Otherwise use http://127.0.0.1:5000.

Run the following checks against the Flask server:

1. **GET /api/ratings/summary** — Fetch all ratings grouped by station. Report how many stations have ratings and show a few examples.

2. **GET /api/ratings/check?station=TEST** — Check if the current IP has rated a test station. Should return `{ "rated": false }` for a non-existent station.

3. **POST /api/ratings** — Submit a test rating:
   ```
   curl -X POST <BASE_URL>/api/ratings \
     -H "Content-Type: application/json" \
     -d '{"station": "Test Artist - Test Song", "score": 1}'
   ```
   - If 201: rating submitted successfully
   - If 409: already rated (unique constraint working correctly)

4. **Verify the rating**: GET `/api/ratings/summary` again and confirm "Test Artist - Test Song" appears with 1 like.

5. **Duplicate check**: POST the same rating again — should return 409.

Report results clearly. If any step fails, check if MySQL is running and if Flask is up.
