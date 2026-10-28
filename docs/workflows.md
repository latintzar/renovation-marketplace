# Workflows

## Brief and quote

A homeowner describes the work in conversation. The contractor's quote carries phases, amounts, durations and terms beside that conversation. The canvas remains editable before sharing.

```mermaid
flowchart LR
  Brief[Conversation] --> Draft[Priced phases]
  Draft --> Review[Contractor review and edits]
  Review --> Quote[Shared quote record]
  Quote --> Checkout[Stripe Checkout]
```

The scripted entry uses the original FirstQuote page, useChat and quote components. Connected generation uses the retained agent/tool boundary; the script supplies authored replies through the same typed API client.

Sources: [FirstQuote](../apps/scope/product/web/src/pages/FirstQuote.tsx), [editable canvas](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx), [original restored document](../packages/ui/src/QuoteCanvas.tsx), [finance](../packages/payments/src/payments/finance.py).

## Milestone review

A contractor submits evidence against a phase. The homeowner sees the work, note, amount and payee together before confirming release.

```mermaid
flowchart LR
  Proof[Contractor proof] --> Record[Milestone update]
  Record --> Review[Homeowner review]
  Review --> Gate[Identity and paid-state checks]
  Gate --> Transfer[Stripe transfer with idempotency key]
  Transfer --> State[Released phase and notification]
```

The API verifies the caller and assigned project, checks the paid state and phase transition, and uses a stable quote/phase idempotency key. This source derivative also bounds negative phase indexes before effects.

Sources: [milestone API](../apps/scope/product/backend/routes/milestones.py), [state machine](../apps/scope/product/backend/state_machine.py), [review sheet](../apps/scope/product/web/src/components/project/MilestoneDetailSheet.tsx).

![The original milestone review sheet](images/review.png)

## Project chat

Messages remain attached to the paid project. The source derivative resolves the sender from verified identity and checks project membership for reads and writes. The client-supplied legacy identity fields remain accepted for compatibility; the server determines the recorded participant.

Sources: [chat API](../apps/scope/product/backend/routes/messages.py), [party matching](../apps/scope/product/backend/project_access.py), [JobChat](../apps/scope/product/web/src/pages/JobChat.tsx).

## Notifications

A notification identifies the recipient, project and phase. Mark-read updates include the current recipient filter. WhatsApp delivery is a separate configured transport; sandbox mode suppresses that delivery.

Source: [notifications](../apps/scope/product/backend/routes/notifications.py).
