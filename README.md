# Cadoopet Invoice Bot

A Telegram bot that automates invoice processing using Google Gemini AI, Google Sheets, and Google Drive.

## Workflow

1. Send a PDF or image invoice to the Telegram bot
2. Bot asks who paid and who will claim the expense
3. Google Gemini extracts: month, invoice date, transaction type, category, supplier, description, amount
4. Bot replies with all extracted info for your approval
5. On approval: data is added to Google Sheet and the file is uploaded to Google Drive

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. Get a Google Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key

### 3. Set Up Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin > Service Accounts** and create a service account
5. Create a JSON key for the service account
6. Download the JSON key file and save it as `credentials/service_account.json`

### 4. Set Up Google Sheet

1. Create a new Google Sheet
2. Add these headers in Row 1:
   ```
   Month | Invoice Date | Transaction Type | Category | Supplier | Description | Amount | Paid By | Claim By
   ```
3. Share the sheet with the service account email (found in the JSON key file as `client_email`) - give **Editor** access
4. Copy the Sheet ID from the URL

### 5. Set Up Google Drive Folder

1. Create a folder in Google Drive for storing invoices
2. Share the folder with the service account email - give **Editor** access
3. Copy the Folder ID from the URL

### 6. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `TELEGRAM_BOT_TOKEN` - from BotFather
- `GEMINI_API_KEY` - from Google AI Studio
- `GOOGLE_SHEET_ID` - from your Google Sheet URL
- `GOOGLE_DRIVE_FOLDER_ID` - from your Google Drive folder URL
- `ALLOWED_USER_IDS` - (optional) comma-separated Telegram user IDs for access control

### 7. Install and Run

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

## Usage

1. Open Telegram and message your bot
2. Send `/start` or directly send a PDF/image invoice
3. Answer "Paid by?" and "Claim by?" prompts
4. Review the extracted information
5. Tap **Approve** to save to Google Sheet + Drive, or **Reject** to discard

## Project Structure

```
cadoopet-bot/
├── bot.py                          # Main entry point
├── config.py                       # Environment configuration
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── handlers/
│   └── invoice_handler.py          # Telegram conversation flow
├── services/
│   ├── gemini_service.py           # Gemini AI invoice extraction
│   ├── google_sheets_service.py    # Google Sheets integration
│   └── google_drive_service.py     # Google Drive file upload
└── credentials/
    └── service_account.json        # Google service account key (not committed)
```
