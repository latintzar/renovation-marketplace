"""Host-adapter registry — the one-way callback seam into routes/workflows."""

from __future__ import annotations

import pytest

from messaging import (
    HostAdapterMissing,
    clear_adapters,
    get_adapter,
    has_adapter,
    register_host_adapter,
)


class TestRegister:
    def test_register_then_lookup(self) -> None:
        def fn(x):
            return x + 1

        register_host_adapter("fake.add1", fn)
        assert get_adapter("fake.add1")(5) == 6

    def test_overwrite_warns_but_succeeds(self, caplog) -> None:
        def a():
            return "a"

        def b():
            return "b"

        register_host_adapter("fake.x", a)
        import logging
        with caplog.at_level(logging.WARNING):
            register_host_adapter("fake.x", b)
        assert get_adapter("fake.x")() == "b"
        assert any("overwriting" in r.message for r in caplog.records)


class TestLookup:
    def test_required_miss_raises(self) -> None:
        with pytest.raises(HostAdapterMissing):
            get_adapter("nonexistent.fn")

    def test_optional_miss_returns_none(self) -> None:
        assert get_adapter("nonexistent.fn", required=False) is None

    def test_has_adapter_before_register(self) -> None:
        assert has_adapter("maybe.fn") is False

    def test_has_adapter_after_register(self) -> None:
        register_host_adapter("maybe.fn", lambda: "ok")
        assert has_adapter("maybe.fn") is True


class TestReset:
    def test_clear_wipes_all(self) -> None:
        register_host_adapter("a.b", lambda: "x")
        register_host_adapter("c.d", lambda: "y")
        clear_adapters()
        assert not has_adapter("a.b")
        assert not has_adapter("c.d")
