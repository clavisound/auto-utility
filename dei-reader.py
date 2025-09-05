
from pypdf import PdfReader
import datetime
import os
import argparse
import re
import json

def extract_text_from_pdf(pdf_path):
    """
    Εξάγει όλο το κείμενο από ένα αρχείο PDF.

    Args:
        pdf_path (str): Η διαδρομή προς το αρχείο PDF.

    Returns:
        str: Το εξαγόμενο κείμενο από το PDF.
    """
    text = ""
    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)

        for page_num in range(num_pages):
            page = reader.pages[page_num]
            text += page.extract_text() + "\n" # Προσθέτουμε αλλαγή γραμμής μεταξύ των σελίδων
        return text
    except Exception as e:
        return f"Σφάλμα κατά την ανάγνωση του PDF: {e}"

# Χρήση της συνάρτησης
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Εξαγωγή κειμένου από αρχείο PDF.")
    # Αλλαγή: Ορισμός του ορίσματος ως positional (χωρίς -o ή --output)
    parser.add_argument("pdf_file_path", help="Η διαδρομή προς το αρχείο PDF που θα διαβαστεί.")
    args = parser.parse_args()

    pdf_file = args.pdf_file_path # Πρόσβαση στο όρισμα με το όνομά του

    extracted_content = extract_text_from_pdf(pdf_file)

    # Εξαγωγή πληροφοριών
    data = {}

    # 1. ΠΟΣΟ ΠΛΗΡΩΜΗΣ
    # Regex: "ΠΟΣΟ ΠΛΗΡΩΜΗΣ" ακολουθούμενο από *, κενά, το ποσό (αριθμοί, κόμματα, τελείες) και €
    match_amount = re.search(r"ΠΟΣΟ ΠΛΗΡΩΜΗΣ\s*\*\s*([\d.,]+)\s*€", extracted_content)
    if match_amount:
        data["amountToPay"] = match_amount.group(1)

    # 2. Κωδικός ηλεκτρονικής πληρωμής (RF)
    # Regex: RF ακολουθούμενο από 20 ή περισσότερα ψηφία (ή όσα είναι συνήθως)
    # Θα πρέπει να είναι πιο συγκεκριμένο αν υπάρχουν άλλα RF στο κείμενο
    match_rf = re.search(r"(RF\d{20,})", extracted_content)
    if match_rf:
        data["RFcode"] = match_rf.group(1)

    # 3. ΕΞΟΦΛΗΣΗ ΕΩΣ (ημερομηνία στην επόμενη γραμμή)
    # Regex: "ΕΞΟΦΛΗΣΗ ΕΩΣ" ακολουθούμενο από οτιδήποτε μέχρι την επόμενη γραμμή, και μετά την ημερομηνία
    match_due_date = re.search(r"ΕΞΟΦΛΗΣΗ ΕΩΣ\s*\n\s*([\d./]+)", extracted_content)
    if match_due_date:
        data["paymentDue"] = match_due_date.group(1)

    # 4. Επόμενη καταμέτρηση (ημερομηνία στην επόμενη γραμμή)
    # Regex: "Επόμενη καταμέτρηση" ακολουθούμενο από οτιδήποτε μέχρι την επόμενη γραμμή, και μετά την ημερομηνία
    match_next_reading = re.search(r"Επόμενη καταμέτρηση\s*\n\s*([\d./]+)", extracted_content)
    if match_next_reading:
        data["nextMeasurement"] = match_next_reading.group(1)

    # Εμφάνιση των δεδομένων σε μορφή JSON
    print(json.dumps(data, ensure_ascii=False, indent=4))
