import gspread
from google.oauth2.service_account import Credentials
import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client() -> gspread.Client:
    """Create an authenticated gspread client."""
    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    return gspread.authorize(creds)


def append_invoice_row(data: dict) -> int:
    """Append a row of invoice data to the Google Sheet.

    Expected data keys:
        month, invoice_date, transaction_type, category,
        supplier, description, amount, paid_by, claim_by

    Returns the row number where data was inserted.
    """
    client = _get_client()
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    worksheet = sheet.worksheet(config.GOOGLE_SHEET_WORKSHEET)

    row = [
        data.get("month", ""),
        data.get("invoice_date", ""),
        data.get("transaction_type", ""),
        data.get("category", ""),
        data.get("supplier", ""),
        data.get("description", ""),
        data.get("amount", ""),
        data.get("paid_by", ""),
        data.get("claim_by", ""),
        data.get("drive_link", ""),
    ]

    worksheet.append_row(row, value_input_option="USER_ENTERED")
    return len(worksheet.get_all_values())
