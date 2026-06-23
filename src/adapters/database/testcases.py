from adapters.database.connection import get_connection


def upsert_testcase(name: str, yaml_text: str, category: str = "",
                    comment: str = "") -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO testcases (name, category, yaml_text, comment, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(name) DO UPDATE SET
            category   = excluded.category,
            yaml_text  = excluded.yaml_text,
            comment    = excluded.comment,
            updated_at = datetime('now')
    """, (name, category, yaml_text, comment))
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


def fetch_comment(name: str) -> str:
    conn = get_connection()
    row = conn.execute(
        "SELECT comment FROM testcases WHERE name = ?", (name,)
    ).fetchone()
    return str(row["comment"] or "") if row else ""


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


def fetch_screenshot_on_error(name: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT screenshot_on_error FROM testcases WHERE name = ?", (name,)
    ).fetchone()
    return bool(row["screenshot_on_error"]) if row else False


def update_screenshot_on_error(name: str, value: bool) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE testcases SET screenshot_on_error = ? WHERE name = ?",
        (1 if value else 0, name)
    )
    conn.commit()


def fetch_run_timeout(name: str) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT run_timeout FROM testcases WHERE name = ?", (name,)
    ).fetchone()
    return int(row["run_timeout"]) if row else 0


def update_run_timeout(name: str, minutes: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE testcases SET run_timeout = ? WHERE name = ?",
        (max(0, minutes), name)
    )
    conn.commit()


def fetch_step_timeout(name: str) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT step_timeout FROM testcases WHERE name = ?", (name,)
    ).fetchone()
    return int(row["step_timeout"]) if row else 0


def update_step_timeout(name: str, seconds: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE testcases SET step_timeout = ? WHERE name = ?",
        (max(0, seconds), name)
    )
    conn.commit()


def fetch_parallel(name: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT parallel FROM testcases WHERE name = ?", (name,)
    ).fetchone()
    return bool(row["parallel"]) if row else False


def update_parallel(name: str, value: bool) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE testcases SET parallel = ? WHERE name = ?",
        (1 if value else 0, name)
    )
    conn.commit()


def fetch_stop_on_error(name: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT stop_on_error FROM testcases WHERE name = ?", (name,)
    ).fetchone()
    return bool(row["stop_on_error"]) if row else False


def update_stop_on_error(name: str, value: bool) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE testcases SET stop_on_error = ? WHERE name = ?",
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

