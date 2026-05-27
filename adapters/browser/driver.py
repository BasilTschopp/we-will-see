import os
import sys
import shutil
import logging

from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium import webdriver

from models.models import log


def setup_logging():
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s  %(message)s",
                                          datefmt="%H:%M:%S"))
        log.addHandler(h)
    log.setLevel(logging.DEBUG)


def _driver_version(path: str) -> tuple[int, ...]:
    import re
    m = re.search(r'(?<=[/\\])(\d+)\.(\d+)\.(\d+)\.(\d+)(?=[/\\])',
                  path.replace('\\', '/'))
    if m:
        return tuple(int(x) for x in m.groups())
    try:
        import subprocess
        out = subprocess.check_output(
            [path, "--version"], stderr=subprocess.STDOUT, timeout=5
        ).decode(errors="ignore")
        for p in out.split():
            nums = p.split(".")
            if nums[0].isdigit():
                return tuple(int(x) for x in nums if x.isdigit())
    except Exception:
        pass
    return (0,)


def _browser_version(browser: str) -> tuple[int, ...]:
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
    browser_major = _browser_version(browser)[0] if browser else 0

    def _version_ok(path: str) -> bool:
        if not browser_major:
            return True
        drv_major = _driver_version(path)[0]
        return drv_major != 0 and drv_major == browser_major

    candidates: list[str] = []
    found = shutil.which(name) or shutil.which(name + ".exe")
    if found and _version_ok(found):
        return found

    if sys.platform == "win32":
        exe = name if name.endswith(".exe") else name + ".exe"

        if "msedge" in name:
            for d in [
                os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"),
                os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "SysWOW64"),
                r"C:\Program Files (x86)\Microsoft\Edge\Application",
                r"C:\Program Files\Microsoft\Edge\Application",
                r"C:\ProgramData\chocolatey\bin",
                r"C:\tools\msedgedriver",
            ]:
                p = os.path.join(d, "msedgedriver.exe")
                if os.path.isfile(p):
                    candidates.append(p)
            for base in [
                r"C:\Program Files (x86)\Microsoft\Edge\Application",
                r"C:\Program Files\Microsoft\Edge\Application",
            ]:
                if os.path.isdir(base):
                    for root, _dirs, files in os.walk(base):
                        for f in files:
                            if f.lower() == "msedgedriver.exe":
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

        selenium_cache = os.path.join(os.path.expanduser("~"), ".cache", "selenium")
        if os.path.isdir(selenium_cache):
            for root, _dirs, files in os.walk(selenium_cache):
                if exe.lower() in [f.lower() for f in files]:
                    candidates.append(os.path.join(root, exe))

        for wdm_root in [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "wdm", "drivers"),
            os.path.join(os.path.expanduser("~"), ".wdm", "drivers"),
        ]:
            if os.path.isdir(wdm_root):
                for root, _dirs, files in os.walk(wdm_root):
                    if exe.lower() in [f.lower() for f in files]:
                        candidates.append(os.path.join(root, exe))

    for c in candidates:
        if _version_ok(c):
            return c
    return ""


def _driver_cache_dir() -> str:
    local_app = os.environ.get("LOCALAPPDATA", "")
    base = local_app if local_app else os.path.expanduser("~")
    d = os.path.join(base, "bugula", "drivers")
    os.makedirs(d, exist_ok=True)
    return d


def _download_msedgedriver(major_version: int) -> str:
    if not major_version:
        return ""
    cache_dir = _driver_cache_dir()
    cached = os.path.join(cache_dir, f"msedgedriver_{major_version}.exe")
    if os.path.isfile(cached):
        return cached
    import urllib.request, zipfile, io
    version_url = (f"https://msedgedriver.azureedge.net/"
                   f"LATEST_RELEASE_{major_version}_WINDOWS")
    try:
        with urllib.request.urlopen(version_url, timeout=10) as r:
            full_version = r.read().decode().strip()
        zip_url = (f"https://msedgedriver.azureedge.net/{full_version}/"
                   f"edgedriver_win64.zip")
        with urllib.request.urlopen(zip_url, timeout=60) as r:
            zip_data = r.read()
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for name in zf.namelist():
                if name.lower().endswith("msedgedriver.exe"):
                    with zf.open(name) as src_f, open(cached, "wb") as dst_f:
                        dst_f.write(src_f.read())
                    return cached
    except Exception as e:
        log.warning(f"  msedgedriver download failed: {e}")
    return ""


def _find_edge_binary() -> str:
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
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
        service = FirefoxService(driver_path) if driver_path else FirefoxService()
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
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
        })
        driver_path = _find_driver("msedgedriver", "edge")
        if not driver_path:
            driver_path = _download_msedgedriver(_browser_version("edge")[0])
        if driver_path:
            driver = webdriver.Edge(service=EdgeService(driver_path), options=options)
        else:
            edge_bin = _find_edge_binary()
            if not edge_bin:
                raise RuntimeError(
                    "Edge-Browser nicht gefunden. Bitte Microsoft Edge installieren.")
            chrome_opts = ChromeOptions()
            chrome_opts.binary_location = edge_bin
            for arg in options.arguments:
                chrome_opts.add_argument(arg)
            chrome_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_opts.add_experimental_option("prefs", {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.password_manager_leak_detection": False,
            })
            cd_path = (_find_driver("chromedriver", "edge")
                       or _find_driver("chromedriver", "")
                       or _find_driver("chromedriver", "chrome"))
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
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
        })
        driver_path = _find_driver("chromedriver", "chrome")
        service = ChromeService(driver_path) if driver_path else ChromeService()
        driver = webdriver.Chrome(service=service, options=options)

    driver.implicitly_wait(1)
    driver.set_page_load_timeout(30)
    return driver


def quit_browser(driver):
    if driver:
        try:
            driver.quit()
        except Exception:
            pass

