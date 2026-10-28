"""Tests for :mod:`llm.config`."""

from __future__ import annotations

import importlib
import os

import pytest


def test_module_constants_present():
    import llm.config as cfg

    assert isinstance(cfg.LITELLM_BASE_URL, str)
    assert isinstance(cfg.LITELLM_API_KEY, str)
    assert isinstance(cfg.LITELLM_PORT, int)


def test_base_url_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://proxy.example.com/")
    import llm.config as cfg

    importlib.reload(cfg)
    try:
        assert cfg.LITELLM_BASE_URL == "http://proxy.example.com"
        assert cfg.proxy_base_url() == "http://proxy.example.com"
    finally:
        monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
        importlib.reload(cfg)


def test_default_base_url_includes_port(monkeypatch):
    monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
    monkeypatch.setenv("LITELLM_PORT", "5555")
    import llm.config as cfg

    importlib.reload(cfg)
    try:
        assert cfg.LITELLM_BASE_URL == "http://localhost:5555"
    finally:
        monkeypatch.delenv("LITELLM_PORT", raising=False)
        importlib.reload(cfg)


def test_no_v1_suffix_invariant():
    """Per D12, the base URL must NOT include ``/v1`` — providers append it."""
    import llm.config as cfg

    assert not cfg.LITELLM_BASE_URL.endswith("/v1")
    assert not cfg.LITELLM_BASE_URL.endswith("/v1/")


def test_api_key_env_override(monkeypatch):
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test-override")
    import llm.config as cfg

    importlib.reload(cfg)
    try:
        assert cfg.LITELLM_API_KEY == "sk-test-override"
        assert cfg.proxy_api_key() == "sk-test-override"
    finally:
        monkeypatch.delenv("LITELLM_API_KEY", raising=False)
        importlib.reload(cfg)


def test_accessors_are_functions():
    import llm.config as cfg

    assert callable(cfg.proxy_base_url)
    assert callable(cfg.proxy_api_key)


def test_all_exports():
    import llm.config as cfg

    assert set(cfg.__all__) == {
        "LITELLM_BASE_URL",
        "LITELLM_API_KEY",
        "proxy_base_url",
        "proxy_api_key",
    }
