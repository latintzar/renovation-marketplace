"""Tests for :mod:`llm.usage`."""

from __future__ import annotations

from llm.providers.base import ChatResponse, Usage
from llm.usage import record_usage, register_observer, unregister_observer


def _make_response(model: str = "anthropic/claude-haiku-4.5") -> ChatResponse:
    return ChatResponse(
        text="ok",
        model=model,
        usage=Usage(input_tokens=10, output_tokens=5, total_tokens=15, model=model),
    )


class TestObserverRegistry:
    def test_register_and_fire(self):
        events = []

        def obs(resp):
            events.append(resp)

        register_observer(obs)
        try:
            record_usage(_make_response())
        finally:
            unregister_observer(obs)
        assert len(events) == 1

    def test_unregister(self):
        events = []

        def obs(resp):
            events.append(resp)

        register_observer(obs)
        unregister_observer(obs)
        record_usage(_make_response())
        assert events == []

    def test_unregister_twice_is_no_op(self):
        def obs(resp):
            pass

        register_observer(obs)
        unregister_observer(obs)
        unregister_observer(obs)  # silent no-op

    def test_observer_exception_does_not_break_others(self):
        events = []

        def bad(resp):
            raise RuntimeError("boom")

        def good(resp):
            events.append(resp)

        register_observer(bad)
        register_observer(good)
        try:
            record_usage(_make_response())
        finally:
            unregister_observer(bad)
            unregister_observer(good)
        assert len(events) == 1

    def test_observers_called_in_registration_order(self):
        order = []

        def first(resp):
            order.append(1)

        def second(resp):
            order.append(2)

        register_observer(first)
        register_observer(second)
        try:
            record_usage(_make_response())
        finally:
            unregister_observer(first)
            unregister_observer(second)
        assert order == [1, 2]
