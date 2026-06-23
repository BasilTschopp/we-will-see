from adapters.database.connection import get_connection


def create_tables():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS testcases (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL UNIQUE,
            category            TEXT    NOT NULL DEFAULT '',
            yaml_text           TEXT    NOT NULL DEFAULT '',
            automated           INTEGER NOT NULL DEFAULT 0,
            screenshot_on_error INTEGER NOT NULL DEFAULT 0,
            run_timeout         INTEGER NOT NULL DEFAULT 0,
            step_timeout        INTEGER NOT NULL DEFAULT 0,
            parallel            INTEGER NOT NULL DEFAULT 0,
            stop_on_error       INTEGER NOT NULL DEFAULT 0,
            created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS presets (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL UNIQUE,
            url      TEXT    NOT NULL DEFAULT '',
            username TEXT    NOT NULL DEFAULT '',
            password TEXT    NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS testresults (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
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
            timestamp       TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    # migration: add automated column to existing databases
    try:
        conn.execute(
            "ALTER TABLE testcases ADD COLUMN automated INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    # migration: add comment column to existing databases
    try:
        conn.execute(
            "ALTER TABLE testcases ADD COLUMN comment TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    # migration: add release column to testresults
    try:
        conn.execute(
            "ALTER TABLE testresults ADD COLUMN release TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    # migration: add screenshot_on_error column to testcases
    try:
        conn.execute(
            "ALTER TABLE testcases ADD COLUMN screenshot_on_error INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    # migration: add screenshot_path column to testresults
    try:
        conn.execute(
            "ALTER TABLE testresults ADD COLUMN screenshot_path TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    # migration: add run_timeout, step_timeout and parallel columns to testcases
    for col in ("run_timeout INTEGER NOT NULL DEFAULT 0",
                "step_timeout INTEGER NOT NULL DEFAULT 0",
                "parallel INTEGER NOT NULL DEFAULT 0",
                "stop_on_error INTEGER NOT NULL DEFAULT 0"):
        try:
            conn.execute(f"ALTER TABLE testcases ADD COLUMN {col}")
            conn.commit()
        except Exception:
            pass

