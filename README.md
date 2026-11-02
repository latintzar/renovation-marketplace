# Leo.casa

Renovation quotes, project chat and milestone payments

Leo.casa is a renovation marketplace for homeowners and contractors, with quotes, project chat and milestone payments.

[Website](https://leo.casa) · [Open demo](https://preview.atelierneyra.com/apps/renovation-marketplace/?local_role=contractor) · [Product tour](docs/product-tour.md) · [Documentation](https://docs.atelierneyra.com/renovation-marketplace/overview/)

![project messages beside the renovation quote canvas](https://atelierneyra.com/assets/product-motion-v5/renovation-marketplace-c423bf0a3793.jpg)

## Product areas

The quote, conversation, evidence of work and payments often live in different places. Both sides need a shared understanding of what was agreed, what changed and what is ready to pay.

| Feature | What it does |
| --- | --- |
| Quote canvas | Build priced phases beside the conversation, then directly edit the work, materials, durations, terms and totals. |
| Project chat | Discuss the quote and keep messages with the project. |
| Variations | Review changes to the agreed work and price. |
| Milestone review | Submit proof, then review the phase, contractor’s note, amount and payee together. |
| Stripe Connect | The source includes checkout, connected accounts, transfers, refunds, disputes and event handling. |

## Explore a renovation project

Open the contractor’s workspace to edit and save the existing quote, send a project message, submit phase proof or propose a change. Open the [homeowner’s workspace](https://preview.atelierneyra.com/apps/renovation-marketplace/my-projects?local_role=homeowner) to inspect that project, the submitted work and the agreement. The [product tour](docs/product-tour.md) follows both roles and links their screens to the backend and payment domain.

The native preview runs the original React and FastAPI app with private visitor records. Quote edits, messages, phase proof and variations persist. The original quote-building conversation is also available as a separately selected [scripted walkthrough](docs/historical-walkthroughs.md), showing the real quote canvas forming beside the chat with its vellum treatment. Live model work and Stripe payments use your configured services. [Reached stage and product context](docs/PROJECT.md).

## Run locally

Use Node 22.12+ and Python 3.12+:

```sh
git clone https://github.com/latintzar/renovation-marketplace.git
cd renovation-marketplace
make install
make doctor
make build
make dev
```

Open [the local app](http://127.0.0.1:18260/app/). Edit a saved quote, send project messages, submit phase proof and inspect the homeowner review. The original React pages and FastAPI functions use your own private SQLite workspace. [Native workspace guide](docs/native-workspace.md).

[Product tour](docs/product-tour.md) · [Getting started](docs/get-started.md) · [Setup and credentials](docs/setup.md) · [Workflows](docs/workflows.md) · [Design decisions](docs/design.md) · [Architecture](docs/architecture.md) · [Source reference](docs/reference.md)

## What is included

| Layer | Included work | Verification |
| --- | --- | --- |
| Product UI | Onboarding, chat, quote editor, original quote document, project phases, proof and release review | TypeScript/Vite build; actual backend edits, messages and phase proof |
| Payment domain | Financial arithmetic, Checkout, Connect, transfers, refunds, disputes, variations and event handling | Fake provider/repository tests |
| Backend source | Auth, records, quotes, project chat, milestone release, notifications, provider adapters and documents | Selected domain/security tests; live integrations use your configured services and their own tests |
| Local workspace | Visitor-scoped SQLite, private cookie identity and original API/domain functions | Persisted edits, project chat, phase proof, restart, isolation and request/service guards |
| Supabase developer database | Five core tables, party-scoped reads and server-owned writes | Explicitly reconstructed baseline; isolated PG/RLS/restart proof |
| Shared packages | Core, LLM, storage, messaging, voice, full-text, scraping, payments, brand, UI and TypeScript configuration | Source closure and navigation; optional provider requirements retain their own setup |

The original hosted database schema could not be exported from its inactive project. The new developer baseline covers the core quote/project/milestone path and is distinct from that historical schema. [Database guide](docs/database.md) identifies its tables, auth model, tested scope and the extension work still ahead.

The original full backend also expects a compatible Hermes runtime. Its historical vendor checkout was outside the retained tracked tree; this release identifies that dependency explicitly. The local first result uses the included original route/domain functions and a local storage/auth adapter. [Status and dependencies](docs/status.md).

## Continue the work

The [product tour](docs/product-tour.md) links each product area to its components and actions. The deeper workflows retain API records, state transitions and design rationale. [The agent skill](.agents/skills/install-renovation-marketplace/SKILL.md) follows the same setup path and keeps your credentials in a private file outside the checkout.

```sh
make test
make schema-check           # PostgreSQL 16 tools, unprivileged local user
```

[Contributing](docs/contributing.md)

Original code and authored samples use the [MIT licence](LICENSE). Optional dependencies, fonts and integration marks retain their [own terms](THIRD_PARTY.md). Historical operating records, customer uploads, credential-bearing notes and unverified photo/video assets remain outside this release.

[made by atelier neyra](https://atelierneyra.com)
