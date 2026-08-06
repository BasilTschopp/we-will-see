import os
import re
import sqlite3

from adapters.database.dbconfig import load_db_config


def _db_path(sqlite_path_override: str = "") -> str:
    path = os.environ.get("APP_DB", "").strip() or sqlite_path_override.strip()
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return path
    import sys
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
        db_dir = os.path.join(base, "data", "database")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "app.db")
    # __file__ is src/adapters/database/connection.py — go up 3 levels to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    db_dir = os.path.join(project_root, "data", "database")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "app.db")


class _PgConnection:
    """Adapts a psycopg2 connection to the sqlite3.Connection subset this
    codebase relies on: .execute()/.executescript() returning a cursor with
    .fetchone()/.fetchall() and dict-style row access, plus .commit()."""

    def __init__(self, pg_conn):
        self._conn = pg_conn

    def execute(self, sql: str, params=()):
        import psycopg2.extras
        translated = re.sub(r"datetime\('now'\)", "CURRENT_TIMESTAMP", sql)
        translated = translated.replace("?", "%s")
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(translated, params)
        return cur

    def executescript(self, sql: str):
        cur = self._conn.cursor()
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _pg_connect(cfg: dict) -> "_PgConnection":
    import psycopg2
    conn = psycopg2.connect(
        host=cfg["pg_host"],
        port=cfg["pg_port"] or 5432,
        dbname=cfg["pg_dbname"],
        user=cfg["pg_user"],
        password=cfg["pg_password"],
    )
    return _PgConnection(conn)


def get_connection():
    cfg = load_db_config()
    if cfg.get("engine") == "postgres":
        return _pg_connect(cfg)
    conn = sqlite3.connect(_db_path(cfg.get("sqlite_path", "")))
    conn.row_factory = sqlite3.Row
    return conn

