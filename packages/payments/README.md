# `@scope/payments`

**Leo's Stripe-owning layer.** Every Stripe SDK call in the backend flows through
this package post-migration. Nothing else imports `stripe` directly.

- Sandbox + credential resolution (`sandbox`)
- Per-request Stripe client factory — race-safe (`client`, D1)
- Quote financials — IVA-aware totals, milestones tracking (`finance`)
- Homeowner escrow checkout — Stripe Checkout Sessions (`checkout`)
- Contractor Stripe Express onboarding (`connect`)
- Milestone transfers — release escrowed funds to contractor (`milestones`)
- Variation-order checkout + lifecycle (`variations`)
- Refunds — project cancellation (`refunds`)
- Dispute-state transitions — milestone status + DB (`disputes`)
- Stripe webhook verification + handlers (`webhooks`)
- Supabase persistence helpers (`repo`)
- Payments-specific error hierarchy (`errors`)

## Layout

```
packages/payments/
  src/payments/
    __init__.py        — curated 54-symbol public API
    sandbox.py         — SandboxContext, resolve_sandbox, resolve_for_quote
    client.py          — StripeClient (Protocol), get_stripe_client
    errors.py          — 14 typed error classes (AppError-compatible)
    finance.py         — compute_quote_financials, parse_euro_string
    repo.py            — PaymentsRepo + 5 row dataclasses
    checkout.py        — create_session (escrow), maybe_reuse_open_session
    connect.py         — create_account, create_onboarding_link, get_account_status
    milestones.py      — submit_proof, release (with idempotency reconciliation)
    variations.py      — create_variation, approve_variation, decline_variation
    refunds.py         — cancel_project
    disputes.py        — open_dispute_state, list_disputes
    webhooks.py        — verify_stripe_event (tri-state), dispatch_event, 5 handlers
  tests/               — unit tests using a FakeStripeClient
```

## Allowed dependencies

- `core` — `core.db.Supabase`, `core.errors.AppError`
- `domain` — `domain.money.to_cents` for rounding
- `stripe>=7` — the SDK (uses `stripe.StripeClient`, **not** `stripe.api_key`)
- `httpx>=0.27`
- `fastapi>=0.110` — only for the `Header` dep resolver in `sandbox.py`

Forbidden: `messaging`, any `apps/*`, any `routes/*`, `config.settings`,
`leo_agent/*`.

## Key invariants

### D1 — No module-global Stripe state

`stripe.api_key = X` is a **process-global** assignment that races under async
concurrency (request A sets test, request B sets live, A's next call uses live).
This package instead builds a fresh `stripe.StripeClient(api_key=...)` per
request via `get_stripe_client(ctx)`. Every function in the package takes a
`StripeClient` parameter.

### D2 — ROUND_HALF_UP everywhere

Financial rounding uses `domain.money.to_cents` (ROUND_HALF_UP, Spanish tax
convention). Legacy quotes on exact-`.5`-cent boundaries may differ by ±1 cent
from historical float-round() values. Documented, accepted.

### D5 — Escrow model

`stripe.checkout.Session.create` does **not** use
`payment_intent_data.transfer_data.destination`. Homeowner funds hold in
Leo's platform account. Per-milestone `stripe.transfers.create` moves funds
to the contractor's Connect account when the homeowner releases.

### D9 — Idempotency reconciliation

Release key: `payments:release:{token}:{idx}`. Refund key:
`payments:refund:{token}`. On `IdempotencyError` the real `transfer_id` or
`refund_id` is recovered via the Stripe list API — callers never receive the
`'idempotent-duplicate'` sentinel string.

### D12 — Column rename at boundary

Internal symbol: `leo_fee_cents`. DB column: `stripe_fee_cents`. The
`PaymentsRepo.patch_quote` helper renames at the boundary so no caller sees
the legacy name.

### Sandbox

`X-Sandbox: true` → test Stripe keys. `X-Allow-WhatsApp: true` → real WhatsApp
even under sandbox (notification-test escape hatch). The two are orthogonal.
`resolve_for_quote` promotes a quote-local `is_sandbox=true` to a request-local
test key for downstream calls (milestones, disputes).

## Stripe client injection

The `StripeClient` Protocol is runtime-checkable. Tests inject a fake with the
same namespace shape (`client.checkout.sessions.create(...)`, etc.). Production
uses `stripe.StripeClient` (version ≥ 7.x).

## Testing

```bash
cd packages/payments
python -m pytest tests/
```

Unit tests cover every public function. There are **no network or Stripe API
calls at test time** — a `FakeStripeClient` implements the `StripeClient`
Protocol and an in-memory Supabase stub backs the repo tests. Webhook signature
verification is exercised via `stripe.Webhook.construct_event` with a generated
test signature (the one place `stripe` needs to be importable in tests).

## Notes

- `stripe.error.IdempotencyError` is mapped to an internal sentinel in
  `milestones.release` and `refunds.cancel_project`, then reconciled via
  `transfers.list` / `refunds.list`.
- `webhooks.verify_stripe_event` tri-state verifies against `live_secret`
  first, then `test_secret`. Both fail → `InvalidWebhookSignature`.
- The package deliberately does **not** emit notifications. `submit_proof`,
  `release`, `cancel_project`, `open_dispute_state` return rich dataclasses
  carrying every datum (`contractor_name`, `homeowner_phone`, etc.) that a
  messaging layer needs — but `messaging.notify` is the one who fans out.
