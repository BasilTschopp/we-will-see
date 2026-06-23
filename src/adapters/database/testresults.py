from datetime import datetime

from core.core import NavigationResult, log


def save_results(run_name: str, results: list[NavigationResult],
                 release: str = "") -> None:
    from adapters.database.connection import get_connection
    conn = get_connection()
    for r in results:
        conn.execute("""
            INSERT INTO testresults
                (run_name, release, status, error_detail, url, page_title,
                 method, description, element_text, source_url,
                 http_status, load_time_ms, depth, screenshot_path, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            run_name, release, r.status, r.error_detail, r.url, r.page_title,
            r.method, r.description, r.element_text, r.source_url,
            r.http_status, r.load_time_ms, r.depth, r.screenshot_path,
            r.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
    conn.commit()
    log.info(f"Results saved to DB: {run_name} ({len(results)} rows)"
             + (f" [release: {release}]" if release else ""))


def fetch_results(run_name: str) -> list[NavigationResult]:
    from adapters.database.connection import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT status, error_detail, url, page_title, method,
               description, element_text, source_url, http_status,
               load_time_ms, depth, screenshot_path, timestamp
        FROM testresults
        WHERE run_name = ?
        ORDER BY timestamp
    """, (run_name,)).fetchall()
    return [
        NavigationResult(
            status=r["status"], error_detail=r["error_detail"],
            url=r["url"], page_title=r["page_title"],
            method=r["method"], description=r["description"],
            element_text=r["element_text"], source_url=r["source_url"],
            http_status=r["http_status"], load_time_ms=r["load_time_ms"],
            depth=r["depth"],
            screenshot_path=str(r["screenshot_path"] or ""),
            timestamp=str(r["timestamp"]),
        )
        for r in rows
    ]


def list_runs(release: str = "") -> list[str]:
    from adapters.database.connection import get_connection
    conn = get_connection()
    if release:
        rows = conn.execute("""
            SELECT DISTINCT run_name FROM testresults
            WHERE release = ?
            ORDER BY run_name DESC
        """, (release,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT DISTINCT run_name FROM testresults ORDER BY run_name DESC
        """).fetchall()
    return [r["run_name"] for r in rows]


def list_releases() -> list[str]:
    from adapters.database.connection import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT release FROM testresults
        WHERE release != ''
        ORDER BY release DESC
    """).fetchall()
    return [r["release"] for r in rows]


def fetch_release(run_name: str) -> str:
    from adapters.database.connection import get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT release FROM testresults WHERE run_name = ? LIMIT 1", (run_name,)
    ).fetchone()
    return (row["release"] or "") if row else ""


def delete_run(run_name: str) -> None:
    import os
    from adapters.database.connection import get_connection
    conn = get_connection()
    rows = conn.execute(
        "SELECT screenshot_path FROM testresults WHERE run_name = ? AND screenshot_path != ''",
        (run_name,)
    ).fetchall()
    for row in rows:
        path = row["screenshot_path"]
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
    conn.execute("DELETE FROM testresults WHERE run_name = ?", (run_name,))
    conn.commit()


def fetch_run_summaries(release: str = "") -> list[dict]:
    """Returns per-run stats: run_name, release, date, total, errors, pass_pct."""
    from adapters.database.connection import get_connection
    conn = get_connection()
    if release:
        rows = conn.execute("""
            SELECT
                run_name,
                release,
                MIN(timestamp)                                      AS date,
                COUNT(*)                                            AS total,
                SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END)  AS errors
            FROM testresults
            WHERE release = ?
            GROUP BY run_name
            ORDER BY date DESC
        """, (release,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT
                run_name,
                release,
                MIN(timestamp)                                      AS date,
                COUNT(*)                                            AS total,
                SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END)  AS errors
            FROM testresults
            GROUP BY run_name
            ORDER BY date DESC
        """).fetchall()
    result = []
    for r in rows:
        total  = r["total"]  or 0
        errors = r["errors"] or 0
        ok     = total - errors
        pct    = round(ok / total * 100) if total else 0
        result.append({
            "run_name": r["run_name"],
            "release":  r["release"] or "",
            "date":     (r["date"] or "")[:16],
            "total":    total,
            "errors":   errors,
            "ok":       ok,
            "pass_pct": pct,
        })
    return result
