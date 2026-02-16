# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot that automates invoice processing: users send PDF/image invoices, Google Gemini AI extracts structured data, and approved invoices are saved to Google Sheets with files uploaded to Google Drive.

## Running the Bot

```bash
uv run bot.py
```

This auto-creates a virtual environment and installs dependencies via `uv`. No separate install step needed.

There are no automated tests in this project.

## Architecture

**Entry point:** `bot.py` — creates the Telegram application, registers the conversation handler, and runs polling.

**Configuration:** `config.py` — loads all settings from `.env` via `python-dotenv`. Exposes module-level constants. `ALLOWED_USER_IDS` is parsed from a comma-separated string; an empty list means all users are allowed.

**Conversation flow:** `handlers/invoice_handler.py` — implements a 4-state `ConversationHandler`:
1. `WAITING_FILE` → user sends PDF or image (JPG, JPEG, PNG, WEBP)
2. `WAITING_PAID_BY` → bot asks who paid
3. `WAITING_CLAIM_BY` → bot asks who claims; triggers Gemini extraction
4. `WAITING_APPROVAL` → displays extracted data with Approve/Reject inline buttons

On approval: appends row to Google Sheet, uploads file to Google Drive, deletes local file. On reject: deletes local file only.

**Services layer** (`services/`):
- `gemini_service.py` — sends invoice to `gemini-2.0-flash` model, returns structured JSON with 7 fields (month, invoice_date, transaction_type, category, supplier, description, amount). Handles both PDF binary data and PIL images.
- `google_sheets_service.py` — authenticates via service account, appends a 9-column row (7 extracted fields + paid_by + claim_by) using `gspread`.
- `google_drive_service.py` — authenticates via service account, uploads file with correct MIME type, returns web view link.

## Key Dependencies

- `python-telegram-bot` (v21.10) — async Telegram bot framework
- `google-generativeai` — Gemini AI client
- `gspread` — Google Sheets client
- `google-api-python-client` — Google Drive API
- `Pillow` — image loading for Gemini

## Environment Configuration

Copy `.env.example` to `.env`. Required variables: `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_SHEET_ID`, `GOOGLE_DRIVE_FOLDER_ID`. Google service account credentials go in `credentials/service_account.json`.
