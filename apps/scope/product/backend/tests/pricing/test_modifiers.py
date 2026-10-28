"""Tests for :mod:`pricing.modifiers`."""
from __future__ import annotations

import warnings

import pytest

from pricing import apply_modifiers, regional_multiplier
from pricing.modifiers import normalise_modifiers


class TestNormaliseModifiers:
    def test_none_returns_empty(self) -> None:
        assert normalise_modifiers(None) == []

    def test_list_preserves_valid(self) -> None:
        out = normalise_modifiers(["urgent", "peak_season"])
        assert out == ["urgent", "peak_season"]

    def test_unknown_kept_in_normalise(self) -> None:
        """``normalise_modifiers`` is shape-coercion only; unknown keys
        are filtered later by :func:`apply_modifiers`.
        """

        out = normalise_modifiers(["urgent", "bogus"])
        assert set(out) == {"urgent", "bogus"}

    def test_string_split_comma(self) -> None:
        out = normalise_modifiers("urgent,peak_season")
        assert set(out) == {"urgent", "peak_season"}

    def test_legacy_rural_deprecation_via_apply(self) -> None:
        """The legacy 'rural' modifier warns when routed through
        :func:`apply_modifiers` (not at normalise time)."""

        # Reset the one-shot warning latch so the test is independent
        from pricing import modifiers as mods

        mods._RURAL_WARNED = False

        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            adj, applied = apply_modifiers(1000.0, ["rural"])
        assert any(issubclass(w.category, DeprecationWarning) for w in rec)
        # 'rural' is NOT applied anymore — base passes through unchanged
        assert adj == 1000.0
        assert "rural" not in applied


class TestApplyModifiers:
    def test_no_modifiers(self) -> None:
        adj, applied = apply_modifiers(1000.0, None)
        assert adj == 1000.0
        assert applied == []

    def test_single_modifier_urgent(self) -> None:
        adj, applied = apply_modifiers(1000.0, ["urgent"])
        # MODIFIERS['urgent'] == 1.25 → 1250
        assert adj == 1250.0
        assert applied == ["urgent"]

    def test_combined_modifiers_multiply(self) -> None:
        # 1000 * 1.25 (urgent) * 1.15 (peak) = 1437.5
        adj, applied = apply_modifiers(1000.0, ["urgent", "peak_season"])
        assert adj == pytest.approx(1437.5, rel=0.001)
        assert set(applied) == {"urgent", "peak_season"}

    def test_unknown_modifier_ignored(self) -> None:
        adj, applied = apply_modifiers(1000.0, ["urgent", "unknown"])
        assert adj == 1250.0
        assert applied == ["urgent"]

    def test_zero_base_stays_zero(self) -> None:
        adj, applied = apply_modifiers(0.0, ["urgent"])
        assert adj == 0.0


class TestRegionalMultiplier:
    def test_madrid(self) -> None:
        assert regional_multiplier("Madrid") == 1.15

    def test_barcelona(self) -> None:
        assert regional_multiplier("Barcelona") == 1.12

    def test_none_returns_1(self) -> None:
        assert regional_multiplier(None) == 1.0
        assert regional_multiplier("") == 1.0

    def test_unknown_falls_back_low_tier(self) -> None:
        """Small town → the default rural-tier multiplier (< 1.0)."""

        assert regional_multiplier("Xxnowhereville") == 0.95

    def test_case_insensitive(self) -> None:
        assert regional_multiplier("madrid") == 1.15
        assert regional_multiplier("MADRID") == 1.15

    def test_accents_ignored(self) -> None:
        # Málaga → Malaga match
        assert regional_multiplier("Málaga") == regional_multiplier("Malaga")
