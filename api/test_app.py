"""Unit tests for Radio Calico API — 61 tests targeting 98% coverage of app.py."""

import app as app_module

# ── Helpers ────────────────────────────────────────────────────


class TestHashPassword:
    """PBKDF2 password hashing: salt generation, determinism, uniqueness."""

    def test_generates_salt_when_none(self):
        salt, hashed = app_module.hash_password("secret")
        assert len(salt) == 32  # 16 bytes hex
        assert len(hashed) == 64  # sha256 hex

    def test_uses_provided_salt(self):
        salt, h1 = app_module.hash_password("secret", "fixedsalt")
        _, h2 = app_module.hash_password("secret", "fixedsalt")
        assert h1 == h2

    def test_different_passwords_different_hashes(self):
        _, h1 = app_module.hash_password("secret", "salt")
        _, h2 = app_module.hash_password("other", "salt")
        assert h1 != h2


class TestVerifyPassword:
    """Timing-safe password verification via hmac.compare_digest."""

    def test_correct_password(self):
        salt, hashed = app_module.hash_password("mypass")
        assert app_module.verify_password("mypass", salt, hashed) is True

    def test_wrong_password(self):
        salt, hashed = app_module.hash_password("mypass")
        assert app_module.verify_password("wrong", salt, hashed) is False


class TestGetUserFromToken:
    """Token-to-user lookup: empty, invalid, and valid tokens."""

    def test_returns_none_for_empty_token(self):
        assert app_module.get_user_from_token("") is None
        assert app_module.get_user_from_token(None) is None

    def test_returns_none_for_invalid_token(self):
        assert app_module.get_user_from_token("nonexistent_token") is None

    def test_returns_user_for_valid_token(self, client, auth_token):
        user = app_module.get_user_from_token(auth_token)
        assert user is not None
        assert user["username"] == "testuser"


# ── Index ──────────────────────────────────────────────────────


