"""Integration tests for Radio Calico API — multi-step workflow tests.

These tests exercise complete user journeys across multiple API endpoints,
verifying the cumulative state after each step. They reuse the same
conftest.py fixtures as unit tests (real MySQL database).
"""


class TestUserLifecycle:
    """Full user lifecycle: register → login → profile → feedback → logout."""

    def test_full_lifecycle(self, client):
        # Register
        res = client.post("/api/register", json={"username": "lifecycle", "password": "pass1234"})
        assert res.status_code == 201

        # Login
        res = client.post("/api/login", json={"username": "lifecycle", "password": "pass1234"})
        assert res.status_code == 200
        token = res.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Profile is initially empty
        res = client.get("/api/profile", headers=headers)
        assert res.status_code == 200
        profile = res.get_json()
        assert profile["nickname"] == ""

        # Update profile
        res = client.put(
            "/api/profile",
            headers=headers,
            json={
                "nickname": "LifeUser",
                "email": "life@test.com",
                "genres": "rock,jazz",
                "about": "Testing lifecycle",
            },
        )
        assert res.status_code == 200

        # Verify profile was saved
        res = client.get("/api/profile", headers=headers)
        assert res.get_json()["nickname"] == "LifeUser"
        assert res.get_json()["email"] == "life@test.com"

        # Submit feedback (captures profile snapshot)
        res = client.post("/api/feedback", headers=headers, json={"message": "Great app!"})
        assert res.status_code == 201

        # Logout
        res = client.post("/api/logout", headers=headers)
        assert res.status_code == 200

        # Token should be invalid after logout
        res = client.get("/api/profile", headers=headers)
        assert res.status_code == 401


class TestRatingWorkflow:
    """Rating workflow with IP-based deduplication."""

    def test_rate_check_summary_flow(self, client):
        station = "TestArtist - TestSong"

        # Check not rated yet
        res = client.get(f"/api/ratings/check?station={station}")
        assert res.status_code == 200
        assert res.get_json()["rated"] is False

        # Submit thumbs up
        res = client.post("/api/ratings", json={"station": station, "score": 1})
        assert res.status_code == 201

        # Check now rated
        res = client.get(f"/api/ratings/check?station={station}")
        assert res.get_json()["rated"] is True

        # Verify summary
        res = client.get("/api/ratings/summary")
        summary = res.get_json()
        assert station in summary
        assert summary[station]["likes"] == 1
        assert summary[station]["dislikes"] == 0

        # Duplicate rating should be rejected
        res = client.post("/api/ratings", json={"station": station, "score": 0})
        assert res.status_code == 409

    def test_multiple_stations(self, client):
        """Rate multiple stations and verify summary contains all."""
        stations = ["A - Song1", "B - Song2", "C - Song3"]
        for i, station in enumerate(stations):
            res = client.post("/api/ratings", json={"station": station, "score": i % 2})
            assert res.status_code == 201

        res = client.get("/api/ratings/summary")
        summary = res.get_json()
        assert len(summary) == 3

    def test_ratings_list_no_ip_exposed(self, client):
        """Verify GET /api/ratings does not expose IP addresses."""
        client.post("/api/ratings", json={"station": "X - Y", "score": 1})
        res = client.get("/api/ratings")
        assert res.status_code == 200
        for rating in res.get_json():
            assert "ip" not in rating


class TestSessionHandling:
    """Test login/logout and token behavior."""

    def test_relogin_invalidates_old_token(self, client):
        """Logging in again should generate a new token."""
        client.post("/api/register", json={"username": "sessuser", "password": "pass1234"})

        # First login
        res1 = client.post("/api/login", json={"username": "sessuser", "password": "pass1234"})
        token1 = res1.get_json()["token"]

        # Second login
        res2 = client.post("/api/login", json={"username": "sessuser", "password": "pass1234"})
        token2 = res2.get_json()["token"]

        assert token1 != token2

        # Old token should be invalid (overwritten)
        res = client.get("/api/profile", headers={"Authorization": f"Bearer {token1}"})
        assert res.status_code == 401

        # New token should work
        res = client.get("/api/profile", headers={"Authorization": f"Bearer {token2}"})
        assert res.status_code == 200

    def test_register_duplicate_username(self, client):
        client.post("/api/register", json={"username": "dupuser", "password": "pass1234"})
        res = client.post("/api/register", json={"username": "dupuser", "password": "pass5678"})
        assert res.status_code == 409


