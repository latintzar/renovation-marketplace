"""
state_machine — Project / milestone / variation state machine (scope app)
===========================================================================

Explicit, testable definition of every valid state transition for Leo
scope quotes. Routes call :func:`can_transition` instead of writing
inline guard logic — the transition table is the single source of truth.

This module is **scope-app-specific**. Other apps that want state
machines should either:

1. Import the generic idea (pattern-copy `_TRANSITIONS` table +
   `can_transition` / `assert_transition` shape with their own states),
2. Or promote a generic `state-machine` capability to
   ``packages/core/state_machine.py`` if it's reused across ≥ 2 apps.

Phase 5 Wave 2: moved from ``packages/domain/states.py`` to
``apps/scope/product/backend/state_machine.py``. The project/milestone/variation
states here describe Leo's escrow workflow and don't belong in a shared
package.

Tier: leaf (inside scope backend). Depends on stdlib only.

State machines
--------------

Project (``quotes.status``)::

    finalized → paid → in_progress → complete
                                   ↘ cancelled
    (cancellable from ``paid`` or ``in_progress`` when no work started)

Milestone (``quotes.milestones[*].status``)::

    pending → proof_submitted → released

Variation order (``variation_orders.status``)::

    pending → approved
            ↘ declined

TODO(variation-reentrance): today there is no ``declined → pending`` edge
— contractors who want to revise a declined variation have to create a
new one. Product hasn't signed off on the loop yet.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Tuple

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

PROJECT_STATES = frozenset(
    ["finalized", "paid", "in_progress", "complete", "cancelled"]
)
MILESTONE_STATES = frozenset(["pending", "proof_submitted", "released"])
VARIATION_STATES = frozenset(["pending", "approved", "declined"])

Entity = Literal["project", "milestone", "variation"]
Actor = Literal["contractor", "homeowner", "system"]
# ``"either"`` is allowed on the transition table (signals
# contractor-OR-homeowner) but is NOT a valid ``actor_role`` input.
_AllowedActor = Literal["contractor", "homeowner", "system", "either"]


# ---------------------------------------------------------------------------
# Transition table — (entity, from, to) → rule dict
# ---------------------------------------------------------------------------
# ``actor`` tells us WHO can trigger. ``"either"`` = contractor OR
# homeowner (``system`` is always ok since it's internal).
# ``trigger`` is a human-readable note (unused by the engine).
# ``guard`` is a named predicate run after actor check.

_TRANSITIONS: dict[tuple[str, str, str], dict[str, Any]] = {
    # --- Project -------------------------------------------------------
    ("project", "finalized", "paid"): {
        "actor": "system",
        "trigger": "payment_webhook",
    },
    ("project", "paid", "in_progress"): {
        "actor": "contractor",
        "trigger": "first_proof",
    },
    ("project", "in_progress", "complete"): {
        "actor": "system",
        "trigger": "all_released",
    },
    ("project", "paid", "cancelled"): {
        "actor": "either",
        "guard": "no_work_started",
    },
    ("project", "in_progress", "cancelled"): {
        "actor": "either",
        "guard": "no_work_started",
    },
    # --- Milestone -----------------------------------------------------
    ("milestone", "pending", "proof_submitted"): {"actor": "contractor"},
    ("milestone", "proof_submitted", "released"): {"actor": "homeowner"},
    # --- Variation -----------------------------------------------------
    ("variation", "pending", "approved"): {"actor": "homeowner"},
    ("variation", "pending", "declined"): {"actor": "homeowner"},
}


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def _guard_no_work_started(
    milestones: Optional[list[dict[str, Any]]],
) -> Tuple[bool, str]:
    """True iff every milestone is still ``pending`` / unset.

    If *any* milestone is past ``pending`` (e.g. proof submitted) then
    cancellation is refused — work is in flight and the homeowner owes
    the contractor partial payment via escrow split.

    Empty or ``None`` milestones list → ok.
    """
    if not milestones:
        return True, ""
    for m in milestones:
        if m.get("status") not in ("pending", None, ""):
            return False, "Cannot cancel — work has already started on a milestone"
    return True, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def can_transition(
    entity: Entity,
    from_status: Optional[str],
    to_status: str,
    actor_role: Actor,
    milestones: Optional[list[dict[str, Any]]] = None,
) -> Tuple[bool, str]:
    """Check whether a state transition is allowed.

    Returns ``(True, "")`` on success or ``(False, error_message)`` on
    failure. Callers that want a one-liner HTTPException use
    :func:`assert_transition`.

    Parameters
    ----------
    entity:
        ``"project" | "milestone" | "variation"``.
    from_status:
        Current status value. ``None`` is treated as ``"pending"`` for
        milestones (legacy rows with null status).
    to_status:
        Desired new status.
    actor_role:
        Who is performing the action. System transitions (payment
        webhook, auto-complete) pass ``"system"``.
    milestones:
        Current milestones list — required only for the
        ``no_work_started`` guard. Safe to leave ``None`` otherwise.
    """
    key = (entity, from_status or "pending", to_status)
    rule = _TRANSITIONS.get(key)

    if rule is None:
        return False, f"Transition {entity}:{from_status} → {to_status} is not allowed"

    allowed_actor = rule["actor"]
    if (
        allowed_actor != "either"
        and allowed_actor != "system"
        and allowed_actor != actor_role
    ):
        return False, f"Only a {allowed_actor} can perform this action"

    guard = rule.get("guard")
    if guard == "no_work_started":
        ok, err = _guard_no_work_started(milestones)
        if not ok:
            return False, err

    return True, ""


def assert_transition(
    entity: Entity,
    from_status: Optional[str],
    to_status: str,
    actor_role: Actor,
    milestones: Optional[list[dict[str, Any]]] = None,
    status_code: int = 400,
) -> None:
    """:func:`can_transition` + raise ``HTTPException`` on failure.

    Convenience wrapper for routes that want a guard one-liner. Imports
    ``HTTPException`` lazily — keeping ``domain.states`` tiered as a
    leaf module with no hard FastAPI dependency for non-HTTP callers.
    """
    from fastapi import HTTPException as _HTTPException

    ok, err = can_transition(entity, from_status, to_status, actor_role, milestones)
    if not ok:
        raise _HTTPException(status_code=status_code, detail=err)


__all__ = [
    "PROJECT_STATES",
    "MILESTONE_STATES",
    "VARIATION_STATES",
    "can_transition",
    "assert_transition",
]
