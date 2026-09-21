import argparse
import base64
import json
import os
import sys
import time
import unicodedata

import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
)

USER = os.environ["EYATH_USER"]
PASS = os.environ["EYATH_PASS"]

# ---------- CLI ----------

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Fetch the EYATH communal water balance for a customer/meter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s -k 11-22-123-50-30 -H '1234567\u03A6123LL'\n"
            "  %(prog)s -k 11-22-123-50-30 -H '1234567\\u03A6123LL'\n"
            "  %(prog)s -k 11-22-123-50-30 -H '1234567%CE%A6123LL'\n"
        ),
    )
    p.add_argument(
        "-k", "--customer",
        required=True,
        help="customer number (e.g. 11-22-123-50-30)",
    )
    p.add_argument(
        "-H", "--hydrometer",
        required=True,
        help="hydrometer number; accepts literal Φ, \\\\u03A6, or %%CE%%A6",
    )
    p.add_argument(
        "--keep-open",
        action="store_true",
        help="keep the browser window open after the API call",
    )
    return p.parse_args(argv)


def normalize_hydrometer(s):
    """Accept Φ, \\u03A6, %CE%A6, and return the real Unicode string.

    The API expects the Greek capital Phi (U+03A6). Users may pass it
    directly (if their shell is UTF-8), as a Python escape, or as the
    URL-encoded form seen in curl commands.
    """
    if s is None:
        return s
    # If the user pasted a URL-encoded string, decode it.
    if "%" in s:
        try:
            s = requests.utils.unquote(s)
        except Exception:
            pass
    # If the user wrote a Python-style \uXXXX escape, decode it.
    try:
        s = s.encode("utf-8").decode("unicode_escape").encode("latin1").decode("utf-8")
    except Exception:
        pass
    # Normalize to NFC so visually-identical forms compare equal.
    return unicodedata.normalize("NFC", s)


ARGS = parse_args()
CUSTOMER = ARGS.customer
HYDROMETER = normalize_hydrometer(ARGS.hydrometer)

LOTTIE = (By.CSS_SELECTOR, "lottie-player.lottie")

# ---------- helpers ----------

def get_balance(token, customer, hydrometer):
    r = requests.get(
        "https://gateway.portal.eyath.gr/api/customer_connection/communal_check",
        params={
            "customer_number": customer,
            "hydrometer_number": hydrometer,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://portal.eyath.gr",
            "Referer": "https://portal.eyath.gr/",
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64; rv:140.0) "
                           "Gecko/20100101 Firefox/140.0"),
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def wait_for_lottie_gone(driver, timeout=10):
    """Wait for the Lottie loading overlay to disappear. Never raises."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located(LOTTIE)
        )
        return True
    except TimeoutException:
        return False


def human_move(driver, element):
    """Move the real cursor to the element via ActionChains."""
    ActionChains(driver) \
        .move_to_element(element) \
        .pause(0.3) \
        .perform()


def human_click(driver, element):
    """Move to the element, then click it via ActionChains.

    Falls back to a JS click if the Lottie overlay intercepts.
    """
    wait_for_lottie_gone(driver)
    try:
        ActionChains(driver) \
            .move_to_element(element) \
            .pause(0.2) \
            .click(element) \
            .perform()
    except (ElementClickInterceptedException,
            StaleElementReferenceException,
            WebDriverException) as e:
        print(f"  ActionChains click failed ({type(e).__name__}), trying JS click")
        driver.execute_script("arguments[0].click();", element)


def wait_click(driver, by, value, timeout=20):
    """Wait for element to be present, activate it with a mouse move, click it."""
    el = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )
    human_move(driver, el)
    human_click(driver, el)
    return el


def dismiss_continue_if_present(driver, timeout=9):
    """Click the 'Συνέχεια' mat-dialog-close button if a dialog is open."""
    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 "mat-dialog-container button.button1[mat-dialog-close]")
            )
        )
    except TimeoutException:
        return False

    try:
        btn.click()
    except (ElementClickInterceptedException,
            StaleElementReferenceException,
            WebDriverException):
        driver.execute_script("arguments[0].click();", btn)
    return True


def get_token(driver, timeout=30):
    """Wait for the JWT in sessionStorage['Token'] and return it."""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            "return !!window.sessionStorage.getItem('Token');"
        )
    )
    return driver.execute_script(
        "return window.sessionStorage.getItem('Token');"
    )


# ---------- browser ----------

driver = webdriver.Firefox()
driver.set_window_size(1287, 800)
driver.get("https://portal.eyath.gr/")


# ---------- login ----------

print("[1] opening login form")
wait_click(driver, By.CSS_SELECTOR, ".button2")

print("[2] waiting for login form to appear")
WebDriverWait(driver, 20).until(
    EC.visibility_of_element_located((By.ID, "j_username"))
)

print("[3] filling credentials")
driver.find_element(By.ID, "j_username").send_keys(USER)
driver.find_element(By.ID, "j_password").send_keys(PASS)

print("[4] submitting login")
wait_click(driver, By.ID, "btn-login-submit")

print("[5] confirming")
wait_click(driver, By.ID, "btn-submit")


# ---------- optional "Συνέχεια" dialog ----------

print("[6] dismissing optional 'Συνέχεια' dialog")
dismissed = dismiss_continue_if_present(driver, timeout=9)
print("    dismissed:", dismissed)


# ---------- wait for token ----------

print("[7] waiting for Token in sessionStorage")
try:
    token = get_token(driver, timeout=30)
    print("    token preview:", token[:25] + "..." + token[-10:])
except TimeoutException:
    print("    no Token in sessionStorage within 30s — dumping anyway")
    token = None


# ---------- storage dump ----------

print("\n=== localStorage keys ===")
print(driver.execute_script("return Object.keys(window.localStorage)"))
print("=== sessionStorage keys ===")
print(driver.execute_script("return Object.keys(window.sessionStorage)"))

print("\n=== previews (values redacted) ===")
for store in ("localStorage", "sessionStorage"):
    for k in driver.execute_script(f"return Object.keys(window.{store})"):
        v = driver.execute_script(f"return window.{store}.getItem({k!r})")
        if v and len(v) > 40:
            v = v[:20] + "..." + v[-10:]
        print(f"{store}[{k!r}] = {v}")

if token:
    print(f"\n>>> Token length: {len(token)}")


# ---------- call the API ----------

print("\n[8] calling gateway API")
print(f"    customer:   {CUSTOMER}")
print(f"    hydrometer: {HYDROMETER}  (U+%04X for char 9)"
      % ord(HYDROMETER[8]) if len(HYDROMETER) > 8 else "")

try:
    data = get_balance(token, CUSTOMER, HYDROMETER)
    print("    response:", json.dumps(data, ensure_ascii=False))
    if "balance" in data:
        print(f"\n>>> BALANCE: {data['balance']}")
    if "rfCode" in data:
        print(f">>> RF CODE: {data['rfCode']}")
except requests.HTTPError as e:
    print("    HTTP error:", e)
    if e.response is not None:
        print("    status:", e.response.status_code)
        print("    body:", e.response.text[:500])
except Exception as e:
    print("    error:", type(e).__name__, e)

if ARGS.keep_open:
    input("\nPress Enter to close the browser...")
driver.quit()
