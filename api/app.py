"""Radio Calico Flask REST API.

Provides endpoints for track ratings, user authentication, profile management,
and feedback submission. Serves the static frontend and streams metadata
alongside an HLS audio stream delivered via CloudFront.

All API routes are prefixed with ``/api``. Data is stored in a local MySQL 5.7
database accessed through PyMySQL with parameterized queries.
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
import uuid

import pymysql
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pythonjsonlogger import json as jsonlogger

load_dotenv()

# ── Structured JSON logging ──────────────────────────────────
log_handler = logging.StreamHandler()
log_handler.setFormatter(
    jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )
)
logger = logging.getLogger("radiocalico")
logger.handlers = [log_handler]
logger.setLevel(logging.INFO)
# Suppress default Flask/werkzeug request logs (we log our own)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
CORS(app, origins=[os.environ.get("CORS_ORIGIN", "http://127.0.0.1:5000")])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.before_request
def before_request_logging():
    """Attach request_id and start time to every request."""
    g.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    g.start_time = time.time()


@app.after_request
def after_request_logging(response):
    """Log every request in structured JSON format."""
    duration_ms = round((time.time() - getattr(g, "start_time", time.time())) * 1000, 1)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
    ip = ip.split(",")[0].strip()
    log_data = {
        "request_id": getattr(g, "request_id", "-"),
        "method": request.method,
        "path": request.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
        "ip": ip,
        "user_agent": request.headers.get("User-Agent", ""),
    }
    if response.status_code >= 500:
        logger.error("request", extra=log_data)
    elif response.status_code >= 400:
        logger.warning("request", extra=log_data)
    else:
        logger.info("request", extra=log_data)
    response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
    return response


DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "radiocalico"),
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_db():
    """Create and return a new PyMySQL database connection.

    Returns:
        pymysql.connections.Connection: An open connection configured with
        ``DictCursor`` so rows are returned as dictionaries.
    """
    return pymysql.connect(**DB_CONFIG)


def hash_password(password, salt=None):
    """Hash a password using PBKDF2-HMAC-SHA256 with 260 000 iterations.

    Args:
        password: The plaintext password to hash.
        salt: Optional hex-encoded salt. If ``None``, a random 16-byte salt
            is generated.

    Returns:
        tuple[str, str]: A ``(salt, hashed)`` pair where both values are
        hex-encoded strings.
    """
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()
    return salt, hashed


def verify_password(password, salt, hashed):
    """Verify a plaintext password against a stored salt and hash.

    Uses constant-time comparison via ``hmac.compare_digest`` to prevent
    timing attacks.

    Args:
        password: The plaintext password to verify.
        salt: The hex-encoded salt originally used to hash the password.
        hashed: The hex-encoded hash to compare against.

    Returns:
        bool: ``True`` if the password matches, ``False`` otherwise.
    """
    _, check = hash_password(password, salt)
    return hmac.compare_digest(check, hashed)


def get_user_from_token(token):
    """Look up a user by their authentication token.

    Args:
        token: The bearer token string. May be ``None`` or empty.

    Returns:
        dict | None: A dictionary with ``id`` and ``username`` keys if a
        matching user is found, or ``None`` otherwise.
    """
    if not token:
        return None
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id, username FROM users WHERE token = %s", (token,))
            user = cursor.fetchone()
    finally:
        db.close()
    return user


def require_auth():
    """Extract the bearer token from the Authorization header and resolve the user.

    Expects the header format ``Authorization: Bearer <token>``.

    Returns:
        dict | None: The authenticated user dict (``id``, ``username``), or
        ``None`` if the header is missing or the token is invalid.
    """
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    return get_user_from_token(token)


@app.route("/")
def serve_index():
    """Serve the main ``index.html`` page.

    GET /

    Returns:
        Response: The static ``index.html`` file with a 200 status.
    """
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/ratings", methods=["GET"])
def get_ratings():
    """Return all ratings ordered by most recent first.

    GET /api/ratings

    Returns:
        Response: JSON array of rating objects, each containing ``id``,
        ``station``, ``score``, and ``created_at``. Status 200.
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id, station, score, created_at FROM ratings ORDER BY created_at DESC")
            rows = cursor.fetchall()
    finally:
        db.close()
    return jsonify(rows)


