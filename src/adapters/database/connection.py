import os
import sqlite3


def _db_path() -> str:
    path = os.environ.get("APP_DB", "").strip()
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return path
    import sys
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
        return os.path.join(base, "app.db")
    # __file__ is src/adapters/database/connection.py — go up 3 levels to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    db_dir = os.path.join(project_root, "data")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "app.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn

