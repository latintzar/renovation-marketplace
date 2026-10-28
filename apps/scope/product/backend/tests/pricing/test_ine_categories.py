"""Tests for :mod:`pricing.ine_categories`."""
from __future__ import annotations

from pricing import ine_category_for_query
from pricing.ine_categories import ine_category_for_cype_code


class TestIneCategoryForCypeCode:
    """``ine_category_for_cype_code`` takes a CYPE **material** code
    (``mt19``, ``mt37``...), NOT a CYPE item code like ``IFM006``.
    """

    def test_mt37_resolves_to_plasticos(self) -> None:
        assert ine_category_for_cype_code("mt37010") == "plasticos"

    def test_mt37b_longer_prefix_wins(self) -> None:
        """``mt37b`` is longer than ``mt37`` so wins prefix race → cobre."""

        assert ine_category_for_cype_code("mt37b005") == "cobre"

    def test_mt19_resolves_to_ceramica(self) -> None:
        assert ine_category_for_cype_code("mt19001") == "ceramica"

    def test_mt22_resolves_to_madera(self) -> None:
        assert ine_category_for_cype_code("mt22007") == "madera"

    def test_unknown_returns_none(self) -> None:
        assert ine_category_for_cype_code("zzzz999") is None

    def test_empty_returns_none(self) -> None:
        assert ine_category_for_cype_code("") is None

    def test_case_insensitive(self) -> None:
        assert ine_category_for_cype_code("MT37010") == "plasticos"


class TestIneCategoryForQuery:
    def test_azulejo_resolves_to_ceramica(self) -> None:
        assert ine_category_for_query("colocar azulejo") == "ceramica"

    def test_fontaneria_resolves_to_plasticos(self) -> None:
        assert ine_category_for_query("cambio de fontanería") == "plasticos"

    def test_tubo_resolves_to_plasticos(self) -> None:
        assert ine_category_for_query("cambio de tubo") == "plasticos"

    def test_madera_resolves(self) -> None:
        assert ine_category_for_query("puerta de madera") == "madera"

    def test_cemento_resolves(self) -> None:
        assert ine_category_for_query("cemento para cimentación") == "cemento"

    def test_unknown_returns_none(self) -> None:
        assert ine_category_for_query("xzqnonsense") is None

    def test_empty_returns_none(self) -> None:
        assert ine_category_for_query("") is None

    def test_case_insensitive(self) -> None:
        assert ine_category_for_query("Azulejo") == "ceramica"
        assert ine_category_for_query("AZULEJO") == "ceramica"