@app.route("/api/ratings/summary", methods=["GET"])
def get_ratings_summary():
    """Return aggregated likes and dislikes per station.

    GET /api/ratings/summary

    Returns:
        Response: JSON object keyed by station name, each value containing
        ``likes`` (int) and ``dislikes`` (int). Status 200.
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT station, SUM(score = 1) AS likes, SUM(score = 0) AS dislikes FROM ratings GROUP BY station"
            )
            rows = cursor.fetchall()
    finally:
        db.close()
    # Return as a dict keyed by station name for easy lookup
    summary = {}
    for row in rows:
        summary[row["station"]] = {"likes": int(row["likes"]), "dislikes": int(row["dislikes"])}
    return jsonify(summary)


@app.route("/api/ratings", methods=["POST"])
def post_rating():
    """Submit a rating (like or dislike) for a track.

    POST /api/ratings

    Request body (JSON):
        station (str): Track identifier in ``"Artist - Title"`` format.
        score (int): ``1`` for like, ``0`` for dislike.

    Returns:
        Response: ``{"status": "ok"}`` with status 201 on success.

    Raises:
        400: Missing or invalid JSON, missing fields, or invalid score.
        409: The client IP has already rated this station.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    station = data.get("station")
    score = data.get("score")
    if not station or score is None:
        return jsonify({"error": "station and score required"}), 400
    if score not in (0, 1):
        return jsonify({"error": "score must be 0 or 1"}), 400
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
    ip = ip.split(",")[0].strip()  # first IP if behind proxy
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("INSERT INTO ratings (station, score, ip) VALUES (%s, %s, %s)", (station, score, ip))
        db.commit()
    except pymysql.err.IntegrityError:
        logger.info("rating_duplicate", extra={"station": station, "ip": ip})
        return jsonify({"error": "already rated"}), 409
    finally:
        db.close()
    logger.info("rating_created", extra={"station": station, "score": score, "ip": ip})
    return jsonify({"status": "ok"}), 201


@app.route("/api/ratings/check", methods=["GET"])
def check_rating():
    """Check whether the current client IP has already rated a station.

    GET /api/ratings/check?station=<station>

    Query params:
        station (str): The track identifier to check.

    Returns:
        Response: JSON with ``rated`` (bool) and, if rated, ``score`` (int).
        Status 200.
    """
    station = request.args.get("station", "")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
    ip = ip.split(",")[0].strip()
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT score FROM ratings WHERE station = %s AND ip = %s", (station, ip))
            row = cursor.fetchone()
    finally:
        db.close()
    if row:
        return jsonify({"rated": True, "score": row["score"]})
    return jsonify({"rated": False})


