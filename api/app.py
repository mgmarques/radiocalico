import os
import hashlib
import hmac
import secrets
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pymysql

load_dotenv()

STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')
CORS(app, origins=[os.environ.get('CORS_ORIGIN', 'http://127.0.0.1:5000')])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'radiocalico'),
    'cursorclass': pymysql.cursors.DictCursor,
}

def get_db():
    return pymysql.connect(**DB_CONFIG)


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000).hex()
    return salt, hashed


def verify_password(password, salt, hashed):
    _, check = hash_password(password, salt)
    return hmac.compare_digest(check, hashed)


def get_user_from_token(token):
    """Look up user by auth token. Returns user row or None."""
    if not token:
        return None
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT id, username FROM users WHERE token = %s', (token,))
            user = cursor.fetchone()
    finally:
        db.close()
    return user


def require_auth():
    """Extract token from Authorization header and return user or None."""
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
    return get_user_from_token(token)


@app.route('/')
def serve_index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/api/ratings', methods=['GET'])
def get_ratings():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT id, station, score, created_at FROM ratings ORDER BY created_at DESC')
            rows = cursor.fetchall()
    finally:
        db.close()
    return jsonify(rows)


@app.route('/api/ratings/summary', methods=['GET'])
def get_ratings_summary():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                'SELECT station, '
                'SUM(score = 1) AS likes, '
                'SUM(score = 0) AS dislikes '
                'FROM ratings GROUP BY station'
            )
            rows = cursor.fetchall()
    finally:
        db.close()
    # Return as a dict keyed by station name for easy lookup
    summary = {}
    for row in rows:
        summary[row['station']] = {
            'likes': int(row['likes']),
            'dislikes': int(row['dislikes'])
        }
    return jsonify(summary)


@app.route('/api/ratings', methods=['POST'])
def post_rating():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    station = data.get('station')
    score = data.get('score')
    if not station or score is None:
        return jsonify({'error': 'station and score required'}), 400
    if score not in (0, 1):
        return jsonify({'error': 'score must be 0 or 1'}), 400
    ip = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
    ip = ip.split(',')[0].strip()  # first IP if behind proxy
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                'INSERT INTO ratings (station, score, ip) VALUES (%s, %s, %s)',
                (station, score, ip)
            )
        db.commit()
    except pymysql.err.IntegrityError:
        return jsonify({'error': 'already rated'}), 409
    finally:
        db.close()
    return jsonify({'status': 'ok'}), 201


@app.route('/api/ratings/check', methods=['GET'])
def check_rating():
    station = request.args.get('station', '')
    ip = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
    ip = ip.split(',')[0].strip()
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                'SELECT score FROM ratings WHERE station = %s AND ip = %s',
                (station, ip)
            )
            row = cursor.fetchone()
    finally:
        db.close()
    if row:
        return jsonify({'rated': True, 'score': row['score']})
    return jsonify({'rated': False})


@app.route('/api/feedback', methods=['POST'])
def post_feedback():
    user = require_auth()
    if not user:
        return jsonify({'error': 'Login required to send feedback'}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'Message required'}), 400

    # Get user's full profile data
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT nickname, email, genres, about FROM profiles WHERE user_id = %s', (user['id'],))
            profile = cursor.fetchone()

        email    = (profile['email'] if profile and profile.get('email') else '')
        nickname = (profile['nickname'] if profile and profile.get('nickname') else '')
        genres   = (profile['genres'] if profile and profile.get('genres') else '')
        about    = (profile['about'] if profile and profile.get('about') else '')

        ip = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
        ip = ip.split(',')[0].strip()
        with db.cursor() as cursor:
            cursor.execute(
                'INSERT INTO feedback (email, message, ip, username, nickname, genres, about) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (email, message, ip, user['username'], nickname, genres, about)
            )
        db.commit()
    finally:
        db.close()
    return jsonify({'status': 'ok'}), 201


@app.route('/api/register', methods=['POST'])
@limiter.limit("5/minute")
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if len(username) > 50:
        return jsonify({'error': 'Username too long'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if len(password) > 128:
        return jsonify({'error': 'Password must be at most 128 characters'}), 400

    salt, hashed = hash_password(password)
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                'INSERT INTO users (username, password_hash, salt) VALUES (%s, %s, %s)',
                (username, hashed, salt)
            )
        db.commit()
    except pymysql.err.IntegrityError:
        return jsonify({'error': 'Username already taken'}), 409
    finally:
        db.close()
    return jsonify({'status': 'ok'}), 201


@app.route('/api/login', methods=['POST'])
@limiter.limit("5/minute")
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT id, password_hash, salt FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()

        if not user or not verify_password(password, user['salt'], user['password_hash']):
            return jsonify({'error': 'Invalid username or password'}), 401

        token = secrets.token_hex(32)
        with db.cursor() as cursor:
            cursor.execute('UPDATE users SET token = %s WHERE id = %s', (token, user['id']))
        db.commit()
    finally:
        db.close()
    return jsonify({'token': token, 'username': username})


@app.route('/api/logout', methods=['POST'])
def logout():
    user = require_auth()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('UPDATE users SET token = NULL WHERE id = %s', (user['id'],))
        db.commit()
    finally:
        db.close()
    return jsonify({'status': 'ok'})


@app.route('/api/profile', methods=['GET'])
def get_profile():
    user = require_auth()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT nickname, email, genres, about FROM profiles WHERE user_id = %s', (user['id'],))
            profile = cursor.fetchone()
    finally:
        db.close()
    if not profile:
        return jsonify({'nickname': '', 'email': '', 'genres': '', 'about': ''})
    return jsonify(profile)


@app.route('/api/profile', methods=['PUT'])
def update_profile():
    user = require_auth()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    nickname = (data.get('nickname') or '')[:100]
    email    = (data.get('email') or '')[:255]
    genres   = (data.get('genres') or '')[:500]
    about    = (data.get('about') or '')[:1000]

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT id FROM profiles WHERE user_id = %s', (user['id'],))
            exists = cursor.fetchone()
            if exists:
                cursor.execute(
                    'UPDATE profiles SET nickname=%s, email=%s, genres=%s, about=%s WHERE user_id=%s',
                    (nickname, email, genres, about, user['id'])
                )
            else:
                cursor.execute(
                    'INSERT INTO profiles (user_id, nickname, email, genres, about) VALUES (%s, %s, %s, %s, %s)',
                    (user['id'], nickname, email, genres, about)
                )
        db.commit()
    finally:
        db.close()
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes')
    app.run(port=5000, debug=debug)
