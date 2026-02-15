#!/usr/bin/env python3
"""Telegram Invoice Bot - Main entry point.

Workflow:
1. User sends a PDF/image invoice to the bot
2. Bot asks who paid and who will claim the expense
3. Gemini AI extracts invoice details (month, date, type, category, supplier, description, amount)
4. Bot replies with all extracted info for user approval
5. On approval: data is written to Google Sheet and file is uploaded to Google Drive
"""

import logging

from telegram.ext import ApplicationBuilder

import config
from handlers.invoice_handler import get_invoice_conversation_handler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Check your .env file.")
    if not config.GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set. Check your .env file.")

    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register the invoice conversation handler
    app.add_handler(get_invoice_conversation_handler())

    logger.info("Bot started. Listening for messages...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
