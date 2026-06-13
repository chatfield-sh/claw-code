"""OAuth state signing + token encryption."""

from __future__ import annotations

from app import security


def test_state_roundtrip():
    state = security.sign_state({"uid": "abc"})
    payload = security.verify_state(state)
    assert payload and payload["uid"] == "abc"


def test_state_rejects_tampering():
    state = security.sign_state({"uid": "abc"})
    raw, _sig = state.rsplit(".", 1)
    forged = f"{raw}.deadbeef"
    assert security.verify_state(forged) is None


def test_state_rejects_expired():
    state = security.sign_state({"uid": "abc"}, ttl_seconds=-1)
    assert security.verify_state(state) is None


def test_state_rejects_garbage():
    assert security.verify_state("not-a-state") is None
    assert security.verify_state("") is None


def test_encrypt_roundtrip():
    token = "ya29.secret-access-token"
    enc = security.encrypt(token)
    assert enc != token  # actually encrypted
    assert security.decrypt(enc) == token


def test_encrypt_handles_none():
    assert security.encrypt(None) is None
    assert security.decrypt(None) is None


def test_decrypt_tolerates_legacy_plaintext():
    # Rows written before encryption should still be readable.
    assert security.decrypt("plain-legacy-token") == "plain-legacy-token"
