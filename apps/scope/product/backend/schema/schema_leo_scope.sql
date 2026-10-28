-- Leo Scope (current product) — minimal tables for onboarding, WhatsApp, leads, skill proposals.
-- No Leo Estimate pipeline_jobs / pipeline_runs (legacy; other account).
-- Apply via Supabase SQL Editor or: python3 tools/supabase_apply_schema.py

create extension if not exists "pgcrypto";

-- Leads from web chat / signups / referrals
create table if not exists public.cs_leads (
    id uuid primary key default gen_random_uuid(),
    name text,
    whatsapp text,
    location text,
    source text,
    audience text default 'homeowner',
    chat_summary text,
    chat_history jsonb,
    referred_by text,
    created_at timestamptz not null default now()
);

create index if not exists idx_cs_leads_whatsapp on public.cs_leads (whatsapp);
create index if not exists idx_cs_leads_created on public.cs_leads (created_at desc);

-- Fallback table (save_signup)
create table if not exists public.early_access_signups (
    id uuid primary key default gen_random_uuid(),
    email text,
    whatsapp text,
    location text,
    source text,
    created_at timestamptz not null default now()
);

-- Voice / text job capture from landing
create table if not exists public.landing_leads (
    id uuid primary key,
    job_description text,
    transcript text,
    audio_url text,
    phone text,
    location text,
    photo_urls jsonb,
    chat_history jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_landing_leads_created on public.landing_leads (created_at desc);

-- WhatsApp transcript store
create table if not exists public.whatsapp_messages (
    id uuid primary key default gen_random_uuid(),
    phone_number text not null,
    role text not null,
    message_text text,
    message_type text default 'text',
    media_urls jsonb not null default '[]'::jsonb,
    media_types jsonb not null default '[]'::jsonb,
    wa_message_id text,
    reply_to_wa_id text,
    reply_to_text text,
    created_at timestamptz not null default now()
);

create index if not exists idx_wa_msgs_phone_time on public.whatsapp_messages (phone_number, created_at desc);

create table if not exists public.whatsapp_user_profiles (
    phone_number text primary key,
    display_name text,
    memory_summary text,
    message_count int not null default 0,
    updated_at timestamptz not null default now()
);

-- Hermes skill change proposals (founder approval via WhatsApp)
create table if not exists public.agent_skill_proposals (
    id uuid primary key default gen_random_uuid(),
    skill_name text not null,
    action text not null,
    reason text not null,
    content text,
    skill_payload jsonb not null default '{}'::jsonb,
    status text not null default 'pending',
    pattern_count int not null default 1,
    similar_proposals jsonb not null default '[]'::jsonb,
    conversation_id text,
    created_at timestamptz not null default now(),
    resolved_at timestamptz,
    constraint agent_skill_proposals_action_chk check (
        action in ('create', 'edit', 'patch', 'delete', 'write_file', 'remove_file')
    ),
    constraint agent_skill_proposals_status_chk check (
        status in ('pending', 'approved', 'rejected', 'draft')
    )
);

create index if not exists idx_skill_proposals_status on public.agent_skill_proposals (status, created_at desc);

-- Optional: Copilot conversation list (RPC). App falls back to raw query if missing.
create or replace function public.copilot_conversations()
returns table (
    phone_number text,
    last_message text,
    last_role text,
    last_at timestamptz,
    display_name text
)
language sql
stable
security definer
set search_path = public
as $$
    select distinct on (m.phone_number)
        m.phone_number,
        m.message_text as last_message,
        m.role as last_role,
        m.created_at as last_at,
        p.display_name
    from public.whatsapp_messages m
    left join public.whatsapp_user_profiles p on p.phone_number = m.phone_number
    order by m.phone_number, m.created_at desc;
$$;

grant execute on function public.copilot_conversations() to service_role;

-- ==========================================================================
-- MIGRATION: scopes → quotes (Shared Infrastructure Upgrade, Apr 2026)
-- ==========================================================================
-- Run once via Supabase SQL Editor if not already applied:
--
-- ALTER TABLE IF EXISTS public.scopes RENAME TO quotes;
-- ALTER TABLE IF EXISTS public.quotes RENAME COLUMN scope_data TO quote_data;
-- CREATE OR REPLACE VIEW public.scopes AS
--   SELECT *, quote_data AS scope_data FROM public.quotes;
-- GRANT ALL ON public.quotes TO service_role;
-- GRANT SELECT ON public.scopes TO service_role;
--
-- Note: the `scopes` view provides backward compatibility during the transition.
-- Drop it once all code is confirmed to use `quotes` directly.
