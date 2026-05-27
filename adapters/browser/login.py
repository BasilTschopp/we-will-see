import time
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from models.models import log


def login(driver, url: str, username: str = "", password: str = "") -> str:
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

    pre_login_url    = current
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
            for inp in driver.find_elements(By.CSS_SELECTOR, "input"):
                if inp.is_displayed() and inp.get_attribute("type") in ("text", "email", ""):
                    uf = inp
                    break

        if not uf:
            log.warning("No username field found at all")
            return driver.current_url

        uf.clear()
        uf.send_keys(username)

        pf = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        pf.clear()
        pf.send_keys(password)

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
                    break
            except Exception:
                continue

        if not sb:
            pf.send_keys("\n")
        else:
            sb.click()

        log.info("Login submitted, waiting for redirect...")

        for i in range(30):
            time.sleep(0.5)
            current = driver.current_url
            current_domain = urlparse(current).netloc
            if current_domain != pre_login_domain:
                break
            if (current != pre_login_url
                    and "/login" not in current.lower()
                    and "/auth" not in current.lower()
                    and "/realms" not in current.lower()):
                break
        else:
            log.warning("Login redirect timeout after 15s")

        crawl_url = driver.current_url
        log.info(f"Login done â†’ {crawl_url}")
        return crawl_url

    except Exception as e:
        log.warning(f"Login failed: {e}")
        return driver.current_url

