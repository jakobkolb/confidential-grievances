import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.hashing import compute_hash

logger = logging.getLogger(__name__)


async def handle_grievance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a private DM: hash it and route to Mediator + TP groups."""
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    body = message.text or ""
    timestamp = datetime.now(timezone.utc).isoformat()

    mediator_chat_id = context.bot_data["mediator_chat_id"]
    tp_chat_id = context.bot_data["tp_chat_id"]
    salt = context.bot_data["secret_salt"]

    msg_hash = compute_hash(user.id, body, timestamp, salt)

    # Mediator group: body + hash + timestamp (NO identity)
    mediator_text = (
        f"New grievance\n"
        f"Hash: {msg_hash}\n"
        f"Time: {timestamp}\n\n"
        f"{body}"
    )
    await context.bot.send_message(chat_id=mediator_chat_id, text=mediator_text)

    # TP group: hash + identity + timestamp (NO body)
    sender = f"@{user.username}" if user.username else f"id:{user.id}"
    tp_text = (
        f"Identity record\n"
        f"Hash: {msg_hash}\n"
        f"Sender: {sender} (uid: {user.id})\n"
        f"Time: {timestamp}"
    )
    await context.bot.send_message(chat_id=tp_chat_id, text=tp_text)

    # Confirm receipt to PG
    await message.reply_text("Your grievance has been received.")
    logger.info("Grievance routed — hash: %s", msg_hash)


async def handle_escalate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /escalate <hash> from the Mediator group — notify the TP group."""
    message = update.effective_message
    if message is None:
        return

    mediator_chat_id = context.bot_data["mediator_chat_id"]

    # Only allow from the Mediator group
    if message.chat_id != mediator_chat_id:
        return

    if not context.args:
        await message.reply_text("Usage: /escalate <hash>")
        return

    msg_hash = context.args[0]
    tp_chat_id = context.bot_data["tp_chat_id"]

    tp_text = (
        f"Escalation request\n"
        f"Hash: {msg_hash}\n\n"
        f"Please look up this hash and contact the sender."
    )
    await context.bot.send_message(chat_id=tp_chat_id, text=tp_text)
    await message.reply_text(f"Escalation for {msg_hash} sent to Trusted Party.")
    logger.info("Escalation routed — hash: %s", msg_hash)
