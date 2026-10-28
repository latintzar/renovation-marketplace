"""Tests for :mod:`llm.vision`."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm.errors import ModelNotFound
from llm.providers.base import ChatResponse
from llm.vision import complete_vision_sync, complete_vision


class TestDataURLNormalisation:
    def test_bytes_input(self, monkeypatch, stub_bedrock_client):
        client = stub_bedrock_client()
        from llm.providers import bedrock as _bedrock

        orig = _bedrock.complete_sync
        captured = {}

        def patched(messages, **kwargs):
            captured["msg"] = messages[0]
            return orig(messages, client=client, **kwargs)

        monkeypatch.setattr(_bedrock, "complete_sync", patched)

        complete_vision_sync(
            "describe this", b"\x89PNG\r\nfake"
        )

        blocks = captured["msg"].content
        assert any(
            b.get("type") == "image_url"
            and b["image_url"]["url"].startswith("data:image/png;")
            for b in blocks
        )

    def test_path_input(self, monkeypatch, stub_bedrock_client, tmp_path):
        client = stub_bedrock_client()
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\nbody")

        from llm.providers import bedrock as _bedrock

        orig = _bedrock.complete_sync
        captured = {}

        def patched(messages, **kwargs):
            captured["msg"] = messages[0]
            return orig(messages, client=client, **kwargs)

        monkeypatch.setattr(_bedrock, "complete_sync", patched)

        complete_vision_sync("describe", png_file)
        blocks = captured["msg"].content
        assert any(
            b.get("type") == "image_url"
            and "base64" in b["image_url"]["url"]
            for b in blocks
        )

    def test_data_url_passthrough(self, monkeypatch, stub_bedrock_client):
        client = stub_bedrock_client()
        url = "data:image/jpeg;base64,AAAAAA=="

        from llm.providers import bedrock as _bedrock

        orig = _bedrock.complete_sync
        captured = {}

        def patched(messages, **kwargs):
            captured["msg"] = messages[0]
            return orig(messages, client=client, **kwargs)

        monkeypatch.setattr(_bedrock, "complete_sync", patched)

        complete_vision_sync("describe", url)
        blocks = captured["msg"].content
        assert any(
            b.get("type") == "image_url" and b["image_url"]["url"] == url
            for b in blocks
        )


class TestVisionModelGating:
    def test_non_vision_model_raises(self, stub_bedrock_client):
        with pytest.raises(ModelNotFound):
            complete_vision_sync(
                "describe", b"body", model="anthropic/claude-haiku-4.5"
            )

    def test_default_model_is_vision_tier(self, monkeypatch, stub_bedrock_client):
        client = stub_bedrock_client()
        from llm.providers import bedrock as _bedrock
        from llm.models.tiers import DEFAULT_VISION

        orig = _bedrock.complete_sync
        captured = {}

        def patched(messages, *, model, **kwargs):
            captured["model"] = model
            return orig(messages, model=model, client=client, **kwargs)

        monkeypatch.setattr(_bedrock, "complete_sync", patched)

        complete_vision_sync("describe", b"\x89PNG\r\n")
        assert captured["model"] == DEFAULT_VISION


class TestVisionAsync:
    @pytest.mark.asyncio
    async def test_async(self, monkeypatch):
        from llm.providers import bedrock as _bedrock

        async def fake_complete(messages, **kwargs):
            return ChatResponse(
                text="I see a dog.", model=kwargs.get("model", "")
            )

        monkeypatch.setattr(_bedrock, "complete", fake_complete)

        resp = await complete_vision(
            "what's in the image",
            b"\x89PNG\r\n",
            model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        )
        assert resp.text == "I see a dog."
