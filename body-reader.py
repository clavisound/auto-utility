
import base64
import re
import json
import sys
from email import message_from_string
import argparse

def parse_eyath_email(processed_content):
    data = {}
    data["type"] = "water"
    data["company"] = "eyath"
    
    # Consumer Number: "Αριθμός καταναλωτή:"
    consumer_number_match = re.search(r"Αριθμός καταναλωτή:\s*([0-9-]{15})", processed_content)
    if consumer_number_match:
        data["consumerNumber"] = consumer_number_match.group(1)

    # Account Number: "ΑΚΝ" followed by alphanumeric characters
    account_number_match = re.search(r"ΑΚΝ([A-Z0-9]+)", processed_content)
    if account_number_match:
        data["accountNumber"] = "ΑΚΝ" + account_number_match.group(1)

    # RF Code: "Κωδ. Εντολής Πληρωμής:" (There are two, taking the first one)
    rf_code_match = re.search(r"Κωδ\. Εντολής Πληρωμής:\s*([A-Z0-9]+)", processed_content)
    if rf_code_match:
        data["RFcode"] = rf_code_match.group(1)

    # Amount: "Ποσό πληρωμής:"
    amount_match = re.search(r"Ποσό πληρωμής:\s*([0-9,\.]+)", processed_content)
    if amount_match:
        data["amount"] = amount_match.group(1).replace(',', '.') # Replace comma with dot for consistency

    # Payment Due: "Ημερομηνία λήξης:"
    payment_due_match = re.search(r"Ημερομηνία λήξης:\s*(\d{2}/\d{2}/\d{4})", processed_content)
    if payment_due_match:
        data["paymentDue"] = payment_due_match.group(1)

    return json.dumps(data, ensure_ascii=False, indent=4)

def parse_dei_email(processed_content):
    data = {}
    data["type"] = "electricity"
    data["company"] = "dei"

    # RF Code: "Κωδικός Ηλεκτρονικής Πληρωμής"
    rf_code_match = re.search(r"Κωδικός Ηλεκτρονικής Πληρωμής\s*([A-Z0-9\s]+)", processed_content)
    if rf_code_match:
        data["RFcode"] = re.sub(r'\s+', '', rf_code_match.group(1))
        # Contract Number: last 12 digits of RFcode
        data["contractNumber"] = re.sub(r'\s+', '', rf_code_match.group(1))[-12:]

    # Amount: "Τελικό Ποσό Πληρωμής"
    amount_match = re.search(r"Τελικό Ποσό Πληρωμής\s*([0-9,\.]+)\s*€", processed_content)
    if amount_match:
        data["amount"] = amount_match.group(1).replace(',', '.')

    # Payment Due: "Ημερομηνία Λήξης"
    payment_due_match = re.search(r"Ημερομηνία Λήξης\s*(\d{2}/\d{2}/\d{4})", processed_content)
    if payment_due_match:
        data["paymentDue"] = payment_due_match.group(1)

    return json.dumps(data, ensure_ascii=False, indent=4)

def get_email_content(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return sys.stdin.read()

def main():
    parser = argparse.ArgumentParser(description="Parse email content for utility data.")
    parser.add_argument("--eyath", action="store_true", help="Parse as EYATH email.")
    parser.add_argument("--dei", action="store_true", help="Parse as DEI email.")
    parser.add_argument("-d", "--debug", action="store_true", help="Print decoded content as a single line for debugging.")
    parser.add_argument("file", nargs="?", help="Path to the email file (optional, reads from stdin if not provided).")
    args = parser.parse_args()

    email_content = get_email_content(args)

    msg = message_from_string(email_content)
    plain_text_payload = None
    for part in msg.walk():
        if part.get_content_type() == "text/plain" and part.get("Content-Transfer-Encoding") == "base64":
            plain_text_payload = part.get_payload()
            break

    if plain_text_payload is None:
        processed_content = "" # Or handle error appropriately
        # For now, let's assume it's an error if no plain text payload
        if not args.debug: # Only return error if not in debug mode
            print(json.dumps({"error": "Could not find base64 encoded plain text part."}, ensure_ascii=False, indent=4))
            sys.exit(1)
    else:
        processed_content = base64.b64decode(plain_text_payload).decode('utf-8').replace('>', '')

    if args.debug:
        print(processed_content.replace("\n", "\t").replace("\r", "\t"))
        sys.exit(0)
    
    result = None
    if args.eyath:
        result = parse_eyath_email(processed_content)
    elif args.dei:
        result = parse_dei_email(processed_content)
    else:
        # Auto-detect based on content
        if "eyath.gr" in processed_content:
            result = parse_eyath_email(processed_content)
        elif "dei.gr" in processed_content:
            result = parse_dei_email(processed_content)
        else:
            result = json.dumps({"error": "Could not determine email type. Use --eyath or --dei, or ensure 'eyath.gr' or 'dei.gr' is in the email content."}, ensure_ascii=False, indent=4)
    
    print(result)

if __name__ == "__main__":
    main()
