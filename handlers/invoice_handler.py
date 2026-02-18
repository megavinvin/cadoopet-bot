import asyncio
import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import config
from services.gemini_service import extract_invoice_data
from services.google_sheets_service import append_invoice_row
from services.google_drive_service import upload_file

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FILE, WAITING_PAID_BY, WAITING_CLAIM_BY, WAITING_APPROVAL = range(4)


def _is_allowed(user_id: int) -> bool:
    """Check if user is in the allowed list (allow all if list is empty)."""
    if not config.ALLOWED_USER_IDS:
        return True
    return user_id in config.ALLOWED_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if not _is_allowed(update.effective_user.id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome to Invoice Bot!\n\n"
        "Send me a PDF or image of your invoice to get started.\n\n"
        "Commands:\n"
        "/start - Start new invoice submission\n"
        "/cancel - Cancel current operation"
    )
    return WAITING_FILE


async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming document or photo."""
    if not _is_allowed(update.effective_user.id):
        return ConversationHandler.END

    message = update.message
    file_path = None

    try:
        if message.document:
            doc = message.document
            file_name = doc.file_name or "invoice"
            ext = os.path.splitext(file_name)[1].lower()

            if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".webp"):
                await message.reply_text(
                    "Please send a PDF or image file (JPG, PNG, WEBP)."
                )
                return WAITING_FILE

            tg_file = await doc.get_file()
            file_path = os.path.join(config.DOWNLOAD_DIR, file_name)
            await tg_file.download_to_drive(file_path)

        elif message.photo:
            # Get the highest resolution photo
            photo = message.photo[-1]
            tg_file = await photo.get_file()
            file_name = f"invoice_{photo.file_unique_id}.jpg"
            file_path = os.path.join(config.DOWNLOAD_DIR, file_name)
            await tg_file.download_to_drive(file_path)

        else:
            await message.reply_text(
                "Please send a PDF document or a photo of your invoice."
            )
            return WAITING_FILE

        # Store file info in context
        context.user_data["file_path"] = file_path
        context.user_data["file_name"] = file_name

        await message.reply_text("Got it! Who paid for this invoice?")
        return WAITING_PAID_BY

    except Exception as e:
        logger.error(f"Error receiving file: {e}")
        await message.reply_text(
            "Error processing the file. Please try again."
        )
        return WAITING_FILE


async def receive_paid_by(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle paid_by input."""
    context.user_data["paid_by"] = update.message.text.strip()
    await update.message.reply_text("Who will claim this expense?")
    return WAITING_CLAIM_BY


