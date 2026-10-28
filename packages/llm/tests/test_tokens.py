"""Tests for :mod:`llm.tokens`."""

from __future__ import annotations

from llm.providers.base import Message
from llm.tokens import count_message_tokens, count_tokens


class TestCountTokens:
    def test_empty_string(self):
        """Empty string: tiktoken returns 0 (correct); fallback returns max(1, 0) = 1."""
        assert count_tokens("") >= 0

    def test_short_string(self):
        assert count_tokens("hello") >= 1

    def test_longer_string_has_more_tokens(self):
        assert count_tokens("a" * 100) > count_tokens("a" * 10)


class TestCountMessageTokens:
    def test_single_message(self):
        msgs = [Message(role="user", content="hello")]
        n = count_message_tokens(msgs)
        # at least 4-token overhead + content tokens
        assert n >= 5

    def test_multiple_messages_add_up(self):
        msgs_one = [Message(role="user", content="hello world")]
        msgs_two = [
            Message(role="user", content="hello world"),
            Message(role="assistant", content="hi there"),
        ]
        assert count_message_tokens(msgs_two) > count_message_tokens(msgs_one)

    def test_content_blocks_text(self):
        msg = Message(
            role="user",
            content=[
                {"type": "text", "text": "describe this"},
                {"type": "image_url", "image_url": {"url": "data:..."}},
            ],
        )
        n = count_message_tokens([msg])
        # block path + 256-token budget for image
        assert n >= 256
