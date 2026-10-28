"""Shared pytest fixtures for the scraping test suite.

Deliberately narrow: no network, no Playwright, no scrapling. Each
test that needs those boundaries mocks them locally so suite runs are
deterministic and offline-safe (matches the pattern set by the ``llm``
and ``search`` packages).
"""
from __future__ import annotations

import pytest


@pytest.fixture
def simple_html() -> str:
    """Well-formed HTML fixture for lxml/bs4/text extraction tests."""

    return """<!doctype html>
<html>
<head>
  <title>Kitchen renovation quote</title>
  <link rel="stylesheet" href="./style.css">
</head>
<body>
  <h1>Cocina integral en Madrid</h1>
  <p>Contact: <a href="tel:+34 612 345 678">612 345 678</a></p>
  <img src="/a.jpg" srcset="/a.jpg 1x, /a@2x.jpg 2x, /a@3x.jpg 3x">
  <script>var x = 1;</script>
  <style>body{}</style>
</body>
</html>
"""


@pytest.fixture
def ig_profile_html() -> str:
    """Minimal IG profile HTML with embedded JSON fields the extractor keys on."""

    return '''<html><head><title>@garciaplomberia</title></head><body>
<script>window._data = {
"username": "garciaplomberia",
"full_name": "Garcia Plomberia Madrid",
"biography": "Fontaner\u00eda 24h \u2022 Madrid \u2022 Llama +34 612 345 678 o 910 200 300",
"external_url": "https://garcia-plomberia.es"
};</script>
</body></html>'''


@pytest.fixture
def cache_tmp(tmp_path):
    """Isolated cache dir for disk-cache tests."""

    d = tmp_path / "scraping-cache"
    d.mkdir()
    return d
