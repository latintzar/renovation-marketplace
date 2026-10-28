# Stripe — Payment & Escrow Infrastructure

**Last updated:** 2026-04-14
**Status:** Fully integrated — Connect, Checkout, Transfers, Webhooks, Refunds
**Dashboard:** https://dashboard.stripe.com
**Test dashboard:** https://dashboard.stripe.com/test

---

## How Money Flows Through Leo

Three Stripe products work together to create the escrow system. This is the core of the business.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LEO PAYMENT FLOW                                 │
│                                                                         │
│  SETUP (once per contractor)                                            │
│  ┌──────────────────────────────────────────────────┐                   │
│  │  Stripe Connect — Contractor Onboarding           │                   │
│  │                                                    │                   │
│  │  POST /v1/stripe/create-account                    │                   │
│  │  → Creates Express Connected Account (ES, EUR)     │                   │
│  │  → Contractor completes KYC via hosted form         │                   │
│  │  → stripe_account_id stored on contractors table    │                   │
│  │  → Destination for all future transfers             │                   │
│  └──────────────────────────────────────────────────┘                   │
│                                                                         │
│  PHASE 1: Homeowner pays                                                │
│  ┌──────────────────────────────────────────────────┐                   │
│  │  Stripe Checkout — Full Amount Into Escrow         │                   │
│  │                                                    │                   │
│  │  POST /v1/payment/create-checkout                  │                   │
│  │  → Creates Checkout Session for full project total  │                   │
│  │  → Homeowner pays with card (4242... in test mode)  │                   │
│  │  → Money lands in LEO'S platform account            │                   │
│  │  → Webhook: checkout.session.completed              │                   │
│  │  → Quote marked payment_status = "paid"             │                   │
│  │  → This is ESCROW — Leo holds, not the contractor   │                   │
│  └──────────────────────────────────────────────────┘                   │
│                                                                         │
│  PHASE 2: Work happens, milestones release funds                        │
│  ┌──────────────────────────────────────────────────┐                   │
│  │  Stripe Transfer — Per-Milestone Release            │                   │
│  │                                                    │                   │
│  │  For each milestone:                                │                   │
│  │    1. Contractor uploads proof (photos + note)      │                   │
│  │       POST /v1/milestone/submit-proof               │                   │
│  │    2. Homeowner reviews and approves                │                   │
│  │       POST /v1/payment/release-milestone            │                   │
│  │    3. stripe.Transfer.create() moves funds          │                   │
│  │       Leo platform account → Contractor account     │                   │
│  │    4. Idempotency key prevents double-release       │                   │
│  │                                                    │                   │
│  │  When all milestones released → quote.status =      │                   │
│  │  "complete"                                         │                   │
│  └──────────────────────────────────────────────────┘                   │
│                                                                         │
│  VARIATION ORDERS (mid-project changes)                                 │
│  ┌──────────────────────────────────────────────────┐                   │
│  │  Contractor proposes extra work:                    │                   │
│  │    POST /v1/variation/create                        │                   │
│  │  Homeowner approves → new Stripe Checkout Session   │                   │
│  │    POST /v1/variation/approve                       │                   │
│  │  Homeowner declines → nothing happens               │                   │
│  │    POST /v1/variation/decline                       │                   │
│  └──────────────────────────────────────────────────┘                   │
│                                                                         │
│  CANCELLATION (before work starts)                                      │
│  ┌──────────────────────────────────────────────────┐                   │
│  │  POST /v1/job/cancel                                │                   │
│  │  → stripe.Refund.create() on payment_intent         │                   │
│  │  → Full refund to homeowner                         │                   │
│  │  → Only if no milestone has started                  │                   │
│  └──────────────────────────────────────────────────┘                   │
│                                                                         │
│  DISPUTES                                                               │
│  ┌──────────────────────────────────────────────────┐                   │
│  │  POST /v1/dispute/open                              │                   │
│  │  → Opens Chatwoot conversation with full context    │                   │
│  │  → Milestone status → "disputed"                    │                   │
│  │  → Funds remain in escrow until resolved            │                   │
│  │  → Aparejador reviews evidence and mediates         │                   │
│  └──────────────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## State Machines

### Quote (project-level)

```
draft → finalized → paid → in_progress → complete
                                       → cancelled (pre-work only, triggers refund)
                                       → disputed
```

### Milestone (per-milestone)

```
pending → proof_submitted → released
                          → disputed (homeowner flags issue)
```

### Payment Status

```
unpaid → pending (Checkout session created) → paid (webhook received)
                                             → refunded (cancellation)
```

## Who Does What

| Actor | Action | Endpoint | Stripe Product |
|-------|--------|----------|----------------|
| **Contractor** | Onboards (once) | `POST /v1/stripe/create-account` | Connect |
| **Contractor** | Completes KYC | Stripe-hosted onboarding URL | Connect |
| **Contractor** | Creates quote | `POST /v1/quote/finalize` | — |
| **Contractor** | Submits milestone proof | `POST /v1/milestone/submit-proof` | — |
| **Contractor** | Proposes variation | `POST /v1/variation/create` | — |
| **Homeowner** | Agrees to scope | `POST /v1/documents/{token}/record-consent` | — |
| **Homeowner** | Pays full amount | `POST /v1/payment/create-checkout` → Stripe Checkout | Checkout |
| **Homeowner** | Approves milestone | `POST /v1/payment/release-milestone` | Transfer |
| **Homeowner** | Approves variation | `POST /v1/variation/approve` → Stripe Checkout | Checkout |
| **Homeowner** | Declines variation | `POST /v1/variation/decline` | — |
| **Homeowner** | Opens dispute | `POST /v1/dispute/open` | — |
| **Either party** | Cancels job | `POST /v1/job/cancel` | Refund |
| **Homeowner** | Leaves review | `POST /v1/reviews/create` | — |
| **Stripe** | Payment completed | Webhook → `checkout.session.completed` | Webhook |
| **Stripe** | Account onboarded | Webhook → `account.updated` | Webhook |
| **Stripe** | Payment failed | Webhook → `payment_intent.payment_failed` | Webhook |

