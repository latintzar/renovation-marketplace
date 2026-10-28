"""Unit tests for ``core.phone``."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.phone import (
    PhoneNormalizer,
    dedup_by_phone,
    extract_from_html,
    is_valid_spanish,
    normalize,
    to_digits,
    to_e164,
)


class TestToDigits:
    def test_plain_digits(self) -> None:
        assert to_digits("612345678") == "612345678"

    def test_strip_non_digits(self) -> None:
        assert to_digits("+34 (612) 345-678") == "34612345678"

    def test_empty_string(self) -> None:
        assert to_digits("") == ""

    def test_none_like(self) -> None:
        assert to_digits("") == ""

    def test_no_digits(self) -> None:
        assert to_digits("+()-") == ""


class TestNormalize:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("+34 612 345 678", "612345678"),
            ("0034-912-345-678", "912345678"),
            ("34 612.345.678", "612345678"),
            ("612345678", "612345678"),
            ("  612  345  678  ", "612345678"),
            ("(612) 345-678", "612345678"),
        ],
    )
    def test_spanish_strips_prefix(self, raw: str, expected: str) -> None:
        assert normalize(raw) == expected

    def test_non_spanish_prefix_preserved(self) -> None:
        # UK number starting with 4 — prefix regex requires 6/7/8/9 next.
        assert normalize("00000000000") == "00000000000"

    def test_empty_string(self) -> None:
        assert normalize("") == ""

    def test_prefix_not_stripped_if_wrong_first_digit(self) -> None:
        # '34123456789' — '1' isn't in 6/7/8/9 so the '34' stays.
        assert normalize("34123456789") == "34123456789"

    def test_idempotent(self) -> None:
        once = normalize("+34 612 345 678")
        twice = normalize(once)
        assert once == twice


class TestExtractFromHtml:
    def test_single_tel_link(self) -> None:
        html = '<a href="tel:+34612345678">call</a>'
        assert extract_from_html(html) == ["612345678"]

    def test_multiple_tel_links(self) -> None:
        html = """
        <a href="tel:+34612345678">a</a>
        <a href='tel:0034912345678'>b</a>
        """
        assert extract_from_html(html) == ["612345678", "912345678"]

    def test_no_tel_links(self) -> None:
        assert extract_from_html("<a href='mailto:x@y'>x</a>") == []

    def test_empty_html(self) -> None:
        assert extract_from_html("") == []

    def test_double_quotes_and_single_quotes(self) -> None:
        html = """<a href="tel:+34612345678">x</a><a href='tel:+34912345678'>y</a>"""
        assert extract_from_html(html) == ["612345678", "912345678"]


class TestIsValidSpanish:
    @pytest.mark.parametrize("phone", ["612345678", "712345678", "812345678", "912345678"])
    def test_valid_spanish_numbers(self, phone: str) -> None:
        assert is_valid_spanish(phone)

    def test_accepts_raw_with_prefix(self) -> None:
        assert is_valid_spanish("+34 612 345 678")

    def test_rejects_too_short(self) -> None:
        assert not is_valid_spanish("12345")

    def test_rejects_wrong_leading_digit(self) -> None:
        assert not is_valid_spanish("512345678")  # starts with 5

    def test_rejects_empty(self) -> None:
        assert not is_valid_spanish("")

    def test_rejects_uk_number(self) -> None:
        assert not is_valid_spanish("00000000000")


class TestToE164:
    def test_bare_spanish_mobile(self) -> None:
        assert to_e164("612345678") == "+34612345678"

    def test_already_e164(self) -> None:
        assert to_e164("+34612345678") == "+34612345678"

    def test_spanish_spaces(self) -> None:
        assert to_e164("612 345 678") == "+34612345678"

    def test_uk_number(self) -> None:
        assert to_e164("00000000000") == "00000000000"

    def test_empty_string(self) -> None:
        assert to_e164("") == ""

    def test_reject_non_spanish_when_required(self) -> None:
        assert to_e164("00000000000", require_region="ES") == ""

    def test_allow_spanish_when_required(self) -> None:
        assert to_e164("612345678", require_region="ES") == "+34612345678"

    def test_invalid_number(self) -> None:
        assert to_e164("abc") == ""

    def test_default_region_uk(self) -> None:
        # Without country prefix + default_region=GB
        assert to_e164("07578244644", default_region="GB") == "00000000000"


@dataclass
class _Person:
    phone: str


class TestDedupByPhone:
    def test_dict_dedup_basic(self) -> None:
        items = [
            {"phone": "+34612345678"},
            {"phone": "612 345 678"},
            {"phone": "699999999"},
        ]
        assert dedup_by_phone(items) == [
            {"phone": "+34612345678"},
            {"phone": "699999999"},
        ]

    def test_preserves_order(self) -> None:
        items = [{"phone": "699999999"}, {"phone": "+34612345678"}, {"phone": "612345678"}]
        assert dedup_by_phone(items) == [
            {"phone": "699999999"},
            {"phone": "+34612345678"},
        ]

    def test_empty_phones_are_all_kept(self) -> None:
        items = [{"phone": ""}, {"phone": ""}, {"phone": None}]
        # None gets coerced via ``str(item.get(key) or "")`` to empty.
        assert len(dedup_by_phone(items)) == 3

    def test_custom_key(self) -> None:
        items = [
            {"mobile": "612345678"},
            {"mobile": "+34612345678"},
        ]
        assert len(dedup_by_phone(items, key="mobile")) == 1

    def test_attribute_based(self) -> None:
        items = [_Person(phone="612345678"), _Person(phone="+34612345678")]
        assert len(dedup_by_phone(items)) == 1

    def test_mixed_valid_and_empty(self) -> None:
        items = [
            {"phone": "612345678"},
            {"phone": ""},  # kept (unkeyable)
            {"phone": "+34612345678"},  # dup of first
            {"phone": "699999999"},
        ]
        result = dedup_by_phone(items)
        # empty + 2 uniques = 3
        assert len(result) == 3


class TestPhoneNormalizerProtocol:
    def test_runtime_checkable(self) -> None:
        """Fake impls should satisfy the Protocol via structural typing."""

        class Fake:
            def normalize(self, raw: str) -> str:
                return raw

            def to_e164(self, raw: str) -> str:
                return raw

            def is_valid_spanish(self, phone: str) -> bool:
                return True

        assert isinstance(Fake(), PhoneNormalizer)

    def test_missing_method_fails(self) -> None:
        class Incomplete:
            def normalize(self, raw: str) -> str:
                return raw

        assert not isinstance(Incomplete(), PhoneNormalizer)
