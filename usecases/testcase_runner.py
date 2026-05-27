import time
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

from models.models import (
    log, NavigationItem, NavigationResult, dom_fingerprint,
    dismiss_cookie_banner,
    NAV_CLICK_SELECTORS, MODAL_TRIGGER_SELECTORS, MODAL_CONTAINER_SELECTORS,
    PAGINATION_SELECTORS, TABLE_ROW_SELECTORS,
)
from usecases.testcase_reader import load_testcases
from usecases.testcase_writer import save_testcase
from usecases.testcase_recorder import SessionRecorder

def run_test(app, tc_names: list[str], headless: bool = True):
    from adapters.browser.driver import start_browser, quit_browser
    from adapters.browser.login import login
    from adapters.database.testresults import save_results

    try:
        all_items = []
        url = ""
        browser_name = "chrome"
        username = ""
        password = ""
        private = False

        for name in tc_names:
            items, meta = load_testcases(name)
            all_items.extend(items)
            if meta.get("url"):
                url = meta["url"]
            if meta.get("browser"):
                browser_name = meta["browser"].strip().lower()
            if meta.get("username"):
                username = str(meta["username"]).strip()
            if meta.get("password"):
                password = str(meta["password"]).strip()
            if meta.get("private"):
                private = bool(meta["private"])

        if not url:
            log.error("No URL found in YAML meta.")
            from tkinter import messagebox
            app.root.after(0, lambda: messagebox.showwarning(
                "", "No URL found in testcases."))
            return

        if browser_name not in ("chrome", "edge", "firefox"):
            browser_name = "chrome"

        app.driver = start_browser(headless=headless,
                                   browser=browser_name, private=private)
        if not app.running:
            return

        login(app.driver, url, username, password)
        dismiss_cookie_banner(app.driver)
        if not app.running:
            return

        ts = datetime.now().strftime("%y.%m.%d - %H:%M")
        result_name = f"{ts} - {', '.join(tc_names)}"

        tester = NavigationTester(
            driver=app.driver, items=all_items)
        app.results = tester.test_all()

        save_results(result_name, app.results)

        ok  = sum(1 for r in app.results if r.status == "OK")
        err = sum(1 for r in app.results if r.status == "FEHLER")
        log.info(f"Done — {ok} OK, {err} errors")
        if err:
            from adapters.email_notifier import send_failure_alert
            try:
                send_failure_alert(result_name, app.results)
            except Exception as mail_exc:
                log.error(f"Email alert failed: {mail_exc}")
                from tkinter import messagebox
                app.root.after(0, lambda e=mail_exc: messagebox.showerror(
                    "Email Alert", f"Failed to send alert email:\n{e}"))
        app.root.after(0, app._refresh_results_list)

    except Exception as e:
        log.error(f"Error: {e}")
    finally:
        from adapters.browser.driver import quit_browser
        quit_browser(app.driver)
        app.driver  = None
        app.running = False
        app.root.after(0, app._set_running, False)


def run_automated_cli():
    from adapters.database.testcases import list_automated_testcases
    from adapters.browser.driver import start_browser, quit_browser
    from adapters.browser.login import login
    from adapters.database.testresults import save_results

    names = list_automated_testcases()
    if not names:
        print("No automated testcases defined.")
        return

    print(f"Running {len(names)} automated testcase(s): {', '.join(names)}")
    driver = None
    try:
        all_items, url, browser_name, username, password, private = [], "", "chrome", "", "", False
        for name in names:
            items, meta = load_testcases(name)
            all_items.extend(items)
            if meta.get("url"):      url          = meta["url"]
            if meta.get("browser"):  browser_name = meta["browser"].strip().lower()
            if meta.get("username"): username     = str(meta["username"]).strip()
            if meta.get("password"): password     = str(meta["password"]).strip()
            if meta.get("private"):  private      = bool(meta["private"])

        if not url:
            print("ERROR: No URL found in testcases.")
            return
        if browser_name not in ("chrome", "edge", "firefox"):
            browser_name = "chrome"

        driver = start_browser(headless=True, browser=browser_name, private=private)
        login(driver, url, username, password)
        dismiss_cookie_banner(driver)

        ts          = datetime.now().strftime("%y.%m.%d - %H:%M")
        result_name = f"{ts} - {', '.join(names)}"
        results     = NavigationTester(driver=driver, items=all_items).test_all()

        save_results(result_name, results)

        ok  = sum(1 for r in results if r.status == "OK")
        err = sum(1 for r in results if r.status == "FEHLER")
        print(f"Done — {ok} OK, {err} errors  |  {result_name}")
        if err:
            from adapters.email_notifier import send_failure_alert
            send_failure_alert(result_name, results, automated=True)

    except Exception as e:
        print(f"ERROR: {e}")
        log.error(f"CLI run error: {e}")
    finally:
        quit_browser(driver)


