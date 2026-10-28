# packages/messaging

Shared capability: **messaging** — channel-aware transport, media enrichment,
verification, and an agent-framework adapter protocol. Any app that talks to
humans via WhatsApp, email, or web can depend on this package.

## What's here

```
src/messaging/
  channel.py         # Channel, LeoMessage, MediaAttachment, *_CAPABILITIES
  comms.py           # notify(), NotifyRequest, NotifyResult
  constants.py       # META_API_BASE, META_API_VERSION
  email/             # Resend + raw email transport (send_email, send_email_resend)
  whatsapp/          # Meta Cloud API send + storage + templates
  media/             # enrich_message, parse_media (audio→transcript, PDF→text, URL→page)
  verification/      # NIF/VIES/REA + social-proof checks (ProfileResult, TrustSignals, …)
  frameworks/        # AgentFramework Protocol + host-adapter registry + hermes provider
```

## What's **not** here (and why)

* **Leo's agent runtime / tools / persona** — these are scope-app policy.
  They live in `apps/scope/product/backend/agent/` (moved there in Phase 5 Wave 6).
  A future app can run its own agent, pick a different framework provider,
  or skip agents entirely without touching this package.
* **Dossier / contractor records** — scope-specific business records, live in
  `apps/scope/product/backend/records/`.

## Canonical imports

```python
from messaging import (
    # Channel abstraction
    Channel, ChannelCapabilities, LeoMessage, MediaAttachment,
    WEB_CAPABILITIES, WHATSAPP_CAPABILITIES, EMAIL_CAPABILITIES,

    # Transport (async)
    send_wa_message, send_email, notify,
    NotifyRequest, NotifyResult, SendResult,

    # Media gateway (audio/pdf/docx/url extraction)
    enrich_message, parse_media, parse_url, transcribe_file,

    # Verification (NIF/VIES/REA + social proof)
    ProfileResult, TrustSignals, Credential,
    validate_nif, check_vies, check_rea,
    run_verification_checks, run_social_proof_checks,

    # Agent framework protocol + DI registry
    AgentFramework, register_host_adapter, get_adapter, HostAdapterMissing,
)
```

## Agent-framework protocol

`messaging/frameworks/` answers the question *"how does a host app wire up an
AI agent behind this messaging layer?"* without hard-coding which framework.

* `protocol.py` — `AgentFramework` Protocol (name, vendor_path, is_available()).
* `adapters.py` — name-keyed registry (`register_host_adapter`, `get_adapter`)
  so agent tool handlers in app code can call back into host routes/workflows
  without breaking the `packages/ → no-host` direction.
* `hermes.py` — first concrete provider: wraps Hermes's `AIAgent`, `SessionDB`,
  `tools.registry.registry`, and `create_custom_toolset` behind a stable
  surface.

To add a new provider (OpenAI Agents SDK, LangGraph, in-house, …), drop a new
module alongside `hermes.py` that implements the `AgentFramework` Protocol.
No other code in `messaging/` needs to change.

## Boundaries (invariants)

* Audio is never decoded inside `messaging` — `packages/voice/` owns codecs.
* Route handlers are never imported from here — host adapters come in via
  `register_host_adapter()`.
* `routes/` → `packages/messaging/` is the **only** allowed arrow.

## Layer rule

`messaging` may import from: `core`, `llm`, `storage`, `fulltext`, `voice`,
`scraping`, `payments`. It may **not** import from any app, route, or
workflow. Enforced by `scripts/checks/layer_rule.py`. (Document rendering
moved to `apps/scope/product/backend/documents/` in Phase 5 Wave 8 — it rejoins
`packages/` only when a second app needs PDF/consent rendering.)

## Changelog (recent)

* **Phase 5 Wave 6** — split into capability vs. scope-policy. Leo's agent
  runtime, tools, persona, and founder-notify code moved to
  `apps/scope/product/backend/agent/`. `messaging/dossier/` deleted (scope records
  live in `apps/scope/product/backend/records/`). New `messaging/frameworks/` lifts
  the hard-coded "Hermes is the one true framework" assumption.
