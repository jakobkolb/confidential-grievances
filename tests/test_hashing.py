from src.bot.hashing import compute_hash


def test_compute_hash_is_deterministic():
    h1 = compute_hash(123, "hello", "2025-01-01T00:00:00", "salt")
    h2 = compute_hash(123, "hello", "2025-01-01T00:00:00", "salt")
    assert h1 == h2


def test_compute_hash_is_hex_sha256():
    h = compute_hash(1, "msg", "ts", "s")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_hash_differs_with_different_input():
    h1 = compute_hash(1, "msg", "ts", "salt")
    h2 = compute_hash(2, "msg", "ts", "salt")
    assert h1 != h2


def test_compute_hash_differs_with_different_salt():
    h1 = compute_hash(1, "msg", "ts", "salt_a")
    h2 = compute_hash(1, "msg", "ts", "salt_b")
    assert h1 != h2