def run_record(app, url: str, tc_name: str,
               browser_name: str = "chrome",
               username: str = "", password: str = "",
               private: bool = False, category: str = "",
               no_wait: bool = False):
    from adapters.browser.driver import start_browser, quit_browser
    from adapters.browser.login import login

    try:
        app.driver = start_browser(headless=False, browser=browser_name,
                                   private=private)
        crawl_url = login(app.driver, url, username, password)

        recorder = SessionRecorder(app.driver, crawl_url)
        recorder.start()
        app.recorder = recorder

        log.info("Recordingâ€¦ close browser or press Stop to finish.")

        def _tick():
            if not app.running:
                return
            n = recorder.event_count()
            try:
                app.root.after(0, app._update_record_status,
                               f"Recordingâ€¦ {n} events captured")
            except Exception:
                pass
            import threading
            threading.Timer(1.0, _tick).start()

        _tick()

        while app.running:
            try:
                _ = app.driver.current_url
            except Exception:
                log.info("Browser closed by user — stopping recorder.")
                break
            time.sleep(0.5)

        recorder.stop()

        yaml_text = recorder.to_yaml(
            name=tc_name,
            url=url,
            browser=browser_name,
            username=username,
            password=password,
            no_wait=no_wait,
        )

        saved_name = save_testcase(
            name=tc_name,
            yaml_text=yaml_text,
            category=category,
        )

        log.info(f"Recording saved: {saved_name}")
        app.root.after(0, app._on_record_saved, saved_name)

    except Exception as e:
        log.error(f"Recording error: {e}")
        import traceback; traceback.print_exc()
    finally:
        from adapters.browser.driver import quit_browser
        quit_browser(app.driver)
        app.driver   = None
        app.recorder = None
        app.running  = False
        app.root.after(0, app._set_running, False)
        app.root.after(0, app._update_record_status, "")


# ---------------------------------------------------------------------------
# NavigationTester — executes testcase steps in the browser
# ---------------------------------------------------------------------------

