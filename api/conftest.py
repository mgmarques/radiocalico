"""Pytest fixtures for Radio Calico API tests."""
import pymysql
import pytest
import app as app_module


TEST_DB = 'radiocalico_test'


def _admin_conn():
    """Connect as root without selecting a database."""
    return pymysql.connect(
        host=app_module.DB_CONFIG['host'],
        user=app_module.DB_CONFIG['user'],
        password=app_module.DB_CONFIG['password'],
        cursorclass=pymysql.cursors.DictCursor,
    )


def _setup_test_db():
    """Create the test database and tables from scratch."""
    conn = _admin_conn()
    with conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS {TEST_DB}')
        cur.execute(f'CREATE DATABASE {TEST_DB}')
        cur.execute(f'USE {TEST_DB}')
        cur.execute('''
            CREATE TABLE ratings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                station VARCHAR(255) NOT NULL,
                score TINYINT NOT NULL,
                ip VARCHAR(45) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_rating (station, ip)
            )
        ''')
        cur.execute('''
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(64) NOT NULL,
                salt VARCHAR(32) NOT NULL,
                token VARCHAR(64) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                nickname VARCHAR(100) DEFAULT '',
                email VARCHAR(255) DEFAULT '',
                genres VARCHAR(500) DEFAULT '',
                about TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        cur.execute('''
            CREATE TABLE feedback (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) DEFAULT '',
                message TEXT NOT NULL,
                ip VARCHAR(45) DEFAULT '',
                username VARCHAR(50) DEFAULT '',
                nickname VARCHAR(100) DEFAULT '',
                genres VARCHAR(500) DEFAULT '',
                about TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()


def _teardown_test_db():
    conn = _admin_conn()
    with conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS {TEST_DB}')
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def test_db():
    """Create a fresh test database for every test, point app at it."""
    _setup_test_db()
    app_module.DB_CONFIG['database'] = TEST_DB
    yield
    app_module.DB_CONFIG['database'] = 'radiocalico'
    _teardown_test_db()


@pytest.fixture
def client():
    """Flask test client."""
    app_module.app.config['TESTING'] = True
    app_module.limiter.enabled = False  # disable rate limiter in tests
    with app_module.app.test_client() as c:
        yield c
    app_module.limiter.enabled = True


@pytest.fixture
def registered_user(client):
    """Register a user and return (username, password)."""
    username, password = 'testuser', 'pass1234'
    client.post('/api/register', json={'username': username, 'password': password})
    return username, password


@pytest.fixture
def auth_token(client, registered_user):
    """Login and return a valid auth token."""
    username, password = registered_user
    res = client.post('/api/login', json={'username': username, 'password': password})
    return res.get_json()['token']


@pytest.fixture
def auth_headers(auth_token):
    """Return Authorization headers dict."""
    return {'Authorization': f'Bearer {auth_token}'}
