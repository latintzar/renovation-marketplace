# apps/scope/product/backend/agent

**Leo — the scope app's AI agent.** Persona, tools, per-turn context, chat
runtime glue, and founder notifications. Moved here from
`packages/messaging/src/messaging/leo_agent/` in Phase 5 Wave 6 as part of
the architectural recalibration:

> Leo is the **scope app's** agent, not a cross-app capability.
>
> The shared `packages/messaging/` provides the *capability* (channels,
> transport, media, verification, framework adapter protocol). This
> directory is where we wire Leo's persona, tools, and business-specific
> policy against that capability.

Other apps that want their own agent (e.g. the April-18 demo deck, a
future livestock agent, the leo-internal-sales recorder) each bring
their own `agent/` dir with their own persona and tools. They reuse
`packages/messaging/` for channels + the framework protocol.

## Layout

```
agent/
  __init__.py          # public surface (re-exports from the modules below)
  leo.py               # LeoAgent runtime: per-conversation agent pool, run_leo_chat, whatsapp_reply
  ephemeral_context.py # per-turn system-prompt builder (channel rules, founder tools, etc.)
  tool_registry.py     # register_leo_tools(registry) — wires all tools into the active framework
  tools/               # Leo's 8 tool-handler modules
    canvas.py          # update_quote, update_profile, set_drawer, create_page
    user_flow.py       # save_signup, whatsapp_handoff, start_job_intake
    delivery.py        # send_whatsapp, send_email, request_human
    legal.py           # search_spanish_law, get_boe_norm_text, search_eu_law
    pricing.py         # lookup_price, lookup_product, estimate_cost
    discovery.py       # find_houzz_contractors, search_fb_groups, enrich_contractor
    outreach.py        # outreach_contractor, batch_outreach, control_outreach, rank_job_responses
    admin.py           # founder_dashboard, propose_skill_change, skill_manage, create_job
  legal_tools.py       # Spanish-law API clients used by tools/legal.py
  tool_utils.py        # shared helpers for tool handlers
  peter_notify.py      # founder-direction notifications, skill proposals, email resend
  marketplace_config.json  # marketplace catalogue used by tools (Cal.com, etc.)
```

## Typical imports

```python
# From scope routes:
from agent import (
    run_leo_chat,                    # web + email chat entry
    whatsapp_reply,                  # WhatsApp-specific reply handler
    evict_stale_agents,              # background TTL eviction
    notify_peter_lead_submitted,     # founder notifications
    try_handle_founder_skill_reply,  # WA skill-proposal flow
)
```

## Framework abstraction

`agent.leo` is written against the `messaging.frameworks.AgentFramework`
Protocol. Today it uses the Hermes provider
(`messaging.frameworks.hermes`), but swapping to OpenAI Agents SDK,
LangGraph, or a custom in-house framework is:

1. Add a new adapter module alongside `messaging/frameworks/hermes.py`
   that implements the Protocol.
2. Flip an env var or inject the new framework here.

No caller-side churn — `routes/` only sees `run_leo_chat(...)` and
doesn't care which runtime is answering.

## Host-adapter injection

Leo's tool handlers call back into host routes/workflows via the
name-keyed `messaging.frameworks.adapters` registry so the
`packages/ → no host` rule stays intact. `apps/scope/product/backend/main.py`
registers the 15 adapters at startup (`job_inbox.*`, `workflows.*`,
`skill_manager.*`). Tool handlers lookup via `get_adapter("...")`.

## Tests

```
apps/scope/product/backend/tests/agent/
  conftest.py          # flushes the agent pool between tests
  test_agent_pool.py   # TTL eviction + conversation-key normalisation
```

Run via the scope tests conftest (sandbox backend on localhost:8000).
