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


def get_report_errors_only() -> bool:
    return get_setting("report_errors_only", "0") == "1"


def set_report_errors_only(value: bool) -> None:
    set_setting("report_errors_only", "1" if value else "0")


def get_report_include_screenshots() -> bool:
    return get_setting("report_include_screenshots", "1") == "1"


def set_report_include_screenshots(value: bool) -> None:
    set_setting("report_include_screenshots", "1" if value else "0")
