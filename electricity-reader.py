
import io
import sys
from pypdf import PdfReader
import datetime
import os
import argparse
import re
import json


def extract_rf_code(extracted_content):
    """This is a generic RFcode reader."""
    rf_data = {}
    match_rf = re.search(r"(RF\d{20,})", extracted_content)
    if match_rf:
        rf_data["RFcode"] = match_rf.group(1)
        rf_data["contractNumber"] = rf_data["RFcode"][-12:]
    return rf_data

def parse_dei_data(extracted_content):
    """Dedicated DEI pdf reader. Valid from SEP25."""
    data = {}
    # 1. ΠΟΣΟ ΠΛΗΡΩΜΗΣ
    # Regex: "ΠΟΣΟ ΠΛΗΡΩΜΗΣ" ακολουθούμενο από *, κενά, το ποσό (αριθμοί, κόμματα, τελείες) και €
    match_amount = re.search(r"ΠΟΣΟ ΠΛΗΡΩΜΗΣ\s*\*\s*([\d.,]+)\s*€", extracted_content)
    if match_amount:
        data["amountToPay"] = match_amount.group(1)

    # 2. Κωδικός ηλεκτρονικής πληρωμής (RF) and Contract Number
    rf_data = extract_rf_code(extracted_content)
    data.update(rf_data)

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
    return data

def parse_zenith_pdf_data(extracted_content):
    """Dedicated zenith pdf reader. Valid from SEP25."""
    data = {
        "paymentDue": "error",
        "amountToPay": "error",
        "RFcode": "error",
        "contractNumber": "error"
    }
    # Regex to find dates in DD/MM/YYYY format
    date_pattern = r"\d{2}/\d{2}/\d{4}"
    all_dates = re.findall(date_pattern, extracted_content)

    # Check if there are at least 5 dates
    if len(all_dates) >= 5:
        data["paymentDue"] = all_dates[4] # 5th occurrence (0-indexed is 4)
        # Find the index of the duePayment date in the extracted content
        due_payment_index = extracted_content.find(data["paymentDue"])
        if due_payment_index != -1:
            # Search for amount after the duePayment date
            # Regex for amount: numbers with optional comma/dot for decimals, followed by €
            amount_pattern = r"([\d.,]+)\s*€"
            # Search only in the part of the string after the duePayment date
            search_area = extracted_content[due_payment_index + len(data["paymentDue"]):]
            match_amount = re.search(amount_pattern, search_area)
            if match_amount:
                data["amountToPay"] = match_amount.group(1)

    # RFcode and Contract Number
    rf_data = extract_rf_code(extracted_content)
    data.update(rf_data)

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Εξαγωγή κειμένου από αρχείο PDF.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dei", action="store_true", help="Επεξεργασία αρχείου PDF της ΔΕΗ.")
    group.add_argument("--zenith", action="store_true", help="Επεξεργασία αρχείου PDF της Zenith.")

    args = parser.parse_args()

    pdf_content = sys.stdin.buffer.read()
    reader = PdfReader(io.BytesIO(pdf_content))
    extracted_content = ""
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        extracted_content += page.extract_text() + "\n" # Προσθέτουμε αλλαγή γραμμής μεταξύ των σελίδων

    if args.dei:
        data = parse_dei_data(extracted_content)
    elif args.zenith:
        data = parse_zenith_pdf_data(extracted_content)
    elif "dei.gr" in extracted_content:
        data = parse_dei_data(extracted_content)
    elif "Ζενίθ" in extracted_content:
        data = parse_zenith_pdf_data(extracted_content)
    else:
        data = parse_zenith_pdf_data(extracted_content)

    # Εμφάνιση των δεδομένων σε μορφή JSON
    print(json.dumps(data, ensure_ascii=False, indent=4))
