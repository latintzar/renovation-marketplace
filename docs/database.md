# Database and auth

## Developer core

[`0001_developer_core.sql`](../supabase/migrations/0001_developer_core.sql) is a new developer baseline reconstructed from the retained route contracts. It is separate from the unrecovered historical production schema.

| Table | Purpose |
| --- | --- |
| `contractors` | Auth-user binding, profile/dossier/canvas and Stripe destination state |
| `quotes` | Shared quote/project record, ordered phases, amounts and payment state |
| `milestone_updates` | Phase evidence, note, review state and transfer receipt identifier |
| `job_messages` | Project conversation, with the verified sender stored by the server |
| `notifications` | Recipient, project, phase and read state |

`quotes.milestones` is an ordered JSON array. Amounts stored as cents use integer columns. The original API uses `scope_token` in proof, chat and notification tables; that legacy column name is preserved.

## Recipient setup

The included local configuration selects PostgreSQL 17. Use a fresh recipient Supabase project with Docker and the [official CLI](https://supabase.com/docs/guides/local-development/cli/getting-started).

```sh
supabase start
supabase db reset
python3 tools/configure.py from-local
python3 tools/configure.py frontend
```

The helper captures the local API URL, anon key and service-role key into an owner-only file outside the checkout. It prints names and paths. The frontend export includes public client fields only.

For an owned hosted project, use the CLI's normal project-link and migration workflow, then save the recipient's credentials through `tools/configure.py init --features auth`. The original project is outside this setup path.

## Auth structure

Supabase manages `auth.users`, sessions, OAuth and `auth.uid()`. This migration references that managed user ID; it creates only the application tables. The application derives contractor status from `contractors.auth_user_id`. Standard email/Google callbacks return to `/app/auth/callback` on the recipient's app origin.

For local auth, configure site URL `http://127.0.0.1:18260/app/`. Add the recipient's deployed app origin when enabling hosted sign-in. Google OAuth uses that Supabase project's provider configuration and callback URL.

## RLS

The new baseline permits authenticated parties to read their own contractor/project records. Proof and chat inherit project visibility; notifications are recipient-scoped. Application clients read those records while authoritative mutations pass through the authenticated backend and its server key.

The isolated test checks homeowner/contractor visibility, stranger and anonymous denial, direct client-write denial, proof-index bounds and persistence across a database restart:

```sh
make schema-check
```

[Exact result](../provenance/schema-contract.json). This uses PostgreSQL 16 and synthetic managed-auth stubs over a private Unix socket; it is a core SQL contract check, separate from full Supabase/PostgREST/provider acceptance.

## Historical recovery

The retained `schema_leo_scope.sql` defines six acquisition/WhatsApp tables and is a historical supplement. The full original marketplace DDL/RLS was absent from the retained source and the March archive. Read-only metadata recovery authenticated to the project used by the deployed app bundle; the database was inactive on 28 October 2026. It was left unchanged and customer rows were not read.

The developer core covers quote/project/milestone, chat and notification records. Profiles beyond the contractor record, discovery/outreach, document snapshots, consent, variation/dispute and other extension schemas retain separate reconstruction or recovery work. The historical supplement is kept as reference rather than automatically applied to a recipient's project.

Attachment and PDF storage have their own adapters. The original document facade uses S3 plus document records; this core migration activates the core business tables.
