"""Tests for :mod:`llm.providers.base` — canonical types."""

from __future__ import annotations

import pytest

from llm.providers.base import (
    ChatResponse,
    Message,
    StreamChunk,
    Tool,
    ToolCall,
    Usage,
)


class TestMessage:
    def test_minimal(self):
        m = Message(role="user", content="hi")
        assert m.role == "user"
        assert m.content == "hi"
        assert m.name is None

    def test_with_blocks(self):
        blocks = [{"type": "text", "text": "hi"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA="}}]
        m = Message(role="user", content=blocks)
        assert isinstance(m.content, list)
        assert len(m.content) == 2

    def test_frozen(self):
        m = Message(role="user", content="hi")
        with pytest.raises(Exception):
            m.role = "assistant"


class TestTool:
    def test_construct(self):
        t = Tool(
            name="get_weather",
            description="Look up weather",
            parameters={"type": "object", "properties": {}},
        )
        assert t.name == "get_weather"
        assert "type" in t.parameters


class TestToolCall:
    def test_construct(self):
        tc = ToolCall(id="call_abc", name="run", arguments={"x": 1})
        assert tc.id == "call_abc"
        assert tc.arguments == {"x": 1}


class TestUsage:
    def test_construct(self):
        u = Usage(input_tokens=10, output_tokens=5, total_tokens=15, model="x")
        assert u.input_tokens == 10
        assert u.total_tokens == 15

    def test_cost_usd_unknown_model_is_zero(self):
        u = Usage(
            input_tokens=100, output_tokens=100, total_tokens=200, model="unknown"
        )
        assert u.cost_usd == 0.0

    def test_cost_usd_known_model(self):
        u = Usage(
            input_tokens=1000,
            output_tokens=1000,
            total_tokens=2000,
            model="anthropic/claude-haiku-4.5",
        )
        # 0.0008 + 0.004 per 1k
        assert u.cost_usd == pytest.approx(0.0008 + 0.004)


class TestChatResponse:
    def test_defaults(self):
        r = ChatResponse(text="hi")
        assert r.text == "hi"
        assert r.tool_calls == []
        assert r.finish_reason == "stop"
        assert r.used_fallback is False
        assert r.attempt_count == 1

    def test_with_fallback_flag(self):
        r = ChatResponse(text="", used_fallback=True, fallback_reason="RateLimitError")
        assert r.used_fallback
        assert r.fallback_reason == "RateLimitError"


class TestStreamChunk:
    def test_intermediate(self):
        c = StreamChunk(delta="partial ", done=False)
        assert c.delta == "partial "
        assert not c.done

    def test_terminal(self):
        u = Usage(10, 5, 15, "x")
        c = StreamChunk(delta="", done=True, usage=u, finish_reason="stop")
        assert c.done
        assert c.usage is u
