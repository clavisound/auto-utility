import time
import os
import base64
import urllib.parse as up
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import argparse


class TestAutodei:
    def __init__(self, headless_mode=False, quiet_mode=False):
        self.headless_mode = headless_mode
        self.quiet_mode = quiet_mode
        self.download_dir = None
        self.driver = None
        self.wait = None

    def _print_message(self, message):
        if not self.quiet_mode:
            print(message)

    def setup_method(self, method):
        self.download_dir = os.path.join(os.getcwd(), "dei")
        os.makedirs(self.download_dir, exist_ok=True)
        self._print_message(f"Οι λήψεις PDF θα αποθηκευτούν στον κατάλογο: {self.download_dir}")

        firefox_options = Options()
        if self.headless_mode:
            firefox_options.add_argument("-headless")
            self._print_message("Εκτέλεση σε headless mode.")

        self.driver = webdriver.Firefox(options=firefox_options)
        self.wait = WebDriverWait(self.driver, 30)

    def teardown_method(self, method):
        if self.driver:
            self.driver.quit()

    # ---------- helpers ----------

    def _fetch_via_js(self, url):
        """Fetch a URL inside the page (sends browser cookies) and return bytes or None."""
        b64 = self.driver.execute_async_script("""
            const url = arguments[0], done = arguments[arguments.length - 1];
            fetch(url, {credentials: 'include'})
              .then(r => r.arrayBuffer())
              .then(buf => {
                let bin = ''; const b = new Uint8Array(buf);
                for (let i = 0; i < b.length; i++) bin += String.fromCharCode(b[i]);
                done(btoa(bin));
              })
              .catch(() => done(null));
        """, url)
        return base64.b64decode(b64) if b64 else None

    @staticmethod
    def _dt_from_url(url):
        try:
            return url.split("dt=")[1].split("&")[0]
        except Exception:
            return "unknown"

    def _select_rows(self, history, dt_filter=None, download_all=False):
        rows = [r for r in history.get("data", [])
                if r.get("type") == 1 and r.get("fileUrlView")]
        if dt_filter:
            rows = [r for r in rows if self._dt_from_url(r["fileUrlView"]) == dt_filter]
        if not download_all:
            rows = rows[:1]
        return rows

    def _read_summary(self):
        """Return (rf_code, amount_str) from the e-link-supply block, or (None, None)."""
        rf_code = None
        try:
            href = self.wait.until(EC.presence_of_element_located(
                (By.XPATH,
                 "//div[contains(@class,'e-link-supply__conts')]"
                 "//a[contains(@href,'paymentCode=')]")
            )).get_attribute("href")
            rf_code = (up.parse_qs(up.urlparse(href).query).get("paymentCode") or [None])[0]
        except Exception:
            rf_code = None

        amount = None
        try:
            amount = self.wait.until(EC.presence_of_element_located(
                (By.XPATH,
                 "//div[contains(@class,'e-link-supply__name')]"
                 "[.//em[normalize-space()='Ποσό πληρωμής']]"
                 "//div[contains(@class,'e-link-supply__name__txt')]")
            )).text.strip()
        except Exception:
            amount = None

        return rf_code, amount

    # ---------- main ----------

    def test_autodei(self, account_number, dt_filter=None, download_all=False):
        self.driver.get("https://mydei.dei.gr/el")
        self.driver.set_window_size(650, 528)
        time.sleep(3)

        # cookie banner
        try:
            self.wait.until(EC.element_to_be_clickable(
                (By.ID, "onetrust-accept-btn-handler"))).click()
            self._print_message("Το cookie banner έγινε αποδεκτό.")
            time.sleep(2)
        except Exception:
            self._print_message("Το cookie banner δεν βρέθηκε ή δεν ήταν clickable.")

        # "Κοινόχρηστα"
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[.//div[text()='Κοινόχρηστα']]"))).click()

        # ContractAccount
        field = self.wait.until(EC.element_to_be_clickable((By.ID, "ContractAccount")))
        field.clear()
        field.send_keys(account_number)

        # submit
        self.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".b-login-panel__submit"))).click()

        # wait until window.historyData is populated
        self.wait.until(lambda d: d.execute_script("return !!window.historyData"))
        history = self.driver.execute_script("return window.historyData;")
        self._print_message(f"Βρέθηκαν {len(history.get('data', []))} κινήσεις.")

        rows = self._select_rows(history, dt_filter=dt_filter, download_all=download_all)
        if not rows:
            self._print_message("Δεν βρέθηκε κατάλληλος λογαριασμός για λήψη.")
            return

        # summary block (RF / amount) — wait for it, read once
        try:
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".e-link-supply__conts")))
        except Exception:
            pass
        rf_code, amount = self._read_summary()
        if rf_code or amount:
            self._print_message(f"RF: {rf_code or '-'}  |  Ποσό: {amount or '-'}")

        for row in rows:
            url = "https://mydei.dei.gr" + row["fileUrlView"]
            pdf = self._fetch_via_js(url)
            if not pdf:
                self._print_message(f"Αποτυχία λήψης: {url}")
                continue
            dt = self._dt_from_url(row["fileUrlView"])
            fn = os.path.join(self.download_dir, f"bill_{dt}.pdf")
            with open(fn, "wb") as f:
                f.write(pdf)
            self._print_message(f"Αποθηκεύτηκε: {fn} ({len(pdf)} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Αυτοματοποίηση λήψης λογαριασμού από το myΔΕΗ.")
    parser.add_argument("-a", "--account", required=True,
                        help="Ο αριθμός λογαριασμού συμβολαίου (π.χ., 300004254333).")
    parser.add_argument("--headless", action="store_true",
                        help="Εκτέλεση του browser σε headless mode.")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Καταστολή μηνυμάτων στην κονσόλα.")
    parser.add_argument("--dt", default=None,
                        help="Συγκεκριμένη ημερομηνία λογαριασμού (π.χ. 20261019).")
    parser.add_argument("--all", action="store_true",
                        help="Κατέβασε όλους τους εκκαθαριστικούς.")
    args = parser.parse_args()

    runner = TestAutodei(headless_mode=args.headless, quiet_mode=args.quiet)
    try:
        runner.setup_method(None)
        runner.test_autodei(args.account, dt_filter=args.dt, download_all=args.all)
    finally:
        runner.teardown_method(None)
