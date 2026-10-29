# Architecture

```mermaid
flowchart TB
  UI[React product and shared UI] --> Client[Typed API client]
  Client --> API[FastAPI routes]
  API --> Auth[Supabase JWT identity and project-party gates]
  API --> Records[Business records]
  Records --> DB[PostgreSQL through Supabase REST]
  API --> Pay[Shared payment domain and Stripe adapter]
  API --> Agent[Hermes boundary and product tools]
  Agent --> Model[Recipient model/proxy account]
  API --> Delivery[Configured messaging and document adapters]
```

## Browser

`apps/scope/product/web` contains the signed-in React product. `packages/ui` owns shared components and document types. `packages/brand` owns tokens, typography, logo assets and the original gradient renderer. The original Source Sans3 and Playfair Display fonts are self-hosted with their OFL notices.

The default local app calls the original FastAPI route functions and persists visitor-scoped SQLite records. Its private request-scoped REST transport and HTTP cookie auth are described in [Native workspace](native-workspace.md). The historical reel remains a separately selected presentation layer; local mode selects the normal backend.

## Server

`apps/scope/product/backend/routes` owns product HTTP actions. `records` owns durable application facts; the shared storage package provides generic memory/search engines. `state_machine.py` owns allowed phase/project transitions. The payment package provides typed operations, financial arithmetic, provider abstractions and fake repositories.

Some retained routes still use direct provider-adapter calls alongside shared helpers. The code reference shows the actual boundaries; this release preserves that migration state.

## Local runtime

The local factory mounts original route modules without starting provider/job lifecycles from the connected main. The core HTTP factory binds its internal SQLite transport through a context variable, keeping concurrent visitor requests separate. The original configured transport remains the default outside that context. Original project-party checks derive message senders and authorize phase proof. Monetary provider execution requires the connected runtime.

## Identity

The backend verifies Supabase identity. A claimed `contractors.auth_user_id` row identifies a contractor; another authenticated subject resolves as a homeowner. Project actions then check the assigned contractor or homeowner. [Database and auth](database.md).

## Agent runtime

The application-specific persona, tool handlers and orchestration live in `backend/agent`. `packages/messaging/frameworks/hermes.py` is the upstream-runtime boundary. The historical external vendor checkout and its exact pin were not retained in this tracked source. The full connected agent needs a compatible recipient installation and a separate acceptance run.

## Source navigation

[Reference](reference.md) maps real modules, functions, routes and configuration names. The original application source remains under its existing directory names, preserving useful relationships for contributors.
