
# confidential-grievances
A Telegram bot to enable confidential handling of grievances in an organization.

# Grievance Mediation System — Technical Specification

Minimal architecture enabling pseudonymous grievance submission with controlled identity escrow and escalation, using Telegram groups as the sole data store.

---

## Overview

A Telegram bot receives grievances via DM and routes them to two Telegram groups:

- **Mediator Group** — receives the grievance text + a reference hash
- **Trusted Party (TP) Group** — receives the reference hash + the sender's Telegram identity

No external database is used. The chat history in each group is the record.

### Core Properties

- Pseudonymous submission via bot DM
- Identity escrow via TP group
- Hash‑based escalation reference
- Data minimization: each group sees only what it needs
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
| Which groups receive data | No |

---

## 2) Mediator Group

A Telegram group whose members review grievances and facilitate resolution.

- Receives: message body, message hash, timestamp
- Does **not** receive the sender's Telegram identity
- Can request escalation by forwarding the hash to the TP group (or via a bot command)

| Data | Visible |
|------|---------|
| Message body | Yes |
| Message hash | Yes |
| Telegram identity of PG | No |

---

## 3) Trusted Party (TP) Group

A Telegram group acting as identity escrow.

- Receives: message hash, sender's Telegram user ID / handle, timestamp
- Does **not** receive the message body
- Upon escalation request (hash from Mediator), contacts the PG to facilitate voluntary identification

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

- Uniquely reference a grievance across both groups
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
5. Bot posts to **TP Group**:
   - Hash
   - Telegram user ID / handle
   - Timestamp
6. Bot confirms receipt to PG (no details leaked)

## 2) Escalation

1. Mediator group member identifies a grievance that requires contact with the PG
2. Mediator posts the hash to the TP group (or uses a bot command: `/escalate <hash>`)
3. TP group member looks up the hash in their chat history to find the corresponding identity
4. TP contacts PG via Telegram DM
5. PG may voluntarily reach out to the Mediator

---

# Security & Privacy

## Data Separation

Enforced by Telegram group membership:

| Group | Sees | Does NOT see |
|-------|------|--------------|
| Mediator | Message body, hash | PG identity |
| TP | PG identity, hash | Message body |

No single group has both identity and message content.

## Access Control

- Bot must be a member of both groups with permission to post
- Group membership is managed by the respective group admins
- Bot secret salt is stored as an environment variable on the bot host

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Someone in both groups | Organizational policy: no overlapping membership |
| Bot host compromise | Rotate bot token + salt; bot holds no persistent data |
| False submissions | Rate limiting per Telegram user ID |
| Chat history deletion | Telegram group settings: restrict message deletion |

---

# Deployment Architecture

```
PG (Telegram DM)
       │
       ▼
  Bot Process
   ├── compute hash
   ├──► Mediator Group  (body + hash)
   └──► TP Group        (identity + hash)
```

The bot is a single stateless process. It needs:

- A Telegram bot token
- The chat IDs of the Mediator and TP groups
- A secret salt (environment variable)

---

# Tech Stack

- Python with `python-telegram-bot`
- Single deployment target (any host that can run a Python process)
- No database

---

# MVP Scope

Included:

- Telegram bot accepting DMs from PGs
- Hash computation and dual routing to Mediator / TP groups
- `/escalate <hash>` bot command for Mediator group
- Receipt confirmation to PG

Excluded:

- Anonymous reply channels (PG cannot receive messages back through the bot)
- Analytics / reporting
- Case management beyond chat history

---

# Acceptance Criteria

- PG can submit a grievance via bot DM
- Grievance body appears in Mediator group without PG identity
- PG identity appears in TP group without grievance body
- Hash links the two records
- `/escalate <hash>` triggers a notification in the TP group
- No external database is required

---

# Setup

## Prerequisites

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather) and note the **bot token**
2. Create two Telegram groups (Mediator and Trusted Party)
3. Add the bot to both groups and note their **chat IDs**
4. Choose a **secret salt** (any random string)

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
TP_CHAT_ID=-100987654321
BOT_SECRET_SALT=your-random-secret
```

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
sudo systemctl restart grievance-bot   # restart
sudo systemctl stop grievance-bot      # stop
```

## Development

```bash
uv run flake8 src/ tests/    # lint
uv run pytest tests/ -v      # test
```

---