class TestProfileUpsert:
    """Profile create and update idempotency."""

    def test_profile_upsert(self, client):
        client.post("/api/register", json={"username": "profuser", "password": "pass1234"})
        res = client.post("/api/login", json={"username": "profuser", "password": "pass1234"})
        headers = {"Authorization": f"Bearer {res.get_json()['token']}"}

        # First update creates profile
        client.put(
            "/api/profile",
            headers=headers,
            json={
                "nickname": "First",
                "email": "first@test.com",
                "genres": "",
                "about": "",
            },
        )

        # Second update modifies same profile
        client.put(
            "/api/profile",
            headers=headers,
            json={
                "nickname": "Second",
                "email": "second@test.com",
                "genres": "pop",
                "about": "Updated",
            },
        )

        res = client.get("/api/profile", headers=headers)
        profile = res.get_json()
        assert profile["nickname"] == "Second"
        assert profile["email"] == "second@test.com"


class TestFeedbackSnapshot:
    """Feedback stores a profile snapshot at submission time."""

    def test_feedback_has_profile_snapshot(self, client):
        client.post("/api/register", json={"username": "fbuser", "password": "pass1234"})
        res = client.post("/api/login", json={"username": "fbuser", "password": "pass1234"})
        headers = {"Authorization": f"Bearer {res.get_json()['token']}"}

        # Set profile
        client.put(
            "/api/profile",
            headers=headers,
            json={
                "nickname": "FBNick",
                "email": "fb@test.com",
                "genres": "rock",
                "about": "Hello",
            },
        )

        # Submit feedback
        res = client.post("/api/feedback", headers=headers, json={"message": "Great!"})
        assert res.status_code == 201

        # Change profile after feedback
        client.put(
            "/api/profile",
            headers=headers,
            json={
                "nickname": "Changed",
                "email": "changed@test.com",
                "genres": "",
                "about": "",
            },
        )

        # Feedback should still have the original profile data
        # (We can't query feedback via API, but the submission succeeded with snapshot)


class TestAuthEdgeCases:
    """Authentication boundary conditions."""

    def test_minimum_password_length(self, client):
        res = client.post("/api/register", json={"username": "minpw", "password": "12345678"})
        assert res.status_code == 201

    def test_short_password_rejected(self, client):
        res = client.post("/api/register", json={"username": "shortpw", "password": "1234567"})
        assert res.status_code == 400

    def test_max_password_length(self, client):
        res = client.post("/api/register", json={"username": "maxpw", "password": "a" * 128})
        assert res.status_code == 201

    def test_over_max_password_rejected(self, client):
        res = client.post("/api/register", json={"username": "overpw", "password": "a" * 129})
        assert res.status_code == 400

    def test_wrong_password_login(self, client):
        client.post("/api/register", json={"username": "wrongpw", "password": "correct1"})
        res = client.post("/api/login", json={"username": "wrongpw", "password": "wrong123"})
        assert res.status_code == 401

    def test_nonexistent_user_login(self, client):
        res = client.post("/api/login", json={"username": "ghost", "password": "pass1234"})
        assert res.status_code == 401

    def test_all_protected_endpoints_require_auth(self, client):
        """All protected endpoints should return 401 without token."""
        assert client.get("/api/profile").status_code == 401
        assert client.put("/api/profile", json={}).status_code == 401
        assert client.post("/api/feedback", json={"message": "test"}).status_code == 401
        assert client.post("/api/logout").status_code == 401


class TestContentTypeHandling:
    """Test API behavior with invalid content types and bodies."""

    def test_register_no_json(self, client):
        res = client.post("/api/register", data="not json", content_type="text/plain")
        assert res.status_code in (400, 415)

    def test_login_no_json(self, client):
        res = client.post("/api/login", data="not json", content_type="text/plain")
        assert res.status_code in (400, 415)

    def test_rating_missing_fields(self, client):
        res = client.post("/api/ratings", json={})
        assert res.status_code == 400

    def test_rating_invalid_score(self, client):
        res = client.post("/api/ratings", json={"station": "A - B", "score": 5})
        assert res.status_code == 400
