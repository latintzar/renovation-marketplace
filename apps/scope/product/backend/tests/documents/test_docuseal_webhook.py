"""Unit tests for `documents.docuseal.webhook`."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from documents import DocusealWebhookEvent, parse_webhook_event, verify_docuseal_webhook


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestVerifyWebhook:
    def test_valid_signature(self) -> None:
        body = b'{"event_type":"submission.completed","data":{}}'
        secret = "whsec_test_abc"
        sig = _sign(body, secret)
        assert verify_docuseal_webhook(body=body, signature=sig, secret=secret)

    def test_invalid_signature(self) -> None:
        body = b'{"event_type":"submission.completed"}'
        assert not verify_docuseal_webhook(
            body=body, signature="deadbeef", secret="whsec_test_abc"
        )

    def test_empty_signature(self) -> None:
        assert not verify_docuseal_webhook(
            body=b"{}", signature="", secret="whsec_x"
        )

    def test_empty_secret(self) -> None:
        assert not verify_docuseal_webhook(
            body=b"{}", signature="abc", secret=""
        )

    def test_tampered_body(self) -> None:
        original = b'{"event":"a"}'
        tampered = b'{"event":"b"}'
        secret = "whsec"
        sig = _sign(original, secret)
        assert not verify_docuseal_webhook(
            body=tampered, signature=sig, secret=secret
        )


class TestParseWebhook:
    def test_parses_submission_completed(self) -> None:
        body = json.dumps(
            {
                "event_type": "submission.completed",
                "submission_id": "sub_123",
                "external_id": "q_abc:v1",
                "status": "completed",
                "occurred_at": "2026-04-18T10:00:00Z",
                "data": {"payload": "ignored"},
            }
        ).encode()
        event = parse_webhook_event(body)
        assert isinstance(event, DocusealWebhookEvent)
        assert event.event_type == "submission.completed"
        assert event.submission_id == "sub_123"
        assert event.external_id == "q_abc:v1"
        assert event.status == "completed"

    def test_tolerates_unknown_fields(self) -> None:
        body = json.dumps(
            {
                "event_type": "form.viewed",
                "submission_id": "s1",
                "external_id": "e1",
                "status": "viewed",
                "occurred_at": "2026-04-18T10:00:00Z",
                "data": {},
                "custom_field": "whatever",
            }
        ).encode()
        event = parse_webhook_event(body)
        assert event.event_type == "form.viewed"

    def test_handles_missing_event_type(self) -> None:
        body = json.dumps(
            {
                "submission_id": "s1",
                "external_id": "e1",
                "status": "",
                "occurred_at": "2026-04-18T10:00:00Z",
                "data": {},
            }
        ).encode()
        event = parse_webhook_event(body)
        assert event.event_type == ""

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(ValueError):
            parse_webhook_event(b"not json at all")
