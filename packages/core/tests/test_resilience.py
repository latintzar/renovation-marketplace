"""Tests for :mod:`core.resilience`."""

from __future__ import annotations

import asyncio
import time
from datetime import timedelta

import pytest

from core import RateLimiter, async_retry, retry, run_sync, timed_cache
from core.resilience import (
    as_completed,
    shared_thread_pool,
    shutdown_thread_pool,
)


@pytest.fixture(autouse=True)
def _reset_pool() -> None:
    yield
    shutdown_thread_pool(wait=True)


# ---------------------------------------------------------------------------
# retry
# ---------------------------------------------------------------------------


def test_retry_succeeds_on_second_attempt() -> None:
    calls: list[int] = []

    @retry(attempts=3, base_delay=0, jitter=0)
    def flaky() -> str:
        calls.append(1)
        if len(calls) < 2:
            raise ValueError("blip")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 2


def test_retry_reraises_last_exception_after_exhaustion() -> None:
    @retry(attempts=2, base_delay=0, jitter=0)
    def always_fail() -> str:
        raise ValueError("persistent")

    with pytest.raises(ValueError, match="persistent"):
        always_fail()


def test_retry_fires_on_retry_callback() -> None:
    seen: list[int] = []

    @retry(
        attempts=3,
        base_delay=0,
        jitter=0,
        on_retry=lambda idx, exc: seen.append(idx),
    )
    def flaky() -> int:
        if len(seen) < 2:
            raise RuntimeError("nope")
        return 42

    assert flaky() == 42
    assert seen == [1, 2]


def test_retry_selective_retry_on() -> None:
    """Unlisted exceptions bubble without retrying."""

    @retry(attempts=5, base_delay=0, jitter=0, retry_on=(ValueError,))
    def err() -> str:
        raise TypeError("won't retry this")

    with pytest.raises(TypeError):
        err()


# ---------------------------------------------------------------------------
# async_retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_retry_succeeds_on_second_attempt() -> None:
    counter = {"n": 0}

    @async_retry(attempts=3, base_delay=0, jitter=0)
    async def flaky() -> str:
        counter["n"] += 1
        if counter["n"] < 2:
            raise RuntimeError("blip")
        return "ok"

    assert await flaky() == "ok"
    assert counter["n"] == 2


@pytest.mark.asyncio
async def test_async_retry_reraises_on_exhaustion() -> None:
    @async_retry(attempts=2, base_delay=0, jitter=0)
    async def always_fail() -> str:
        raise RuntimeError("stuck")

    with pytest.raises(RuntimeError):
        await always_fail()


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


def test_rate_limiter_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError):
        RateLimiter(max_per_window=0, window_seconds=1)
    with pytest.raises(ValueError):
        RateLimiter(max_per_window=1, window_seconds=0)


def test_rate_limiter_nonblocking_denies_when_full() -> None:
    rl = RateLimiter(max_per_window=2, window_seconds=60)
    assert rl.acquire(block=False) is True
    assert rl.acquire(block=False) is True
    assert rl.acquire(block=False) is False


def test_rate_limiter_frees_slot_after_window() -> None:
    rl = RateLimiter(max_per_window=1, window_seconds=0.05)
    assert rl.acquire(block=False) is True
    assert rl.acquire(block=False) is False
    time.sleep(0.06)
    assert rl.acquire(block=False) is True


@pytest.mark.asyncio
async def test_rate_limiter_aacquire() -> None:
    rl = RateLimiter(max_per_window=1, window_seconds=0.02)
    assert await rl.aacquire() is True
    await asyncio.sleep(0.03)
    assert await rl.aacquire() is True


# ---------------------------------------------------------------------------
# timed_cache
# ---------------------------------------------------------------------------


def test_timed_cache_hits_within_ttl() -> None:
    calls: list[int] = []

    @timed_cache(timedelta(seconds=60))
    def slow(x: int) -> int:
        calls.append(x)
        return x * 2

    assert slow(1) == 2
    assert slow(1) == 2
    assert calls == [1]


def test_timed_cache_evicts_past_ttl() -> None:
    calls: list[int] = []

    @timed_cache(timedelta(milliseconds=10))
    def slow(x: int) -> int:
        calls.append(x)
        return x

    slow(1)
    time.sleep(0.02)
    slow(1)
    assert calls == [1, 1]


def test_timed_cache_invalidate() -> None:
    calls: list[int] = []

    @timed_cache(timedelta(seconds=60))
    def slow(x: int) -> int:
        calls.append(x)
        return x

    slow(1)
    slow(1)  # cached
    slow.cache_clear()  # type: ignore[attr-defined]
    slow(1)  # recomputed
    assert calls == [1, 1]


def test_timed_cache_maxsize_evicts_oldest() -> None:
    calls: list[int] = []

    @timed_cache(timedelta(seconds=60), maxsize=2)
    def slow(x: int) -> int:
        calls.append(x)
        return x

    slow(1)
    slow(2)
    slow(3)  # evicts 1 (oldest)
    slow(1)  # recompute since 1 was evicted
    assert calls == [1, 2, 3, 1]


# ---------------------------------------------------------------------------
# shared_thread_pool
# ---------------------------------------------------------------------------


def test_shared_thread_pool_is_singleton() -> None:
    a = shared_thread_pool()
    b = shared_thread_pool()
    assert a is b


def test_shared_thread_pool_thread_name_prefix() -> None:
    """Invariant: thread_name_prefix='leo-shared' must be preserved."""
    pool = shared_thread_pool()
    assert pool._thread_name_prefix == "leo-shared"  # type: ignore[attr-defined]


def test_shared_thread_pool_works() -> None:
    pool = shared_thread_pool()
    futures = [pool.submit(lambda x=i: x * 2) for i in range(5)]
    results = [f.result(timeout=5) for f in as_completed(futures)]
    assert sorted(results) == [0, 2, 4, 6, 8]


# ---------------------------------------------------------------------------
# run_sync
# ---------------------------------------------------------------------------


def test_run_sync_no_running_loop() -> None:
    async def work() -> int:
        return 7

    assert run_sync(work()) == 7


def test_run_sync_with_timeout() -> None:
    import concurrent.futures

    async def slow() -> int:
        await asyncio.sleep(1)
        return 1

    # No running loop path — asyncio.run waits; can't test timeout there.
    # Test timeout in the offload path via a thread:
    import threading

    ready = threading.Event()

    async def keep_loop() -> int:
        await asyncio.sleep(1)
        return 99

    def in_thread() -> None:
        async def entry() -> None:
            ready.set()
            with pytest.raises(concurrent.futures.TimeoutError):
                run_sync(keep_loop(), timeout=0.05)

        asyncio.run(entry())

    t = threading.Thread(target=in_thread)
    t.start()
    t.join(timeout=5)
    assert not t.is_alive()


@pytest.mark.asyncio
async def test_run_sync_in_running_loop_offloads() -> None:
    async def work() -> int:
        return 42

    # A loop IS running (pytest-asyncio). run_sync must offload to the
    # shared pool and still return the result.
    assert run_sync(work()) == 42