async def receive_claim_by(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle claim_by input and process the invoice with Gemini."""
    context.user_data["claim_by"] = update.message.text.strip()

    await update.message.reply_text("Processing your invoice with AI... please wait.")

    file_path = context.user_data["file_path"]

    try:
        extracted = await asyncio.to_thread(extract_invoice_data, file_path)
    except Exception as e:
        logger.error(f"Gemini extraction error: {e}")
        await update.message.reply_text(
            f"Failed to extract invoice data: {e}\n\n"
            "Please try sending the invoice again with /start."
        )
        return ConversationHandler.END

    # Merge user-provided fields
    extracted["paid_by"] = context.user_data["paid_by"]
    extracted["claim_by"] = context.user_data["claim_by"]
    context.user_data["invoice_data"] = extracted

    # Format summary for approval
    summary = (
        "Here is the extracted invoice info:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Month:            {extracted.get('month', 'N/A')}\n"
        f"  Invoice Date:     {extracted.get('invoice_date', 'N/A')}\n"
        f"  Transaction Type: {extracted.get('transaction_type', 'N/A')}\n"
        f"  Category:         {extracted.get('category', 'N/A')}\n"
        f"  Supplier:         {extracted.get('supplier', 'N/A')}\n"
        f"  Description:      {extracted.get('description', 'N/A')}\n"
        f"  Amount:           {extracted.get('amount', 'N/A')}\n"
        f"  Paid By:          {extracted.get('paid_by', 'N/A')}\n"
        f"  Claim By:         {extracted.get('claim_by', 'N/A')}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Do you approve this information?"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Approve", callback_data="approve"),
                InlineKeyboardButton("Reject", callback_data="reject"),
            ]
        ]
    )

    await update.message.reply_text(summary, reply_markup=keyboard)
    return WAITING_APPROVAL


async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle approve/reject callback."""
    query = update.callback_query

    if query is None:
        return ConversationHandler.END

    try:
        # Always acknowledge callback quickly to stop Telegram loading UI.
        await query.answer()
    except Exception as e:
        logger.warning(f"Failed to answer callback query: {e}")

    logger.info(
        "Approval callback received: data=%s user_id=%s has_session=%s",
        query.data,
        update.effective_user.id if update.effective_user else "unknown",
        bool(context.user_data),
    )

    if query.data == "approve":
        required_keys = ("invoice_data", "file_path", "file_name")
    else:
        required_keys = ("file_path",)

    if not all(key in context.user_data for key in required_keys):
        expired_msg = (
            "This approval session has expired or was reset.\n\n"
            "Please send /start and submit the invoice again."
        )
        try:
            await query.edit_message_text(expired_msg)
        except Exception:
            if query.message:
                await query.message.reply_text(expired_msg)
        context.user_data.clear()
        return ConversationHandler.END

    try:
        if query.data == "approve":
            await query.edit_message_text("Approved! Saving to Google Sheet and uploading to Drive...")

            invoice_data = context.user_data["invoice_data"]
            file_path = context.user_data["file_path"]
            file_name = context.user_data["file_name"]

            errors = []

            # 1. Upload file to Google Drive first (so we can include the link in Sheets)
            drive_link = ""
            try:
                drive_link = await asyncio.to_thread(upload_file, file_path, file_name)
                drive_msg = f"Google Drive: Uploaded - {drive_link}"
            except Exception as e:
                logger.error(f"Google Drive error: {e}")
                drive_msg = f"Google Drive: Failed - {e}"
                errors.append("drive")

            # 2. Append to Google Sheet (with drive link)
            invoice_data["drive_link"] = drive_link
            try:
                row_num = await asyncio.to_thread(append_invoice_row, invoice_data)
                sheet_msg = f"Google Sheet: Row {row_num} added."
            except Exception as e:
                logger.error(f"Google Sheets error: {e}")
                sheet_msg = f"Google Sheet: Failed - {e}"
                errors.append("sheet")

            # Clean up downloaded file
            try:
                os.remove(file_path)
            except OSError:
                pass

            status = "Done!" if not errors else "Completed with some errors."
            await query.message.reply_text(
                f"{status}\n\n"
                f"{sheet_msg}\n"
                f"{drive_msg}\n\n"
                "Send another invoice or use /start to begin again."
            )

        else:
            # Clean up downloaded file
            try:
                os.remove(context.user_data.get("file_path", ""))
            except OSError:
                pass

            await query.edit_message_text(
                "Rejected. No data was saved.\n\n"
                "Send another invoice or use /start to begin again."
            )
    except Exception as e:
        logger.error(f"Error in handle_approval: {e}", exc_info=True)
        await query.message.reply_text(
            f"An error occurred: {e}\n\n"
            "Please try again with /start."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command."""
    # Clean up downloaded file if any
    try:
        os.remove(context.user_data.get("file_path", ""))
    except (OSError, TypeError):
        pass

    context.user_data.clear()
    await update.message.reply_text(
        "Operation cancelled. Send /start to begin again."
    )
    return ConversationHandler.END


def get_invoice_conversation_handler() -> ConversationHandler:
    """Build and return the conversation handler for invoice processing."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            # Also allow sending a file directly without /start
            MessageHandler(filters.Document.ALL | filters.PHOTO, receive_file),
        ],
        states={
            WAITING_FILE: [
                MessageHandler(filters.Document.ALL | filters.PHOTO, receive_file),
            ],
            WAITING_PAID_BY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_paid_by),
            ],
            WAITING_CLAIM_BY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_claim_by),
            ],
            WAITING_APPROVAL: [
                CallbackQueryHandler(handle_approval, pattern="^(approve|reject)$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
        name="invoice_conversation",
        persistent=True,
    )
