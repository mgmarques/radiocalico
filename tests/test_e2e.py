"""End-to-end tests for Radio Calico production stack.

Tests the full nginx → gunicorn → MySQL flow by making HTTP requests
to the published Docker port. Requires the prod stack to be running:
    docker compose --profile prod up --build -d
"""

import uuid

import requests


class TestStaticFiles:
    """Nginx serves static files directly."""

    def test_index_html(self, base_url):
        res = requests.get(f'{base_url}/', timeout=10)
        assert res.status_code == 200
        assert 'Radio Calico' in res.text
        assert 'text/html' in res.headers['Content-Type']

    def test_player_js(self, base_url):
        res = requests.get(f'{base_url}/js/player.js', timeout=10)
        assert res.status_code == 200
        assert 'application/javascript' in res.headers['Content-Type'] or 'text/javascript' in res.headers['Content-Type']

    def test_player_css(self, base_url):
        res = requests.get(f'{base_url}/css/player.css', timeout=10)
        assert res.status_code == 200
        assert 'text/css' in res.headers['Content-Type']

    def test_logo_png(self, base_url):
        res = requests.get(f'{base_url}/logo.png', timeout=10)
        assert res.status_code == 200
        assert 'image/' in res.headers['Content-Type']

    def test_static_cache_headers(self, base_url):
        res = requests.get(f'{base_url}/js/player.js', timeout=10)
        assert 'Cache-Control' in res.headers


class TestSecurityHeaders:
    """Nginx adds security headers."""

    def test_x_content_type_options(self, base_url):
        res = requests.get(f'{base_url}/', timeout=10)
        assert res.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_x_frame_options(self, base_url):
        res = requests.get(f'{base_url}/', timeout=10)
        assert res.headers.get('X-Frame-Options') == 'SAMEORIGIN'

    def test_csp_header(self, base_url):
        res = requests.get(f'{base_url}/', timeout=10)
        assert 'Content-Security-Policy' in res.headers

    def test_permissions_policy(self, base_url):
        res = requests.get(f'{base_url}/', timeout=10)
        assert 'Permissions-Policy' in res.headers

    def test_server_version_hidden(self, base_url):
        res = requests.get(f'{base_url}/', timeout=10)
        server = res.headers.get('Server', '')
        assert 'nginx/' not in server  # version should be hidden


class TestHealthEndpoint:
    """Nginx health check endpoint."""

    def test_health_returns_ok(self, base_url):
        res = requests.get(f'{base_url}/health', timeout=10)
        assert res.status_code == 200
        assert res.text == 'ok'


class TestAPIProxy:
    """Nginx proxies /api/* to gunicorn."""

    def test_ratings_summary(self, base_url):
        res = requests.get(f'{base_url}/api/ratings/summary', timeout=10)
        assert res.status_code == 200
        assert res.headers['Content-Type'].startswith('application/json')

    def test_ratings_list(self, base_url):
        res = requests.get(f'{base_url}/api/ratings', timeout=10)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_register_login_profile_flow(self, base_url):
        """Full auth flow through nginx proxy."""
        unique = uuid.uuid4().hex[:8]
        username = f'e2e_{unique}'

        # Register
        res = requests.post(f'{base_url}/api/register', json={
            'username': username, 'password': 'testpass1',
        }, timeout=10)
        assert res.status_code == 201

        # Login
        res = requests.post(f'{base_url}/api/login', json={
            'username': username, 'password': 'testpass1',
        }, timeout=10)
        assert res.status_code == 200
        token = res.json()['token']

        # Get profile
        res = requests.get(f'{base_url}/api/profile', headers={
            'Authorization': f'Bearer {token}',
        }, timeout=10)
        assert res.status_code == 200

        # Logout
        res = requests.post(f'{base_url}/api/logout', headers={
            'Authorization': f'Bearer {token}',
        }, timeout=10)
        assert res.status_code == 200

    def test_rating_submission(self, base_url):
        unique = uuid.uuid4().hex[:8]
        station = f'E2E Artist - E2E Song {unique}'

        res = requests.post(f'{base_url}/api/ratings', json={
            'station': station, 'score': 1,
        }, timeout=10)
        assert res.status_code == 201

        # Verify in summary
        res = requests.get(f'{base_url}/api/ratings/summary', timeout=10)
        summary = res.json()
        assert station in summary
        assert summary[station]['likes'] == 1


class TestErrorHandling:
    """Error cases through the full stack."""

    def test_spa_fallback(self, base_url):
        """Non-existent paths return index.html (SPA fallback)."""
        res = requests.get(f'{base_url}/nonexistent/path', timeout=10)
        assert res.status_code == 200
        assert 'Radio Calico' in res.text

    def test_bad_json_on_ratings(self, base_url):
        res = requests.post(f'{base_url}/api/ratings',
                            data='not json',
                            headers={'Content-Type': 'application/json'},
                            timeout=10)
        assert res.status_code in (400, 415, 500)

    def test_unauthorized_profile(self, base_url):
        res = requests.get(f'{base_url}/api/profile', timeout=10)
        assert res.status_code == 401
