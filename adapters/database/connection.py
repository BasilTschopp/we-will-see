import os
import sqlite3


def _db_path() -> str:
    path = os.environ.get("BUGULA_DB", "").strip()
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return path
    import sys
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, "bugula.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn

