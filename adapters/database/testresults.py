from datetime import datetime

from models.models import NavigationResult, log


def save_results(run_name: str, results: list[NavigationResult]) -> None:
    from adapters.database.connection import get_connection
    conn = get_connection()
    for r in results:
        conn.execute("""
            INSERT INTO testresults
                (run_name, status, error_detail, url, page_title,
                 method, description, element_text, source_url,
                 http_status, load_time_ms, depth, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            run_name, r.status, r.error_detail, r.url, r.page_title,
            r.method, r.description, r.element_text, r.source_url,
            r.http_status, r.load_time_ms, r.depth,
            r.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
    conn.commit()
    log.info(f"Results saved to DB: {run_name} ({len(results)} rows)")


def fetch_results(run_name: str) -> list[NavigationResult]:
    from adapters.database.connection import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT status, error_detail, url, page_title, method,
               description, element_text, source_url, http_status,
               load_time_ms, depth, timestamp
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
            depth=r["depth"], timestamp=str(r["timestamp"]),
        )
        for r in rows
    ]


def list_runs() -> list[str]:
    from adapters.database.connection import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT run_name FROM testresults ORDER BY run_name DESC
    """).fetchall()
    return [r["run_name"] for r in rows]


def delete_run(run_name: str) -> None:
    from adapters.database.connection import get_connection
    conn = get_connection()
    conn.execute("DELETE FROM testresults WHERE run_name = ?", (run_name,))
    conn.commit()

