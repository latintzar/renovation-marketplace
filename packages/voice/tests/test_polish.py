"""Polish tests — ``llm.chat_sync`` routing + never-raises contract + env toggles.

Phase 5 Wave 7: ``voice.polish`` now delegates to :func:`llm.chat_sync`,
so the Bedrock-specific routing tests (anthropic Messages vs Converse,
system-block retry, boto3 client construction) are no longer this
layer's concern — those live in ``packages/llm/tests/providers/
test_bedrock.py``.

What we still own here:
* never-raises contract (empty/whitespace input, disabled env, empty
  model id, LLM call fails, LLM returns empty)
* model & system-prompt overrides flow through to ``chat_sync``
* the ``Message`` envelope passed to ``chat_sync`` carries the correct
  system/user roles and prefix
"""

from __future__ import annotations

import sys

import voice  # noqa: F401 — ensure submodule is imported
from voice.polish import polish, polish_sync

polish_mod = sys.modules["voice.polish"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _response(text: str, in_tok: int = 10, out_tok: int = 20):
    """Build a minimal :class:`llm.ChatResponse` stub."""
    from llm.providers.base import ChatResponse, Usage

    usage = Usage(
        input_tokens=in_tok,
        output_tokens=out_tok,
        total_tokens=in_tok + out_tok,
        model="stub",
    )
    return ChatResponse(text=text, usage=usage, model="stub")


# ---------------------------------------------------------------------------
# polish_sync — behaviour
# ---------------------------------------------------------------------------


class TestPolishSync:
    def test_empty_returns_empty(self):
        assert polish_sync("") == ""

    def test_whitespace_returns_empty_after_strip(self):
        assert polish_sync("   \n ") == ""

    def test_disabled_returns_raw(self, monkeypatch):
        monkeypatch.setenv("TRANSCRIPT_POLISH_ENABLED", "false")
        assert polish_sync("hola mundo") == "hola mundo"

    def test_empty_model_id_returns_raw(self, fake_chat, monkeypatch):
        from voice import config

        monkeypatch.setattr(config, "polish_model_id", lambda: "")
        assert polish_sync("raw") == "raw"
        fake_chat.assert_not_called()

    def test_success_returns_text(self, fake_chat):
        fake_chat.return_value = _response("Cleaned transcript.")
        assert polish_sync("raw transcript") == "Cleaned transcript."
        fake_chat.assert_called_once()

    def test_never_raises_on_chat_failure(self, fake_chat):
        fake_chat.side_effect = RuntimeError("service unavailable")
        assert polish_sync("raw text") == "raw text"

    def test_never_raises_on_empty_result_returns_raw(self, fake_chat):
        fake_chat.return_value = _response("")
        assert polish_sync("raw text") == "raw text"

    def test_whitespace_only_response_returns_raw(self, fake_chat):
        fake_chat.return_value = _response("   \n\t ")
        assert polish_sync("raw text") == "raw text"

    def test_model_override_forwarded(self, fake_chat):
        fake_chat.return_value = _response("x")
        polish_sync("raw", model_id="us.anthropic.claude-opus-4")
        _, kwargs = fake_chat.call_args
        assert kwargs["model"] == "us.anthropic.claude-opus-4"

    def test_system_prompt_override_forwarded(self, fake_chat):
        fake_chat.return_value = _response("x")
        polish_sync("raw", system_prompt="Just capitalize the first letter.")
        args, _ = fake_chat.call_args
        messages = args[0]
        assert messages[0].role == "system"
        assert messages[0].content == "Just capitalize the first letter."

    def test_default_system_prompt_is_polish_system(self, fake_chat):
        fake_chat.return_value = _response("x")
        polish_sync("raw")
        args, _ = fake_chat.call_args
        messages = args[0]
        assert messages[0].role == "system"
        assert messages[0].content == polish_mod.POLISH_SYSTEM

    def test_user_message_carries_prefix(self, fake_chat):
        fake_chat.return_value = _response("x")
        polish_sync("hola mundo")
        args, _ = fake_chat.call_args
        messages = args[0]
        assert messages[1].role == "user"
        assert messages[1].content.startswith("Raw automatic transcription")
        assert "hola mundo" in messages[1].content

    def test_inference_params(self, fake_chat):
        fake_chat.return_value = _response("x")
        polish_sync("raw")
        _, kwargs = fake_chat.call_args
        assert kwargs["temperature"] == 0.15
        assert kwargs["max_tokens"] == 4096


# ---------------------------------------------------------------------------
# polish (async)
# ---------------------------------------------------------------------------


class TestPolishAsync:
    async def test_polish_returns_cleaned(self, fake_chat):
        fake_chat.return_value = _response("Cleaned.")
        assert await polish("raw") == "Cleaned."

    async def test_polish_never_raises(self, fake_chat):
        fake_chat.side_effect = RuntimeError("boom")
        assert await polish("raw text") == "raw text"


# ---------------------------------------------------------------------------
# Constant — stability check
# ---------------------------------------------------------------------------


class TestPolishSystem:
    def test_constant_shape(self):
        from voice.polish import POLISH_SYSTEM

        assert POLISH_SYSTEM.startswith("You turn raw speech-to-text")
        assert "Voice fidelity" in POLISH_SYSTEM
        assert "Formatting" in POLISH_SYSTEM
