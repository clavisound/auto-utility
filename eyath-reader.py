#!/usr/bin/env python3
import sys
import re
import json
from pypdf import PdfReader
import email
import os
import tempfile

def extract_data_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n" # Add newline to separate page content

    # Convert to one-liner and replace newlines with tabs
    one_liner_text = text.replace('\n', '\t')

    # print("One-liner text:\n", one_liner_text)

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

    # duePayment - New logic based on 5th and 6th date occurrences
    due_payment_found = False
    if len(dates) >= 6 and dates[4] == dates[5]:
        data["duePayment"] = dates[4]
        due_payment_found = True
    elif len(dates) >= 6:
        print("Warning: 5th and 6th dates found but do not match for duePayment.", file=sys.stderr)
    elif len(dates) >= 5:
        print("Warning: Only 5th date found, not enough dates for duePayment based on new rule.", file=sys.stderr)
    else:
        print("Warning: Not enough dates to apply new duePayment rule (need at least 6).", file=sys.stderr)

    # Existing duePayment logic as a fallback if not found by new rule
    if not due_payment_found:
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
    input_source = None
    if len(sys.argv) < 2 or sys.argv[1] == '-':
        # Read from stdin
        input_source = sys.stdin.buffer # Use buffer for binary read
        print("Reading email from stdin...", file=sys.stderr)
    else:
        # Read from file specified as argument
        pdf_file_path = sys.argv[1]
        print(f"Processing PDF from file: {pdf_file_path}", file=sys.stderr)
        try:
            extracted_json = extract_data_from_pdf(pdf_file_path)
            print(extracted_json)
        except Exception as e:
            print(f"An error occurred while processing file {pdf_file_path}: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0) # Exit after processing the file

    # If we are here, it means we are processing from stdin
    raw_email = input_source.read()
    msg = email.message_from_bytes(raw_email)

    pdf_found = False
    for part in msg.walk():
        if part.get_content_maintype() == 'application' and part.get_content_subtype() == 'pdf':
            pdf_found = True
            filename = part.get_filename()
            if not filename:
                filename = "attachment.pdf"

            # Get system temp directory
            temp_dir = tempfile.gettempdir()
            # Construct path for 'dei' folder inside temp directory
            eyath_folder = os.path.join(temp_dir, 'eyath')
            # Create 'dei' folder if it doesn't exist
            os.makedirs(eyath_folder, exist_ok=True)

            # Create a temporary file inside the 'dei' folder
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=eyath_folder) as temp_pdf:
                temp_pdf.write(part.get_payload(decode=True))
                temp_pdf_path = temp_pdf.name

            print(f"Processing attached PDF: {filename} (saved to {temp_pdf_path})", file=sys.stderr)
            try:
                extracted_json = extract_data_from_pdf(temp_pdf_path)
                print(extracted_json)
            except Exception as e:
                print(f"Error processing PDF attachment {filename}: {e}", file=sys.stderr)
            finally:
                os.remove(temp_pdf_path)
            break # Assuming only one PDF attachment is expected

    if not pdf_found:
        print("No PDF attachment found in the email.", file=sys.stderr)
        sys.exit(1)
