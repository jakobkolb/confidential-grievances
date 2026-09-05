
# confidential-grievances
A Telegram bot to enable confidential handling of grievances in an organization.

# Grievance Mediation System — Technical Specification

Minimal architecture enabling pseudonymous grievance submission with controlled identity escrow and escalation. The Mediator communicates via a Telegram group; the Trusted Party receives notifications by email.

---

## Overview

A Telegram bot receives grievances via DM and routes them to two separate parties:

- **Mediator Group** — a Telegram group that receives the grievance text + a reference hash
- **Trusted Party (TP)** — an email inbox that receives the reference hash + the sender's Telegram identity

No external database is used. The Mediator group's chat history and the TP's email inbox are the records.

### Core Properties

- Pseudonymous submission via bot DM
- Identity escrow via TP email
- Hash‑based escalation reference
- Data minimization: each party sees only what it needs
- Sent emails are deleted from the bot's Sent folder immediately after delivery (privacy)
- Zero infrastructure beyond the bot process itself

---

# Roles

## 1) Person with Grievances (PG)

Individual submitting a grievance.

- Sends messages to the bot via private DM
- May self‑identify voluntarily in the message body
- May respond to contact requests relayed through the TP

| Data | Visible to PG |
|------|---------------|
| Own message | Yes |
| Routing metadata | No |
| Where data is sent | No |

---

## 2) Mediator Group

A Telegram group whose members review grievances and facilitate resolution.

- Receives: message body, message hash, timestamp
- Does **not** receive the sender's Telegram identity
- Can request escalation via the bot command `/escalate <hash>`

| Data | Visible |
|------|---------|
| Message body | Yes |
| Message hash | Yes |
| Telegram identity of PG | No |

---

## 3) Bot Steward

The person responsible for operating and maintaining the bot.

- Deploys the bot and keeps it running (monitors the systemd service)
- Receives error notifications directly via Telegram when something goes wrong
- Rotates credentials (bot token, email password, secret salt) when needed
- Implements improvements and applies updates
- Has access to the bot host, the `.env` configuration, and the service logs

| Access | Details |
|--------|---------|
| Bot host & config | Full access (required for operation) |
| Grievance content | No — logs contain only hashes, never message bodies or identities |
| Mediator group | No (unless also a Mediator member — should be avoided) |
| TP inbox | No (unless also a TP member — should be avoided) |

The steward's access to the host means they could in principle read environment variables or intercept traffic. This is an accepted operational trust boundary: the steward must be a trusted individual, and credential rotation limits the blast radius of any compromise.

---

## 4) Trusted Party (TP)


An email inbox acting as identity escrow.

- Receives an email per grievance with: message hash, sender's Telegram user ID / handle, timestamp
- Does **not** receive the message body
- Upon escalation request, contacts the PG to facilitate voluntary identification
- The bot deletes each email from its own Sent folder ~1 second after sending

| Data | Visible |
|------|---------|
| Message hash | Yes |
| Telegram identity of PG | Yes |
| Message body | No |

---

# Hashing Specification

**Algorithm:** SHA‑256

**Input:**

```
hash = SHA256(
  telegram_user_id +
  message_body +
  timestamp +
  bot_secret_salt
)
```

**Purpose:**

- Uniquely reference a grievance across both parties
- Prevent spoofing
- Enable escalation without identity disclosure

---

# Processes

## 1) Grievance Submission

1. PG sends a message to the bot via private DM
2. Bot captures: message body, Telegram user ID, timestamp
3. Bot computes the hash
4. Bot posts to **Mediator Group**:
   - Message body
   - Hash
   - Timestamp
5. Bot sends email to **TP inbox**:
   - Hash
   - Telegram user ID / handle
   - Timestamp
6. Bot deletes the email from its own Sent folder after ~1 second
7. Bot confirms receipt to PG (no details leaked)

## 2) Escalation

1. Mediator group member identifies a grievance that requires contact with the PG
2. Mediator uses the bot command: `/escalate <hash>`
3. Bot sends an escalation email to the TP inbox with the hash
4. TP member looks up the hash in their inbox to find the corresponding identity
5. TP contacts PG via Telegram DM
6. PG may voluntarily reach out to the Mediator

---

# Security & Privacy

## Data Separation

| Party | Sees | Does NOT see |
|-------|------|--------------|
| Mediator group | Message body, hash | PG identity |
| Trusted Party (email) | PG identity, hash | Message body |

No single party has both identity and message content.

## Sent-mail Scrubbing

After each email to the TP, the bot waits 1 second then connects via IMAP and deletes the message from its Sent folder. This ensures no persistent record of sent emails exists on the bot's mail account. If the Sent folder cannot be located or the message is not found (e.g. slow server indexing), an error is logged but the grievance submission is not interrupted.

## Access Control

