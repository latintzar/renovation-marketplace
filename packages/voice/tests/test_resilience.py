"""Concurrency semaphore tests."""

from __future__ import annotations

import asyncio

import pytest

from voice import resilience


class TestVoiceSemaphore:
    def test_creates_semaphore_in_event_loop(self):
        async def _run():
            sem = resilience.voice_semaphore()
            assert isinstance(sem, asyncio.Semaphore)
            return sem

        sem = asyncio.new_event_loop().run_until_complete(_run())

    def test_reuses_same_semaphore_in_same_loop(self):
        async def _run():
            a = resilience.voice_semaphore()
            b = resilience.voice_semaphore()
            return a, b

        loop = asyncio.new_event_loop()
        try:
            a, b = loop.run_until_complete(_run())
        finally:
            loop.close()
        assert a is b

    def test_default_size_is_eight(self, monkeypatch):
        monkeypatch.delenv("VOICE_CONCURRENCY", raising=False)
        resilience.reset_semaphore_for_tests()

        async def _run():
            sem = resilience.voice_semaphore()
            return sem._value

        loop = asyncio.new_event_loop()
        try:
            val = loop.run_until_complete(_run())
        finally:
            loop.close()
        assert val == 8

    def test_respects_voice_concurrency_env(self, monkeypatch):
        monkeypatch.setenv("VOICE_CONCURRENCY", "3")
        resilience.reset_semaphore_for_tests()

        async def _run():
            return resilience.voice_semaphore()._value

        loop = asyncio.new_event_loop()
        try:
            val = loop.run_until_complete(_run())
        finally:
            loop.close()
        assert val == 3

    def test_rebinds_across_loops(self):
        """When a new event loop starts (e.g. pytest-asyncio per-test isolation),
        a fresh semaphore is created bound to it — else we'd get
        'Semaphore bound to different event loop'.
        """
        async def _run():
            return resilience.voice_semaphore()

        loop1 = asyncio.new_event_loop()
        try:
            sem1 = loop1.run_until_complete(_run())
        finally:
            loop1.close()

        loop2 = asyncio.new_event_loop()
        try:
            sem2 = loop2.run_until_complete(_run())
        finally:
            loop2.close()

        # Different loops → different semaphore instances
        assert sem1 is not sem2

    def test_reset_clears_cache(self, monkeypatch):
        monkeypatch.setenv("VOICE_CONCURRENCY", "5")
        resilience.reset_semaphore_for_tests()

        async def _run_1():
            return resilience.voice_semaphore()

        async def _run_2(expected_size):
            sem = resilience.voice_semaphore()
            assert sem._value == expected_size
            return sem

        loop = asyncio.new_event_loop()
        try:
            sem_first = loop.run_until_complete(_run_1())
            # Change env, reset, new one should pick it up
            monkeypatch.setenv("VOICE_CONCURRENCY", "2")
            resilience.reset_semaphore_for_tests()
            sem_second = loop.run_until_complete(_run_2(2))
            assert sem_first is not sem_second
        finally:
            loop.close()
