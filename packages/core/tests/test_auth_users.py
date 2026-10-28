"""Tests for :class:`core.auth.users.CurrentUser`."""

from __future__ import annotations

from core import CurrentUser


def test_current_user_fields() -> None:
    u = CurrentUser(
        id="user-1", email="x@example.com", role="contractor", contractor_id="c-1"
    )
    assert u.id == "user-1"
    assert u.email == "x@example.com"
    assert u.role == "contractor"
    assert u.contractor_id == "c-1"


def test_homeowner_has_none_contractor_id() -> None:
    """Invariant: homeowner role has no contractor_id by default."""
    u = CurrentUser(id="user-2", email="h@example.com", role="homeowner")
    assert u.contractor_id is None
