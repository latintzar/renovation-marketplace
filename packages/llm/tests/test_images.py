"""Tests for :mod:`llm.images` — the image-generation primitive."""

from __future__ import annotations

import base64

import httpx
import pytest

from llm.errors import (
    InvalidResponseShape,
    ProviderError,
    ProviderUnavailable,
    RateLimitError,
)
from llm.images import generate_image, generate_image_async


# A minimal 1x1 transparent PNG — enough bytes to assert the magic header.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_TINY_PNG = (
    _PNG_MAGIC
    + b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    + b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    + b"\x00\x00\x00\rIDATx\x9cc\xfc\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _b64_response(png_bytes: bytes = _TINY_PNG) -> dict:
    return {
        "created": 0,
        "data": [{"b64_json": base64.b64encode(png_bytes).decode("ascii")}],
    }


def _url_response(url: str = "https://example.test/img.png") -> dict:
    return {"created": 0, "data": [{"url": url}]}


def _mock_client(
    *,
    status_code: int = 200,
    payload: dict | None = None,
    handler=None,
) -> httpx.Client:
    if handler is None:
        body = _b64_response() if payload is None else payload

        def handler(request):
            return httpx.Response(status_code, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _mock_async_client(
    *,
    status_code: int = 200,
    payload: dict | None = None,
    handler=None,
) -> httpx.AsyncClient:
    if handler is None:
        body = _b64_response() if payload is None else payload

        def handler(request):
            return httpx.Response(status_code, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class TestGenerateImageSync:
    def test_returns_png_bytes_on_happy_path(self):
        client = _mock_client(payload=_b64_response())
        png = generate_image("a pencil sketch", client=client)
        assert isinstance(png, bytes)
        assert png[:8] == _PNG_MAGIC

    def test_returns_url_when_response_format_url(self):
        client = _mock_client(payload=_url_response("https://example.test/a.png"))
        out = generate_image("x", response_format="url", client=client)
        assert out == "https://example.test/a.png"

    def test_builds_openai_shape_body(self):
        captured = {}

        def handler(request):
            captured["body"] = request.content
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("Authorization", "")
            return httpx.Response(200, json=_b64_response())

        client = _mock_client(handler=handler)
        generate_image("hello", model="gemini-2.5-flash-image", size="512x512", client=client)

        import json as _json

        body = _json.loads(captured["body"])
        assert body["model"] == "gemini-2.5-flash-image"
        assert body["prompt"] == "hello"
        assert body["size"] == "512x512"
        assert body["n"] == 1
        assert body["response_format"] == "b64_json"
        assert captured["url"].endswith("/v1/images/generations")
        assert captured["auth"].startswith("Bearer ")

    def test_extra_kwargs_merged_into_body(self):
        captured = {}

        def handler(request):
            import json as _json

            captured["body"] = _json.loads(request.content)
            return httpx.Response(200, json=_b64_response())

        client = _mock_client(handler=handler)
        generate_image("x", client=client, extra={"quality": "hd", "style": "natural"})
        assert captured["body"]["quality"] == "hd"
        assert captured["body"]["style"] == "natural"

    def test_429_maps_to_rate_limit(self):
        client = _mock_client(status_code=429, payload={"error": "slow down"})
        with pytest.raises(RateLimitError):
            generate_image("x", client=client)

    def test_500_maps_to_provider_unavailable(self):
        client = _mock_client(status_code=500, payload={"error": "boom"})
        with pytest.raises(ProviderUnavailable):
            generate_image("x", client=client)

    def test_400_maps_to_provider_error(self):
        client = _mock_client(status_code=400, payload={"error": "bad"})
        with pytest.raises(ProviderError) as info:
            generate_image("x", client=client)
        assert not isinstance(info.value, RateLimitError)
        assert not isinstance(info.value, ProviderUnavailable)

    def test_missing_data_raises_invalid_shape(self):
        client = _mock_client(payload={})
        with pytest.raises(InvalidResponseShape):
            generate_image("x", client=client)

    def test_missing_b64_raises_invalid_shape(self):
        client = _mock_client(payload={"data": [{"no_b64": "here"}]})
        with pytest.raises(InvalidResponseShape):
            generate_image("x", client=client)

    def test_missing_url_raises_invalid_shape(self):
        client = _mock_client(payload={"data": [{"no_url": "here"}]})
        with pytest.raises(InvalidResponseShape):
            generate_image("x", response_format="url", client=client)


class TestGenerateImageAsync:
    @pytest.mark.asyncio
    async def test_returns_png_bytes_on_happy_path(self):
        client = _mock_async_client(payload=_b64_response())
        png = await generate_image_async("a pencil sketch", client=client)
        assert isinstance(png, bytes)
        assert png[:8] == _PNG_MAGIC

    @pytest.mark.asyncio
    async def test_429_maps_to_rate_limit(self):
        client = _mock_async_client(status_code=429, payload={"error": "slow"})
        with pytest.raises(RateLimitError):
            await generate_image_async("x", client=client)


class TestPublicImport:
    def test_importable_from_top_level(self):
        import llm

        assert hasattr(llm, "generate_image")
        assert llm.generate_image is generate_image

    def test_default_model_resolves(self):
        from llm import DEFAULT_IMAGE_GEN, MODEL_REGISTRY

        assert DEFAULT_IMAGE_GEN in MODEL_REGISTRY
