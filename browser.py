import os
import sys
import shutil
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

from models import log
from tester import NavigationTester, export_to_csv
from testcases import load_testcases, TESTCASES_DIR
from recorder import SessionRecorder


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
    # Always show browser/driver errors regardless of log level
    log.setLevel(logging.DEBUG)


def _driver_version(path: str) -> tuple[int, ...]:
    """Return the major version tuple of a driver binary, e.g. (148, 0).

    First tries to extract the version from the file path (reliable, fast),
    then falls back to running --version (may fail on some systems).
    """
    import re

    # Extract version from path: .../chromedriver/win64/148.0.7778.167/...
    m = re.search(r'(?<=[/\\])(\d+)\.(\d+)\.(\d+)\.(\d+)(?=[/\\])', path.replace('\\', '/'))
    if m:
        return tuple(int(x) for x in m.groups())

    # Fallback: run the binary
    try:
        out = subprocess.check_output(
            [path, "--version"], stderr=subprocess.STDOUT, timeout=5
        ).decode(errors="ignore")
        parts = out.split()
        for p in parts:
            nums = p.split(".")
            if nums[0].isdigit():
                return tuple(int(x) for x in nums if x.isdigit())
    except Exception:
        pass
    return (0,)


def _browser_version(browser: str) -> tuple[int, ...]:
    """Read the installed browser version from the registry or binary."""
    if sys.platform != "win32":
        return (0,)
    try:
        import winreg
        keys = {
            "chrome": [
                r"SOFTWARE\Google\Chrome\BLBeacon",
                r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon",
            ],
            "edge": [
                r"SOFTWARE\Microsoft\Edge\BLBeacon",
                r"SOFTWARE\WOW6432Node\Microsoft\Edge\BLBeacon",
            ],
        }
        for key_path in keys.get(browser, []):
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, key_path) as k:
                        ver, _ = winreg.QueryValueEx(k, "version")
                        parts = str(ver).split(".")
                        return tuple(int(x) for x in parts if x.isdigit())
                except Exception:
                    continue
    except Exception:
        pass
    return (0,)


def _find_driver(name: str, browser: str = "") -> str:
    """
    Locate a matching WebDriver executable without hitting the internet.

    Search order:
      1. PATH  (shutil.which)
      2. Windows-specific known locations
      3. Selenium Manager cache  (~/.cache/selenium)
      4. wdm cache  (%LOCALAPPDATA%/wdm  or  ~/.wdm)

    Version check: driver major must match browser major.
    Falls back to "" so Selenium Manager can try online if all else fails.
    """
    browser_major = _browser_version(browser)[0] if browser else 0
    log.debug(f"_find_driver: name={name!r} browser={browser!r} "
              f"browser_major={browser_major}")

    def _version_ok(path: str) -> bool:
        if not browser_major:
            return True   # no browser specified → accept any version
        drv_major = _driver_version(path)[0]
        if drv_major == 0:
            return False  # could not determine version → reject (safe default)
        ok = drv_major == browser_major
        log.debug(f"  version_ok({os.path.basename(path)}): "
                  f"driver={drv_major} browser={browser_major} → {ok}")
        return ok

    candidates: list[str] = []

    # 1. PATH
    found = shutil.which(name) or shutil.which(name + ".exe")
    if found:
        log.debug(f"  Found in PATH: {found}")
        if _version_ok(found):
            return found

    if sys.platform == "win32":
        exe = name if name.endswith(".exe") else name + ".exe"

        if "msedge" in name:
            # Edge does NOT ship msedgedriver.exe alongside the browser.
            # It is distributed via Windows Update into System32 / SysWOW64,
            # or can be found in the Selenium / wdm cache.
            for d in [
                os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"),
                os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "SysWOW64"),
                # Some enterprise deployments place it here
                r"C:\Program Files (x86)\Microsoft\Edge\Application",
                r"C:\Program Files\Microsoft\Edge\Application",
                # Chocolatey / winget
                r"C:\ProgramData\chocolatey\bin",
                r"C:\tools\msedgedriver",
            ]:
                p = os.path.join(d, "msedgedriver.exe")
                if os.path.isfile(p):
                    log.debug(f"  Edge candidate: {p}")
                    candidates.append(p)
            # Also walk Edge Application subfolders (some Edge builds do
            # include the driver in the versioned subfolder)
            for base in [
                r"C:\Program Files (x86)\Microsoft\Edge\Application",
                r"C:\Program Files\Microsoft\Edge\Application",
            ]:
                if os.path.isdir(base):
                    for root, _dirs, files in os.walk(base):
                        for f in files:
                            if f.lower() == "msedgedriver.exe":
                                log.debug(f"  Edge candidate (walk): "
                                          f"{os.path.join(root, f)}")
                                candidates.append(os.path.join(root, f))

        if "chromedriver" in name:
            for base in [
                r"C:\Program Files\Google\Chrome\Application",
                r"C:\Program Files (x86)\Google\Chrome\Application",
            ]:
                if os.path.isdir(base):
                    for root, _dirs, files in os.walk(base):
                        for f in files:
                            if f.lower() == "chromedriver.exe":
                                candidates.append(os.path.join(root, f))

        if "gecko" in name:
            for base in [
                r"C:\Program Files\Mozilla Firefox",
                r"C:\Program Files (x86)\Mozilla Firefox",
            ]:
                p = os.path.join(base, "geckodriver.exe")
                if os.path.isfile(p):
                    candidates.append(p)

        # Selenium Manager cache  (~/.cache/selenium/<browser>/...)
        selenium_cache = os.path.join(
            os.path.expanduser("~"), ".cache", "selenium")
        if os.path.isdir(selenium_cache):
            for root, _dirs, files in os.walk(selenium_cache):
                if exe.lower() in [f.lower() for f in files]:
                    candidates.append(os.path.join(root, exe))

        # wdm cache
        wdm_roots = []
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            wdm_roots.append(os.path.join(local_app, "wdm", "drivers"))
        wdm_roots.append(
            os.path.join(os.path.expanduser("~"), ".wdm", "drivers"))
        for wdm_root in wdm_roots:
            if os.path.isdir(wdm_root):
                for root, _dirs, files in os.walk(wdm_root):
                    if exe.lower() in [f.lower() for f in files]:
                        candidates.append(os.path.join(root, exe))

    log.debug(f"  Candidates: {candidates}")
    for c in candidates:
        if _version_ok(c):
            log.info(f"  Using driver: {c}")
            return c

    log.info(f"  No matching local driver for {name!r} "
             f"(browser_major={browser_major}) – delegating to Selenium Manager")
    return ""



