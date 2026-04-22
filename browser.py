import os
import time
import logging
from datetime import datetime
from urllib.parse import urlparse

from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from models import log
from tester import NavigationTester, export_to_csv
from testcases import load_testcases, TESTCASES_DIR


def _results_dir() -> str:
    import sys
    d = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "results")
    os.makedirs(d, exist_ok=True)
    return d


def setup_logging():
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s  %(message)s",
                                          datefmt="%H:%M:%S"))
        log.addHandler(h)


def start_browser(headless: bool = True, browser: str = "chrome"):
    if browser == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")
        driver = webdriver.Firefox(
            service=FirefoxService(GeckoDriverManager().install()),
            options=options)

    elif browser == "edge":
        options = EdgeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches",
                                        ["enable-automation"])
        driver = webdriver.Edge(
            service=EdgeService(EdgeChromiumDriverManager().install()),
            options=options)

    else:
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches",
                                        ["enable-automation"])
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options)

    driver.implicitly_wait(5)
    driver.set_page_load_timeout(30)
    return driver


def login(driver, url: str, username: str = "", password: str = "") -> str:
    if not (username or password):
        return url

    log.info(f"Login: navigating to {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    except Exception:
        log.warning("No input fields found after 15s")
        return driver.current_url

    current = driver.current_url
    log.info(f"Login page loaded: {current}")
    log.info(f"Page title: {driver.title}")

    try:
        inputs = driver.find_elements(By.CSS_SELECTOR, "input")
        log.info(f"Found {len(inputs)} input fields:")
        for i, inp in enumerate(inputs):
            inp_type = inp.get_attribute("type") or ""
            inp_name = inp.get_attribute("name") or ""
            inp_id = inp.get_attribute("id") or ""
            inp_vis = inp.is_displayed()
            log.info(f"  [{i}] type={inp_type} name={inp_name} id={inp_id} visible={inp_vis}")
    except Exception as e:
        log.warning(f"Could not list inputs: {e}")

    pre_login_url = current
    pre_login_domain = urlparse(pre_login_url).netloc

    try:
        user_selectors = [
            '#username',
            'input[name="username"]',
            'input[type="email"]',
            'input[type="text"][name*="user"]',
            'input[name*="login"]',
            'input[name*="email"]',
            'input[autocomplete="username"]',
        ]
        uf = None
        for sel in user_selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    uf = el
                    log.info(f"Username field found: {sel}")
                    break
            except Exception:
                continue

        if not uf:
            log.warning("No username field found, trying first visible text input")
            for inp in driver.find_elements(By.CSS_SELECTOR, "input"):
                if inp.is_displayed() and inp.get_attribute("type") in ("text", "email", ""):
                    uf = inp
                    log.info(f"Using fallback input: type={inp.get_attribute('type')} id={inp.get_attribute('id')}")
                    break

        if not uf:
            log.warning("No username field found at all")
            return driver.current_url

        uf.clear()
        uf.send_keys(username)
        log.info(f"Username entered: {username}")

        pf = driver.find_element(
            By.CSS_SELECTOR, 'input[type="password"]')
        pf.clear()
        pf.send_keys(password)
        log.info("Password entered")

        submit_selectors = [
            '#kc-login',
            'input[type="submit"]',
            'button[type="submit"]',
            'button[name="login"]',
            'button[class*="login"]',
            'button[class*="submit"]',
        ]
        sb = None
        for sel in submit_selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    sb = el
                    log.info(f"Submit button found: {sel}")
                    break
            except Exception:
                continue

        if not sb:
            log.warning("No submit button found, trying Enter key")
            pf.send_keys("\n")
        else:
            sb.click()

        log.info("Login submitted, waiting for redirect...")

        for i in range(30):
            time.sleep(0.5)
            current = driver.current_url
            current_domain = urlparse(current).netloc
            if current_domain != pre_login_domain:
                log.info(f"Redirect detected: {current}")
                break
            if current != pre_login_url \
                    and "/login" not in current.lower() \
                    and "/auth" not in current.lower() \
                    and "/realms" not in current.lower():
                log.info(f"URL changed: {current}")
                break
            if i % 10 == 9:
                log.info(f"Still waiting... ({(i+1)*0.5:.0f}s)")
        else:
            log.warning("Login redirect timeout after 15s")

        crawl_url = driver.current_url
        log.info(f"Login done → {crawl_url}")
        return crawl_url
    except Exception as e:
        log.warning(f"Login failed: {e}")
        return driver.current_url


def quit_browser(driver):
    if driver:
        try:
            driver.quit()
        except Exception:
            pass


def run_test(app, yaml_paths: list[str], headless: bool = True):
    try:
        all_items = []
        url = ""
        browser_name = "chrome"
        username = ""
        password = ""
        for path in yaml_paths:
            items, meta = load_testcases(path)
            all_items.extend(items)
            if meta.get("url"):
                url = meta["url"]
            if meta.get("browser"):
                browser_name = meta["browser"].strip().lower()
            if meta.get("username"):
                username = str(meta["username"]).strip()
            if meta.get("password"):
                password = str(meta["password"]).strip()

        if not url:
            log.error("No URL found in YAML meta.")
            from tkinter import messagebox
            app.root.after(0, lambda: messagebox.showwarning(
                "", "No URL found in testcases."))
            return

        if browser_name not in ("chrome", "edge", "firefox"):
            browser_name = "chrome"

        app.driver = start_browser(headless=headless, browser=browser_name)

        if not app.running:
            return

        login(app.driver, url, username, password)

        if not app.running:
            return

        ts = datetime.now().strftime("%y.%m.%d - %H.%M Uhr")
        tc_names = [os.path.basename(p).replace(".yaml", "")
                    for p in yaml_paths]
        result_name = f"{ts} - {', '.join(tc_names)}"
        rd = _results_dir()

        tester = NavigationTester(
            driver=app.driver, items=all_items, wait_time=0.3)
        app.results = tester.test_all()

        csv_path = os.path.join(rd, f"{result_name}.csv")
        export_to_csv(app.results, csv_path)

        ok = sum(1 for r in app.results if r.status == "OK")
        err = sum(1 for r in app.results if r.status == "FEHLER")
        log.info(f"Done – {ok} OK, {err} errors")
        app.root.after(0, app._refresh_results_list)

    except Exception as e:
        log.error(f"Error: {e}")
    finally:
        quit_browser(app.driver)
        app.driver = None
        app.running = False
        app.root.after(0, app._set_running, False)