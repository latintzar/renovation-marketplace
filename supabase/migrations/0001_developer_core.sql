-- Developer core reconstructed from the released HTTP route contracts.
-- Authored 2026-10-28. This is separate from the unrecovered historical schema.
-- Target: a fresh recipient Supabase project. Auth/roles are managed by Supabase.
BEGIN;
CREATE TABLE public.contractors (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 auth_user_id uuid UNIQUE REFERENCES auth.users(id) ON DELETE SET NULL,
 token text UNIQUE DEFAULT gen_random_uuid()::text,
 slug text UNIQUE,
 name text NOT NULL DEFAULT '', business_name text NOT NULL DEFAULT '',
 email text, phone text, trade text, location text,
 provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
 dossier jsonb NOT NULL DEFAULT '{}'::jsonb,
 canvas jsonb NOT NULL DEFAULT '{}'::jsonb,
 stripe_account_id text, stripe_onboarding_complete boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.quotes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 token text NOT NULL UNIQUE DEFAULT gen_random_uuid()::text,
 contractor_id uuid NOT NULL REFERENCES public.contractors(id),
 homeowner_auth_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
 homeowner_email text, homeowner_phone text,
 quote_data jsonb NOT NULL DEFAULT '{}'::jsonb,
 milestones jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(milestones)='array'),
 amount_total_cents bigint NOT NULL DEFAULT 0 CHECK (amount_total_cents>=0),
 status text NOT NULL DEFAULT 'draft', payment_status text NOT NULL DEFAULT 'unpaid',
 checkout_session_id text, payment_intent_id text,
 is_sandbox boolean NOT NULL DEFAULT true,
 consent_id uuid, homeowner_consent_id uuid,
 finalized_at timestamptz, paid_at timestamptz, completed_at timestamptz,
 cancelled_at timestamptz, cancellation_reason text,
 refund_id text, refunded_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.milestone_updates (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 scope_token text NOT NULL REFERENCES public.quotes(token) ON DELETE CASCADE,
 milestone_index integer NOT NULL CHECK (milestone_index>=0),
 photos text[] NOT NULL DEFAULT '{}', voice_url text, note text,
 status text NOT NULL DEFAULT 'proof_submitted',
 stripe_transfer_id text, released_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.job_messages (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 scope_token text NOT NULL REFERENCES public.quotes(token) ON DELETE CASCADE,
 sender_role text NOT NULL CHECK (sender_role IN ('contractor','homeowner')),
 sender_id text NOT NULL, body text NOT NULL CHECK (length(btrim(body))>0),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.notifications (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id text NOT NULL, scope_token text REFERENCES public.quotes(token) ON DELETE CASCADE,
 type text NOT NULL, milestone_index integer CHECK (milestone_index>=0),
 read boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX milestone_updates_project_idx ON public.milestone_updates(scope_token,milestone_index,created_at DESC);
CREATE INDEX quotes_contractor_idx ON public.quotes(contractor_id);
CREATE INDEX quotes_homeowner_idx ON public.quotes(homeowner_auth_id);
CREATE INDEX job_messages_project_created_idx ON public.job_messages(scope_token,created_at);
CREATE INDEX notifications_user_created_idx ON public.notifications(user_id,created_at DESC);
ALTER TABLE public.contractors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.milestone_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY developer_contractor_read ON public.contractors FOR SELECT TO authenticated USING (auth_user_id=auth.uid());
CREATE POLICY developer_quote_read ON public.quotes FOR SELECT TO authenticated USING (
 homeowner_auth_id=auth.uid() OR contractor_id IN (SELECT c.id FROM public.contractors AS c WHERE c.auth_user_id=auth.uid())
);
CREATE POLICY developer_proof_read ON public.milestone_updates FOR SELECT TO authenticated USING (
 scope_token IN (SELECT q.token FROM public.quotes AS q)
);
CREATE POLICY developer_message_read ON public.job_messages FOR SELECT TO authenticated USING (
 scope_token IN (SELECT q.token FROM public.quotes AS q)
);
CREATE POLICY developer_notification_read ON public.notifications FOR SELECT TO authenticated USING (
 user_id=auth.uid()::text OR user_id IN (SELECT c.id::text FROM public.contractors AS c WHERE c.auth_user_id=auth.uid())
);
REVOKE ALL ON public.contractors,public.quotes,public.milestone_updates,public.job_messages,public.notifications FROM PUBLIC,anon,authenticated;
GRANT USAGE ON SCHEMA public TO authenticated,service_role;
GRANT SELECT ON public.contractors,public.quotes,public.milestone_updates,public.job_messages,public.notifications TO authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.contractors,public.quotes,public.milestone_updates,public.job_messages,public.notifications TO service_role;
COMMIT;