## Codebase

| File | What it does |
|------|-------------|
| `backend/routes/stripe_connect.py` | Connect account creation, onboarding links, status checks, webhooks |
| `backend/routes/payment.py` | Checkout session creation (homeowner pays into escrow) |
| `backend/routes/milestone.py` | Proof submission, milestone release (Transfer), variations, cancellation, reviews, notifications |
| `backend/routes/dispute.py` | Dispute opening, replies, Chatwoot integration |
| `backend/routes/messages.py` | In-project chat between homeowner and contractor |
| `backend/routes/documents.py` | Consent recording, agreement PDF, invoice PDF |
| `backend/shared/sandbox.py` | Resolves `X-Sandbox: true` → test keys vs live keys |

## Keys and Configuration

| Variable | Purpose | Format |
|---|---|---|
| `STRIPE_SECRET_KEY` | Live mode — real money | `sk_live_51SGKjz...` |
| `STRIPE_SECRET_KEY_TEST` | Test mode — real API calls, no real money | `sk_test_51SGKjz...` |
| `STRIPE_PUBLISHABLE_KEY` | Live frontend key | `pk_live_51SGKjz...` |
| `STRIPE_PUBLISHABLE_KEY_TEST` | Test frontend key | `pk_test_51SGKjz...` |
| `STRIPE_WEBHOOK_SECRET` | Live webhook signature verification | `whsec_...` |
| `STRIPE_WEBHOOK_SECRET_TEST` | Test webhook signature verification | `whsec_...` |

All keys are in `.env.local`. Both live and test keys come from the same Stripe account (same `acct_...`), toggled in the Stripe Dashboard top-right.

Sandbox mode (`X-Sandbox: true` header) selects the test key automatically via `backend/shared/sandbox.py`. Routes never branch on sandbox — they use `ctx.stripe_key`.

## Test Mode Behaviour

In Stripe test mode (`sk_test_` keys):

- `stripe.Account.create()` → real Express accounts (no actual KYC needed)
- `stripe.checkout.Session.create()` → real checkout sessions (test card: `4242 4242 4242 4242`)
- `stripe.Transfer.create()` → real transfers (no actual money moves)
- `stripe.Refund.create()` → real refunds
- All objects visible in the [test dashboard](https://dashboard.stripe.com/test)
- Connected accounts can be deleted via `stripe.Account.delete()`

Sandbox mode in Leo = Stripe test mode. The `X-Sandbox: true` header routes all Stripe calls to test keys. The backend tests use this exclusively.

## Webhook Events We Handle

| Event | Leo Action | Route |
|-------|-----------|-------|
| `checkout.session.completed` | Mark quote `payment_status = "paid"`, store `payment_intent_id`, update homeowner email | `stripe_connect.py` |
| `account.updated` | Mark contractor `stripe_onboarding_complete = true` if fully enabled | `stripe_connect.py` |
| `payment_intent.payment_failed` | Log failure, notify homeowner | `stripe_connect.py` |

## Planned but Not Yet Built

| Feature | Status | Notes |
|---------|--------|-------|
| 14-day auto-release | Not built | Trust strategy requires this (see `how-leo-builds-trust.md` Chapter 3) |
| Materials card (Wallester) | Not built | See `internal/service-integrations/wallester/` |
| Retention withholding (5-10% for jobs >€20k) | Not built | Trust strategy Chapter 2 |
| Payout monitoring (`payout.paid` / `payout.failed`) | Not built | Currently transfers happen but payout status is not tracked |
| `charge.dispute.created` webhook | Not built | Chargeback handling not implemented |

## Cost Model

| Fee | Amount |
|-----|--------|
| European card payments | 1.5% + €0.25 |
| Non-European cards | 2.5% + €0.25 |
| Connect platform fee per payout | 0.25% + €0.25 |
| Instant Payouts | 1% (min €0.50) |
| Standard Payouts (SEPA) | Free (2 business day) |
| Disputes (chargebacks) | €15 per dispute |

For a €5,000 project: Stripe takes ~€88, Leo's 5% fee is €250, net to Leo ~€162.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid API Key: sk_test_****_KEY` | Placeholder key in `.env.local` | Get real key from Stripe Dashboard (Test mode toggle) |
| `Contractor has no Stripe account` | `stripe_account_id` not on contractor row | Call `POST /v1/stripe/create-account` first |
| `Transfer failed: No such destination` | Express account deleted or wrong ID | Re-create via `create-account` |
| `transfers capability is inactive` | New Express account not yet activated | Complete onboarding flow or modify account in dashboard |
| `payment_status still unpaid after checkout` | Webhook not received | Check webhook endpoint is registered, check `STRIPE_WEBHOOK_SECRET_TEST` |
| `Cannot cancel — work has already started` | A milestone is past `pending` | Cancellation only allowed before any milestone has proof submitted |

## Related Documents

| Document | What it covers |
|----------|---------------|
| `.cursor/rules/stripe-configuration.mdc` | Agent guidance: key resolution, sandbox behaviour |
| `internal/strategy/how-leo-builds-trust.md` | Business logic: trust stack, escrow rationale, dispute ladder, 14-day auto-release |
| `scope-app/public/terms.html` | Legal terms describing the escrow system |
| `scope-app/public/agreement.html` | Public explanation of how payments/milestones work |
| `backend/tests/` | Integration tests using Stripe test mode |
