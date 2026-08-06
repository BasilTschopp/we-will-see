from adapters.database.connection import get_connection
from adapters.database.dbconfig import load_db_config


def create_tables():
    conn = get_connection()
    pk = "SERIAL PRIMARY KEY" if load_db_config().get("engine") == "postgres" \
        else "INTEGER PRIMARY KEY AUTOINCREMENT"
    conn.executescript(f"""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS testcases (
            id                  {pk},
            name                TEXT    NOT NULL UNIQUE,
            category            TEXT    NOT NULL DEFAULT '',
            yaml_text           TEXT    NOT NULL DEFAULT '',
            automated           INTEGER NOT NULL DEFAULT 0,
            created             TEXT    NOT NULL DEFAULT (CURRENT_TIMESTAMP),
            updated             TEXT    NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        );

        CREATE TABLE IF NOT EXISTS presets (
            id       {pk},
            name     TEXT    NOT NULL UNIQUE,
            url      TEXT    NOT NULL DEFAULT '',
            username TEXT    NOT NULL DEFAULT '',
            password TEXT    NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS testresults (
            id              {pk},
            run_name        TEXT    NOT NULL,
            release         TEXT    NOT NULL DEFAULT '',
            status          TEXT    NOT NULL DEFAULT '',
            error_detail    TEXT    NOT NULL DEFAULT '',
            url             TEXT    NOT NULL DEFAULT '',
            page_title      TEXT    NOT NULL DEFAULT '',
            method          TEXT    NOT NULL DEFAULT '',
            description     TEXT    NOT NULL DEFAULT '',
            element_text    TEXT    NOT NULL DEFAULT '',
            source_url      TEXT    NOT NULL DEFAULT '',
            http_status     TEXT    NOT NULL DEFAULT '',
            load_time_ms    INTEGER NOT NULL DEFAULT 0,
            depth           INTEGER NOT NULL DEFAULT 0,
            screenshot_path TEXT    NOT NULL DEFAULT '',
            username        TEXT    NOT NULL DEFAULT '',
            timestamp       TEXT    NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        );
    """)
    conn.commit()
    # migration: add automated column to existing databases
    try:
        conn.execute(
            "ALTER TABLE testcases ADD COLUMN automated INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except Exception:
        conn.rollback()
    # migration: add comment column to existing databases
    try:
        conn.execute(
            "ALTER TABLE testcases ADD COLUMN comment TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        conn.rollback()
    # migration: add release column to testresults
    try:
        conn.execute(
            "ALTER TABLE testresults ADD COLUMN release TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        conn.rollback()
    # migration: add screenshot_path column to testresults
    try:
        conn.execute(
            "ALTER TABLE testresults ADD COLUMN screenshot_path TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        conn.rollback()
    # migration: add username column to testresults
    try:
        conn.execute(
            "ALTER TABLE testresults ADD COLUMN username TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        conn.rollback()
    # migration: rename created_at/updated_at to created/updated on testcases
    for old, new in (("created_at", "created"), ("updated_at", "updated")):
        try:
            conn.execute(
                f"ALTER TABLE testcases RENAME COLUMN {old} TO {new}")
            conn.commit()
        except Exception:
            conn.rollback()
    # migration: execution settings (screenshot_on_error, run_timeout,
    # step_timeout, stop_on_error) moved from per-testcase to global settings
    for col in ("screenshot_on_error", "run_timeout", "step_timeout", "stop_on_error"):
        try:
            conn.execute(f"ALTER TABLE testcases DROP COLUMN {col}")
            conn.commit()
        except Exception:
            conn.rollback()

