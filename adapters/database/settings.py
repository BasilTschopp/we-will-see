from adapters.database.connection import get_connection


def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()


def get_categories() -> list[str]:
    raw = get_setting("categories", "")
    return [c.strip() for c in raw.split(",") if c.strip()]


def set_categories(cats: list[str]) -> None:
    set_setting("categories", ",".join(cats))