@app.route("/api/feedback", methods=["POST"])
def post_feedback():
    """Submit user feedback. Requires authentication.

    POST /api/feedback

    Request body (JSON):
        message (str): The feedback message text.

    The feedback record is stored alongside a snapshot of the user's profile
    data (email, nickname, genres, about) at the time of submission.

    Returns:
        Response: ``{"status": "ok"}`` with status 201 on success.

    Raises:
        400: Missing or invalid JSON, or empty message.
        401: Authentication required (missing or invalid token).
    """
    user = require_auth()
    if not user:
        return jsonify({"error": "Login required to send feedback"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message required"}), 400

    # Get user's full profile data
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT nickname, email, genres, about FROM profiles WHERE user_id = %s", (user["id"],))
            profile = cursor.fetchone()

        email = profile["email"] if profile and profile.get("email") else ""
        nickname = profile["nickname"] if profile and profile.get("nickname") else ""
        genres = profile["genres"] if profile and profile.get("genres") else ""
        about = profile["about"] if profile and profile.get("about") else ""

        ip = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
        ip = ip.split(",")[0].strip()
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO feedback (email, message, ip, username, nickname, genres, about) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (email, message, ip, user["username"], nickname, genres, about),
            )
        db.commit()
    finally:
        db.close()
    logger.info("feedback_submitted", extra={"username": user["username"]})
    return jsonify({"status": "ok"}), 201


@app.route("/api/register", methods=["POST"])
@limiter.limit("5/minute")
def register():
    """Register a new user account. Rate-limited to 5 requests per minute.

    POST /api/register

    Request body (JSON):
        username (str): Desired username (max 50 characters).
        password (str): Password (8--128 characters).

    Returns:
        Response: ``{"status": "ok"}`` with status 201 on success.

    Raises:
        400: Missing or invalid JSON, missing fields, or password/username
            length violations.
        409: Username already taken.
        429: Rate limit exceeded.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if len(username) > 50:
        return jsonify({"error": "Username too long"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if len(password) > 128:
        return jsonify({"error": "Password must be at most 128 characters"}), 400

    salt, hashed = hash_password(password)
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (%s, %s, %s)", (username, hashed, salt)
            )
        db.commit()
    except pymysql.err.IntegrityError:
        logger.info("register_duplicate", extra={"username": username})
        return jsonify({"error": "Username already taken"}), 409
    finally:
        db.close()
    logger.info("user_registered", extra={"username": username})
    return jsonify({"status": "ok"}), 201


@app.route("/api/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    """Authenticate a user and return a bearer token. Rate-limited to 5 requests per minute.

    POST /api/login

    Request body (JSON):
        username (str): The registered username.
        password (str): The account password.

    Returns:
        Response: JSON with ``token`` (str) and ``username`` (str). Status 200.

    Raises:
        400: Missing or invalid JSON, or missing fields.
        401: Invalid username or password.
        429: Rate limit exceeded.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id, password_hash, salt FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

        if not user or not verify_password(password, user["salt"], user["password_hash"]):
            logger.warning("login_failed", extra={"username": username})
            return jsonify({"error": "Invalid username or password"}), 401

        token = secrets.token_hex(32)
        with db.cursor() as cursor:
            cursor.execute("UPDATE users SET token = %s WHERE id = %s", (token, user["id"]))
        db.commit()
    finally:
        db.close()
    logger.info("user_logged_in", extra={"username": username})
    return jsonify({"token": token, "username": username})


@app.route("/api/logout", methods=["POST"])
def logout():
    """Log out the authenticated user by clearing their stored token.

    POST /api/logout

    Requires ``Authorization: Bearer <token>`` header.

    Returns:
        Response: ``{"status": "ok"}`` with status 200 on success.

    Raises:
        401: Authentication required (missing or invalid token).
    """
    user = require_auth()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("UPDATE users SET token = NULL WHERE id = %s", (user["id"],))
        db.commit()
    finally:
        db.close()
    logger.info("user_logged_out", extra={"username": user["username"]})
    return jsonify({"status": "ok"})


@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Retrieve the authenticated user's profile.

    GET /api/profile

    Requires ``Authorization: Bearer <token>`` header.

    Returns:
        Response: JSON with ``nickname``, ``email``, ``genres``, and ``about``
        fields. Returns empty strings for each field if no profile exists yet.
        Status 200.

    Raises:
        401: Authentication required (missing or invalid token).
    """
    user = require_auth()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT nickname, email, genres, about FROM profiles WHERE user_id = %s", (user["id"],))
            profile = cursor.fetchone()
    finally:
        db.close()
    if not profile:
        return jsonify({"nickname": "", "email": "", "genres": "", "about": ""})
    return jsonify(profile)


@app.route("/api/profile", methods=["PUT"])
def update_profile():
    """Create or update the authenticated user's profile.

    PUT /api/profile

    Requires ``Authorization: Bearer <token>`` header.

    Request body (JSON):
        nickname (str, optional): Display name (max 100 chars).
        email (str, optional): Email address (max 255 chars).
        genres (str, optional): Comma-separated genre tags (max 500 chars).
        about (str, optional): Free-text bio (max 1000 chars).

    If the user has no profile yet, one is created (upsert behaviour).

    Returns:
        Response: ``{"status": "ok"}`` with status 200 on success.

    Raises:
        400: Missing or invalid JSON.
        401: Authentication required (missing or invalid token).
    """
    user = require_auth()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    nickname = (data.get("nickname") or "")[:100]
    email = (data.get("email") or "")[:255]
    genres = (data.get("genres") or "")[:500]
    about = (data.get("about") or "")[:1000]

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM profiles WHERE user_id = %s", (user["id"],))
            exists = cursor.fetchone()
            if exists:
                cursor.execute(
                    "UPDATE profiles SET nickname=%s, email=%s, genres=%s, about=%s WHERE user_id=%s",
                    (nickname, email, genres, about, user["id"]),
                )
            else:
                cursor.execute(
                    "INSERT INTO profiles (user_id, nickname, email, genres, about) VALUES (%s, %s, %s, %s, %s)",
                    (user["id"], nickname, email, genres, about),
                )
        db.commit()
    finally:
        db.close()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    logger.info("server_starting", extra={"host": host, "port": 5000, "debug": debug})
    app.run(host=host, port=5000, debug=debug)
