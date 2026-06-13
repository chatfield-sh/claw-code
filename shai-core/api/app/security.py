"""Security primitives: signed OAuth state + token encryption at rest.

Both derive from ``settings.shai_secret_key``. Set a strong value per
environment — the default is intentionally obvious so it fails loudly in review.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time

from cryptography.fernet import Fernet, InvalidToken

from .config import settings

log = logging.getLogger("shai.security")


def _secret() -> bytes:
    return settings.shai_secret_key.encode()


# ---- Signed OAuth state (CSRF protection) ---------------------------------
def sign_state(payload: dict | None = None, ttl_seconds: int = 600) -> str:
    """Return a tamper-evident state string carrying an expiry."""
    body = {**(payload or {}), "exp": int(time.time()) + ttl_seconds}
    raw = base64.urlsafe_b64encode(json.dumps(body).encode()).decode()
    sig = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def verify_state(state: str) -> dict | None:
    """Return the payload if the signature is valid and unexpired, else None."""
    try:
        raw, sig = state.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        body = json.loads(base64.urlsafe_b64decode(raw))
    except (ValueError, json.JSONDecodeError):
        return None
    if float(body.get("exp", 0)) < time.time():
        return None
    return body


# ---- Token encryption at rest ---------------------------------------------
def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(_secret()).digest())
    return Fernet(key)


def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str | None) -> str | None:
    """Decrypt, tolerating legacy plaintext rows so existing data keeps working."""
    if token is None:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return token  # not encrypted (legacy) — return as-is
