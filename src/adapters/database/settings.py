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


_DEFAULT_RELEASE_REGEX    = r"rc-release_([\w.-]+)"
_DEFAULT_RELEASE_LABEL    = "Release"
_DEFAULT_RELEASE_SELECTOR = 'input[aria-label="Frontend"]'


def get_release_regex() -> str:
    return get_setting("release_regex", _DEFAULT_RELEASE_REGEX)


def set_release_regex(pattern: str) -> None:
    set_setting("release_regex", pattern)


def get_release_label() -> str:
    return get_setting("release_label", _DEFAULT_RELEASE_LABEL)


def set_release_label(label: str) -> None:
    set_setting("release_label", label)


def get_release_selector() -> str:
    return get_setting("release_selector", _DEFAULT_RELEASE_SELECTOR)


def set_release_selector(selector: str) -> None:
    set_setting("release_selector", selector)


_DEFAULT_ERROR_PAGE_KEYWORDS = [
    "404", "not found", "500", "403", "forbidden",
    "fehler", "nicht gefunden", "wartungsarbeiten",
    "nicht erreichbar", "refused", "err_connection",
]


def get_error_page_keywords() -> list[str]:
    raw = get_setting("error_page_keywords", "")
    if not raw:
        return list(_DEFAULT_ERROR_PAGE_KEYWORDS)
    return [k.strip() for k in raw.split("\n") if k.strip()]


def set_error_page_keywords(keywords: list[str]) -> None:
    set_setting("error_page_keywords", "\n".join(keywords))


def get_screenshot_on_error() -> bool:
    return get_setting("screenshot_on_error", "0") == "1"


def set_screenshot_on_error(value: bool) -> None:
    set_setting("screenshot_on_error", "1" if value else "0")


def get_stop_on_error() -> bool:
    return get_setting("stop_on_error", "0") == "1"


def set_stop_on_error(value: bool) -> None:
    set_setting("stop_on_error", "1" if value else "0")


def get_run_timeout() -> int:
    try:
        return max(0, int(get_setting("run_timeout", "0")))
    except ValueError:
        return 0


def set_run_timeout(minutes: int) -> None:
    set_setting("run_timeout", str(max(0, minutes)))


def get_step_timeout() -> int:
    try:
        return max(0, int(get_setting("step_timeout", "0")))
    except ValueError:
        return 0


def set_step_timeout(seconds: int) -> None:
    set_setting("step_timeout", str(max(0, seconds)))


def get_parallel_execution() -> bool:
    return get_setting("parallel_execution", "0") == "1"


def set_parallel_execution(value: bool) -> None:
    set_setting("parallel_execution", "1" if value else "0")


def get_performance_threshold_prev() -> float:
    try:
        return max(0.0, float(get_setting("performance_threshold_prev", "0")))
    except ValueError:
        return 0.0


def set_performance_threshold_prev(percent: float) -> None:
    set_setting("performance_threshold_prev", str(max(0.0, percent)))


def get_performance_threshold_first() -> float:
    try:
        return max(0.0, float(get_setting("performance_threshold_first", "0")))
    except ValueError:
        return 0.0


def set_performance_threshold_first(percent: float) -> None:
    set_setting("performance_threshold_first", str(max(0.0, percent)))


