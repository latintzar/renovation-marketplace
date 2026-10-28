"""Verification — pure NIF/CIF/NIE validator + type round-trips.

The network-touching functions (``check_vies``, ``check_rea``,
``search_review_signals``, ``search_fb_posts``) need external infra and
are covered via higher-layer integration tests. Here we pin the pure
math (``validate_nif``) and Pydantic model field-ordering invariant.
"""

from __future__ import annotations

import pytest

from messaging import Credential, ProfileResult, TrustSignals, validate_nif


class TestNifChecksum:
    """Canonical Spanish NIF/CIF/NIE examples — math only, no network."""

    def test_valid_nif_natural_person(self) -> None:
        # 12345678Z is the classic textbook-valid NIF.
        r = validate_nif("12345678Z")
        assert r["valid"] is True
        assert r["type"] == "nif"
        assert r["normalized"] == "12345678Z"

    def test_invalid_nif_wrong_letter(self) -> None:
        r = validate_nif("12345678A")
        assert r["valid"] is False
        assert r["type"] == "nif"

    def test_valid_nie(self) -> None:
        # X1234567L is the textbook-valid NIE.
        r = validate_nif("X1234567L")
        assert r["valid"] is True
        assert r["type"] == "nie"

    def test_invalid_too_short(self) -> None:
        r = validate_nif("1234")
        assert r["valid"] is False
        assert r["type"] == "unknown"

    def test_invalid_too_long(self) -> None:
        r = validate_nif("1234567890")
        assert r["valid"] is False

    def test_strips_whitespace_and_dashes(self) -> None:
        r = validate_nif(" 12345678-Z ")
        assert r["valid"] is True
        assert r["normalized"] == "12345678Z"

    def test_lowercase_normalized(self) -> None:
        r = validate_nif("12345678z")
        assert r["valid"] is True
        assert r["normalized"] == "12345678Z"

    def test_empty_rejected(self) -> None:
        assert validate_nif("")["valid"] is False
        assert validate_nif(None)["valid"] is False  # type: ignore[arg-type]


class TestCifChecksum:
    def test_valid_cif_letter_first(self) -> None:
        # A58818501 — valid Spanish CIF (Repsol reference).
        r = validate_nif("A58818501")
        assert r["type"] == "cif"
        assert r["valid"] is True

    def test_invalid_cif_bad_checksum(self) -> None:
        r = validate_nif("A58818502")
        assert r["type"] == "cif"
        assert r["valid"] is False


class TestTrustSignalsModel:
    def test_defaults_are_empty(self) -> None:
        ts = TrustSignals()
        assert ts.nif_valid is None
        assert ts.review_sources == []
        assert ts.fb_mention_count == 0
        assert ts.last_checked_at == ""

    def test_field_order_invariant(self) -> None:
        """Field order is serialisation-significant — pin it."""
        keys = list(TrustSignals.model_fields.keys())
        assert keys[:4] == [
            "nif_valid",
            "nif_value",
            "vies_valid",
            "vies_company_name",
        ]
        assert keys[-1] == "last_checked_at"

    def test_round_trip(self) -> None:
        ts = TrustSignals(nif_valid=True, trust_score=80)
        j = ts.model_dump()
        assert j["nif_valid"] is True
        assert j["trust_score"] == 80


class TestProfileResultModel:
    def test_minimum_valid_profile(self) -> None:
        p = ProfileResult(source="habitissimo", source_url="https://h/abc")
        assert p.source == "habitissimo"
        assert p.trust_signals is None
        assert p.reviews == []

    def test_attached_trust_signals(self) -> None:
        p = ProfileResult(
            source="houzz",
            source_url="https://x",
            trust_signals=TrustSignals(trust_score=75),
        )
        assert p.trust_signals.trust_score == 75

    def test_credential_list(self) -> None:
        p = ProfileResult(
            source="website",
            source_url="https://x",
            credentials=[
                Credential(type="nif", value="A58818501", verified=True),
            ],
        )
        assert len(p.credentials) == 1
        assert p.credentials[0].verified is True

    def test_field_order_invariant(self) -> None:
        """Regression guard: serialization order is load-bearing (DB rows)."""
        keys = list(ProfileResult.model_fields.keys())
        assert keys[0] == "source"
        assert keys[1] == "source_url"
        assert keys[-1] == "trust_signals"
