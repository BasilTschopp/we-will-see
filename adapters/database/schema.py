from adapters.database.connection import get_connection


def create_tables():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS testcases (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            category   TEXT    NOT NULL DEFAULT '',
            yaml_text  TEXT    NOT NULL DEFAULT '',
            automated  INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS testresults (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_name     TEXT    NOT NULL,
            status       TEXT    NOT NULL DEFAULT '',
            error_detail TEXT    NOT NULL DEFAULT '',
            url          TEXT    NOT NULL DEFAULT '',
            page_title   TEXT    NOT NULL DEFAULT '',
            method       TEXT    NOT NULL DEFAULT '',
            description  TEXT    NOT NULL DEFAULT '',
            element_text TEXT    NOT NULL DEFAULT '',
            source_url   TEXT    NOT NULL DEFAULT '',
            http_status  TEXT    NOT NULL DEFAULT '',
            load_time_ms INTEGER NOT NULL DEFAULT 0,
            depth        INTEGER NOT NULL DEFAULT 0,
            timestamp    TEXT    NOT NULL DEFAULT (datetime('now'))
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

