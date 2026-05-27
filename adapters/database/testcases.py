from adapters.database.connection import get_connection


def upsert_testcase(name: str, yaml_text: str, category: str = "") -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO testcases (name, category, yaml_text, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(name) DO UPDATE SET
            category   = excluded.category,
            yaml_text  = excluded.yaml_text,
            updated_at = datetime('now')
    """, (name, category, yaml_text))
    conn.commit()


def fetch_testcase_yaml(name: str) -> tuple[str, str]:
    """Returns (yaml_text, category)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT yaml_text, category FROM testcases WHERE name = ?", (name,)
    ).fetchone()
    if not row:
        return "", ""
    return row["yaml_text"], row["category"]


def fetch_automated(name: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT automated FROM testcases WHERE name = ?", (name,)
    ).fetchone()
    return bool(row["automated"]) if row else False


def update_automated(name: str, value: bool) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE testcases SET automated = ? WHERE name = ?",
        (1 if value else 0, name)
    )
    conn.commit()


def list_automated_testcases() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT name FROM testcases WHERE automated = 1 ORDER BY updated_at DESC"
    ).fetchall()
    return [r["name"] for r in rows]


def list_testcases() -> list[tuple[str, str]]:
    """Returns list of (name, category) ordered by updated_at desc."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT name, category FROM testcases ORDER BY updated_at DESC"
    ).fetchall()
    return [(r["name"], r["category"]) for r in rows]


def delete_testcase(name: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM testcases WHERE name = ?", (name,))
    conn.commit()


def rename_testcase(old_name: str, new_name: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE testcases SET name = ?, updated_at = datetime('now') WHERE name = ?",
        (new_name, old_name)
    )
    conn.commit()


def update_category(name: str, category: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE testcases SET category = ?, updated_at = datetime('now') WHERE name = ?",
        (category, name)
    )
    conn.commit()

