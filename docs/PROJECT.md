# Renovation quotes, project chat and milestone payments

Leo.casa is a renovation marketplace for homeowners and contractors. They agree on an editable quote, keep the conversation with the project, and review completed work before releasing each milestone through Stripe Connect.

The quote, conversation, evidence of work and payments often live in different places. Both sides need a shared understanding of what was agreed, what changed and what is ready to pay.

| Feature | What it does |
| --- | --- |
| Quote canvas | Edit phases, work, materials and totals in the offer itself. |
| Project chat | Discuss the quote and keep messages with the project. |
| Variations | Review changes to the agreed work and price. |
| Milestone review | Submit proof, review the phase and record acceptance. |
| Stripe Connect | The source includes checkout, connected accounts, transfers, refunds, disputes and event handling. |

## Workflow

Quote and conversation → Agreed phases → Work and proof → Homeowner review → Milestone payment

## Design decisions

- The quote acts as a shared canvas inside the conversation, so scope and discussion remain connected.
- Payments follow reviewed milestones, with financial events and variations modeled explicitly.

## Status and next steps

The native preview runs the original React and FastAPI app with a private visitor workspace. Quote edits, messages, proof and reviews persist. Real payment and provider operations are commissioned with your own accounts. Set up the database and Stripe Connect account, then complete account-specific payment and compliance acceptance.

Source: [docs/workflows.md](../docs/workflows.md), [docs/design.md](../docs/design.md), [docs/native-workspace.md](../docs/native-workspace.md), [docs/setup.md](../docs/setup.md).
