# Service Integrations — Vendor API Explorations

This directory holds **exploratory learning documentation** for the third-party services Leo depends on. Each vendor gets a subdirectory with notes on how their API works, what's relevant to us, what we tested, and what we learned.

This is **not architecture documentation** (that lives in the protected READMEs like `backend/README.md`). This is also **not strategy** (that lives in `internal/strategy/`). This is the kind of reference a new engineer or CTO would read to answer: "How does this vendor work and what matters for Leo?"

---

## What belongs here

- API authentication patterns and credentials references
- Endpoint inventories with request/response shapes
- Live test results (curl commands, actual responses)
- Feature mapping: what the vendor offers vs. what Leo uses
- Cost models and pricing breakdowns
- Limitations and gaps (what the vendor does NOT do)
- SDK and integration options for our stack
- Gotchas, edge cases, and things that surprised us

## What does NOT belong here

- Integration code (that goes in `backend/` or `scope-app/`)
- Strategic decisions about *why* we chose a vendor (that goes in `internal/strategy/`)
- Raw research comparing vendors (that goes in `internal/field-notes/`)
- Architecture diagrams showing how the integration fits into Leo (that goes in architecture READMEs)

---

## Vendors

| Vendor | Directory | What Leo uses it for | Status |
|--------|-----------|---------------------|--------|
| **Didit** (didit.me) | [`didit/`](./didit/) | Identity verification, AML screening, NIF validation, company screening | Explored, API tested |
| **Stripe** | [`stripe/`](./stripe/) | Payments, escrow, Connect marketplace, milestone transfers, refunds | **Fully integrated** — Connect, Checkout, Transfer, Webhooks |
| **Supabase Auth** | [`supabase-auth/`](./supabase-auth/) | User authentication, session management, RLS | Database only — auth not yet used |
| **Wallester** | [`wallester/`](./wallester/) | Materials Card for contractor purchases (card issuing, MCC controls) | Explored, no API key yet |
| **Native App** (Expo) | [`native-app/`](./native-app/) | App store presence, biometrics, deep links, Stripe native SDK | Research complete, Expo recommended |

---

## Related

| Where | What |
|-------|------|
| `internal/strategy/` | Why we chose these vendors, how they fit the business model |
| `internal/field-notes/` | Chronological research sessions, vendor comparisons |
| `backend/README.md` | How integrations are wired into the codebase |
| `.cursor/rules/` | Agent guidance for working with these services |
| mem0 | Cross-session strategic memory (confirmed decisions, confirmed outcomes) |
