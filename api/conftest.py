"""Pytest fixtures for Radio Calico API tests.

Uses an in-memory mock database so tests run without MySQL.
"""

import re
from datetime import datetime, timezone

import app as app_module
import pymysql
import pytest

# ── In-memory mock database ──────────────────────────────────


class MockDB:
    """Shared in-memory store for all four tables."""

    def __init__(self):
        self.tables = {
            "ratings": [],
            "users": [],
            "profiles": [],
            "feedback": [],
        }
        self.auto_ids = {"ratings": 0, "users": 0, "profiles": 0, "feedback": 0}

    def next_id(self, table):
        self.auto_ids[table] += 1
        return self.auto_ids[table]


class MockCursor:
    """Minimal cursor that interprets the SQL patterns used in app.py."""

    def __init__(self, db):
        self._db = db
        self._results = []
        self._pos = 0
        self.lastrowid = None
        self.description = None

    # ── context manager ──
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def close(self):
        pass

    def execute(self, sql, args=None):
        sql = sql.strip()
        args = args or ()
        # Normalize whitespace for easier matching
        norm = " ".join(sql.split())
        self._results = []
        self._pos = 0

        if norm.upper().startswith("INSERT"):
            self._do_insert(norm, args)
        elif norm.upper().startswith("SELECT"):
            self._do_select(norm, args)
        elif norm.upper().startswith("UPDATE"):
            self._do_update(norm, args)
        elif norm.upper().startswith("DELETE"):
            self._do_delete(norm, args)
        # Ignore DDL (CREATE, DROP, USE)

    # ── INSERT ──
    def _do_insert(self, sql, args):
        table = self._extract_table_insert(sql)
        cols = self._extract_insert_cols(sql)
        row = dict(zip(cols, args, strict=False))

        # Check unique constraints
        self._check_unique(table, row)

        row_id = self._db.next_id(table)
        row["id"] = row_id
        row["created_at"] = datetime.now(tz=timezone.utc).isoformat()
        if table == "profiles":
            row["updated_at"] = row["created_at"]
        self._db.tables[table].append(row)
        self.lastrowid = row_id

    def _check_unique(self, table, row):
        """Raise IntegrityError on duplicate unique key violations."""
        if table == "ratings":
            for existing in self._db.tables["ratings"]:
                if existing["station"] == row.get("station") and existing["ip"] == row.get("ip"):
                    raise pymysql.err.IntegrityError(1062, "Duplicate entry")
        elif table == "users":
            for existing in self._db.tables["users"]:
                if existing["username"] == row.get("username"):
                    raise pymysql.err.IntegrityError(1062, "Duplicate entry")
        elif table == "profiles":
            for existing in self._db.tables["profiles"]:
                if existing["user_id"] == row.get("user_id"):
                    raise pymysql.err.IntegrityError(1062, "Duplicate entry")

    # ── SELECT ──
    def _do_select(self, sql, args):
        upper = sql.upper()

        # SUM/GROUP BY — ratings summary
        if "SUM(" in upper and "GROUP BY" in upper:
            self._do_summary()
            return

        table = self._extract_table_select(sql)
        cols = self._extract_select_cols(sql)
        rows = list(self._db.tables.get(table, []))

        # WHERE clause
        rows = self._apply_where(sql, rows, args)

        # ORDER BY created_at DESC
        if "ORDER BY" in upper:
            rows = sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)

        # LIMIT / OFFSET
        limit, offset = self._extract_limit_offset(sql, args)
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]

        # Project columns
        self._results = [self._project(r, cols) for r in rows]

    def _do_summary(self):
        """Handle: SELECT station, SUM(score=1) AS likes, SUM(score=0) AS dislikes FROM ratings GROUP BY station"""
        groups = {}
        for r in self._db.tables["ratings"]:
            s = r["station"]
            if s not in groups:
                groups[s] = {"station": s, "likes": 0, "dislikes": 0}
            if r["score"] == 1:
                groups[s]["likes"] += 1
            else:
                groups[s]["dislikes"] += 1
        self._results = list(groups.values())

    # ── UPDATE ──
    def _do_update(self, sql, args):
        table = self._extract_table_update(sql)
        set_clause, where_clause = self._split_set_where(sql)
        set_cols = self._extract_set_cols(set_clause)
        where_cols = self._extract_where_cols(where_clause)
        n_set = len(set_cols)
        set_vals = args[:n_set]
        where_vals = args[n_set:]

        for row in self._db.tables.get(table, []):
            if self._row_matches(row, where_cols, where_vals):
                for col, val in zip(set_cols, set_vals, strict=False):
                    row[col] = val

    # ── DELETE ──
    def _do_delete(self, sql, args):
        table = self._extract_table_delete(sql)
        where_cols = self._extract_where_cols(sql)
        self._db.tables[table] = [r for r in self._db.tables[table] if not self._row_matches(r, where_cols, args)]

    # ── Helpers ──
    def _extract_table_insert(self, sql):
        m = re.search(r"INTO\s+(\w+)", sql, re.IGNORECASE)
        return m.group(1) if m else ""

    def _extract_insert_cols(self, sql):
        m = re.search(r"\(([^)]+)\)\s*VALUES", sql, re.IGNORECASE)
        if m:
            return [c.strip() for c in m.group(1).split(",")]
        return []

    def _extract_table_select(self, sql):
        m = re.search(r"FROM\s+(\w+)", sql, re.IGNORECASE)
        return m.group(1) if m else ""

    def _extract_select_cols(self, sql):
        m = re.search(r"SELECT\s+(.+?)\s+FROM", sql, re.IGNORECASE)
        if not m:
            return []
        raw = m.group(1)
        cols = []
        for part in raw.split(","):
            part = part.strip()
            # Handle "SUM(...) AS alias"
            alias_m = re.search(r"AS\s+(\w+)", part, re.IGNORECASE)
            if alias_m:
                cols.append(alias_m.group(1))
            else:
                cols.append(part)
        return cols

    def _extract_table_update(self, sql):
        m = re.search(r"UPDATE\s+(\w+)", sql, re.IGNORECASE)
        return m.group(1) if m else ""

    def _extract_table_delete(self, sql):
        m = re.search(r"FROM\s+(\w+)", sql, re.IGNORECASE)
        return m.group(1) if m else ""

    def _split_set_where(self, sql):
        """Split UPDATE ... SET ... WHERE ... into set_clause and where_clause."""
        upper = sql.upper()
        set_idx = upper.index("SET ") + 4
        where_idx = upper.find("WHERE ")
        if where_idx == -1:
            return sql[set_idx:], ""
        return sql[set_idx:where_idx], sql[where_idx:]

    def _extract_set_cols(self, clause):
        """Extract column names from 'col=%s, col2=%s'."""
        return [m.strip().split("=")[0].strip() for m in clause.split(",") if "=" in m]

    def _extract_where_cols(self, sql):
        """Extract column names from WHERE col = %s AND col2 = %s."""
        upper = sql.upper()
        idx = upper.find("WHERE ")
        if idx == -1:
            return []
        where_part = sql[idx + 6 :]
        parts = re.split(r"\s+AND\s+", where_part, flags=re.IGNORECASE)
        cols = []
        for p in parts:
            m = re.match(r"\s*(\w+)\s*=", p)
            if m:
                cols.append(m.group(1))
        return cols

    def _apply_where(self, sql, rows, args):
        """Filter rows by WHERE clause. Handles %s params after LIMIT/OFFSET params are excluded."""
        where_cols = self._extract_where_cols(sql)
        if not where_cols:
            return rows

        # Count how many %s are in WHERE vs LIMIT/OFFSET
        upper = sql.upper()
        where_idx = upper.find("WHERE ")
        if where_idx == -1:
            return rows

        # Find the end of WHERE clause (before ORDER BY, LIMIT, etc.)
        where_end = len(sql)
        for kw in ["ORDER BY", "LIMIT", "GROUP BY"]:
            ki = upper.find(kw, where_idx)
            if ki != -1 and ki < where_end:
                where_end = ki

        where_section = sql[where_idx:where_end]
        n_where_params = where_section.count("%s")
        where_vals = args[:n_where_params]

        return [r for r in rows if self._row_matches(r, where_cols, where_vals)]

    def _extract_limit_offset(self, sql, args):
        """Extract LIMIT and OFFSET values from the query."""
        upper = sql.upper()
        limit = None
        offset = 0

        # Count %s in WHERE to know where LIMIT/OFFSET params start
        limit_idx = upper.find("LIMIT ")
        if limit_idx == -1:
            return None, 0

        # Count %s before LIMIT
        before_limit = sql[:limit_idx]
        n_before = before_limit.count("%s")

        # LIMIT %s OFFSET %s
        after_limit = sql[limit_idx:]
        n_limit_params = after_limit.count("%s")

        if n_limit_params >= 1:
            limit = int(args[n_before])
        if n_limit_params >= 2:
            offset = int(args[n_before + 1])

        return limit, offset

    def _row_matches(self, row, cols, vals):
        for col, val in zip(cols, vals, strict=False):
            if row.get(col) != val:
                return False
        return True

    def _project(self, row, cols):
        return {c: row.get(c) for c in cols}

    def fetchone(self):
        if self._pos < len(self._results):
            r = self._results[self._pos]
            self._pos += 1
            return r
        return None

    def fetchall(self):
        results = self._results[self._pos :]
        self._pos = len(self._results)
        return results


class MockConnection:
    """Mock PyMySQL connection backed by a shared MockDB."""

    def __init__(self, db):
        self._db = db

    def cursor(self):
        return MockCursor(self._db)

    def commit(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def test_db(monkeypatch):
    """Patch get_db to return an in-memory mock connection."""
    db = MockDB()

    def mock_get_db():
        return MockConnection(db)

    monkeypatch.setattr(app_module, "get_db", mock_get_db)
    yield


@pytest.fixture
def client():
    """Flask test client."""
    app_module.app.config["TESTING"] = True
    app_module.limiter.enabled = False  # disable rate limiter in tests
    with app_module.app.test_client() as c:
        yield c
    app_module.limiter.enabled = True


@pytest.fixture
def registered_user(client):
    """Register a user and return (username, password)."""
    username, password = "testuser", "pass1234"
    client.post("/api/register", json={"username": username, "password": password})
    return username, password


@pytest.fixture
def auth_token(client, registered_user):
    """Login and return a valid auth token."""
    username, password = registered_user
    res = client.post("/api/login", json={"username": username, "password": password})
    return res.get_json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Return Authorization headers dict."""
    return {"Authorization": f"Bearer {auth_token}"}
