# Supabase — Leo Scope (current)

- **Schema:** `schema_leo_scope.sql` — `cs_leads`, `landing_leads`, `early_access_signups`, `whatsapp_messages`, `whatsapp_user_profiles`, `agent_skill_proposals`, RPC `copilot_conversations`.
- **Apply:** `python3 tools/supabase_apply_schema.py` (needs `SUPABASE_ACCESS_TOKEN` in `.env.local`).
- **Legacy:** Leo Estimate pipeline tables (`pipeline_jobs`, etc.) stay on the old account; not created here.
