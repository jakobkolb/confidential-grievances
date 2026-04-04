import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from telegram import Bot, Update
from telegram.error import ChatMigrated
from telegram.ext import ContextTypes

from src.bot.hashing import compute_hash

logger = logging.getLogger(__name__)

_MESSAGES_PATH = Path(__file__).parent.parent.parent / "messages.json"
with _MESSAGES_PATH.open() as _f:
    MESSAGES: dict = json.load(_f)


async def _send(bot: Bot, bot_data: dict, chat_id_key: str, text: str) -> None:
    """Send a message, transparently handling group->supergroup migration."""
    try:
        await bot.send_message(chat_id=bot_data[chat_id_key], text=text)
    except ChatMigrated as exc:
        old_id = bot_data[chat_id_key]
        bot_data[chat_id_key] = exc.new_chat_id
        logger.warning(
            "Chat '%s' migrated: %s -> %s. Update your .env!",
            chat_id_key, old_id, exc.new_chat_id,
        )
        await bot.send_message(chat_id=exc.new_chat_id, text=text)


async def handle_grievance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a private DM: hash it and route to Mediator + TP groups."""
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    body = message.text or ""
    timestamp = datetime.now(timezone.utc).isoformat()

    salt = context.bot_data["secret_salt"]

    msg_hash = compute_hash(user.id, body, timestamp, salt)

    # Mediator group: body + hash + timestamp (NO identity)
    mediator_text = MESSAGES["mediator_message"].format(
        msg_hash=msg_hash, timestamp=timestamp, body=body
    )
    await _send(context.bot, context.bot_data, "mediator_chat_id", mediator_text)

    # TP group: hash + identity + timestamp (NO body)
    sender = f"@{user.username}" if user.username else f"id:{user.id}"
    tp_text = MESSAGES["tp_grievance_message"].format(
        msg_hash=msg_hash, sender=sender, user_id=user.id, timestamp=timestamp
    )
    await _send(context.bot, context.bot_data, "tp_chat_id", tp_text)

    # Confirm receipt to PG
    await message.reply_text(MESSAGES["grievance_received"])
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
        await message.reply_text(MESSAGES["escalate_usage"])
        return

    msg_hash = context.args[0]

    tp_text = MESSAGES["tp_escalation_message"].format(msg_hash=msg_hash)
    await _send(context.bot, context.bot_data, "tp_chat_id", tp_text)
    await message.reply_text(MESSAGES["escalate_sent"].format(msg_hash=msg_hash))
    logger.info("Escalation routed — hash: %s", msg_hash)
