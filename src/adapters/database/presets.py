from adapters.database.connection import get_connection
from adapters.encryption.crypto import encrypt, decrypt


def list_presets() -> list[str]:
    conn = get_connection()
    rows = conn.execute("SELECT name FROM presets ORDER BY name").fetchall()
    return [r["name"] for r in rows]


def get_preset(name: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT name, url, username, password FROM presets WHERE name = ?",
        (name,)
    ).fetchone()
    if not row:
        return None
    return {
        "name":     row["name"],
        "url":      row["url"],
        "username": decrypt(row["username"]),
        "password": decrypt(row["password"]),
    }


def upsert_preset(name: str, url: str, username: str, password: str) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO presets (name, url, username, password) VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            url      = excluded.url,
            username = excluded.username,
            password = excluded.password
    """, (name, url, encrypt(username) if username else "", encrypt(password) if password else ""))
    conn.commit()


def delete_preset(name: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM presets WHERE name = ?", (name,))
    conn.commit()
