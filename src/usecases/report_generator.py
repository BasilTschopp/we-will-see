import os
import base64
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_REPORTS_DIR = os.path.join(_PROJECT_ROOT, "data", "reports")

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f0f2f5;
    color: #1d1d1f;
    font-size: 13px;
    line-height: 1.5;
}
.header {
    background: #2c3e50;
    color: white;
    padding: 28px 0;
}
.header-inner {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 40px;
}
h1 {
    font-size: 24px;
    font-weight: 600;
    letter-spacing: -0.3px;
}
.date {
    font-size: 13px;
    color: rgba(255,255,255,0.5);
    margin-top: 4px;
}
.container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 32px 40px;
}
.run-card {
    background: white;
    border-radius: 10px;
    margin-bottom: 28px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}
.run-header {
    padding: 18px 24px 14px;
    border-bottom: 1px solid #f0f0f2;
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-wrap: wrap;
}
.run-title {
    font-size: 15px;
    font-weight: 600;
    color: #1d1d1f;
}
.run-release {
    font-size: 11px;
    color: #8899a6;
    background: #f5f5f7;
    padding: 2px 8px;
    border-radius: 10px;
    white-space: nowrap;
}
.summary {
    display: flex;
    gap: 20px;
    align-items: center;
    padding: 11px 24px;
    background: #fafafa;
    border-bottom: 1px solid #f0f0f2;
}
.stat { font-size: 12px; font-weight: 600; }
.stat-ok  { color: #4db6a0; }
.stat-err { color: #d47272; }
.stat-total { color: #8899a6; font-weight: 400; }
.table-wrap { overflow-x: auto; }
table {
    width: 100%;
    border-collapse: collapse;
}
th {
    padding: 9px 16px;
    text-align: left;
    font-size: 10px;
    font-weight: 700;
    color: #8899a6;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    background: #fafafa;
    border-bottom: 1px solid #f0f0f2;
    white-space: nowrap;
}
td {
    padding: 9px 16px;
    border-bottom: 1px solid #f7f7f9;
    vertical-align: top;
}
tr:last-child td { border-bottom: none; }
tr.error-row td  { background: #fff9f9; }
.status-ok {
    color: #4db6a0;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.status-err {
    color: #d47272;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.td-time {
    color: #8899a6;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}
.td-ms {
    color: #8899a6;
    white-space: nowrap;
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.td-desc { color: #3a3a3c; max-width: 300px; }
.td-err  { color: #d47272; font-size: 12px; max-width: 280px; word-break: break-word; }
.no-results {
    padding: 20px 24px;
    color: #8899a6;
    font-size: 12px;
    font-style: italic;
}
.screenshots {
    padding: 20px 24px;
    border-top: 1px solid #f0f0f2;
}
.screenshots h3 {
    font-size: 10px;
    font-weight: 700;
    color: #8899a6;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 16px;
}
.screenshot-item { margin-bottom: 24px; }
.screenshot-item:last-child { margin-bottom: 0; }
.screenshot-caption {
    font-size: 12px;
    font-weight: 600;
    color: #d47272;
    margin-bottom: 8px;
}
.screenshot-img {
    max-width: 100%;
    border-radius: 6px;
    border: 1px solid #e8e8ea;
    display: block;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
"""

def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_report(run_names: list[str]) -> str:
    from adapters.database.testresults import fetch_results, fetch_release
    from adapters.database.settings import get_report_errors_only, get_report_include_screenshots

    os.makedirs(_REPORTS_DIR, exist_ok=True)
    errors_only         = get_report_errors_only()
    include_screenshots = get_report_include_screenshots()
    date_str = datetime.now().strftime("%d.%m.%Y  %H:%M")
    runs_html = ""

    for run_name in run_names:
        results = fetch_results(run_name)
        release = fetch_release(run_name)
        if not results:
            continue

        sorted_results = sorted(results, key=lambda r: r.timestamp)
        display_results = [r for r in sorted_results if r.status == "ERROR"] if errors_only else sorted_results

        ok_count  = sum(1 for r in results if r.status == "OK")
        err_count = sum(1 for r in results if r.status == "ERROR")

        rows_html = ""
        screenshots_html = ""

        for result in display_results:
            time_str = result.timestamp.split(" ", 1)[1][:8] if " " in result.timestamp else ""
            is_error = result.status == "ERROR"
            row_class    = "error-row" if is_error else ""
            status_class = "status-err" if is_error else "status-ok"
            status_label = "Error" if is_error else "OK"

            desc = _esc(result.description)
            if result.page_title:
                desc += f" — {_esc(result.page_title)}"

            error = _esc(result.error_detail)
            ms    = f"{result.load_time_ms}&nbsp;ms" if result.load_time_ms else ""

            rows_html += f"""
                    <tr class="{row_class}">
                        <td class="td-time">{time_str}</td>
                        <td><span class="{status_class}">{status_label}</span></td>
                        <td class="td-desc">{desc}</td>
                        <td class="td-ms">{ms}</td>
                        <td class="td-err">{error}</td>
                    </tr>"""

            if (include_screenshots and is_error
                    and result.screenshot_path and os.path.isfile(result.screenshot_path)):
                try:
                    with open(result.screenshot_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    cap = _esc(result.description[:120])
                    screenshots_html += f"""
                <div class="screenshot-item">
                    <div class="screenshot-caption">{cap}</div>
                    <img class="screenshot-img" src="data:image/png;base64,{b64}" alt="Screenshot">
                </div>"""
                except Exception:
                    pass

        release_html = f'<span class="run-release">Release {_esc(release)}</span>' if release else ""
        badge = " · Errors only" if errors_only else ""

        table_html = f"""
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Status</th>
                            <th>Description</th>
                            <th style="text-align:right">Duration</th>
                            <th>Error</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}
                    </tbody>
                </table>
            </div>""" if display_results else '<div class="no-results">No results to display.</div>'

        screenshots_section = f"""
            <div class="screenshots">
                <h3>Screenshots</h3>
                {screenshots_html}
            </div>""" if screenshots_html else ""

        runs_html += f"""
        <div class="run-card">
            <div class="run-header">
                <span class="run-title">{_esc(run_name)}{badge}</span>
                {release_html}
            </div>
            <div class="summary">
                <span class="stat stat-ok">&#10003; {ok_count} OK</span>
                <span class="stat stat-err">&#10007; {err_count} Error{'s' if err_count != 1 else ''}</span>
                <span class="stat stat-total">{len(results)} total</span>
            </div>
            {table_html}
            {screenshots_section}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Test Report</title>
    <style>{_CSS}</style>
</head>
<body>
    <div class="header">
        <div class="header-inner">
            <h1>Test Report</h1>
            <div class="date">{date_str}</div>
        </div>
    </div>
    <div class="container">
        {runs_html}
    </div>
</body>
</html>"""

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "_".join(n.replace(":", "-").replace("/", "-")[:30] for n in run_names[:2])
    path = os.path.join(_REPORTS_DIR, f"{ts}_{safe}.html")

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return path
