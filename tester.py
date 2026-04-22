import csv
import os
import time
from dataclasses import asdict
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

from models import (
    log, NavigationItem, NavigationResult, dom_fingerprint,
    dismiss_cookie_banner,
    NAV_CLICK_SELECTORS, MODAL_TRIGGER_SELECTORS, MODAL_CONTAINER_SELECTORS,
    PAGINATION_SELECTORS, TABLE_ROW_SELECTORS,
)


class NavigationTester:

    def __init__(self, driver, items: list[NavigationItem],
                 wait_time: float = 0.3):
        self.driver = driver
        self.items = items
        self.wait_time = wait_time
        self.results: list[NavigationResult] = []

    def _safe_click(self, element) -> bool:
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", element)
            time.sleep(0.15)
            element.click()
            return True
        except Exception:
            return False

    def test_all(self) -> list[NavigationResult]:
        log.info(f"\n{'='*50}")
        log.info("PHASE 2: Testing navigations")
        log.info(f"{'='*50}")

        total = len(self.items)
        dispatch = {
            "link": self._test_link,
            "nav_click": self._test_nav_click,
            "modal": self._test_modal,
            "tab": self._test_tab,
            "pagination": self._test_pagination,
            "table_row": self._test_table_row,
            "form_input": self._test_form_input,
            "click": self._test_click,
            "assert_text": self._test_assert_text,
            "wait": self._test_wait,
        }

        for idx, item in enumerate(self.items, 1):
            log.info(f"[{idx}/{total}] {item.method}: {item.description}")
            try:
                handler = dispatch.get(item.method)
                if handler:
                    handler(item)
            except Exception as e:
                self._record(item, status="FEHLER",
                             error=f"Unexpected error: {str(e)[:200]}")

        ok = sum(1 for r in self.results if r.status == "OK")
        err = sum(1 for r in self.results if r.status == "FEHLER")
        log.info(f"\n{'='*50}")
        log.info(f"RESULT: {ok} OK  /  {err} ERRORS  /  {total} Total")
        log.info(f"{'='*50}")
        return self.results


    def _navigate_and_find(self, item, selector, match_attr="text"):
        base = item.source_url or item.url.split("#")[0]
        self.driver.get(base)
        time.sleep(self.wait_time)

        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
        for el in elements:
            try:
                if match_attr == "text":
                    val = (el.text.strip()[:50] if el.text else "")
                elif match_attr == "label":
                    val = el.text.strip()[:30] if el.text else ""
                    val = val or (el.get_attribute("aria-label") or "")
                else:
                    val = ""
                if val and item.element_text and val == item.element_text:
                    if el.is_displayed():
                        return el
            except (StaleElementReferenceException, WebDriverException):
                continue
        return None


    def _test_link(self, item: NavigationItem):
        start = time.time()
        try:
            self.driver.get(item.url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body")))
            dismiss_cookie_banner(self.driver)

            load_ms = int((time.time() - start) * 1000)
            title = self.driver.title or ""

            error = self._check_error_page()
            if error:
                self._record(item, status="FEHLER",
                             error=f"Error page: {error}",
                             title=title, load_ms=load_ms)
            else:
                self._record(item, status="OK", title=title, load_ms=load_ms)
                log.info(f"  OK ({load_ms}ms) – {title[:60]}")

        except TimeoutException:
            self._record(item, status="FEHLER",
                         error="Timeout – page did not load",
                         load_ms=int((time.time() - start) * 1000))
        except WebDriverException as e:
            self._record(item, status="FEHLER",
                         error=f"Browser error: {str(e)[:150]}",
                         load_ms=int((time.time() - start) * 1000))

    def _test_nav_click(self, item: NavigationItem):
        start = time.time()
        try:
            selector = ", ".join(NAV_CLICK_SELECTORS)
            el = self._navigate_and_find(item, selector)
            load_ms = int((time.time() - start) * 1000)

            if el and self._safe_click(el):
                time.sleep(self.wait_time)
                title = self.driver.title or ""
                error = self._check_error_page()
                if error:
                    self._record(item, status="FEHLER",
                                 error=f"Error page after click: {error}",
                                 title=title, load_ms=load_ms)
                else:
                    self._record(item, status="OK", title=title, load_ms=load_ms)
                    log.info(f"  OK ({load_ms}ms) – {title[:60]}")
            else:
                self._record(item, status="FEHLER",
                             error=f"Element '{item.element_text}' not clickable",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER",
                         error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_modal(self, item: NavigationItem):
        start = time.time()
        try:
            selector = ", ".join(MODAL_TRIGGER_SELECTORS)
            el = self._navigate_and_find(item, selector)
            load_ms = int((time.time() - start) * 1000)

            if el and self._safe_click(el):
                time.sleep(self.wait_time)
                modal_sel = ", ".join(MODAL_CONTAINER_SELECTORS)
                modals = self.driver.find_elements(By.CSS_SELECTOR, modal_sel)
                visible = [m for m in modals if m.is_displayed()]

                if visible:
                    self._record(item, status="OK",
                                 title=f"Modal opened via '{item.element_text}'",
                                 load_ms=load_ms)
                    log.info(f"  Modal OK ({load_ms}ms)")
                    try:
                        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(0.2)
                    except Exception:
                        pass
                else:
                    self._record(item, status="OK",
                                 title=f"DOM change via '{item.element_text}'",
                                 load_ms=load_ms)
            else:
                self._record(item, status="FEHLER",
                             error=f"Modal trigger '{item.element_text}' not clickable",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER",
                         error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_tab(self, item: NavigationItem):
        start = time.time()
        try:
            el = self._navigate_and_find(item, "[role='tab']")
            pre_fp = dom_fingerprint(self.driver)
            load_ms = int((time.time() - start) * 1000)

            if el and el.is_displayed():
                el.click()
                time.sleep(self.wait_time)
                changed = dom_fingerprint(self.driver) != pre_fp
                self._record(item, status="OK",
                             title=f"Tab '{item.element_text}'"
                                   f"{'' if changed else ' (no DOM change)'}",
                             load_ms=load_ms)
                log.info(f"  Tab OK ({load_ms}ms)")
            else:
                self._record(item, status="FEHLER",
                             error=f"Tab '{item.element_text}' not clickable",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER",
                         error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_pagination(self, item: NavigationItem):
        start = time.time()
        try:
            selector = ", ".join(PAGINATION_SELECTORS)
            el = self._navigate_and_find(item, selector, match_attr="label")
            pre_fp = dom_fingerprint(self.driver)
            load_ms = int((time.time() - start) * 1000)

            if el and self._safe_click(el):
                time.sleep(self.wait_time)
                changed = dom_fingerprint(self.driver) != pre_fp
                self._record(item, status="OK",
                             title=f"Pagination '{item.element_text}'"
                                   f"{'' if changed else ' (no change)'}",
                             load_ms=load_ms)
                log.info(f"  Pagination OK ({load_ms}ms)")
            else:
                self._record(item, status="FEHLER",
                             error=f"Pagination '{item.element_text}' not clickable",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER",
                         error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_table_row(self, item: NavigationItem):
        start = time.time()
        base = item.source_url or item.url.split("#")[0]
        try:
            self.driver.get(base)
            time.sleep(0.5)

            pre_url = self.driver.current_url
            pre_fp = dom_fingerprint(self.driver)

            rows = self.driver.find_elements(
                By.CSS_SELECTOR, ", ".join(TABLE_ROW_SELECTORS))
            data_rows = []
            for r in rows:
                try:
                    if not r.is_displayed():
                        continue
                    parent = r.find_element(By.XPATH, "..").tag_name.lower()
                    if parent == "thead":
                        continue
                    if "header" in (r.get_attribute("class") or "").lower():
                        continue
                    data_rows.append(r)
                except Exception:
                    continue

            clicked = False
            if data_rows:
                row = data_rows[0]
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", row)
                    time.sleep(0.15)
                    for strategy in [
                        lambda: row.find_element(By.CSS_SELECTOR, "a[href]"),
                        lambda: row.find_element(
                            By.CSS_SELECTOR,
                            "td, mat-cell, .mat-cell, .mat-mdc-cell"),
                        lambda: row,
                    ]:
                        try:
                            target = strategy()
                            if target.is_displayed():
                                target.click()
                                clicked = True
                                break
                        except (NoSuchElementException, WebDriverException):
                            continue
                    if not clicked:
                        self.driver.execute_script(
                            "arguments[0].click();", row)
                        clicked = True
                except (StaleElementReferenceException, WebDriverException):
                    try:
                        self.driver.execute_script(
                            "arguments[0].click();", row)
                        clicked = True
                    except Exception:
                        pass

            load_ms = int((time.time() - start) * 1000)

            if clicked:
                time.sleep(0.5)
                post_url = self.driver.current_url
                if post_url != pre_url:
                    title = f"Row → {post_url}"
                elif dom_fingerprint(self.driver) != pre_fp:
                    title = "Row → DOM change"
                else:
                    title = "Row clicked, no reaction"
                self._record(item, status="OK", title=title, load_ms=load_ms)
                log.info(f"  Row OK ({load_ms}ms)")
            else:
                self._record(item, status="FEHLER",
                             error="No clickable table row found",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER",
                         error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))


    def _test_form_input(self, item: NavigationItem):
        start = time.time()
        try:
            if item.source_url:
                self.driver.get(item.source_url)
                time.sleep(self.wait_time)

            el = self.driver.find_element(By.CSS_SELECTOR, item.selector)
            load_ms = int((time.time() - start) * 1000)

            if el.is_displayed():
                el.clear()
                el.send_keys(item.input_value)

                key_map = {
                    "enter": Keys.ENTER, "return": Keys.RETURN,
                    "tab": Keys.TAB, "escape": Keys.ESCAPE,
                }
                if item.submit_key:
                    key = key_map.get(item.submit_key.lower())
                    if key:
                        el.send_keys(key)
                        time.sleep(self.wait_time)

                self._record(item, status="OK",
                             title=f"Input: '{item.input_value[:40]}'"
                                   f"{' + ' + item.submit_key if item.submit_key else ''}",
                             load_ms=load_ms)
                log.info(f"  OK ({load_ms}ms) – Input in {item.selector}")
            else:
                self._record(item, status="FEHLER",
                             error=f"Field '{item.selector}' not visible",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER",
                         error=f"Field '{item.selector}': {str(e)[:150]}",
                         load_ms=int((time.time() - start) * 1000))

    def _test_click(self, item: NavigationItem):
        start = time.time()
        try:
            if item.source_url:
                self.driver.get(item.source_url)
                time.sleep(self.wait_time)

            el = self.driver.find_element(By.CSS_SELECTOR, item.selector)
            pre_url = self.driver.current_url
            pre_fp = dom_fingerprint(self.driver)
            load_ms = int((time.time() - start) * 1000)

            if self._safe_click(el):
                time.sleep(self.wait_time)
                post_url = self.driver.current_url
                if post_url != pre_url:
                    title = f"Click → {post_url}"
                elif dom_fingerprint(self.driver) != pre_fp:
                    title = f"Click → DOM change"
                else:
                    title = f"Click executed"
                error = self._check_error_page()
                if error:
                    self._record(item, status="FEHLER",
                                 error=f"Error page after click: {error}",
                                 load_ms=load_ms)
                else:
                    self._record(item, status="OK", title=title, load_ms=load_ms)
                    log.info(f"  OK ({load_ms}ms) – {title[:60]}")
            else:
                self._record(item, status="FEHLER",
                             error=f"Element '{item.selector}' not clickable",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER",
                         error=f"Klick '{item.selector}': {str(e)[:150]}",
                         load_ms=int((time.time() - start) * 1000))

    def _test_assert_text(self, item: NavigationItem):
        start = time.time()
        try:
            if item.source_url:
                self.driver.get(item.source_url)
                time.sleep(self.wait_time)

            search = item.assert_text or item.input_value
            if not search:
                self._record(item, status="FEHLER",
                             error="No assert_text defined")
                return

            if item.selector:
                try:
                    el = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, item.selector)))
                    body_text = el.text or ""
                except TimeoutException:
                    body_text = ""
            else:
                body_text = self.driver.find_element(
                    By.TAG_NAME, "body").text or ""

            load_ms = int((time.time() - start) * 1000)

            if search in body_text:
                self._record(item, status="OK",
                             title=f"Text found: '{search[:40]}'",
                             load_ms=load_ms)
                log.info(f"  OK ({load_ms}ms) – Text found")
            else:
                self._record(item, status="FEHLER",
                             error=f"Text not found: '{search[:60]}'",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER",
                         error=f"Assert: {str(e)[:150]}",
                         load_ms=int((time.time() - start) * 1000))

    def _test_wait(self, item: NavigationItem):
        try:
            seconds = float(item.input_value) if item.input_value else 1.0
        except ValueError:
            seconds = 1.0
        time.sleep(seconds)
        self._record(item, status="OK",
                     title=f"Wait {seconds}s")
        log.info(f"  OK – Wait {seconds}s")


    def _check_error_page(self) -> str:
        try:
            title = (self.driver.title or "").lower()
            for err in ["404", "not found", "error", "500", "403",
                        "forbidden", "fehler", "nicht gefunden"]:
                if err in title:
                    return f"Title contains '{err}'"

            check = self.driver.execute_script("""
                const b = document.body;
                if (!b) return {t:'', v:0, h:0};
                return {
                    t: (b.innerText||'').substring(0,500).toLowerCase(),
                    v: document.querySelectorAll('*:not(script):not(style)').length,
                    h: b.scrollHeight
                };
            """) or {}

            text = check.get("t", "")
            visible = check.get("v", 0)
            height = check.get("h", 0)

            if "page not found" in text or "seite nicht gefunden" in text:
                return "Page not found"
            if "internal server error" in text:
                return "Internal Server Error"
            if "access denied" in text or "zugriff verweigert" in text:
                return "Access denied"
            if "chunk load" in text or "chunkloaderror" in text:
                return "JavaScript chunk error"

            stripped = text.strip()
            if not stripped and visible < 10:
                return "Empty page"
            if height < 50 and not stripped:
                return "Empty page (body < 50px)"

        except Exception:
            pass
        return ""

    def _record(self, item: NavigationItem, status: str,
                error: str = "", title: str = "", load_ms: int = 0):
        error = error.replace("\n", " ").replace("\r", "")
        if status == "FEHLER":
            log.info(f"  ERROR: {error}")

        self.results.append(NavigationResult(
            status=status, error_detail=error, url=item.url,
            page_title=title, method=item.method,
            description=item.description, element_text=item.element_text,
            source_url=item.source_url, load_time_ms=load_ms,
            depth=item.depth,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))


CSV_COLUMNS = [
    "status", "error_detail", "method", "description",
    "url", "page_title", "element_text", "source_url",
    "http_status", "load_time_ms", "depth", "timestamp",
]


def export_to_csv(results: list[NavigationResult], output_path: str):
    sorted_results = sorted(
        results,
        key=lambda r: (0 if r.status == "FEHLER" else 1, r.method, r.url))

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS,
                                delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in sorted_results:
            row = asdict(r)
            writer.writerow({k: row[k] for k in CSV_COLUMNS})

    err = sum(1 for r in results if r.status == "FEHLER")
    ok = sum(1 for r in results if r.status == "OK")
    log.info(f"CSV: {output_path} ({err} errors, {ok} OK)")