#!/usr/bin/env python3
import sys
import re
import json
from pypdf import PdfReader

def extract_data_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n" # Add newline to separate page content

    # Convert to one-liner and replace newlines with tabs
    one_liner_text = text.replace('\n', '\t')

    print("One-liner text:\n", one_liner_text)

    data = {}

    # RFpayment
    # The first string occurrence that starts with RF and ends with a tab.
    rf_match = re.search(r"\*\s*(RF[^*]+?)\s*\*", one_liner_text)
    if rf_match:
        data["RFpayment"] = rf_match.group(1).replace(' ', '').strip()

    # Dates
    # The first date with numbers like 11/04/2025 is the json startMeasurement.
    # The next date is endMeasurement. The next date is ignored. The next date is the nextStartMeasurement.
    dates = re.findall(r"\d{2}/\d{2}/\d{4}", one_liner_text)
    if len(dates) >= 4:
        data["startMeasurement"] = dates[0]
        data["endMeasurement"] = dates[1]
        # dates[2] is ignored
        data["nextStartMeasurement"] = dates[3]

    # duePayment
    # Before "ΠΑΓΙΟ ΤΕΛΟΣ" is the duePayment json date. Must be the same with before "ΠΟΛΗ" date.
    due_payment_pagio_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*ΠΑΓΙΟ ΤΕΛΟΣ", one_liner_text)
    due_payment_poli_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*ΠΟΛΗ", one_liner_text)

    if due_payment_pagio_match and due_payment_poli_match and \
       due_payment_pagio_match.group(1) == due_payment_poli_match.group(1):
        data["duePayment"] = due_payment_pagio_match.group(1)
    elif due_payment_pagio_match:
        data["duePayment"] = due_payment_pagio_match.group(1)
        print("Warning: 'ΠΑΓΙΟ ΤΕΛΟΣ' date found, but 'ΠΟΛΗ' date not found or mismatched for duePayment.", file=sys.stderr)
    elif due_payment_poli_match:
        data["duePayment"] = due_payment_poli_match.group(1)
        print("Warning: 'ΠΟΛΗ' date found, but 'ΠΑΓΙΟ ΤΕΛΟΣ' date not found or mismatched for duePayment.", file=sys.stderr)
    else:
        print("Warning: Could not find consistent 'duePayment' date based on 'ΠΑΓΙΟ ΤΕΛΟΣ' and 'ΠΟΛΗ'.", file=sys.stderr)


    # amount
    # Before UID text is the amount json data.
    # Assuming it's a number that might have a decimal point or comma.
    amount_match = re.search(r"ΑΡ\s*\.ΠΑΡΑΣΤΑΤΙΚΟΥ\s*:\s*(\d+(?:[.,]\d{1,2})?)", one_liner_text)
    if amount_match:
        # Replace comma with dot for float conversion
        amount_str = amount_match.group(1).replace(',', '.')
        try:
            data["amount"] = float(amount_str)
        except ValueError:
            print(f"Warning: Could not convert '{amount_str}' to float for amount.", file=sys.stderr)

    return json.dumps(data, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 eyath-reader.py <pdf_file_path>")
        sys.exit(1)

    pdf_file_path = sys.argv[1]
    try:
        extracted_json = extract_data_from_pdf(pdf_file_path)
        print(extracted_json)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