def _driver_cache_dir() -> str:
    """Persistent cache directory for downloaded drivers."""
    local_app = os.environ.get("LOCALAPPDATA", "")
    base = local_app if local_app else os.path.expanduser("~")
    d = os.path.join(base, "bugula", "drivers")
    os.makedirs(d, exist_ok=True)
    return d


def _download_msedgedriver(major_version: int) -> str:
    """
    Download msedgedriver.exe from the official Microsoft endpoint and
    cache it locally.  Returns the path on success, "" on failure.
    """
    if not major_version:
        return ""

    cache_dir = _driver_cache_dir()
    cached = os.path.join(cache_dir, f"msedgedriver_{major_version}.exe")
    if os.path.isfile(cached):
        log.info(f"  msedgedriver cached: {cached}")
        return cached

    import urllib.request
    import zipfile
    import io

    # Microsoft's official download URL pattern
    version_url = (
        f"https://msedgedriver.azureedge.net/"
        f"LATEST_RELEASE_{major_version}_WINDOWS"
    )
    try:
        log.info(f"  Fetching Edge driver version from {version_url}")
        with urllib.request.urlopen(version_url, timeout=10) as r:
            full_version = r.read().decode().strip()
        log.info(f"  Edge driver version: {full_version}")

        zip_url = (
            f"https://msedgedriver.azureedge.net/{full_version}/"
            f"edgedriver_win64.zip"
        )
        log.info(f"  Downloading {zip_url}")
        with urllib.request.urlopen(zip_url, timeout=60) as r:
            zip_data = r.read()

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for name in zf.namelist():
                if name.lower().endswith("msedgedriver.exe"):
                    with zf.open(name) as src_f, open(cached, "wb") as dst_f:
                        dst_f.write(src_f.read())
                    log.info(f"  msedgedriver saved to {cached}")
                    return cached

        log.warning("  msedgedriver.exe not found in downloaded zip")
    except Exception as e:
        log.warning(f"  msedgedriver download failed: {e}")
    return ""


def _find_edge_binary() -> str:
    """Return the path to the Microsoft Edge executable, or ''."""
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        # Also check registry
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for key_path in (
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                ):
                    try:
                        with winreg.OpenKey(hive, key_path) as k:
                            path, _ = winreg.QueryValueEx(k, "")
                            if path and os.path.isfile(path):
                                return path
                    except Exception:
                        continue
        except Exception:
            pass
        for p in candidates:
            if os.path.isfile(p):
                log.debug(f"  Edge binary: {p}")
                return p
    elif sys.platform == "darwin":
        p = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        if os.path.isfile(p):
            return p
    else:
        found = shutil.which("microsoft-edge") or shutil.which("microsoft-edge-stable")
        if found:
            return found
    return ""


