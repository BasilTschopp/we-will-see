import hashlib
import logging
from dataclasses import dataclass, field

log = logging.getLogger("app")
log.setLevel(logging.DEBUG)


@dataclass
class NavigationItem:
    """Typed structure for a single testcase step."""
    url: str
    method: str
    description: str
    element_text: str = ""
    source_url: str = ""
    depth: int = 0
    selector: str = ""
    input_value: str = ""
    submit_key: str = ""
    assert_text: str = ""
    store_as: str = ""
    optional: bool = False
    foreach_var: str = ""
    sub_steps: list = field(default_factory=list)


@dataclass
class NavigationResult:
    """Typed structure for a test result."""
    status: str = ""
    error_detail: str = ""
    url: str = ""
    page_title: str = ""
    method: str = ""
    description: str = ""
    element_text: str = ""
    source_url: str = ""
    http_status: str = ""
    load_time_ms: int = 0
    depth: int = 0
    screenshot_path: str = ""
    timestamp: str = ""


NAV_CLICK_SELECTORS = [
    "nav a", "nav button",
    "[role='navigation'] a", "[role='navigation'] button",
    "aside a", ".sidebar a",
    "[role='menuitem']",
    ".menu-item", ".nav-item", "[class*='nav-link']",
    "[role='tab']",
    "header a", "header button",
]

TABLE_ROW_SELECTORS = [
    "table tbody tr",
    "mat-row", ".mat-row", ".mat-mdc-row",
    ".p-datatable tbody tr",
    ".ag-row",
    "tr[routerlink]",
]

COOKIE_ACCEPT_SELECTORS = [
    "button[id*='accept']", "button[id*='cookie']",
    "button[class*='accept']", "button[class*='consent']",
    "[class*='cookie'] button[class*='accept']",
    "[class*='consent'] button[class*='accept']",
    "#onetrust-accept-btn-handler",
    ".cc-accept", ".cc-allow", ".cc-dismiss",
]

COOKIE_BANNER_TEXTS = [
    "alle akzeptieren", "akzeptieren", "accept all", "accept",
    "allow all", "zustimmen", "einverstanden", "ok", "i agree",
]


def dom_fingerprint(driver) -> str:
    try:
        result = driver.execute_script("""
            const body = document.body;
            if (!body) return '';
            return body.innerHTML.length + '|' +
                   document.querySelectorAll('*').length + '|' +
                   (document.title || '');
        """)
        return hashlib.md5((result or "").encode(), usedforsecurity=False).hexdigest()
    except Exception:
        return ""


def dismiss_cookie_banner(driver) -> bool:
    from selenium.webdriver.common.by import By

    combined = ", ".join(COOKIE_ACCEPT_SELECTORS)
    try:
        for btn in driver.find_elements(By.CSS_SELECTOR, combined):
            try:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    log.info("  Cookie banner dismissed")
                    return True
            except Exception:
                continue
    except Exception:
        pass

    try:
        for btn in driver.find_elements(
                By.CSS_SELECTOR, "button, a[role='button']"):
            try:
                if not btn.is_displayed():
                    continue
                text = (btn.text or "").strip().lower()
                if any(t in text for t in COOKIE_BANNER_TEXTS):
                    btn.click()
                    log.info(f"  Cookie banner dismissed ('{text}')")
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False

