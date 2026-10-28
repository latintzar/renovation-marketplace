"""Tests for :mod:`core.aws`.

Safety-critical: explicit credentials only; never fall back to the
default AWS credential chain. Coverage target: 100%.
"""

from __future__ import annotations

import pytest

from core import (
    bedrock_client,
    get_active_leo_aws_account,
    get_leo_aws_credentials,
    leo_boto3_client,
)
from core.aws import (
    clear_leo_aws_credential_cache,
    log_active_leo_aws_account,
    normalize_leo_aws_account,
    validate_leo_aws_for_bedrock,
)


@pytest.fixture(autouse=True)
def cred_cache_reset() -> None:
    clear_leo_aws_credential_cache()
    yield
    clear_leo_aws_credential_cache()


def test_normalize_uppercases_and_replaces_dashes() -> None:
    assert normalize_leo_aws_account("alternate-2") == "ALTERNATE_2"


def test_normalize_accepts_underscore() -> None:
    assert normalize_leo_aws_account("primary_a") == "PRIMARY_A"


@pytest.mark.parametrize("bad", ["", "1-prefix", "@invalid", " "])
def test_normalize_rejects_invalid_chars(bad: str) -> None:
    with pytest.raises(ValueError):
        normalize_leo_aws_account(bad)


def test_get_active_account_raises_when_unset() -> None:
    with pytest.raises(RuntimeError) as info:
        get_active_leo_aws_account()
    assert "LEO_AWS_ACCOUNT" in str(info.value)


def test_get_active_account_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "alternate-2")
    assert get_active_leo_aws_account() == "ALTERNATE_2"


def test_get_creds_raises_without_suffixed_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invariant: never fall back to default AWS credential chain."""
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "PRIMARY")
    # AWS_ACCESS_KEY_ID / SECRET are NOT suffixed, so creds must fail:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAgeneric")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "generic")
    with pytest.raises(RuntimeError) as info:
        get_leo_aws_credentials()
    assert "PRIMARY" in str(info.value)


def test_get_creds_reads_suffixed_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "ALT2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_ALT2", "AKIAsuffixed")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY_ALT2", "suffixed-secret")
    ak, sk = get_leo_aws_credentials()
    assert ak == "AKIAsuffixed"
    assert sk == "suffixed-secret"


def test_get_creds_strips_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace / surrounding quotes get stripped."""
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "ALT3")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_ALT3", '  "AKIAquoted"  ')
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY_ALT3", "'secret-quoted'")
    ak, sk = get_leo_aws_credentials()
    assert ak == "AKIAquoted"
    assert sk == "secret-quoted"


def test_get_creds_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "ALT4")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_ALT4", "AKIA")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY_ALT4", "s")
    first = get_leo_aws_credentials()
    # Mutate env AFTER first call; lru_cache means we still see old values.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_ALT4", "DIFFERENT")
    second = get_leo_aws_credentials()
    assert first == second


def test_clear_cache_invalidates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "ALT5")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_ALT5", "AKIA")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY_ALT5", "s")
    get_leo_aws_credentials()
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_ALT5", "NEW_KEY")
    clear_leo_aws_credential_cache()
    assert get_leo_aws_credentials()[0] == "NEW_KEY"


def test_validate_for_bedrock_raises_when_misconfigured() -> None:
    """Invariant: validate surfaces the RuntimeError from creds resolution."""
    with pytest.raises(RuntimeError):
        validate_leo_aws_for_bedrock()


def test_log_active_account_swallows_exceptions(caplog) -> None:
    """log_active_leo_aws_account must not raise when misconfigured."""
    caplog.clear()
    log_active_leo_aws_account()  # env missing — must not raise


def test_log_active_account_emits_prefix(
    monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "ALT6")
    monkeypatch.setenv(
        "AWS_ACCESS_KEY_ID_ALT6", "AKIAEXAMPLE0123456789"
    )
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY_ALT6", "s")
    with caplog.at_level("INFO", logger="core.aws"):
        log_active_leo_aws_account()
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "ALT6" in joined
    assert "AKIAEXAM" in joined


def test_leo_boto3_client_uses_explicit_creds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """leo_boto3_client passes the cached creds through to boto3.client."""
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "BOTO")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_BOTO", "AKIAboto")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY_BOTO", "secret-boto")

    captured: dict = {}

    def fake_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured["kwargs"] = kwargs
        return object()

    # Patch boto3.client so we don't open real AWS connections.
    import boto3

    monkeypatch.setattr(boto3, "client", fake_client)

    leo_boto3_client("s3", region_name="us-east-1")
    assert captured["service_name"] == "s3"
    assert captured["kwargs"]["aws_access_key_id"] == "AKIAboto"
    assert captured["kwargs"]["aws_secret_access_key"] == "secret-boto"
    assert captured["kwargs"]["region_name"] == "us-east-1"
    # No config kwarg was passed; make sure we didn't leak the parameter.
    assert "config" not in captured["kwargs"]


def test_leo_boto3_client_with_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "CFG")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_CFG", "K")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY_CFG", "S")
    captured: dict = {}
    import boto3
    from botocore.config import Config

    def fake_client(service_name, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(boto3, "client", fake_client)
    cfg = Config()
    leo_boto3_client("s3", region_name="us-east-1", config=cfg)
    assert captured["config"] is cfg


def test_bedrock_client_caches_by_region_and_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invariant: different timeouts → different cached clients."""
    monkeypatch.setenv("LEO_AWS_ACCOUNT", "BDR")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID_BDR", "K")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY_BDR", "S")
    import boto3

    created: list = []

    def fake_client(service_name, **kwargs):
        instance = object()
        created.append((service_name, kwargs))
        return instance

    monkeypatch.setattr(boto3, "client", fake_client)

    a = bedrock_client("us-east-1")
    b = bedrock_client("us-east-1")  # same → cache hit
    c = bedrock_client("us-east-1", read_timeout=120)  # different → new
    assert a is b
    assert a is not c
    assert len(created) == 2
