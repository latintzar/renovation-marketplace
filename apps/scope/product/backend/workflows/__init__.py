"""
Leo Workflows
=============

Deterministic Python pipelines that orchestrate existing tool backends.
Sit between atomic tools and the Hermes agent in the Leo architecture.

    Tool       — atomic operation (search, scrape, send, verify, write)
    Workflow   — deterministic sequence of tool calls (repeatable, improvable)
    Agent      — conversational brain (Hermes) that triggers workflows and
                 talks to humans

Workflows call tool-backend functions directly — they do NOT go through
Hermes's tool dispatch loop. One LLM call is allowed per workflow for
copy generation (copy.py utilities), but that is a single prompt, not
an agent loop.

When a workflow finishes it writes a signal to the dossier's
``workflow_signals`` list. The next time Hermes turns for that
conversation, ephemeral_context.py picks it up and injects it as a
note — "Profile Import complete for hc-abc123, trust score 78, canvas
ready." Hermes then decides when and how to surface it.

Available workflows
-------------------
contractor_discovery  — find contractors on Houzz/FB, create HC records,
                        send outreach, trigger profile import on reply
profile_import        — scrape → verify → dossier → recompute canvas
"""

from workflows.contractor_discovery import run_contractor_discovery
from workflows.profile_import import run_profile_import

__all__ = [
    "run_contractor_discovery",
    "run_profile_import",
]