- Bot must be a member of the Mediator group with permission to post
- Bot email account credentials are stored as environment variables on the bot host
- Group membership is managed by the respective group admins
- Bot secret salt is stored as an environment variable on the bot host

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Someone in both Mediator group and TP inbox | Organizational policy: no overlapping access |
| Bot host compromise | Rotate bot token, email password + salt; bot holds no persistent data |
| False submissions | Rate limiting per Telegram user ID |
| Chat history deletion | Telegram group settings: restrict message deletion |
| Email not scrubbed from Sent | Error is logged; operator should monitor logs |

---

# Deployment Architecture

```
PG (Telegram DM)
       │
       ▼
  Bot Process
   ├── compute hash
   ├──► Mediator Group (Telegram)   body + hash + timestamp
   └──► TP Inbox (email)            identity + hash + timestamp
              └── IMAP delete from Sent (~1s later)
```

The bot is a single stateless process. It needs:

- A Telegram bot token
- The chat ID of the Mediator group
- A dedicated email account (SMTP + IMAP access)
- The TP recipient email address
- A secret salt

---

# Tech Stack

- Python with `python-telegram-bot`
- Stdlib `smtplib` / `imaplib` for email (no extra dependencies)
- Single deployment target (any host that can run a Python process)
- No database

---

# MVP Scope

Included:

- Telegram bot accepting DMs from PGs
- Welcome message on `/start`
- Hash computation and dual routing to Mediator group (Telegram) and TP (email)
- `/escalate <hash>` bot command for the Mediator group
- Sent-mail scrubbing via IMAP
- Receipt confirmation to PG

Excluded:

- Anonymous reply channels (PG cannot receive messages back through the bot)
- Analytics / reporting
- Case management beyond chat history / email inbox

---

# Acceptance Criteria

- PG receives a welcome message when starting the bot
- PG can submit a grievance via bot DM
- Grievance body appears in Mediator group without PG identity
- PG identity is emailed to the TP inbox without the grievance body
- Email is deleted from the bot's Sent folder after delivery
- Hash links the Mediator message and the TP email
- `/escalate <hash>` triggers a notification email to the TP inbox
- No external database is required

---

# Setup

## Prerequisites

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather) and note the **bot token**
2. Create a Telegram group for the Mediator and note its **chat ID**
3. Add the bot to the Mediator group with permission to post
4. Create a dedicated email account for the bot (SMTP + IMAP access required)
5. Note the TP recipient email address
6. Choose a **secret salt** (any random string)

## Install

```bash
git clone <repo-url> && cd confidential-grievances
./scripts/setup.sh
```

This installs [uv](https://docs.astral.sh/uv/) and all project dependencies.

## Configure

```bash
cp .env.example .env
```

Edit `.env` with your values:

```
BOT_TOKEN=123456:ABC-DEF...
MEDIATOR_CHAT_ID=-100123456789
BOT_SECRET_SALT=your-random-secret

TP_EMAIL_RECIPIENT=trustedparty@example.org
BOT_EMAIL_ADDRESS=grievance-bot@example.org
BOT_EMAIL_PASSWORD=your-email-password
SMTP_HOST=smtp.example.org
SMTP_PORT=465
IMAP_HOST=imap.example.org
IMAP_PORT=993
```

`SMTP_PORT=465` uses implicit TLS (`SMTP_SSL`). For STARTTLS on port 587, see the note in `src/bot/email_tp.py`.

`MEDIATOR_CHAT_ID` is the mediator group's chat ID. The `-100` prefix (as in the example above) only applies to **supergroups**/channels — a plain **basic group** has an unprefixed id like `-123456789`. Using the wrong form gives `telegram.error.BadRequest: Chat not found` when the bot tries to send there. To get the right value, add the bot to the group, then call `getChat` with the id you suspect, e.g.:

```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/getChat?chat_id=-123456789"
```

A successful response's `"type"` tells you whether it's `"group"` (no `-100` prefix) or `"supergroup"`/`"channel"` (needs it).

## Run

```bash
uv run python -m src.bot.app
```

## Run as a systemd service

To install the bot as a service that starts on boot and auto-restarts on failure:

```bash
./scripts/install-service.sh
```

Useful commands after installation:

```bash
sudo systemctl status grievance-bot    # check status
sudo journalctl -u grievance-bot -f    # follow logs
sudo systemctl restart grievance-bot   # restart after config changes
sudo systemctl stop grievance-bot      # stop
```

## Rotate Kummerkasten Gruppe

- Create new Kummerkasten Telegram Group
- Add Bot to Group. 
- Get Group ID from Telegram Web URL of Group
- Set Group ID in Bot .env
- Restart Bot Service
- Test if message to Bot is forwarded to new group
- Add new Kummerkasten Group Members to Group
- Promote one of them to Admin with full rights
- Transfer ownership of group to said admin
- Leave group.

## Development

```bash
uv run flake8 src/ tests/    # lint
uv run pytest tests/ -v      # test
```

---