def start_browser(headless: bool = True, browser: str = "chrome",
                  private: bool = False):
    if browser == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        if private:
            options.add_argument("--private-window")
            options.set_preference("browser.privatebrowsing.autostart", True)
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")
        driver_path = _find_driver("geckodriver", "firefox")
        service = FirefoxService(driver_path) if driver_path \
                  else FirefoxService()
        driver = webdriver.Firefox(service=service, options=options)

    elif browser == "edge":
        options = EdgeOptions()
        if headless:
            options.add_argument("--headless=new")
        if private:
            options.add_argument("--inprivate")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches",
                                        ["enable-automation"])
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
        })

        # Strategy 1: dedicated msedgedriver (local or downloaded)
        driver_path = _find_driver("msedgedriver", "edge")
        if not driver_path:
            driver_path = _download_msedgedriver(_browser_version("edge")[0])

        if driver_path:
            log.info(f"Edge: using msedgedriver at {driver_path}")
            service = EdgeService(driver_path)
            driver = webdriver.Edge(service=service, options=options)
        else:
            # Strategy 2: chromedriver pointed at the Edge binary.
            # Edge is Chromium-based; chromedriver works when
            # options.binary_location is set to msedge.exe.
            # We use ChromeOptions (not EdgeOptions) so Selenium does NOT
            # invoke its own driver-finder logic for Edge.
            edge_bin = _find_edge_binary()
            if not edge_bin:
                raise RuntimeError(
                    "Edge-Browser nicht gefunden. Bitte Microsoft Edge installieren.")

            log.info(f"Edge: no msedgedriver – using chromedriver "
                     f"with Edge binary: {edge_bin}")

            chrome_opts = ChromeOptions()
            chrome_opts.binary_location = edge_bin
            for arg in options.arguments:
                chrome_opts.add_argument(arg)
            chrome_opts.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            chrome_opts.add_experimental_option("prefs", {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.password_manager_leak_detection": False,
            })

            # chromedriver major must match Edge major (they share the
            # Chromium version number)
            edge_major = _browser_version("edge")[0]
            cd_path = _find_driver("chromedriver", "edge")   # tries edge major
            if not cd_path:
                # _find_driver checks driver vs browser major; pass "" so it
                # accepts any cached chromedriver version
                cd_path = _find_driver("chromedriver", "")
            if not cd_path:
                cd_path = _find_driver("chromedriver", "chrome")
            log.info(f"Edge/chromedriver path: {cd_path or '(Selenium Manager)'}")
            c_service = ChromeService(cd_path) if cd_path else ChromeService()
            driver = webdriver.Chrome(service=c_service, options=chrome_opts)

    else:
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        if private:
            options.add_argument("--incognito")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches",
                                        ["enable-automation"])
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
        })
        driver_path = _find_driver("chromedriver", "chrome")
        service = ChromeService(driver_path) if driver_path \
                  else ChromeService()
        driver = webdriver.Chrome(service=service, options=options)

    driver.implicitly_wait(5)
    driver.set_page_load_timeout(30)
    return driver


def login(driver, url: str, username: str = "", password: str = "") -> str:
    # Always navigate to the target URL first
    log.info(f"Navigating to {url}")
    driver.get(url)

    if not (username or password):
        return driver.current_url

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
        private = False
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

        app.driver = start_browser(headless=headless, browser=browser_name,
                                   private=private)

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


# ---------------------------------------------------------------------------
# Recording session
# ---------------------------------------------------------------------------

def run_record(app, url: str, tc_name: str,
               browser_name: str = "chrome",
               username: str = "", password: str = "",
               private: bool = False):
    """
    Opens a visible browser, logs in (optional), injects the recorder JS
    and waits until app.running is set to False (Stop button).
    Then saves the captured events as a YAML testcase.
    """
    try:
        app.driver = start_browser(headless=False, browser=browser_name,
                                   private=private)

        # Navigate and optionally log in
        crawl_url = login(app.driver, url, username, password)

        # Start recorder
        recorder = SessionRecorder(app.driver, crawl_url)
        recorder.start()
        app.recorder = recorder

        log.info("Recording… close browser or press Stop to finish.")

        # Update status label while running
        def _tick():
            if not app.running:
                return
            n = recorder.event_count()
            try:
                app.root.after(0, app._update_record_status,
                               f"Recording… {n} events captured")
            except Exception:
                pass
            import threading
            threading.Timer(1.0, _tick).start()

        _tick()

        # Wait until stopped
        while app.running:
            try:
                # Check if browser window was closed by user
                _ = app.driver.current_url
            except Exception:
                log.info("Browser closed by user – stopping recorder.")
                break
            time.sleep(0.5)

        recorder.stop()

        # Save YAML
        from testcases import TESTCASES_DIR
        import sys
        tc_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                              TESTCASES_DIR)
        os.makedirs(tc_dir, exist_ok=True)

        safe_name = tc_name.strip().replace(" ", "_") or "recording"
        yaml_path = os.path.join(tc_dir, safe_name + ".yaml")

        # Avoid overwriting: append suffix if needed
        base = yaml_path
        counter = 1
        while os.path.exists(yaml_path):
            yaml_path = base.replace(".yaml", f"_{counter}.yaml")
            counter += 1

        yaml_text = recorder.to_yaml(
            name=safe_name,
            url=url,
            browser=browser_name,
            username=username,
            password=password,
        )
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_text)

        log.info(f"Recording saved: {yaml_path}")
        app.root.after(0, app._on_record_saved, yaml_path)

    except Exception as e:
        log.error(f"Recording error: {e}")
        import traceback; traceback.print_exc()
    finally:
        quit_browser(app.driver)
        app.driver = None
        app.recorder = None
        app.running = False
        app.root.after(0, app._set_running, False)
        app.root.after(0, app._update_record_status, "")