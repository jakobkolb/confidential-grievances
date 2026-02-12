import os
import logging

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from src.bot.handlers import handle_grievance, handle_escalate

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is not set")
    return value


def build_app():
    """Build the Telegram Application from environment variables."""
    token = _require_env("BOT_TOKEN")
    mediator_chat_id = int(_require_env("MEDIATOR_CHAT_ID"))
    tp_chat_id = int(_require_env("TP_CHAT_ID"))
    secret_salt = _require_env("BOT_SECRET_SALT")

    app = ApplicationBuilder().token(token).build()

    app.bot_data["mediator_chat_id"] = mediator_chat_id
    app.bot_data["tp_chat_id"] = tp_chat_id
    app.bot_data["secret_salt"] = secret_salt

    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_grievance))
    app.add_handler(CommandHandler("escalate", handle_escalate))

    return app


def main():
    logger.info("Starting bot...")
    app = build_app()
    app.run_polling()


if __name__ == "__main__":
    main()
