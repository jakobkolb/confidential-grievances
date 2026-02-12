import os
from unittest.mock import patch

import pytest

from src.bot.app import build_app

FULL_ENV = {
    "BOT_TOKEN": "fake-token",
    "MEDIATOR_CHAT_ID": "-1001",
    "TP_CHAT_ID": "-1002",
    "BOT_SECRET_SALT": "salt",
}


@pytest.mark.parametrize("missing_var", [
    "BOT_TOKEN",
    "MEDIATOR_CHAT_ID",
    "TP_CHAT_ID",
    "BOT_SECRET_SALT",
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
        assert app.bot_data["tp_chat_id"] == -1002
        assert app.bot_data["secret_salt"] == "salt"


def test_build_app_registers_handlers():
    with patch.dict(os.environ, FULL_ENV, clear=True):
        app = build_app()
        assert len(app.handlers[0]) == 2  # message handler + /escalate command
