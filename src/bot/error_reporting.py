import json
import logging
import traceback
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


class TelegramErrorHandler(logging.Handler):
    """Logging handler that forwards ERROR+ records to a Telegram chat."""

    def __init__(self, bot_token: str, chat_id: int) -> None:
        super().__init__(level=logging.ERROR)
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._chat_id = chat_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self._format_record(record)
            self._send(text)
        except Exception:
            # Never let error reporting crash the bot.
            self.handleError(record)

    def _format_record(self, record: logging.LogRecord) -> str:
        lines = [
            f"🔴 *Bot Error*",
            f"`{record.levelname}` — `{record.name}`",
            f"```\n{record.getMessage()}\n```",
        ]
        if record.exc_info:
            tb = "".join(traceback.format_exception(*record.exc_info)).strip()
            # Telegram messages have a 4096-char limit; truncate if needed.
            if len(tb) > 3000:
                tb = tb[-3000:]
            lines.append(f"```\n{tb}\n```")
        return "\n".join(lines)

    def _send(self, text: str) -> None:
        payload = json.dumps({
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)


async def handle_update_error(update: object, context) -> None:
    """python-telegram-bot error handler — logs exceptions so the
    TelegramErrorHandler picks them up via the standard logging pipeline."""
    logger.error("Unhandled exception in update handler", exc_info=context.error)
