import asyncio
import imaplib
import logging
import smtplib
import time
from email.message import EmailMessage

logger = logging.getLogger(__name__)

# Common Sent-folder names across providers.
# _find_sent_folder tries RFC 6154 \Sent attribute first (Gmail, Dovecot,
# Fastmail), then probes these names in order.
_SENT_FOLDER_CANDIDATES = [
    "Sent",
    "Sent Items",
    "Sent Messages",
    "INBOX.Sent",
    "[Gmail]/Sent Mail",
]


async def send_tp_email(bot_data: dict, subject: str, body: str) -> None:
    """Send an email to the Trusted Party and delete it from Sent mail."""
    cfg = bot_data["tp_email_cfg"]
    await asyncio.to_thread(_send_and_purge, cfg, subject, body)


# ---------------------------------------------------------------------------
# Synchronous internals (run inside asyncio.to_thread)
# ---------------------------------------------------------------------------

def _send_and_purge(cfg: dict, subject: str, body: str) -> None:
    msg = _build_message(cfg, subject, body)
    _smtp_send(cfg, msg)
    time.sleep(1)  # allow the server to index the sent message before IMAP search
    _imap_delete_sent(cfg, subject)


def _build_message(cfg: dict, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = cfg["from_addr"]
    msg["To"] = cfg["recipient"]
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def _smtp_send(cfg: dict, msg: EmailMessage) -> None:
    # Default assumes port 465 with implicit TLS (SMTP_SSL).
    # For port 587 with STARTTLS: replace SMTP_SSL with SMTP and call
    # smtp.starttls() before smtp.login().
    with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"]) as smtp:
        smtp.login(cfg["from_addr"], cfg["password"])
        smtp.send_message(msg)
    logger.info("TP email sent — subject=%r to=%r", msg["Subject"], msg["To"])


def _find_sent_folder(imap: imaplib.IMAP4_SSL) -> str | None:
    """Return the Sent folder name, or None if not found.

    Strategy:
    1. LIST to find a folder advertising the \\Sent special-use attribute
       (RFC 6154 — supported by Gmail, Dovecot, Fastmail).
    2. Fall back to probing _SENT_FOLDER_CANDIDATES with SELECT.
    """
    # Step 1: RFC 6154 special-use attribute
    try:
        status, lines = imap.list('""', "*")
        if status == "OK":
            for line in lines:
                decoded = line.decode() if isinstance(line, bytes) else line
                if r"\Sent" in decoded:
                    # Format: (\HasNoChildren \Sent) "/" "Folder Name"
                    parts = decoded.rsplit(None, 1)
                    return parts[-1].strip('"')
    except Exception:
        pass

    # Step 2: probe candidates
    for candidate in _SENT_FOLDER_CANDIDATES:
        try:
            status, _ = imap.select(f'"{candidate}"', readonly=True)
            if status == "OK":
                imap.close()
                return candidate
        except Exception:
            continue

    return None


def _imap_delete_sent(cfg: dict, subject: str) -> None:
    with imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"]) as imap:
        imap.login(cfg["from_addr"], cfg["password"])

        folder = _find_sent_folder(imap)
        if folder is None:
            logger.error(
                "Could not locate Sent folder on %s — email NOT deleted from Sent.",
                cfg["imap_host"],
            )
            return

        imap.select(f'"{folder}"')
        status, data = imap.search(None, f'SUBJECT "{subject}"')
        if status != "OK" or not data[0]:
            logger.warning(
                "Sent-folder search found no message with subject %r — skipping delete.",
                subject,
            )
            return

        for seq_num in data[0].split():
            imap.store(seq_num, "+FLAGS", r"\Deleted")
        imap.expunge()
        logger.info("Deleted %d message(s) from Sent folder.", len(data[0].split()))