class TestServeIndex:
    """GET / serves the static index.html page."""

    def test_serves_html(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"<!DOCTYPE html>" in res.data


# ── Ratings ────────────────────────────────────────────────────


class TestGetRatings:
    """GET /api/ratings — paginated list, no IP exposure."""

    def test_empty(self, client):
        res = client.get("/api/ratings")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_returns_ratings(self, client):
        client.post("/api/ratings", json={"station": "A - B", "score": 1})
        res = client.get("/api/ratings")
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["station"] == "A - B"


class TestGetRatingsSummary:
    """GET /api/ratings/summary — aggregated likes/dislikes per station."""

    def test_empty(self, client):
        res = client.get("/api/ratings/summary")
        assert res.status_code == 200
        assert res.get_json() == {}

    def test_counts(self, client):
        client.post("/api/ratings", json={"station": "A - B", "score": 1}, headers={"X-Forwarded-For": "1.1.1.1"})
        client.post("/api/ratings", json={"station": "A - B", "score": 0}, headers={"X-Forwarded-For": "2.2.2.2"})
        res = client.get("/api/ratings/summary")
        data = res.get_json()
        assert data["A - B"]["likes"] == 1
        assert data["A - B"]["dislikes"] == 1


class TestPostRating:
    """POST /api/ratings — submit rating, validation, IP dedup, X-Forwarded-For."""

    def test_success(self, client):
        res = client.post("/api/ratings", json={"station": "X - Y", "score": 1})
        assert res.status_code == 201
        assert res.get_json()["status"] == "ok"

    def test_missing_station(self, client):
        res = client.post("/api/ratings", json={"score": 1})
        assert res.status_code == 400

    def test_missing_score(self, client):
        res = client.post("/api/ratings", json={"station": "X - Y"})
        assert res.status_code == 400

    def test_duplicate_rating(self, client):
        client.post("/api/ratings", json={"station": "X - Y", "score": 1})
        res = client.post("/api/ratings", json={"station": "X - Y", "score": 0})
        assert res.status_code == 409

    def test_x_forwarded_for(self, client):
        res = client.post(
            "/api/ratings", json={"station": "A - B", "score": 1}, headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        )
        assert res.status_code == 201

    def test_empty_station(self, client):
        res = client.post("/api/ratings", json={"station": "", "score": 1})
        assert res.status_code == 400

    def test_invalid_score(self, client):
        res = client.post("/api/ratings", json={"station": "X - Y", "score": 5})
        assert res.status_code == 400
        assert "score must be 0 or 1" in res.get_json()["error"]

    def test_invalid_json(self, client):
        res = client.post("/api/ratings", data="not json", content_type="application/json")
        assert res.status_code == 400


class TestCheckRating:
    """GET /api/ratings/check — IP-based duplicate check per station."""

    def test_not_rated(self, client):
        res = client.get("/api/ratings/check?station=X")
        assert res.status_code == 200
        assert res.get_json()["rated"] is False

    def test_rated(self, client):
        client.post("/api/ratings", json={"station": "X - Y", "score": 1})
        res = client.get("/api/ratings/check?station=X+-+Y")
        data = res.get_json()
        assert data["rated"] is True
        assert data["score"] == 1

    def test_x_forwarded_for(self, client):
        client.post("/api/ratings", json={"station": "A", "score": 0}, headers={"X-Forwarded-For": "5.5.5.5"})
        res = client.get("/api/ratings/check?station=A", headers={"X-Forwarded-For": "5.5.5.5"})
        assert res.get_json()["rated"] is True


# ── Register ───────────────────────────────────────────────────


class TestRegister:
    """POST /api/register — account creation, password rules, duplicate prevention."""

    def test_success(self, client):
        res = client.post("/api/register", json={"username": "new", "password": "pass1234"})
        assert res.status_code == 201

    def test_missing_username(self, client):
        res = client.post("/api/register", json={"username": "", "password": "pass1234"})
        assert res.status_code == 400

    def test_missing_password(self, client):
        res = client.post("/api/register", json={"username": "new", "password": ""})
        assert res.status_code == 400

    def test_short_password(self, client):
        res = client.post("/api/register", json={"username": "new", "password": "short"})
        assert res.status_code == 400
        assert "at least 8" in res.get_json()["error"]

    def test_long_username(self, client):
        res = client.post("/api/register", json={"username": "a" * 51, "password": "pass1234"})
        assert res.status_code == 400
        assert "too long" in res.get_json()["error"]

    def test_long_password(self, client):
        res = client.post("/api/register", json={"username": "new", "password": "x" * 129})
        assert res.status_code == 400
        assert "at most 128" in res.get_json()["error"]

    def test_duplicate_username(self, client, registered_user):
        res = client.post("/api/register", json={"username": "testuser", "password": "otherpw1234"})
        assert res.status_code == 409

    def test_none_fields(self, client):
        res = client.post("/api/register", json={"username": None, "password": None})
        assert res.status_code == 400


# ── Login ──────────────────────────────────────────────────────


class TestLogin:
    """POST /api/login — authentication, token generation, error cases."""

    def test_success(self, client, registered_user):
        username, password = registered_user
        res = client.post("/api/login", json={"username": username, "password": password})
        assert res.status_code == 200
        data = res.get_json()
        assert "token" in data
        assert data["username"] == username

    def test_wrong_password(self, client, registered_user):
        username, _ = registered_user
        res = client.post("/api/login", json={"username": username, "password": "wrongwrong"})
        assert res.status_code == 401

    def test_nonexistent_user(self, client):
        res = client.post("/api/login", json={"username": "nobody", "password": "pass1234"})
        assert res.status_code == 401

    def test_missing_fields(self, client):
        res = client.post("/api/login", json={"username": "", "password": ""})
        assert res.status_code == 400

    def test_none_fields(self, client):
        res = client.post("/api/login", json={"username": None, "password": None})
        assert res.status_code == 400


# ── Profile ────────────────────────────────────────────────────


class TestGetProfile:
    """GET /api/profile — auth required, empty default, token validation."""

    def test_unauthorized(self, client):
        res = client.get("/api/profile")
        assert res.status_code == 401

    def test_invalid_token(self, client):
        res = client.get("/api/profile", headers={"Authorization": "Bearer bad"})
        assert res.status_code == 401

    def test_empty_profile(self, client, auth_headers):
        res = client.get("/api/profile", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["nickname"] == ""
        assert data["email"] == ""
        assert data["genres"] == ""
        assert data["about"] == ""

    def test_no_bearer_prefix(self, client):
        res = client.get("/api/profile", headers={"Authorization": "Token abc"})
        assert res.status_code == 401


class TestUpdateProfile:
    """PUT /api/profile — create, update, upsert, field truncation."""

    def test_unauthorized(self, client):
        res = client.put("/api/profile", json={"nickname": "x"})
        assert res.status_code == 401

    def test_create_profile(self, client, auth_headers):
        res = client.put(
            "/api/profile",
            json={"nickname": "DJ", "email": "dj@test.com", "genres": "Rock,Jazz", "about": "Hello"},
            headers=auth_headers,
        )
        assert res.status_code == 200

        # Verify saved
        res = client.get("/api/profile", headers=auth_headers)
        data = res.get_json()
        assert data["nickname"] == "DJ"
        assert data["email"] == "dj@test.com"
        assert data["genres"] == "Rock,Jazz"
        assert data["about"] == "Hello"

    def test_update_existing_profile(self, client, auth_headers):
        client.put("/api/profile", json={"nickname": "v1"}, headers=auth_headers)
        client.put("/api/profile", json={"nickname": "v2"}, headers=auth_headers)
        res = client.get("/api/profile", headers=auth_headers)
        assert res.get_json()["nickname"] == "v2"

    def test_truncates_long_fields(self, client, auth_headers):
        res = client.put(
            "/api/profile",
            json={"nickname": "x" * 200, "email": "y" * 300, "genres": "z" * 600, "about": "w" * 1100},
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = client.get("/api/profile", headers=auth_headers).get_json()
        assert len(data["nickname"]) == 100
        assert len(data["email"]) == 255
        assert len(data["genres"]) == 500
        assert len(data["about"]) == 1000

    def test_none_fields_default_empty(self, client, auth_headers):
        res = client.put(
            "/api/profile", json={"nickname": None, "email": None, "genres": None, "about": None}, headers=auth_headers
        )
        assert res.status_code == 200


# ── Feedback ───────────────────────────────────────────────────


class TestFeedback:
    """POST /api/feedback — auth, validation, profile snapshot, IP handling."""

    def test_unauthorized(self, client):
        res = client.post("/api/feedback", json={"message": "hi"})
        assert res.status_code == 401

    def test_empty_message(self, client, auth_headers):
        res = client.post("/api/feedback", json={"message": ""}, headers=auth_headers)
        assert res.status_code == 400

    def test_none_message(self, client, auth_headers):
        res = client.post("/api/feedback", json={"message": None}, headers=auth_headers)
        assert res.status_code == 400

    def test_success_without_profile(self, client, auth_headers):
        res = client.post("/api/feedback", json={"message": "Great!"}, headers=auth_headers)
        assert res.status_code == 201

    def test_success_with_profile(self, client, auth_headers):
        # Save profile first
        client.put(
            "/api/profile",
            json={"nickname": "DJ", "email": "dj@test.com", "genres": "Rock", "about": "Music fan"},
            headers=auth_headers,
        )
        res = client.post("/api/feedback", json={"message": "Love it!"}, headers=auth_headers)
        assert res.status_code == 201

    def test_x_forwarded_for(self, client, auth_headers):
        res = client.post(
            "/api/feedback", json={"message": "Hi"}, headers={**auth_headers, "X-Forwarded-For": "9.9.9.9, 8.8.8.8"}
        )
        assert res.status_code == 201

    def test_no_bearer_prefix(self, client):
        res = client.post("/api/feedback", json={"message": "hi"}, headers={"Authorization": "Basic abc"})
        assert res.status_code == 401


# ── Logout ────────────────────────────────────────────────────


class TestLogout:
    """POST /api/logout — token invalidation, auth requirement."""

    def test_unauthorized(self, client):
        res = client.post("/api/logout")
        assert res.status_code == 401

    def test_success(self, client, auth_headers):
        res = client.post("/api/logout", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["status"] == "ok"

    def test_token_invalidated_after_logout(self, client, auth_headers):
        client.post("/api/logout", headers=auth_headers)
        # Token should no longer work
        res = client.get("/api/profile", headers=auth_headers)
        assert res.status_code == 401


# ── Invalid JSON ──────────────────────────────────────────────


class TestInvalidJson:
    """All POST/PUT endpoints reject malformed JSON with 400."""

    def test_register_invalid_json(self, client):
        res = client.post("/api/register", data="bad", content_type="application/json")
        assert res.status_code == 400

    def test_login_invalid_json(self, client):
        res = client.post("/api/login", data="bad", content_type="application/json")
        assert res.status_code == 400

    def test_feedback_invalid_json(self, client, auth_headers):
        res = client.post("/api/feedback", data="bad", content_type="application/json", headers=auth_headers)
        assert res.status_code == 400

    def test_profile_put_invalid_json(self, client, auth_headers):
        res = client.put("/api/profile", data="bad", content_type="application/json", headers=auth_headers)
        assert res.status_code == 400


# ── Ratings no IP exposure ────────────────────────────────────


class TestRatingsNoIpExposure:
    """GET /api/ratings response must not expose IP addresses."""

    def test_no_ip_in_response(self, client):
        client.post("/api/ratings", json={"station": "A - B", "score": 1})
        res = client.get("/api/ratings")
        data = res.get_json()
        assert "ip" not in data[0]


# ── Song Info (LLM) ──────────────────────────────────────────


class TestSongInfo:
    """POST /api/song-info and GET /api/song-info/health."""

    def test_song_info_requires_json(self, client):
        res = client.post("/api/song-info", data="bad", content_type="application/json")
        assert res.status_code == 400

    def test_song_info_requires_query_type(self, client):
        res = client.post("/api/song-info", json={"artist": "A", "track": "T"})
        assert res.status_code == 400
        assert "query_type" in res.get_json()["error"]

    def test_song_info_requires_artist(self, client):
        res = client.post("/api/song-info", json={"query_type": "lyrics", "track": "T"})
        assert res.status_code == 400

    def test_song_info_requires_track(self, client):
        res = client.post("/api/song-info", json={"query_type": "lyrics", "artist": "A"})
        assert res.status_code == 400

    def test_song_info_health_returns_json(self, client):
        res = client.get("/api/song-info/health")
        data = res.get_json()
        assert "ok" in data
        assert "model" in data


# ── Quiz ─────────────────────────────────────────────────────


class TestQuiz:
    """POST /api/quiz/start and POST /api/quiz/answer."""

    def test_quiz_start_requires_json(self, client):
        res = client.post("/api/quiz/start", data="bad", content_type="application/json")
        assert res.status_code == 400

    def test_quiz_start_requires_artist(self, client):
        res = client.post("/api/quiz/start", json={"track": "T"})
        assert res.status_code == 400

    def test_quiz_start_requires_track(self, client):
        res = client.post("/api/quiz/start", json={"artist": "A"})
        assert res.status_code == 400

    def test_quiz_answer_requires_json(self, client):
        res = client.post("/api/quiz/answer", data="bad", content_type="application/json")
        assert res.status_code == 400
