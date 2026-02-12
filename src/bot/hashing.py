import hashlib


def compute_hash(user_id: int, message_body: str, timestamp: str, salt: str) -> str:
    """Compute SHA-256 hash per spec: user_id + message_body + timestamp + salt."""
    raw = f"{user_id}{message_body}{timestamp}{salt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
