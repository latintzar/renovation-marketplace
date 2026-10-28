"""Shared pytest fixtures for the @scope/fulltext test suite."""
from __future__ import annotations

from pathlib import Path

import pytest

from fulltext import DomainIndex


@pytest.fixture
def tmp_index(tmp_path: Path) -> DomainIndex:
    """Fresh on-disk DomainIndex backed by a per-test temp SQLite file."""

    db_path = str(tmp_path / "test.db")
    idx = DomainIndex("test", db_path=db_path)
    idx.drop()
    yield idx
    idx.close()


@pytest.fixture
def populated_index(tmp_index: DomainIndex) -> DomainIndex:
    """Index with three heterogeneous documents covering the main
    retrieval flows (FTS match, synonym expansion, city boost)."""

    tmp_index.add(
        "hab-fontanero",
        slug="fontanero",
        title="Fontanero en Madrid",
        body="Instalación de fontanería en baño y cocina",
        meta={
            "source": "habitissimo",
            "city_prices": [
                {"city": "Madrid", "prices": ["150€/hora"]},
                {"city": "Barcelona", "prices": ["140€/hora"]},
            ],
        },
    )
    tmp_index.add(
        "hab-electricista",
        slug="electricista",
        title="Electricista reforma eléctrica",
        body="Cableado e instalación eléctrica vivienda",
        meta={"source": "habitissimo", "city_prices": [{"city": "Valencia"}]},
    )
    tmp_index.add(
        "cs-pintura",
        slug="pintura-interior",
        title="Pintura interior vivienda",
        body="Pintar paredes de casa con pintura plástica",
        meta={"source": "cronoshare", "city_prices": []},
    )
    tmp_index.add_city_price(
        "hab-fontanero",
        city="Madrid",
        prices=["150€/hora"],
        source="habitissimo",
        title="Fontanero en Madrid",
        slug="fontanero",
    )
    tmp_index.add_city_price(
        "hab-fontanero",
        city="Barcelona",
        prices=["140€/hora"],
        source="habitissimo",
        title="Fontanero en Madrid",
        slug="fontanero",
    )
    tmp_index.commit()
    return tmp_index
