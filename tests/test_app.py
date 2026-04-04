import os
from unittest.mock import patch

import pytest

from src.bot.app import build_app

FULL_ENV = {
    "BOT_TOKEN":           "fake-token",
    "MEDIATOR_CHAT_ID":    "-1001",
    "BOT_SECRET_SALT":     "salt",
    "TP_EMAIL_RECIPIENT":  "tp@example.org",
    "BOT_EMAIL_ADDRESS":   "bot@example.org",
    "BOT_EMAIL_PASSWORD":  "password",
    "SMTP_HOST":           "smtp.example.org",
    "SMTP_PORT":           "465",
    "IMAP_HOST":           "imap.example.org",
    "IMAP_PORT":           "993",
}


@pytest.mark.parametrize("missing_var", [
    "BOT_TOKEN",
    "MEDIATOR_CHAT_ID",
    "BOT_SECRET_SALT",
    "TP_EMAIL_RECIPIENT",
    "BOT_EMAIL_ADDRESS",
    "BOT_EMAIL_PASSWORD",
    "SMTP_HOST",
    "SMTP_PORT",
    "IMAP_HOST",
    "IMAP_PORT",
])
def test_build_app_raises_without_required_env(missing_var):
    env = {k: v for k, v in FULL_ENV.items() if k != missing_var}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(RuntimeError, match=missing_var):
            build_app()


def test_build_app_succeeds_with_all_env():
    with patch.dict(os.environ, FULL_ENV, clear=True):
        app = build_app()
        assert app is not None
        assert app.bot_data["mediator_chat_id"] == -1001
        assert app.bot_data["secret_salt"] == "salt"
        assert app.bot_data["tp_email_cfg"]["recipient"] == "tp@example.org"
        assert app.bot_data["tp_email_cfg"]["smtp_port"] == 465
        assert app.bot_data["tp_email_cfg"]["imap_port"] == 993


def test_build_app_registers_handlers():
    with patch.dict(os.environ, FULL_ENV, clear=True):
        app = build_app()
        assert len(app.handlers[0]) == 3  # /start + message handler + /escalate command
