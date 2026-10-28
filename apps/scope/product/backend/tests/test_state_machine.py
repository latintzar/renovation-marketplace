"""Unit tests for ``state_machine`` (scope-app project/milestone/variation)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from state_machine import (
    MILESTONE_STATES,
    PROJECT_STATES,
    VARIATION_STATES,
    assert_transition,
    can_transition,
)


class TestStateSets:
    def test_project_states_frozenset(self) -> None:
        assert isinstance(PROJECT_STATES, frozenset)
        assert PROJECT_STATES == {
            "finalized",
            "paid",
            "in_progress",
            "complete",
            "cancelled",
        }

    def test_milestone_states_frozenset(self) -> None:
        assert isinstance(MILESTONE_STATES, frozenset)
        assert MILESTONE_STATES == {"pending", "proof_submitted", "released"}

    def test_variation_states_frozenset(self) -> None:
        assert isinstance(VARIATION_STATES, frozenset)
        assert VARIATION_STATES == {"pending", "approved", "declined"}


class TestProjectTransitions:
    def test_finalized_to_paid_system(self) -> None:
        assert can_transition("project", "finalized", "paid", "system") == (True, "")

    def test_finalized_to_paid_any_actor_allowed(self) -> None:
        """``"system"`` in the rule means "skip actor check" — auth gates
        entry to the calling route, not the state machine. Behavioral
        parity with ``shared.states``."""
        assert can_transition("project", "finalized", "paid", "contractor")[0]
        assert can_transition("project", "finalized", "paid", "homeowner")[0]

    def test_paid_to_in_progress_by_contractor(self) -> None:
        assert can_transition("project", "paid", "in_progress", "contractor") == (True, "")

    def test_paid_to_in_progress_by_homeowner_denied(self) -> None:
        ok, err = can_transition("project", "paid", "in_progress", "homeowner")
        assert ok is False
        assert "contractor" in err

    def test_in_progress_to_complete_system(self) -> None:
        assert can_transition("project", "in_progress", "complete", "system") == (True, "")

    def test_paid_to_cancelled_either_actor(self) -> None:
        # "either" means both contractor and homeowner ok (and system).
        assert can_transition("project", "paid", "cancelled", "contractor")[0]
        assert can_transition("project", "paid", "cancelled", "homeowner")[0]
        assert can_transition("project", "paid", "cancelled", "system")[0]

    def test_invalid_transition(self) -> None:
        ok, err = can_transition(
            "project", "finalized", "complete", "system"
        )
        assert ok is False
        assert "not allowed" in err


class TestCancellationGuard:
    def test_cancel_with_no_milestones(self) -> None:
        ok, err = can_transition(
            "project", "paid", "cancelled", "homeowner", milestones=None
        )
        assert ok

    def test_cancel_with_empty_milestones(self) -> None:
        ok, err = can_transition(
            "project", "paid", "cancelled", "homeowner", milestones=[]
        )
        assert ok

    def test_cancel_with_all_pending_milestones(self) -> None:
        milestones = [{"status": "pending"}, {"status": "pending"}]
        ok, err = can_transition(
            "project", "paid", "cancelled", "homeowner", milestones=milestones
        )
        assert ok

    def test_cancel_with_null_status_treated_pending(self) -> None:
        milestones = [{"status": None}, {"status": ""}]
        ok, err = can_transition(
            "project", "paid", "cancelled", "homeowner", milestones=milestones
        )
        assert ok

    def test_cancel_blocked_when_proof_submitted(self) -> None:
        milestones = [
            {"status": "pending"},
            {"status": "proof_submitted"},
        ]
        ok, err = can_transition(
            "project", "in_progress", "cancelled", "homeowner", milestones=milestones
        )
        assert ok is False
        assert "work has already started" in err

    def test_cancel_blocked_when_released(self) -> None:
        milestones = [{"status": "released"}]
        ok, err = can_transition(
            "project", "paid", "cancelled", "contractor", milestones=milestones
        )
        assert ok is False


class TestMilestoneTransitions:
    def test_pending_to_proof_submitted_by_contractor(self) -> None:
        assert can_transition("milestone", "pending", "proof_submitted", "contractor") == (True, "")

    def test_pending_to_proof_submitted_by_homeowner_denied(self) -> None:
        ok, _ = can_transition("milestone", "pending", "proof_submitted", "homeowner")
        assert ok is False

    def test_proof_submitted_to_released_by_homeowner(self) -> None:
        assert can_transition("milestone", "proof_submitted", "released", "homeowner") == (True, "")

    def test_none_from_status_treated_as_pending(self) -> None:
        ok, _ = can_transition("milestone", None, "proof_submitted", "contractor")
        assert ok

    def test_skipping_pending_denied(self) -> None:
        ok, _ = can_transition("milestone", "pending", "released", "homeowner")
        assert ok is False


class TestVariationTransitions:
    def test_pending_to_approved_by_homeowner(self) -> None:
        assert can_transition("variation", "pending", "approved", "homeowner") == (True, "")

    def test_pending_to_declined_by_homeowner(self) -> None:
        assert can_transition("variation", "pending", "declined", "homeowner") == (True, "")

    def test_contractor_cannot_approve(self) -> None:
        ok, _ = can_transition("variation", "pending", "approved", "contractor")
        assert ok is False

    def test_declined_to_pending_not_allowed(self) -> None:
        # design D9: re-entrance not allowed yet.
        ok, err = can_transition("variation", "declined", "pending", "homeowner")
        assert ok is False
        assert "not allowed" in err


class TestAssertTransition:
    def test_success_does_not_raise(self) -> None:
        assert_transition("project", "finalized", "paid", "system")

    def test_failure_raises_400(self) -> None:
        with pytest.raises(HTTPException) as info:
            assert_transition("project", "paid", "in_progress", "homeowner")
        assert info.value.status_code == 400

    def test_failure_custom_status_code(self) -> None:
        with pytest.raises(HTTPException) as info:
            assert_transition(
                "project",
                "paid",
                "in_progress",
                "homeowner",
                status_code=403,
            )
        assert info.value.status_code == 403

    def test_failure_message_includes_reason(self) -> None:
        with pytest.raises(HTTPException) as info:
            assert_transition("project", "paid", "in_progress", "homeowner")
        assert "contractor" in info.value.detail
