import os
import logging

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from src.bot.error_reporting import TelegramErrorHandler, handle_update_error
from src.bot.handlers import handle_grievance, handle_escalate, handle_start

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
    token            = _require_env("BOT_TOKEN")
    error_chat_id    = int(_require_env("TELEGRAM_ERROR_CHAT_ID"))
    mediator_chat_id = int(_require_env("MEDIATOR_CHAT_ID"))
    secret_salt      = _require_env("BOT_SECRET_SALT")

    tp_recipient  = _require_env("TP_EMAIL_RECIPIENT")
    bot_email     = _require_env("BOT_EMAIL_ADDRESS")
    bot_password  = _require_env("BOT_EMAIL_PASSWORD")
    smtp_host     = _require_env("SMTP_HOST")
    smtp_port     = int(_require_env("SMTP_PORT"))
    imap_host     = _require_env("IMAP_HOST")
    imap_port     = int(_require_env("IMAP_PORT"))

    app = ApplicationBuilder().token(token).build()

    logging.getLogger().addHandler(TelegramErrorHandler(token, error_chat_id))
    app.add_error_handler(handle_update_error)

    app.bot_data["mediator_chat_id"] = mediator_chat_id
    app.bot_data["secret_salt"]      = secret_salt
    app.bot_data["tp_email_cfg"] = {
        "recipient": tp_recipient,
        "from_addr": bot_email,
        "password":  bot_password,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "imap_host": imap_host,
        "imap_port": imap_port,
    }

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_grievance))
    app.add_handler(CommandHandler("escalate", handle_escalate))

    return app


def main():
    load_dotenv()
    logger.info("Starting bot...")
    app = build_app()
    app.run_polling()


if __name__ == "__main__":
    main()
