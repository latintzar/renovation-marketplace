# Native local workspace

Date: 2026-10-29. This release adaptation sits alongside the original connected backend.

## Original product

Leo.casa combines a conversational quote builder, an editable quote document, contractor jobs, project chat, phase evidence and homeowner review. The retained QuoteCanvas owns its layout and calculations. Original route modules and shared financial/state functions own the corresponding backend actions.

## Local storage and authority

The retained Supabase schema is incomplete and the historical Hermes runtime needs separate compatibility work. A new recipient-owned SQLite adapter supplies the row contract used by the original route functions. It binds to the current request through the existing HTTP factory. Its internal ASGI endpoint stays inside the Python process.

Each browser receives an opaque HttpOnly cookie; only its SHA-256 digest is stored. Every SQL operation includes that visitor scope. A workspace contains two authored participants, so its contractor/homeowner entry points can inspect both sides of the same project. SameSite=Lax preserves the workspace when returning through a GitHub or documentation link. State-changing API requests additionally validate Origin and Sec-Fetch-Site.

The local launcher selects its own configuration directories, discards ambient provider variables and enables the loopback socket fence. The service unit adds an operating-system network boundary. Provider/payment admission happens before route execution. The saved project is an authored state for product inspection; Stripe creates real payment records only in a separately configured installation.

## Compatibility repairs

The native web and backend had evolved across field names: scope_data/quote_data, scope/quote and scopes/quotes. The routes accept the two input names and expose compatible output aliases. Updates recalculate financial fields through the original shared finance function. Paid projects use variations for changes.

Quote writes now require a verified contractor and compare that identity with the quote owner. The change-order form converts euros to cents once; its prior combination of React Hook Form options sent a displayed 200 euros as 200 cents. The legacy proof route validates the phase index before storing evidence. These repairs apply to the shared product source.

## Reproduction

The normal React routes run against actual HTTP handlers and persisted SQLite records. The same build/start path serves a clone and the hosted workspace. Integration tests check restart, sender authority, quote ownership, isolation and service admission. Playwright exercises saved edits, phase proof, euro-denominated variations, project messages, homeowner review and the original HTML agreement at desktop and mobile sizes.

[made by atelier neyra](https://atelierneyra.com)
