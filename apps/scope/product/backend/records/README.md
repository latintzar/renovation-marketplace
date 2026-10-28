# `records` — scope-app persistent business records

Every durable fact specific to the scope app's business domain: **leads**, **proposals**, **contractors**, **messages**. Split from `packages/storage/` in Phase 5 Wave 3 so the shared `storage` package stays a pure engine (mem0 + pgvector) with no scope-schema leakage.

## What's here

| Submodule | Supabase tables | Purpose |
|---|---|---|
| `records.leads` | `cs_leads`, `early_access_signups` | Homeowner / professional signup writes, with dual-table fallback and `---LEO_STRUCTURED---` marker for brief/profile blobs. |
| `records.proposals` | `agent_skill_proposals` | Leo's self-improvement proposal log + founder-reply parsing. |
| `records.dossier` | `contractors` | Per-contractor dossier (provenance, sources, trust signals) + canvas recomputation for shareable URLs. |
| `records.conversations` | `whatsapp_messages`, `web_messages` | Per-user, per-channel message log. Paginated reads, recency-weighted summarization. |
| `records.types` | — | Dataclasses: `Lead`, `Proposal`, `Contractor`, `Message`, `LeadSaveResult`, `ProposalResult`, `SkillReplyIntent`. |

## Pairing with storage engines

`records` describes *what* scope persists. `packages/storage` provides the generic engines — `storage.remember` / `storage.recall` (mem0) and `storage.index_text` / `storage.search_similar` (pgvector). Scope code typically imports both:

```python
from records import save_lead, add_message, Lead   # scope schemas
from storage import remember, recall               # generic engines
```

The scope-vanishes test: if the scope app were deleted tomorrow, `records` goes with it, but `packages/storage` still works for any other Leo app.

## Use

```python
from records import (
    # Leads
    save_lead, patch_lead_structured, get_lead_by_phone,
    Lead, LeadSaveResult,
    # Proposals
    store_proposal, fetch_pending_proposals, resolve_proposal,
    parse_founder_skill_reply, proposal_short_id,
    Proposal, ProposalResult, SkillReplyIntent,
    # Dossier
    get_or_create_contractor, add_contractor_source, update_trust_signals,
    save_and_recompute_canvas, recompute_canvas,
    Contractor,
    # Conversations
    add_message, get_messages, get_recent_window, summarize_recent,
    Message,
)
```

## Testing

```bash
cd /root/leo
PYTHONPATH="apps/scope/product/backend:packages/core/src:packages/llm/src:packages/storage/src" \
    /root/leo/apps/scope/product/backend/venv/bin/python3 \
    -m pytest apps/scope/product/backend/tests/records/
```

## Open tech-debt: dossier duplication

A parallel dossier implementation lives at `packages/messaging/src/messaging/dossier/contractor.py` — current scope routes import from the messaging copy, not from here. Phase 5 Wave 6 (messaging split) will consolidate them. Until then, `records.dossier` is preserved as the capability-layer version for forward compatibility, and both read/write to the same `contractors` table without contention because writes funnel through messaging.

## Changelog

- **Phase 5 Wave 3**: created. `leads`, `proposals`, `dossier`, `conversations`, and scope-specific types moved here from `packages/storage/` to enforce the capability-vs-configuration rule (shared engines stay in `packages/`; scope-app schemas live in `apps/scope/product/backend/`).
