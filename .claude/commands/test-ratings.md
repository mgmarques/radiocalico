Test the Radio Calico ratings API end-to-end.

Run the following checks against the Flask server at http://127.0.0.1:5000:

1. **GET /api/ratings/summary** — Fetch all ratings grouped by station. Report how many stations have ratings and show a few examples.

2. **GET /api/ratings/check?station=TEST** — Check if the current IP has rated a test station. Should return `{ "rated": false }` for a non-existent station.

3. **POST /api/ratings** — Submit a test rating:
   ```
   curl -X POST http://127.0.0.1:5000/api/ratings \
     -H "Content-Type: application/json" \
     -d '{"station": "Test Artist - Test Song", "score": 1}'
   ```
   - If 200: rating submitted successfully
   - If 409: already rated (unique constraint working correctly)

4. **Verify the rating**: GET `/api/ratings/summary` again and confirm "Test Artist - Test Song" appears with 1 like.

5. **Duplicate check**: POST the same rating again — should return 409.

Report results clearly. If any step fails, check if MySQL is running (`brew services list | grep mysql`) and if Flask is up.
