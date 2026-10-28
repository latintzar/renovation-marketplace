"""Leo's scope tool handlers, grouped by domain.

Each module exposes a ``register(registry)`` function that binds its
handlers into the active agent framework's tool registry (Hermes
today, other providers eventually — see
:mod:`messaging.frameworks`). The top-level orchestrator
:func:`agent.tool_registry.register_leo_tools` calls every module's
``register()`` in turn.

Moved from ``packages/messaging/src/messaging/leo_agent/tools/`` in
Phase 5 Wave 6 — these tools are scope-app policy (Leo persona's
capabilities) and belong next to the Leo agent, not in the shared
messaging capability package.

Modules and their tool sets:

* :mod:`.canvas` — ``update_quote``, ``update_profile``, ``set_drawer``,
  ``create_page``.
* :mod:`.user_flow` — ``save_signup``, ``whatsapp_handoff``,
  ``start_job_intake``.
* :mod:`.delivery` — ``send_whatsapp``, ``send_email``,
  ``request_human``.
* :mod:`.legal` — ``search_spanish_law``, ``get_boe_norm_text``,
  ``search_eu_law``.
* :mod:`.pricing` — ``lookup_price``, ``lookup_product``,
  ``estimate_cost``.
* :mod:`.discovery` — ``find_houzz_contractors``, ``search_fb_groups``,
  ``search_forums``, ``enrich_contractor``.
* :mod:`.outreach` — ``outreach_contractor``, ``batch_outreach``,
  ``control_outreach``, ``rank_job_responses``.
* :mod:`.admin` — ``founder_dashboard``, ``propose_skill_change``,
  ``skill_manage`` (gated), ``create_job``.
"""
