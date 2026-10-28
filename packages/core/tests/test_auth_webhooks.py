"""Tests for :func:`core.verify_webhook_signature`."""

from __future__ import annotations

import hashlib
import hmac

from core import verify_webhook_signature


def _sign(payload: bytes, secret: str, algo: str = "sha256") -> str:
    return hmac.new(
        secret.encode("utf-8"), payload, getattr(hashlib, algo)
    ).hexdigest()


def test_valid_signature() -> None:
    payload = b'{"event":"x"}'
    sig = _sign(payload, "secret")
    assert verify_webhook_signature(payload, sig, "secret") is True


def test_invalid_signature() -> None:
    payload = b'{"event":"x"}'
    assert verify_webhook_signature(payload, "bogus", "secret") is False


def test_missing_signature_returns_false() -> None:
    assert verify_webhook_signature(b"x", "", "secret") is False


def test_missing_secret_returns_false() -> None:
    assert verify_webhook_signature(b"x", "sig", "") is False


def test_sha1_algo() -> None:
    payload = b"hello"
    sig = _sign(payload, "key", algo="sha1")
    assert verify_webhook_signature(payload, sig, "key", algo="sha1") is True


def test_sha512_algo() -> None:
    payload = b"hello"
    sig = _sign(payload, "key", algo="sha512")
    assert verify_webhook_signature(payload, sig, "key", algo="sha512") is True


def test_prefix_is_stripped_before_compare() -> None:
    """GitHub-style ``sha256=...`` header support."""
    payload = b"body"
    core_sig = _sign(payload, "secret")
    header = f"sha256={core_sig}"
    assert (
        verify_webhook_signature(payload, header, "secret", prefix="sha256=")
        is True
    )


def test_prefix_mismatch_is_not_stripped() -> None:
    """If the prefix doesn't actually appear, no stripping happens."""
    payload = b"body"
    core_sig = _sign(payload, "secret")
    # Signature does not have the prefix; should still match (no strip).
    assert (
        verify_webhook_signature(payload, core_sig, "secret", prefix="xxx=")
        is True
    )


def test_payload_can_be_str() -> None:
    payload_str = '{"event":"x"}'
    payload_bytes = payload_str.encode("utf-8")
    sig = _sign(payload_bytes, "secret")
    assert verify_webhook_signature(payload_str, sig, "secret") is True


def test_constant_time_compare_rejects_partial_match() -> None:
    """Tampered signature with correct prefix still rejected."""
    payload = b"body"
    sig = _sign(payload, "secret")
    tampered = sig[:-1] + ("0" if sig[-1] != "0" else "1")
    assert verify_webhook_signature(payload, tampered, "secret") is False