class NavigationTester:

    def __init__(self, driver, items: list[NavigationItem]):
        self.driver  = driver
        self.items   = items
        self.results: list[NavigationResult] = []

    def _safe_click(self, element) -> bool:
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", element)
            time.sleep(0.05)
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
            "link":        self._test_link,
            "nav_click":   self._test_nav_click,
            "modal":       self._test_modal,
            "tab":         self._test_tab,
            "pagination":  self._test_pagination,
            "table_row":   self._test_table_row,
            "form_input":  self._test_form_input,
            "click":       self._test_click,
            "assert_text": self._test_assert_text,
            "wait":        self._test_wait,
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


        ok  = sum(1 for r in self.results if r.status == "OK")
        err = sum(1 for r in self.results if r.status == "FEHLER")
        log.info(f"\n{'='*50}")
        log.info(f"RESULT: {ok} OK  /  {err} ERRORS  /  {total} Total")
        log.info(f"{'='*50}")
        return self.results

    def _navigate_and_find(self, item, selector, match_attr="text"):
        base = item.source_url or item.url.split("#")[0]
        self.driver.get(base)
        self._wait_for_dom_stable()
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
            from urllib.parse import urlparse
            current_base = self.driver.current_url.split("#")[0]
            target_base  = item.url.split("#")[0]

            if current_base == target_base and "#" in item.url:
                hash_part = item.url.split("#", 1)[1]
                pre_fp = dom_fingerprint(self.driver)
                self.driver.execute_script(
                    f"window.location.hash = '{hash_part}'")
                try:
                    WebDriverWait(self.driver, 5).until(
                        lambda d: hash_part in d.current_url)
                except TimeoutException:
                    pass
                self._wait_for_dom_stable(pre_fp=pre_fp)
            else:
                self.driver.get(item.url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body")))
                # JS-OAuth-Redirects abwarten: URL bis zu 5s pollen
                expected_host = urlparse(item.url).netloc
                deadline_url  = time.time() + 5
                last_url      = self.driver.current_url
                while time.time() < deadline_url:
                    time.sleep(0.25)
                    try:
                        cur = self.driver.current_url
                    except Exception:
                        break
                    if urlparse(cur).netloc != expected_host:
                        break  # Redirect auf anderen Host erkannt
                    if cur == last_url:
                        break  # URL hat sich nicht mehr verändert
                    last_url = cur
            load_ms = int((time.time() - start) * 1000)
            title   = self.driver.title or ""

            # Prüfen ob JS-Redirect auf anderen Host geführt hat
            expected_host = urlparse(item.url).netloc
            final_host    = urlparse(self.driver.current_url).netloc
            if expected_host and final_host and final_host != expected_host:
                self._record(item, status="FEHLER",
                             error=f"Redirect zu fremdem Host: {final_host}",
                             title=title, load_ms=load_ms)
                return

            error = self._check_error_page() or self._check_page_loaded()
            if error:
                self._record(item, status="FEHLER",
                             error=error,
                             title=title, load_ms=load_ms)
            else:
                self._record(item, status="OK", title=title, load_ms=load_ms)
                log.info(f"  OK ({load_ms}ms) — {title[:60]}")
        except TimeoutException:
            self._record(item, status="FEHLER",
                         error="Timeout — page did not load",
                         load_ms=int((time.time() - start) * 1000))
        except WebDriverException as e:
            self._record(item, status="FEHLER",
                         error=f"Browser error: {str(e)[:150]}",
                         load_ms=int((time.time() - start) * 1000))

    def _test_nav_click(self, item: NavigationItem):
        start = time.time()
        try:
            selector = ", ".join(NAV_CLICK_SELECTORS)
            el       = self._navigate_and_find(item, selector)
            load_ms  = int((time.time() - start) * 1000)
            pre_url  = self.driver.current_url if el else ""
            if el and self._safe_click(el):
                self._wait_for_dom_stable(pre_url=pre_url)
                title = self.driver.title or ""
                error = self._check_error_page()
                if error:
                    self._record(item, status="FEHLER",
                                 error=f"Error page after click: {error}",
                                 title=title, load_ms=load_ms)
                else:
                    self._record(item, status="OK", title=title, load_ms=load_ms)
                    log.info(f"  OK ({load_ms}ms) — {title[:60]}")
            else:
                self._record(item, status="FEHLER",
                             error=f"Element '{item.element_text}' not clickable",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER", error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_modal(self, item: NavigationItem):
        start = time.time()
        try:
            selector = ", ".join(MODAL_TRIGGER_SELECTORS)
            el       = self._navigate_and_find(item, selector)
            load_ms  = int((time.time() - start) * 1000)
            pre_url  = self.driver.current_url if el else ""
            if el and self._safe_click(el):
                self._wait_for_dom_stable(pre_url=pre_url)
                modal_sel = ", ".join(MODAL_CONTAINER_SELECTORS)
                modals    = self.driver.find_elements(By.CSS_SELECTOR, modal_sel)
                visible   = [m for m in modals if m.is_displayed()]
                if visible:
                    self._record(item, status="OK",
                                 title=f"Modal opened via '{item.element_text}'",
                                 load_ms=load_ms)
                    log.info(f"  Modal OK ({load_ms}ms)")
                    try:
                        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                        self._wait_for_dom_stable()
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
            self._record(item, status="FEHLER", error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_tab(self, item: NavigationItem):
        start = time.time()
        try:
            el      = self._navigate_and_find(item, "[role='tab']")
            pre_fp  = dom_fingerprint(self.driver)
            load_ms = int((time.time() - start) * 1000)
            if el and el.is_displayed():
                el.click()
                self._wait_for_dom_stable()
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
            self._record(item, status="FEHLER", error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_pagination(self, item: NavigationItem):
        start = time.time()
        try:
            selector = ", ".join(PAGINATION_SELECTORS)
            el       = self._navigate_and_find(item, selector, match_attr="label")
            pre_fp   = dom_fingerprint(self.driver)
            load_ms  = int((time.time() - start) * 1000)
            if el and self._safe_click(el):
                self._wait_for_dom_stable()
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
            self._record(item, status="FEHLER", error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_table_row(self, item: NavigationItem):
        start = time.time()
        base  = item.source_url or item.url.split("#")[0]
        try:
            self.driver.get(base)
            self._wait_for_dom_stable()
            pre_url = self.driver.current_url
            pre_fp  = dom_fingerprint(self.driver)
            rows    = self.driver.find_elements(
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
                    time.sleep(0.05)
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
                        self.driver.execute_script("arguments[0].click();", row)
                        clicked = True
                except (StaleElementReferenceException, WebDriverException):
                    try:
                        self.driver.execute_script("arguments[0].click();", row)
                        clicked = True
                    except Exception:
                        pass

            load_ms = int((time.time() - start) * 1000)
            if clicked:
                self._wait_for_dom_stable(pre_url=pre_url)
                post_url = self.driver.current_url
                if post_url != pre_url:
                    title = f"Row â†' {post_url}"
                elif dom_fingerprint(self.driver) != pre_fp:
                    title = "Row â†' DOM change"
                else:
                    title = "Row clicked, no reaction"
                self._record(item, status="OK", title=title, load_ms=load_ms)
                log.info(f"  Row OK ({load_ms}ms)")
            else:
                self._record(item, status="FEHLER",
                             error="No clickable table row found",
                             load_ms=load_ms)
        except Exception as e:
            self._record(item, status="FEHLER", error=str(e)[:200],
                         load_ms=int((time.time() - start) * 1000))

    def _test_form_input(self, item: NavigationItem):
        start = time.time()
        try:
            if item.source_url:
                current = self.driver.current_url
                def _base(u):
                    from urllib.parse import urlparse, urlunparse
                    p = urlparse(u)
                    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
                if _base(current) != _base(item.source_url):
                    self.driver.get(item.source_url)
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, item.selector)))
                    except TimeoutException:
                        pass
            try:
                el = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, item.selector)))
            except TimeoutException:
                el = self.driver.find_element(By.CSS_SELECTOR, item.selector)

            load_ms = int((time.time() - start) * 1000)
            if el.is_displayed():
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", el)
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
                        self._wait_for_dom_stable()
                self._record(item, status="OK",
                             title=f"Input: '{item.input_value[:40]}'"
                                   f"{' + ' + item.submit_key if item.submit_key else ''}",
                             load_ms=load_ms)
                log.info(f"  OK ({load_ms}ms) — Input in {item.selector}")
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
                current = self.driver.current_url
                def _base(u):
                    from urllib.parse import urlparse, urlunparse
                    p = urlparse(u)
                    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
                if _base(current) != _base(item.source_url):
                    self.driver.get(item.source_url)
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, item.selector)))
                    except TimeoutException:
                        pass
            try:
                el = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, item.selector)))
            except TimeoutException:
                el = self.driver.find_element(By.CSS_SELECTOR, item.selector)

            pre_url = self.driver.current_url
            pre_fp  = dom_fingerprint(self.driver)
            load_ms = int((time.time() - start) * 1000)

            if self._safe_click(el):
                self._wait_for_dom_stable(pre_url=pre_url, pre_fp=pre_fp)
                post_url = self.driver.current_url
                if post_url != pre_url:
                    title = f"Click â†' {post_url}"
                elif dom_fingerprint(self.driver) != pre_fp:
                    title = "Click â†' DOM change"
                else:
                    title = "Click executed"
                error = self._check_error_page()
                if error:
                    self._record(item, status="FEHLER",
                                 error=f"Error page after click: {error}",
                                 load_ms=load_ms)
                else:
                    self._record(item, status="OK", title=title, load_ms=load_ms)
                    log.info(f"  OK ({load_ms}ms) — {title[:60]}")
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
                self._wait_for_dom_stable()
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
                log.info(f"  OK ({load_ms}ms) — Text found")
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
        self._record(item, status="OK", title=f"Wait {seconds}s")
        log.info(f"  OK — Wait {seconds}s")

    def _wait_for_dom_stable(self, pre_url: str = "", pre_fp: str = "",
                              timeout: float = 8.0,
                              stable_for: float = 0.25) -> None:
        deadline = time.time() + timeout
        try:
            time.sleep(0.05)
            current_url = self.driver.current_url
            if pre_url and current_url != pre_url:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body")))
                return
            last_fp = dom_fingerprint(self.driver)
            if pre_fp and last_fp != pre_fp:
                return
            stable_since = time.time()
            while time.time() < deadline:
                time.sleep(0.1)
                fp = dom_fingerprint(self.driver)
                if fp != last_fp:
                    last_fp = fp
                    stable_since = time.time()
                elif time.time() - stable_since >= stable_for:
                    return
        except Exception:
            pass

    def _check_error_page(self) -> str:
        try:
            if self.driver.current_url.startswith("chrome-error://"):
                return "Browser error page (chrome-error)"
            title = (self.driver.title or "").lower()
            for err in ["404", "not found", "500", "403", "forbidden",
                        "fehler", "nicht gefunden",
                        "nicht erreichbar", "refused", "err_connection"]:
                if err in title:
                    return f"Title contains '{err}'"
        except Exception:
            pass
        return ""

    def _check_page_loaded(self) -> str:
        try:
            result = self.driver.execute_script("""
                const body = document.body;
                if (!body) return 'Kein Body-Element';
                const text = (body.innerText || '').trim();
                if (text.length < 30) return 'Seite erscheint leer';
                return '';
            """)
            return result or ""
        except Exception:
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

