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

from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, PicklePersistence

import config
from handlers.invoice_handler import get_invoice_conversation_handler, handle_approval

# Configure logging — DEBUG so we can see every getUpdates response
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and answer callback queries so users don't see infinite loading."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.callback_query:
        try:
            await update.callback_query.answer("An error occurred. Please try again.")
        except Exception:
            pass


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Check your .env file.")
    if not config.GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set. Check your .env file.")

    persistence = PicklePersistence(filepath=f"{config.DOWNLOAD_DIR}/conversation_state.pkl")
    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .build()
    )

    # Register the invoice conversation handler
    app.add_handler(get_invoice_conversation_handler())

    # DIAGNOSTIC: catch-all for ANY callback query (runs in separate group so
    # it fires even if the ConversationHandler already handled or skipped it)
    async def debug_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        logger.warning(">>> DEBUG: callback_query received! data=%s user=%s", q.data, q.from_user.id)
        await q.answer()
        return await handle_approval(update, context)

    app.add_handler(CallbackQueryHandler(debug_callback), group=1)

    app.add_error_handler(error_handler)

    logger.info("Bot started. Listening for messages...")
    app.run_polling(
        drop_pending_updates=False,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
