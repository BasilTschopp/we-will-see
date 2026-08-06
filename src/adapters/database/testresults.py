from datetime import datetime

from core.core import NavigationResult, log


def save_results(run_name: str, results: list[NavigationResult],
                 release: str = "", username: str = "") -> None:
    from adapters.database.connection import get_connection
    conn = get_connection()
    for r in results:
        conn.execute("""
            INSERT INTO testresults
                (run_name, release, status, error_detail, url, page_title,
                 method, description, element_text, source_url,
                 http_status, load_time_ms, depth, screenshot_path, username, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            run_name, release, r.status, r.error_detail, r.url, r.page_title,
            r.method, r.description, r.element_text, r.source_url,
            r.http_status, r.load_time_ms, r.depth, r.screenshot_path,
            username,
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


def list_runs_with_status(release: str = "") -> list[tuple[str, bool]]:
    """Returns list of (run_name, has_errors) ordered by run_name DESC."""
    from adapters.database.connection import get_connection
    conn = get_connection()
    if release:
        rows = conn.execute("""
            SELECT run_name,
                   MAX(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) AS has_errors
            FROM testresults
            WHERE release = ?
            GROUP BY run_name
            ORDER BY run_name DESC
        """, (release,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT run_name,
                   MAX(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) AS has_errors
            FROM testresults
            GROUP BY run_name
            ORDER BY run_name DESC
        """).fetchall()
    return [(r["run_name"], bool(r["has_errors"])) for r in rows]


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


def fetch_username(run_name: str) -> str:
    from adapters.database.connection import get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT username FROM testresults WHERE run_name = ? LIMIT 1", (run_name,)
    ).fetchone()
    return (row["username"] or "") if row else ""


def _extract_tc_key(run_name: str) -> str:
    parts = run_name.split(" - ", 2)
    return parts[2] if len(parts) >= 3 else run_name


def list_testcase_keys() -> list[str]:
    """Distinct testcase keys derived from run_name (same grouping as 'Latest per testcase')."""
    from adapters.database.connection import get_connection
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT run_name FROM testresults").fetchall()
    keys = {_extract_tc_key(r["run_name"]) for r in rows}
    return sorted(keys)


def fetch_performance(tc_key: str) -> list[tuple[str, float, float | None, float | None]]:
    """Returns (release, duration_seconds, pct_vs_previous, pct_vs_first) for the
    most recent run of tc_key in each release, ordered by release DESC. Duration
    is the timespan between the first and last step of that run. pct_vs_previous
    is the % change vs. the chronologically previous release (None for the
    oldest); pct_vs_first is the % change vs. the oldest release (None if the
    oldest release's duration is 0)."""
    from adapters.database.connection import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT run_name, release, MIN(timestamp) AS t_min, MAX(timestamp) AS t_max
        FROM testresults
        WHERE release != ''
        GROUP BY run_name
        ORDER BY run_name DESC
    """).fetchall()

    latest_per_release: dict[str, tuple] = {}
    for r in rows:
        if _extract_tc_key(r["run_name"]) != tc_key:
            continue
        release = r["release"]
        if release not in latest_per_release:
            latest_per_release[release] = (r["t_min"], r["t_max"])

    durations = []
    for release, (t_min, t_max) in latest_per_release.items():
        try:
            dt_min = datetime.strptime(t_min, "%Y-%m-%d %H:%M:%S")
            dt_max = datetime.strptime(t_max, "%Y-%m-%d %H:%M:%S")
            duration = (dt_max - dt_min).total_seconds()
        except Exception:
            duration = 0.0
        durations.append((release, duration))
    durations.sort(key=lambda x: x[0])  # ascending: oldest first

    first_duration = durations[0][1] if durations else 0.0
    result: list[tuple[str, float, float | None, float | None]] = []
    prev_duration = None
    for release, duration in durations:
        pct_prev = ((duration - prev_duration) / prev_duration * 100
                    if prev_duration else None)
        pct_first = ((duration - first_duration) / first_duration * 100
                     if first_duration else None)
        result.append((release, duration, pct_prev, pct_first))
        prev_duration = duration

    result.reverse()  # newest first for display
    return result


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


