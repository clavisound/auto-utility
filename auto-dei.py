
import time
import os
import glob
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import argparse
import datetime

class TestAutodei:
    def __init__(self, headless_mode=False, quiet_mode=False):
        self.headless_mode = headless_mode
        self.quiet_mode = quiet_mode
        self.download_dir = None # Initialize to None
        self.driver = None # Initialize to None
        self.wait = None # Initialize to None
        self.vars = {} # Initialize to empty dict

    def _print_message(self, message):
        if not self.quiet_mode:
            print(message)

    def setup_method(self, method):
        # 1. Ορισμός και δημιουργία του υποφακέλου 'dei' για τις λήψεις
        self.download_dir = os.path.join(os.getcwd(), "dei")
        os.makedirs(self.download_dir, exist_ok=True) # Δημιουργία φακέλου αν δεν υπάρχει
        self._print_message(f"Οι λήψεις PDF θα αποθηκευτούν στον κατάλογο: {self.download_dir}")

        # 2. Ρύθμιση επιλογών Firefox για αυτόματη λήψη PDF
        firefox_options = Options()
        # Ορισμός προτιμήσεων για τη διαχείριση λήψεων
        firefox_options.set_preference("browser.download.folderList", 2) # 0=Desktop, 1=Downloads, 2=Custom
        firefox_options.set_preference("browser.download.dir", self.download_dir)
        firefox_options.set_preference("browser.download.manager.showWhenStarting", False) # Να μην εμφανίζεται ο διαχειριστής λήψεων
        firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf") # Να αποθηκεύει αυτόματα τα PDF
        firefox_options.set_preference("pdfjs.disabled", True) # Απενεργοποίηση του ενσωματωμένου PDF viewer του Firefox

        # Ρύθμιση headless mode
        if self.headless_mode:
            firefox_options.add_argument("--headless")
            self._print_message("Εκτέλεση σε headless mode.")

        # 3. Εκκίνηση του Firefox WebDriver με τις προσαρμοσμένες επιλογές
        self.driver = webdriver.Firefox(options=firefox_options)
        # 4. Αρχικοποίηση WebDriverWait για αξιόπιστη αναμονή στοιχείων
        self.wait = WebDriverWait(self.driver, 20) # Αυξήθηκε το timeout για μεγαλύτερη αντοχή

    def teardown_method(self, method):
        # 5. Κλείσιμο του browser
        if self.driver: # Ensure driver exists before quitting
            self.driver.quit()
        # 6. Δεν γίνεται καθαρισμός του φακέλου λήψεων, καθώς ο χρήστης θέλει να διατηρήσει τα αρχεία.

    def test_autodei(self, account_number): # Τροποποίηση για να δέχεται account_number
        self.driver.get("https://mydei.dei.gr/el")
        self.driver.set_window_size(650, 528) # Διατηρείται το αρχικό μέγεθος παραθύρου

        time.sleep(3) # Προσθήκη καθυστέρησης πριν το cookie banner

        # 7. Αναμονή και κλικ στο κουμπί αποδοχής cookies (αν υπάρχει)
        try:
            accept_cookies_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_cookies_button.click()
            self._print_message("Το cookie banner έγινε αποδεκτό.")
            time.sleep(2) # Προσθήκη καθυστέρησης μετά το κλικ στο cookie banner
        except:
            self._print_message("Το cookie banner δεν βρέθηκε ή δεν ήταν clickable.")
            pass # Συνέχισε αν δεν υπάρχει cookie banner ή δεν μπορεί να γίνει κλικ

        # 8. Κλικ στο κουμπί "Κοινόχρηστα"
        # Αναμονή μέχρι το κουμπί να είναι ορατό και clickable
        koinoxrista_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//div[text()='Κοινόχρηστα']]"))
        )
        koinoxrista_button.click()

        # 9. Αναμονή για το πεδίο εισαγωγής "ContractAccount" και εισαγωγή τιμής
        contract_account_field = self.wait.until(
            EC.element_to_be_clickable((By.ID, "ContractAccount"))
        )
        contract_account_field.send_keys(account_number) # Χρήση του account_number από το όρισμα

        # 10. Κλικ στο κουμπί υποβολής
        submit_button = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".b-login-panel__submit"))
        )
        submit_button.click()

        # 11. Κλικ στον σύνδεσμο "Λήψη"
        download_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Λήψη"))
        )
        download_link.click()

        # 12. Αναμονή για την ολοκλήρωση της λήψης του PDF
        downloaded_file_path = self._wait_for_download_completion(self.download_dir, timeout=60) # Αυξήθηκε το timeout

        if downloaded_file_path:
            # 13. Μετονομασία του αρχείου σε ημερομηνία
            current_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_filename = f"{current_date}.pdf"
            new_full_path = os.path.join(self.download_dir, new_filename)

            # Μετακίνηση και μετονομασία του αρχείου
            shutil.move(downloaded_file_path, new_full_path)
            self._print_message(f"Το PDF κατέβηκε επιτυχώς και αποθηκεύτηκε ως: {new_full_path}")
        else:
            self._print_message("Η λήψη του PDF απέτυχε ή έληξε το χρονικό όριο.")

    def _wait_for_download_completion(self, download_folder, timeout=30):
        """
        Περιμένει μέχρι να εμφανιστεί ένα αρχείο PDF στον καθορισμένο φάκελο λήψεων.
        Επιστρέφει την πλήρη διαδρομή του αρχείου αν βρεθεί, αλλιώς None.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Λίστα όλων των αρχείων στον κατάλογο λήψεων
            list_of_files = glob.glob(os.path.join(download_folder, '*'))
            # Φιλτράρισμα για αρχεία PDF
            pdf_files = [f for f in list_of_files if f.endswith('.pdf')]

            if pdf_files:
                # Επιστρέφουμε το πρώτο αρχείο PDF που βρέθηκε
                # Αν αναμένονται πολλαπλές λήψεις, ίσως χρειαστεί πιο σύνθετη λογική
                return pdf_files[0]
            time.sleep(1) # Ελέγχουμε κάθε δευτερόλεπτο
        return None

# Για να εκτελέσετε το script εκτός του pytest framework:
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Αυτοματοποίηση λήψης λογαριασμού από το myΔΕΗ.")
    parser.add_argument("-a", "--account", required=True, help="Ο αριθμός λογαριασμού συμβολαίου (π.χ., 300004254333).")
    parser.add_argument("--headless", action="store_true", help="Εκτέλεση του browser σε headless mode (χωρίς γραφικό περιβάλλον).")
    parser.add_argument("-q", "--quiet", action="store_true", help="Καταστολή μηνυμάτων στην κονσόλα.")
    args = parser.parse_args()

    test_runner = TestAutodei(headless_mode=args.headless, quiet_mode=args.quiet)
    try:
        test_runner.setup_method(None) # 'None' because we don't use 'method' argument in setup_method
        test_runner.test_autodei(args.account) # Πέρασμα του αριθμού λογαριασμού
    finally:
        test_runner.teardown_method(None) # 'None' because we don't use 'method' argument in teardown_method
