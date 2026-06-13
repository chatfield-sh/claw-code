"""Clerk session-token verification.

Verifies a Clerk-issued RS256 JWT against the instance's JWKS (the public keys
published at ``{issuer}/.well-known/jwks.json``). Keys are cached per issuer.
Returns the token claims on success, or ``None`` when verification is not
possible (no library, no key, invalid/expired token) so the caller can decide
how to degrade.
"""

from __future__ import annotations

import logging

import httpx

from .config import settings

try:
    import jwt
    from jwt import PyJWKClient
except ImportError:  # PyJWT optional until auth is wired
    jwt = None  # type: ignore[assignment]
    PyJWKClient = None  # type: ignore[assignment]

log = logging.getLogger("shai.auth")

# Cache one JWKS client per issuer (each fetches + caches signing keys itself).
_jwks_clients: dict[str, "PyJWKClient"] = {}


def _issuer_of(token: str) -> str | None:
    try:
        return jwt.decode(token, options={"verify_signature": False}).get("iss")
    except Exception:  # noqa: BLE001
        return None


def _client_for(issuer: str) -> "PyJWKClient | None":
    if issuer not in _jwks_clients:
        try:
            # Confirm the issuer is reachable before trusting it.
            httpx.get(f"{issuer}/.well-known/jwks.json", timeout=5).raise_for_status()
            _jwks_clients[issuer] = PyJWKClient(f"{issuer}/.well-known/jwks.json")
        except Exception as exc:  # noqa: BLE001
            log.warning("JWKS unavailable for issuer %s: %s", issuer, exc)
            return None
    return _jwks_clients[issuer]


def verify_clerk_token(token: str) -> dict | None:
    """Return verified claims (incl. ``sub``) or None.

    The expected issuer is PINNED to ``settings.clerk_issuer``: tokens with a
    different ``iss`` are rejected, and JWKS is fetched only from the pinned
    issuer — never from a value taken from the (untrusted) token. Without a
    configured issuer we refuse to verify (fail closed).
    """
    if jwt is None or PyJWKClient is None:
        log.debug("PyJWT not installed; cannot verify Clerk token")
        return None
    expected_issuer = settings.clerk_issuer.rstrip("/")
    if not expected_issuer:
        log.warning("CLERK_ISSUER not set; refusing to verify tokens")
        return None
    # The token's self-asserted issuer must match the pinned one before we
    # trust anything else about it (including which keys to verify against).
    if _issuer_of(token) != expected_issuer:
        return None
    client = _client_for(expected_issuer)
    if client is None:
        return None
    try:
        signing_key = client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token, signing_key, algorithms=["RS256"], issuer=expected_issuer,
            options={"require": ["exp", "iss", "sub"]},
        )
    except Exception as exc:  # noqa: BLE001 - any failure => unauthenticated
        log.info("Clerk token rejected: %s", exc)
        return None
