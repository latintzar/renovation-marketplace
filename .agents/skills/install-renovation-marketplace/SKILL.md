---
name: install-renovation-marketplace
description: Run or extend this renovation marketplace from source, configure recipient accounts privately, and follow its quote, project and milestone modules.
---

# Install the renovation marketplace

Read README, docs/native-workspace.md and docs/status.md first. Run make install, make doctor, make build, make dev for the normal React/FastAPI app. Confirm a quote edit survives reload and a project message is returned by the real API. The starter records are authored; the backend, persistence and permissions are real.

Read docs/workflows.md and docs/architecture.md when changing a module. The source reference maps actual functions and routes. Preserve the real HTTP boundary; local storage/auth adapt the original functions. Historical reels remain a separate explicit mode. Preserve the original components, product terminology and source provenance.

For connected setup, select the recipient's own company/account first. Read docs/database.md: the supplied migration is a new, tested five-table developer reconstruction, separate from the unrecovered historical schema. Use a fresh recipient project. Supabase owns auth.users and auth.uid; contractor role derives from the linked contractors.auth_user_id record.

Use tools/configure.py for hidden credential input into an owner-only file outside the checkout. from-local captures only local Supabase configuration; frontend exports only public client fields. Use tools/build.py with an explicit private env file for a connected client build. Keep server and provider secrets out of chat, Git and artifacts.

The full connected backend retains additional schema, runtime and provider acceptance work. Its original AWS billing resolver uses an explicit named account; its agent boundary expects a compatible Hermes runtime. Follow the exact feature names and source configuration reference instead of borrowing an ambient account.

Run make test for the selected provider-free source suites, and make schema-check with unprivileged PostgreSQL16 tools for the isolated developer core. Real messages, identity checks, imports, payments and publication follow the task's explicit authorization and the recipient's configured integrations.

For public local deployment, use tools/native.py build/start with matching --base-path and an exact --public-origin. Use fresh external state and the dedicated service template. Local mode discards ambient grants and holds provider/payment/delivery calls. Session cookies carry authority; public user IDs are display identities. Keep the supplied per-visitor bounds and original party checks active.
