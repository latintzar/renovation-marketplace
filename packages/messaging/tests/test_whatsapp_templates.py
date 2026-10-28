"""WhatsApp template catalogue and routing helpers."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from messaging.whatsapp.templates import TEMPLATES, detect_language, get_template_name


class TestFrozenCatalogue:
    """Templates are read-only at runtime (guarded by MappingProxyType)."""

    def test_is_mapping_proxy(self) -> None:
        assert isinstance(TEMPLATES, MappingProxyType)

    def test_inner_dicts_are_also_frozen(self) -> None:
        for lang_dict in TEMPLATES.values():
            assert isinstance(lang_dict, MappingProxyType)

    def test_outer_dict_rejects_mutation(self) -> None:
        with pytest.raises(TypeError):
            TEMPLATES["new_purpose"] = {}  # type: ignore[index]

    def test_inner_dict_rejects_mutation(self) -> None:
        with pytest.raises(TypeError):
            TEMPLATES["outreach"]["xx"] = "bad"  # type: ignore[index]

    def test_covers_all_documented_purposes(self) -> None:
        expected = {
            "outreach",
            "followup_1",
            "followup_final",
            "referral_pro",
            "referral_ho",
            "onboarding",
            "handoff",
            "general",
            "milestone",
        }
        assert set(TEMPLATES.keys()) == expected

    def test_every_purpose_has_both_languages(self) -> None:
        for purpose, langs in TEMPLATES.items():
            assert "en_US" in langs, f"{purpose} missing en_US"
            assert "es" in langs, f"{purpose} missing es"


class TestDetectLanguage:
    def test_spanish_prefix(self) -> None:
        assert detect_language("34600000000") == "es"

    def test_non_spanish_defaults_to_english(self) -> None:
        assert detect_language("14155550100") == "en_US"
        assert detect_language("447700900123") == "en_US"

    def test_empty_phone(self) -> None:
        assert detect_language("") == "en_US"


class TestGetTemplateName:
    def test_exact_match_spanish(self) -> None:
        assert get_template_name("outreach", "es") == "contractor_intro_v2"

    def test_exact_match_english(self) -> None:
        assert get_template_name("outreach", "en_US") == "contractor_intro_v1"

    def test_unknown_language_falls_back_to_english(self) -> None:
        assert get_template_name("outreach", "zz") == "contractor_intro_v1"

    def test_unknown_purpose_returns_empty(self) -> None:
        assert get_template_name("nonexistent", "es") == ""

    def test_followup_routing(self) -> None:
        assert get_template_name("followup_1", "es") == "contractor_followup1_v2"
        assert get_template_name("followup_final", "en_US") == "contractor_followup_final"
