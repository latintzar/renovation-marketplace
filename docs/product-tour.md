# Product tour

Leo.casa is a renovation marketplace for homeowners and contractors. They agree on an editable quote, keep the project conversation together and review completed work before releasing each phase’s payment through Stripe Connect.

[Open contractor demo](https://preview.atelierneyra.com/apps/renovation-marketplace/?local_role=contractor) · [Open homeowner demo](https://preview.atelierneyra.com/apps/renovation-marketplace/my-projects?local_role=homeowner) · [Run locally](../README.md#run-locally)

## From quote to project review

1. Open the contractor’s **My jobs**. The native workspace contains an editable saved quote and a separate authored project whose first phase is ready for review.
2. Open the saved quote, choose **Edit**, adjust a phase or its duration, then **Save** and reload. The original quote canvas shows the phases, materials, IVA, fee and payment schedule. The saved record and phase amounts stay in step with the document.
3. Open the project chat and send a message. It remains attached to that project when you reload. From **My jobs**, choose **Submit proof**, add a note and **Send to homeowner** to record work against a phase.
4. Switch to the homeowner entry, open the project and choose **Review phase 1**. The review sheet brings the phase description, evidence, contractor’s note, amount and payee into one place. **View agreement** opens the shared construction agreement.
5. For a change in scope, return to the contractor entry and choose **+ Change**. Give the variation a title, reason and price, then **Send to homeowner**. The homeowner reviews the separate change order with its extra amount and can decline it or follow the configured approval/payment path.

The role links select the two participants within your own private visitor workspace. The saved quote and project are authored fixtures; the project’s paid status represents the starting state for exploring proof/review. Local mode persists edits, chat, proof and variations. Checkout, releases and model execution use your separately configured services. [Native workspace](native-workspace.md) describes the actual records, session and route boundaries.

## The quote forming beside the chat

The quote builder places the conversation and editable document side by side on desktop; its phone preview opens the same quote. As structured phase updates arrive, the document gains priced work, durations, materials and tax. The original [vellum treatment](../packages/brand/src/brand/translucency/vellum.py) softens the forming document with a 7px blur and 12% cream film. Once the scope is ready, the contractor reviews and edits it explicitly.

To explore that progression with the actual components and authored replies, run the [original scripted walkthrough](historical-walkthroughs.md). Its `set-milestones` sequence builds one phase, three priced phases, then materials and IVA. The live agent path uses the retained Hermes/tool integration under your own configuration. The native saved-quote editor is the immediate local reuse path.

## Product areas and source

| Area | Actions and results | Source |
| --- | --- | --- |
| Quote builder and canvas | Form priced phases beside chat; inspect, directly edit and save the agreement. | [FirstQuote.tsx](../apps/scope/product/web/src/pages/FirstQuote.tsx), [EditableQuoteCanvas.tsx](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx), [QuoteCanvas.tsx](../packages/ui/src/QuoteCanvas.tsx), [canvas API](../apps/scope/product/backend/routes/canvas.py). |
| Project conversation | Keep messages with the project and verified participant identity. | [JobChat.tsx](../apps/scope/product/web/src/pages/JobChat.tsx), [messages.py](../apps/scope/product/backend/routes/messages.py), [project_access.py](../apps/scope/product/backend/project_access.py). |
| Work and phase review | Submit evidence and inspect the phase, note, amount and payee before authorizing release. | [Dashboard.tsx](../apps/scope/product/web/src/pages/Dashboard.tsx), [MilestoneDetailSheet.tsx](../apps/scope/product/web/src/components/project/MilestoneDetailSheet.tsx), [milestones.py](../apps/scope/product/backend/routes/milestones.py). |
| Variations | Propose an explicit scope/price change, review it separately, approve and pay or decline. | [VariationCreateSheet.tsx](../apps/scope/product/web/src/components/dashboard/VariationCreateSheet.tsx), [VariationDetailSheet.tsx](../apps/scope/product/web/src/components/project/VariationDetailSheet.tsx), [variations.py](../apps/scope/product/backend/routes/variations.py). |
| Payments and state | Calculate quote totals, create Checkout, onboard connected accounts and release funds per phase. | [finance.py](../packages/payments/src/payments/finance.py), [payment.py](../apps/scope/product/backend/routes/payment.py), [stripe_connect.py](../apps/scope/product/backend/routes/stripe_connect.py), [state_machine.py](../apps/scope/product/backend/state_machine.py). |
| Local records and services | Persist each visitor’s workspace through the original route functions; select external services explicitly. | [local server](../apps/scope/product/backend/local_mode/server.py), [store.py](../apps/scope/product/backend/local_mode/store.py), [seed.py](../apps/scope/product/backend/local_mode/seed.py), [setup](setup.md). |

## UX decisions

**Conversation supplies context; the canvas carries the agreement.** Founder discovery found descriptions, prices and previous-work photos already moving through WhatsApp. Keeping the quote beside the discussion makes the agreed work inspectable. Direct edits have their own Save/Cancel state, and incoming agent updates wait while the contractor is editing.

**A phase is the unit of review.** Evidence, note, payee and amount stay together at the release decision. The server verifies the project participant, paid state and allowed phase transition before a configured transfer. A stable quote/phase idempotency key accompanies that transfer.

**Changed work gets a separate decision.** A variation keeps its reason, evidence and additional price visible. In the configured path, approval creates a separate Stripe Checkout session; decline records the decision and notifies the contractor.

[Design decisions](design.md) retain the discovery and canvas-restoration evidence. [Workflows](workflows.md) follow the corresponding quote, chat, milestone and notification actions.

## Payments and reached stage

The source payment flow takes the homeowner’s payment through Stripe Checkout into the platform account and transfers phase amounts to the contractor’s connected account when released. It also retains materials-upfront handling, refunds, disputes and Stripe event processing. Its financial/state-machine tests use fake provider/repository transports. Settled payments, account onboarding and the applicable payment/compliance setup require testing with your own Stripe Connect account.

The local app uses the original React pages and FastAPI functions with visitor-scoped SQLite. The reconstructed Supabase developer baseline is a separate five-table starting point; it differs from the historical inactive database and has documented schema extensions. The full connected agent also requires a compatible Hermes runtime. [Status](status.md), [database](database.md) and [setup](setup.md) record those continuation boundaries.

## Continue from here

- [Getting started](get-started.md) and [native workspace](native-workspace.md) for both role entries, runnable local commands and stored data.
- [Setup and private credentials](setup.md), [database](database.md) and [install skill](../.agents/skills/install-renovation-marketplace/SKILL.md).
- [Architecture](architecture.md), [workflows](workflows.md), [design decisions](design.md) and [source reference](reference.md).
- [Historical walkthroughs](historical-walkthroughs.md) for the complete quote-forming interface sequence.
- [Third-party notices](../THIRD_PARTY.md) and [release status](status.md) for reuse and accepted scope.

A useful continuation is to connect your database and Stripe Connect test account, then verify one complete quote → Checkout → proof → authorized milestone release before using real payments.
