<!-- Radio Calico Skill v1.0.0 -->
Scaffold a new Flask API endpoint with tests and documentation.

The user should provide: the endpoint path, HTTP method, and what it does.
Example: `/add-endpoint POST /api/tracks/favorite — save a favorite track for the logged-in user`

### Steps

1. **Add the route** in `api/app.py`:
   - Follow existing patterns (parameterized SQL, `get_db()`, proper error handling)
   - Add Google-style docstring with method, path, params, returns, raises
   - Use `require_auth()` if the endpoint needs authentication
   - Add structured logging: `logger.info("event_name", extra={...})` for business events
   - Validate input: check JSON body, required fields, value constraints
   - Return proper status codes (201 for create, 200 for read/update, 400/401/409 for errors)

2. **Add unit tests** in `api/test_app.py`:
   - Test happy path
   - Test validation errors (missing fields, invalid values)
   - Test auth required (if applicable)
   - Test edge cases (duplicates, not found, etc.)
   - Use existing fixtures: `client`, `registered_user`, `auth_token`, `auth_headers`

3. **Add integration tests** in `api/test_integration.py` if the endpoint participates in a multi-step workflow

4. **Add E2E test** in `tests/test_e2e.py` if the endpoint should be tested through the nginx proxy

5. **Update schema** in `db/init.sql` if a new table is needed

6. **Run linting**: `make lint-py` (must pass)

7. **Run tests**: `make test-py` (must pass)

8. **Update CLAUDE.md**:
   - Add endpoint to "Key URLs & Endpoints" section
   - Update test counts if new tests were added

9. **Report**: Show the new endpoint, tests added, and how to test it manually with curl

### Patterns to follow

```python
# Route with auth
@app.route("/api/example", methods=["POST"])
def example():
    user = require_auth()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    # ... business logic ...
    logger.info("example_created", extra={"user": user["username"]})
    return jsonify({"status": "ok"}), 201
```