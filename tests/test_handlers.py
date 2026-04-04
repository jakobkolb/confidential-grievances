from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers import handle_grievance, handle_escalate

MEDIATOR_CHAT_ID = -1001
SECRET_SALT = "test-salt"

TP_EMAIL_CFG = {
    "recipient": "tp@example.org",
    "from_addr": "bot@example.org",
    "password":  "pw",
    "smtp_host": "smtp.example.org",
    "smtp_port": 465,
    "imap_host": "imap.example.org",
    "imap_port": 993,
}


@pytest.fixture
def bot_data():
    return {
        "mediator_chat_id": MEDIATOR_CHAT_ID,
        "tp_email_cfg":     TP_EMAIL_CFG,
        "secret_salt":      SECRET_SALT,
    }


@pytest.fixture
def make_update():
    """Factory fixture that creates a minimal mock Update with user and message."""
    def _make(user_id=123, username="testuser", text="hello", chat_id=999):
        update = MagicMock()
        update.effective_user.id = user_id
        update.effective_user.username = username
        update.effective_message.text = text
        update.effective_message.chat_id = chat_id
        update.effective_message.reply_text = AsyncMock()
        return update
    return _make


@pytest.fixture
def context(bot_data):
    ctx = MagicMock()
    ctx.bot_data = bot_data
    ctx.bot.send_message = AsyncMock()
    return ctx


@pytest.fixture
def mock_send_tp_email():
    with patch("src.bot.handlers.send_tp_email", new_callable=AsyncMock) as m:
        yield m


# --- handle_grievance ---


@pytest.mark.asyncio
async def test_grievance_sends_to_mediator_group(make_update, context, mock_send_tp_email):
    update = make_update(username="alice", text="My complaint")

    await handle_grievance(update, context)

    calls = context.bot.send_message.call_args_list
    mediator_call = calls[0]
    assert mediator_call.kwargs["chat_id"] == MEDIATOR_CHAT_ID
    assert "My complaint" in mediator_call.kwargs["text"]
    assert "alice" not in mediator_call.kwargs["text"]


@pytest.mark.asyncio
async def test_grievance_sends_to_tp_email(make_update, context, mock_send_tp_email):
    update = make_update(user_id=42, username="bob", text="My complaint")

    await handle_grievance(update, context)

    mock_send_tp_email.assert_awaited_once()
    _, subject, body = mock_send_tp_email.call_args[0]
    assert "@bob" in body
    assert "42" in body
    assert "My complaint" not in body


@pytest.mark.asyncio
async def test_grievance_hash_links_both_messages(make_update, context, mock_send_tp_email):
    update = make_update(text="linked complaint")

    await handle_grievance(update, context)

    mediator_text = context.bot.send_message.call_args_list[0].kwargs["text"]
    _, _subject, tp_body = mock_send_tp_email.call_args[0]

    for line in mediator_text.splitlines():
        if line.startswith("Hash: "):
            mediator_hash = line.split("Hash: ")[1]
            break

    assert mediator_hash in tp_body


@pytest.mark.asyncio
async def test_grievance_confirms_receipt_to_pg(make_update, context, mock_send_tp_email):
    update = make_update(text="something")

    await handle_grievance(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(
        "Dein Kummer ist eingegangen."
    )


@pytest.mark.asyncio
async def test_grievance_falls_back_to_user_id_when_no_username(make_update, context, mock_send_tp_email):
    update = make_update(user_id=99, username=None, text="anon complaint")

    await handle_grievance(update, context)

    _, _subject, tp_body = mock_send_tp_email.call_args[0]
    assert "id:99" in tp_body


@pytest.mark.asyncio
async def test_grievance_ignores_missing_user(context, mock_send_tp_email):
    update = MagicMock()
    update.effective_user = None
    update.effective_message.text = "text"

    await handle_grievance(update, context)
    context.bot.send_message.assert_not_awaited()
    mock_send_tp_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_grievance_ignores_missing_message(context, mock_send_tp_email):
    update = MagicMock()
    update.effective_message = None
    update.effective_user.id = 1

    await handle_grievance(update, context)
    context.bot.send_message.assert_not_awaited()
    mock_send_tp_email.assert_not_awaited()


# --- handle_escalate ---


@pytest.mark.asyncio
async def test_escalate_forwards_hash_to_tp_email(context, mock_send_tp_email):
    update = MagicMock()
    update.effective_message.chat_id = MEDIATOR_CHAT_ID
    update.effective_message.reply_text = AsyncMock()
    context.args = ["abc123hash"]

    await handle_escalate(update, context)

    mock_send_tp_email.assert_awaited_once()
    _, subject, body = mock_send_tp_email.call_args[0]
    assert "abc123hash" in body
    assert "abc123hash" in subject


@pytest.mark.asyncio
async def test_escalate_confirms_to_mediator(context, mock_send_tp_email):
    update = MagicMock()
    update.effective_message.chat_id = MEDIATOR_CHAT_ID
    update.effective_message.reply_text = AsyncMock()
    context.args = ["abc123hash"]

    await handle_escalate(update, context)

    update.effective_message.reply_text.assert_awaited_once()
    reply_text = update.effective_message.reply_text.call_args[0][0]
    assert "abc123hash" in reply_text


@pytest.mark.asyncio
async def test_escalate_rejects_missing_hash(context, mock_send_tp_email):
    update = MagicMock()
    update.effective_message.chat_id = MEDIATOR_CHAT_ID
    update.effective_message.reply_text = AsyncMock()
    context.args = []

    await handle_escalate(update, context)

    update.effective_message.reply_text.assert_awaited_once_with("Verwendung: /escalate <Hash>")
    mock_send_tp_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_escalate_ignored_outside_mediator_group(context, mock_send_tp_email):
    update = MagicMock()
    update.effective_message.chat_id = 9999  # not the mediator group
    update.effective_message.reply_text = AsyncMock()
    context.args = ["somehash"]

    await handle_escalate(update, context)

    context.bot.send_message.assert_not_awaited()
    mock_send_tp_email.assert_not_awaited()
    update.effective_message.reply_text.assert_not_awaited()
