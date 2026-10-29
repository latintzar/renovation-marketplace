# Source reference

[Architecture](architecture.md) · [Workflows](workflows.md) · [Configuration](setup.md)

This index is generated from the released source. File links preserve the containing implementation and its local context.

## HTTP routes

| Method | Path | Source |
| --- | --- | --- |
| GET | `/api/local/session` | [session](../apps/scope/product/backend/local_mode/server.py#L131) |
| PATCH | `/api/local/session` | [language](../apps/scope/product/backend/local_mode/server.py#L135) |
| DELETE | `/api/local/session` | [logout](../apps/scope/product/backend/local_mode/server.py#L142) |
| GET | `/healthz` | [health](../apps/scope/product/backend/local_mode/server.py#L149) |
| GET | `/{path:path}` | [page](../apps/scope/product/backend/local_mode/server.py#L160) |
| GET | `/health` | [health_check](../apps/scope/product/backend/main.py#L354) |
| GET | `/` | [root](../apps/scope/product/backend/main.py#L364) |
| POST | `/api/admin/api-keys` | [create_api_key](../apps/scope/product/backend/routes/admin.py#L44) |
| GET | `/api/admin/api-keys` | [list_api_keys](../apps/scope/product/backend/routes/admin.py#L78) |
| DELETE | `/api/admin/api-keys/{key_id}` | [deactivate_api_key](../apps/scope/product/backend/routes/admin.py#L96) |
| GET | `/api/admin/customer/{phone}` | [get_customer_360](../apps/scope/product/backend/routes/admin.py#L116) |
| GET | `/canvas/{token}` | [api_get_canvas](../apps/scope/product/backend/routes/canvas.py#L92) |
| POST | `/quote/finalize` | [api_finalize_quote](../apps/scope/product/backend/routes/canvas.py#L170) |
| GET | `/quotes` | [api_list_quotes](../apps/scope/product/backend/routes/canvas.py#L257) |
| POST | `/quote/update` | [api_update_quote](../apps/scope/product/backend/routes/canvas.py#L329) |
| POST | `/claim-profile` | [api_claim_profile](../apps/scope/product/backend/routes/canvas.py#L373) |
| GET | `/contractor/by-auth-user/{auth_user_id}` | [get_contractor_by_auth_user](../apps/scope/product/backend/routes/canvas.py#L430) |
| POST | `/contractor/set-phone` | [api_set_phone](../apps/scope/product/backend/routes/canvas.py#L486) |
| GET | `/homeowner/quotes` | [get_homeowner_quotes](../apps/scope/product/backend/routes/canvas.py#L515) |
| POST | `/chat` | [chat](../apps/scope/product/backend/routes/chat.py#L35) |
| POST | `/cs-chat` | [chat](../apps/scope/product/backend/routes/chat.py#L35) |
| POST | `/api/webhooks/chatwoot-outbound` | [chatwoot_outbound_webhook](../apps/scope/product/backend/routes/chatwoot.py#L184) |
| POST | `/dispute/open` | [open_dispute](../apps/scope/product/backend/routes/dispute.py#L74) |
| POST | `/dispute/reply` | [reply_to_dispute](../apps/scope/product/backend/routes/dispute.py#L247) |
| GET | `/dispute/{quote_token}` | [get_disputes](../apps/scope/product/backend/routes/dispute.py#L285) |
| POST | `/documents/{quote_token}/record-consent` | [record_consent](../apps/scope/product/backend/routes/documents.py#L220) |
| GET | `/documents/{quote_token}/agreement` | [get_agreement](../apps/scope/product/backend/routes/documents.py#L287) |
| GET | `/documents/{quote_token}/invoice` | [get_invoice](../apps/scope/product/backend/routes/documents.py#L308) |
| POST | `/api/events/track` | [track_event](../apps/scope/product/backend/routes/events.py#L43) |
| POST | `/api/extract-doc` | [extract_doc](../apps/scope/product/backend/routes/extract_doc.py#L31) |
| POST | `/jobs` | [api_create_job](../apps/scope/product/backend/routes/job_inbox.py#L381) |
| GET | `/inbox/{token}` | [api_get_inbox](../apps/scope/product/backend/routes/job_inbox.py#L397) |
| POST | `/jobs/{job_id}/responses` | [api_add_response](../apps/scope/product/backend/routes/job_inbox.py#L437) |
| PATCH | `/jobs/{job_id}/responses/{response_id}` | [api_update_response](../apps/scope/product/backend/routes/job_inbox.py#L447) |
| POST | `/jobs/{job_id}/rank` | [api_rank_responses](../apps/scope/product/backend/routes/job_inbox.py#L465) |
| PATCH | `/jobs/{job_id}` | [api_update_job](../apps/scope/product/backend/routes/job_inbox.py#L471) |
| POST | `/inbox/{token}/approve-outreach` | [api_approve_outreach](../apps/scope/product/backend/routes/job_inbox.py#L498) |
| GET | `/ops/{token}` | [api_ops_dashboard](../apps/scope/product/backend/routes/job_inbox.py#L530) |
| POST | `/api/leads/submit` | [submit_lead](../apps/scope/product/backend/routes/landing_leads.py#L205) |
| POST | `/api/leads/phone` | [add_phone](../apps/scope/product/backend/routes/landing_leads.py#L266) |
| POST | `/api/leads/photos` | [upload_photos](../apps/scope/product/backend/routes/landing_leads.py#L458) |
| POST | `/api/leads/update` | [update_lead](../apps/scope/product/backend/routes/landing_leads.py#L503) |
| POST | `/api/leads/check-wa` | [check_whatsapp](../apps/scope/product/backend/routes/landing_leads.py#L538) |
| GET | `/marketplace` | [marketplace_page](../apps/scope/product/backend/routes/marketplace.py#L187) |
| GET | `/api/marketplace/state` | [marketplace_state](../apps/scope/product/backend/routes/marketplace.py#L196) |
| GET | `/api/marketplace/community` | [marketplace_community](../apps/scope/product/backend/routes/marketplace.py#L242) |
| POST | `/api/marketplace/toggle` | [toggle_capability](../apps/scope/product/backend/routes/marketplace.py#L290) |
| POST | `/messages/send` | [send_message](../apps/scope/product/backend/routes/messages.py#L42) |
| GET | `/messages/{quote_token}` | [get_messages](../apps/scope/product/backend/routes/messages.py#L116) |
| GET | `/api/webhooks/meta-whatsapp` | [meta_whatsapp_verify](../apps/scope/product/backend/routes/meta_whatsapp.py#L947) |
| POST | `/api/webhooks/meta-whatsapp` | [meta_whatsapp_webhook](../apps/scope/product/backend/routes/meta_whatsapp.py#L970) |
| GET | `/api/copilot/conversations` | [list_conversations](../apps/scope/product/backend/routes/meta_whatsapp.py#L1324) |
| GET | `/api/copilot/messages/{phone}` | [get_messages](../apps/scope/product/backend/routes/meta_whatsapp.py#L1370) |
| POST | `/api/copilot/send` | [send_message](../apps/scope/product/backend/routes/meta_whatsapp.py#L1406) |
| POST | `/api/copilot/send-template` | [send_template](../apps/scope/product/backend/routes/meta_whatsapp.py#L1518) |
| GET | `/api/media/whatsapp/{filename}` | [serve_media](../apps/scope/product/backend/routes/meta_whatsapp.py#L1590) |
| POST | `/api/copilot/upload-voice` | [upload_voice](../apps/scope/product/backend/routes/meta_whatsapp.py#L1602) |
| POST | `/api/copilot/upload-media` | [upload_media](../apps/scope/product/backend/routes/meta_whatsapp.py#L1731) |
| POST | `/milestone/submit-proof` | [submit_proof](../apps/scope/product/backend/routes/milestone.py#L178) |
| POST | `/payment/release-milestone` | [release_milestone](../apps/scope/product/backend/routes/milestone.py#L273) |
| POST | `/variation/create` | [create_variation](../apps/scope/product/backend/routes/milestone.py#L445) |
| POST | `/variation/approve` | [approve_variation](../apps/scope/product/backend/routes/milestone.py#L501) |
| POST | `/variation/decline` | [decline_variation](../apps/scope/product/backend/routes/milestone.py#L579) |
| POST | `/job/cancel` | [cancel_job](../apps/scope/product/backend/routes/milestone.py#L643) |
| POST | `/reviews/create` | [create_review](../apps/scope/product/backend/routes/milestone.py#L734) |
| GET | `/notifications` | [get_notifications](../apps/scope/product/backend/routes/milestone.py#L796) |
| POST | `/notifications/mark-read` | [mark_notifications_read](../apps/scope/product/backend/routes/milestone.py#L817) |
| GET | `/milestone-updates/{quote_token}` | [get_milestone_updates](../apps/scope/product/backend/routes/milestone.py#L835) |
| GET | `/variation-orders/{quote_token}` | [get_variation_orders](../apps/scope/product/backend/routes/milestone.py#L851) |
| POST | `/projects/{token}/milestones/{idx}/proof` | [submit_proof](../apps/scope/product/backend/routes/milestones.py#L53) |
| POST | `/projects/{token}/milestones/{idx}/release` | [release_milestone](../apps/scope/product/backend/routes/milestones.py#L143) |
| GET | `/notifications` | [get_notifications](../apps/scope/product/backend/routes/notifications.py#L100) |
| POST | `/notifications/mark-read` | [mark_notifications_read](../apps/scope/product/backend/routes/notifications.py#L130) |
| GET | `/p/{token}` | [serve_generated_page](../apps/scope/product/backend/routes/pages.py#L81) |
| POST | `/payment/create-checkout` | [api_create_checkout](../apps/scope/product/backend/routes/payment.py#L62) |
| POST | `/profile-import` | [profile_import](../apps/scope/product/backend/routes/profile_import.py#L4193) |
| POST | `/profile-import-sync` | [profile_import_sync](../apps/scope/product/backend/routes/profile_import.py#L4210) |
| GET | `/projects/{token}` | [get_project](../apps/scope/product/backend/routes/projects.py#L96) |
| POST | `/projects/{token}/cancel` | [cancel_project](../apps/scope/product/backend/routes/projects.py#L142) |
| POST | `/api/webhooks/resend` | [resend_inbound_webhook](../apps/scope/product/backend/routes/resend_inbound.py#L206) |
| POST | `/projects/{token}/review` | [create_review](../apps/scope/product/backend/routes/reviews.py#L32) |
| GET | `/api/search/instagram` | [search_instagram_profiles](../apps/scope/product/backend/routes/search_instagram.py#L57) |
| GET | `/api/search/instagram/batch` | [search_instagram_batch](../apps/scope/product/backend/routes/search_instagram.py#L96) |
| POST | `/stripe/create-account` | [api_create_stripe_account](../apps/scope/product/backend/routes/stripe_connect.py#L105) |
| POST | `/stripe/account-link` | [api_create_account_link](../apps/scope/product/backend/routes/stripe_connect.py#L203) |
| GET | `/stripe/account-status` | [api_get_account_status](../apps/scope/product/backend/routes/stripe_connect.py#L249) |
| POST | `/stripe/webhook` | [api_stripe_webhook](../apps/scope/product/backend/routes/stripe_connect.py#L310) |
| POST | `/api/transcribe` | [transcribe_audio](../apps/scope/product/backend/routes/transcribe.py#L32) |
| POST | `/api/transcribe/polish` | [polish_text](../apps/scope/product/backend/routes/transcribe.py#L81) |
| POST | `/projects/{token}/variations` | [create_variation](../apps/scope/product/backend/routes/variations.py#L50) |
| POST | `/projects/{token}/variations/{variation_id}/approve` | [approve_variation](../apps/scope/product/backend/routes/variations.py#L112) |
| POST | `/projects/{token}/variations/{variation_id}/decline` | [decline_variation](../apps/scope/product/backend/routes/variations.py#L195) |

## Configuration names

Values stay in the recipient’s private runtime file. [Setup](setup.md) groups the load-bearing credentials by feature.

`APP_BASE_URL`, `AWS_REGION`, `BASE_URL`, `BEDROCK_CLAUDE_HAIKU`, `BEDROCK_CLAUDE_SONNET`, `BEDROCK_REGION`, `BRIGHT_DATA_API_KEY`, `CHATWOOT_ACCOUNT_ID`, `CHATWOOT_API_TOKEN`, `CHATWOOT_INBOX_ID`, `CHATWOOT_URL`, `DATABASE_URL`, `DEEPGRAM_API_KEY`, `DEEPGRAM_MODEL`, `DEV`, `DOCUSEAL_API_KEY`, `DOCUSEAL_TEMPLATE_AGREEMENT`, `ELEVENLABS_API_KEY`, `GROQ_API_KEY`, `GROQ_WHISPER_MODEL`, `HABITISSIMO_EMAIL`, `HABITISSIMO_PASSWORD`, `HERMES_HOME`, `HERMES_VENDOR_PATH`, `HF_TOKEN`, `HF_WHISPER_MODEL`, `HOGAMI_API_KEY`, `HUGGINGFACE_HUB_TOKEN`, `LEO_AWS_ACCOUNT`, `LEO_CS_MAX_TOKENS`, `LEO_DISABLE_JWT_CACHE`, `LEO_ENV`, `LEO_FALLBACK_MODEL`, `LEO_JWT_CACHE_SIZE`, `LEO_JWT_CACHE_TTL`, `LEO_MAX_ITERATIONS`, `LEO_PRIMARY_MODEL`, `LEO_PROJECT_EMAIL_DOMAIN`, `LEXAPI_KEY`, `LITELLM_API_KEY`, `LITELLM_BASE_URL`, `LITELLM_PORT`, `MARKETPLACE_TOKEN`, `MEM0_API_KEY`, `META_API_VERSION`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `OPENROUTER_API_KEY`, `OPS_MONITOR_TOKEN`, `OUTREACH_FOLLOWUP_1_HOURS`, `OUTREACH_FOLLOWUP_2_HOURS`, `OUTREACH_FOUNDER_PHONE`, `OUTREACH_MAX_DAILY`, `OUTREACH_STAGGER_SECONDS`, `OUTREACH_TARGET_PER_JOB`, `PETER_WHATSAPP`, `POLISH_API_STYLE`, `PROFILE_STRUCTURE_MODEL`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `RESEND_WEBHOOK_TOLERANCE_SECONDS`, `SALES_TRACKER_TOKEN`, `SCOPE_WEB_BASE_PATH`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_SECRET_KEY_TEST`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET_TEST`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_URL`, `TRANSCRIPT_POLISH_ENABLED`, `TRANSCRIPT_POLISH_MODEL`, `TWILIO_ACCOUNT_SID`, `TWILIO_API_KEY_SECRET`, `TWILIO_API_KEY_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_TWIML_APP_SID`, `VITE_API_URL`, `VITE_LOCAL_MODE`, `VITE_MAPBOX_ACCESS_TOKEN`, `VITE_POSTHOG_KEY`, `VITE_SUPABASE_ANON_KEY`, `VITE_SUPABASE_URL`, `VOICE_CONCURRENCY`, `VOICE_LOG_CONTENT`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEMPLATE_HOMEOWNER`, `WHATSAPP_TEMPLATE_PROFESSIONAL`, `WHATSAPP_TEMPLATE_RECEIVED`, `WHATSAPP_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, `WHISPER_BEAM_SIZE`, `WHISPER_COMPUTE_TYPE`, `WHISPER_CPU_THREADS`, `WHISPER_DEVICE`, `WHISPER_MODEL`

## Functions

### apps/scope/product/backend/agent/ephemeral_context.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [build_enrichment_note](../apps/scope/product/backend/agent/ephemeral_context.py#L202) | enrichment_needed | Build the ENRICHMENT NEXT injection line for the system prompt. |
| [_scope_intake_context](../apps/scope/product/backend/agent/ephemeral_context.py#L499) | audience, profile_context |  |
| [_language_instructions](../apps/scope/product/backend/agent/ephemeral_context.py#L522) | page_locale, user_language_hint |  |
| [build_turn_context](../apps/scope/product/backend/agent/ephemeral_context.py#L551) | mode, audience, lead_context, page_locale, user_language_hint, profile_context, channel, confirmed, lead_phone, capabilities, enrichment_needed | Build the ephemeral_system_prompt for one agent turn. |

### apps/scope/product/backend/agent/legal_tools.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [search_boe](../apps/scope/product/backend/agent/legal_tools.py#L26) | query, limit | Search the BOE consolidated legislation API (free, no auth). |
| [get_boe_norm_text](../apps/scope/product/backend/agent/legal_tools.py#L84) | norm_id | Fetch the full text of a specific BOE norm by identifier. |
| [_get_lexapi_key](../apps/scope/product/backend/agent/legal_tools.py#L115) |  | Load LexAPI key from env. |
| [search_eu_law](../apps/scope/product/backend/agent/legal_tools.py#L124) | query, document_type, domain, max_results | Search EU law via LexAPI (free tier: 50 calls/day). |

### apps/scope/product/backend/agent/leo.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_load_soul](../apps/scope/product/backend/agent/leo.py#L69) |  | Read ~/.hermes/SOUL.md once and cache it. Hermes uses this as slot #1 in _build_system_prompt when skip_context_files=False, but we set skip_context_files=True to avoid injecting dev context files (AGENTS.md, .cursorrules) into customer chats. So we load SOUL.md ourselves and pass it via system_message (slot #4, cached on first turn). |
| [_get_enabled_toolsets](../apps/scope/product/backend/agent/leo.py#L104) |  | Read marketplace_config.json and merge enabled toolsets with leo-quote. |
| [_get_conversation_lock](../apps/scope/product/backend/agent/leo.py#L130) | conversation_id |  |
| [evict_stale_agents](../apps/scope/product/backend/agent/leo.py#L137) |  | Remove agents idle longer than AGENT_TTL_SECS. Returns count evicted. |
| [_get_or_create_agent](../apps/scope/product/backend/agent/leo.py#L149) | conversation_id, channel, model | Return existing agent for this conversation, or create a new one. |
| [_tool_progress](../apps/scope/product/backend/agent/leo.py#L197) | tool_name, preview, args | Fires before any Hermes tool call. Skipped for Leo tools that self-report. |
| [_to_openai_messages](../apps/scope/product/backend/agent/leo.py#L246) | history | Convert frontend/WhatsApp message format directly to OpenAI format. |
| [_extract_text](../apps/scope/product/backend/agent/leo.py#L320) | openai_content | Pull plain text from an OpenAI message content field. |
| [_last_msg_has_images](../apps/scope/product/backend/agent/leo.py#L331) | raw_msgs | Check if the last message has images (raw format or OpenAI multipart format). |
| [_pick_model](../apps/scope/product/backend/agent/leo.py#L347) | mode | Sales mode gets Sonnet 4.6 (founder tool, worth the cost). All other modes use the default PRIMARY_MODEL (Sonnet 4.6). |
| [_resolve_capabilities](../apps/scope/product/backend/agent/leo.py#L355) | channel, caps, page_locale, user_language_hint | Resolve a ChannelCapabilities from either an explicit object or a channel string. |
| [_legacy_msgs_to_leo_messages](../apps/scope/product/backend/agent/leo.py#L377) | raw_msgs | Convert legacy frontend format {role, text, images} to LeoMessage list. |
| [_extract_all_tool_calls](../apps/scope/product/backend/agent/leo.py#L420) | messages | Extract every tool name the agent called from the full Hermes message history. |
| [_extract_improvement_signals](../apps/scope/product/backend/agent/leo.py#L433) | messages | Scan Hermes message history for memory tool calls containing IMPROVEMENT_SIGNAL. Returns a list of signal descriptions. |
| [_phone_key](../apps/scope/product/backend/agent/leo.py#L460) | phone | Normalise a phone to bare digits (no +, spaces, dashes). |
| [whatsapp_reply](../apps/scope/product/backend/agent/leo.py#L469) | messages, mode, raw_history, lead_context, audience, page_locale, user_language_hint, profile_context, lead_phone, conversation_id, capabilities, enrichment_needed | WhatsApp channel wrapper: runs Hermes with WhatsApp formatting + capabilities. |
| [_leo_messages_to_openai](../apps/scope/product/backend/agent/leo.py#L526) | leo_msgs | Convert enriched LeoMessages to OpenAI format for Hermes. After enrichment, messages should be text-only (media already converted). |
| [run_leo_chat](../apps/scope/product/backend/agent/leo.py#L538) | messages, mode, raw_history, lead_context, audience, page_locale, user_language_hint, profile_context, channel, lead_phone, source_tag, confirmed, user_id, conversation_id, capabilities, leo_messages, contractor_id, enrichment_needed | Run one agent turn using a pooled Hermes AIAgent. |
| [_run_agent](../apps/scope/product/backend/agent/leo.py#L642) |  | Synchronous AIAgent call, runs in thread executor. |
| [_run_agent_retry](../apps/scope/product/backend/agent/leo.py#L798) |  |  |

### apps/scope/product/backend/agent/peter_notify.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_wa_text_payload](../apps/scope/product/backend/agent/peter_notify.py#L22) | body, max_len | Build a WhatsApp text payload, enabling link previews when URLs are present. |
| [_get_supabase](../apps/scope/product/backend/agent/peter_notify.py#L30) |  | Get Supabase URL and key from the database module (single source of truth). |
| [_wa_token](../apps/scope/product/backend/agent/peter_notify.py#L59) |  |  |
| [_wa_phone_id](../apps/scope/product/backend/agent/peter_notify.py#L63) |  |  |
| [notify_peter](../apps/scope/product/backend/agent/peter_notify.py#L69) | name, whatsapp, location, chat_summary | Send Peter a WhatsApp message about a new signup. Fire-and-forget. |
| [notify_peter_lead_submitted](../apps/scope/product/backend/agent/peter_notify.py#L93) | phone, name, location, job_text | Notify Peter the instant a homeowner confirms their phone on the landing page. |
| [notify_peter_discovery_complete](../apps/scope/product/backend/agent/peter_notify.py#L137) | job_id, trade, city, sent, deferred, candidates_found | Notify Peter when contractor discovery finishes for a job. |
| [notify_brief_confirmed](../apps/scope/product/backend/agent/peter_notify.py#L181) | brief, phone | Send Peter a WhatsApp with the full brief when a homeowner confirms a job. |
| [save_signup](../apps/scope/product/backend/agent/peter_notify.py#L223) | name, whatsapp, location, source, chat_summary, chat_history |  |
| [whatsapp_handoff](../apps/scope/product/backend/agent/peter_notify.py#L289) | name, whatsapp, detected_lang, audience |  |
| [proposal_short_id](../apps/scope/product/backend/agent/peter_notify.py#L346) | proposal_uuid | First 8 hex chars of UUID (no dashes) for founder WhatsApp replies. |
| [store_skill_proposal](../apps/scope/product/backend/agent/peter_notify.py#L351) | skill_name, action, reason, content, conversation_id, skill_payload | Store a skill change proposal and return the row (including id). |
| [get_similar_proposals](../apps/scope/product/backend/agent/peter_notify.py#L412) | skill_name, action | Find existing draft/pending proposals for the same skill and action. |
| [resolve_skill_proposal](../apps/scope/product/backend/agent/peter_notify.py#L441) | proposal_id, status | Update a proposal's status to approved/rejected/draft. |
| [notify_founder_skill_proposal](../apps/scope/product/backend/agent/peter_notify.py#L473) | proposal_id, skill_name, action, reason, pattern_count, content_preview | Send Peter a WhatsApp message about a skill change proposal. |
| [send_whatsapp_text](../apps/scope/product/backend/agent/peter_notify.py#L514) | to_digits, body | Send a plain text WhatsApp message. Delegates to unified send_wa_message. |
| [fetch_pending_skill_proposals](../apps/scope/product/backend/agent/peter_notify.py#L521) | limit |  |
| [fetch_skill_proposal_by_id](../apps/scope/product/backend/agent/peter_notify.py#L544) | proposal_id |  |
| [resolve_proposal_for_founder](../apps/scope/product/backend/agent/peter_notify.py#L567) | short_opt | Pick the pending proposal matching ref prefix, or latest pending if short_opt is empty. |
| [execute_skill_manage_from_row](../apps/scope/product/backend/agent/peter_notify.py#L581) | row | Apply an approved proposal by calling Hermes skill_manage (sync). |
| [parse_founder_skill_reply](../apps/scope/product/backend/agent/peter_notify.py#L618) | text | Parse founder WhatsApp reply. Returns (verb, optional_ref) where verb is approve / reject / draft. Ref is 8-char hex prefix when provided. |
| [try_handle_founder_skill_reply](../apps/scope/product/backend/agent/peter_notify.py#L651) | sender_digits, text | If sender is founder and text is a skill decision, apply it. Returns (handled, message_to_echo) — message_to_echo is sent back to founder on WhatsApp. |
| [notify_founder_improvement_signal](../apps/scope/product/backend/agent/peter_notify.py#L691) | signal_text, conversation_id | WhatsApp Peter when the agent flagged IMPROVEMENT_SIGNAL (non-customer-facing). |
| [request_human_escalation](../apps/scope/product/backend/agent/peter_notify.py#L710) | reason, conversation_summary, user_name, user_phone, channel | Escalate a conversation to Peter. Sends him a WhatsApp alert with context and returns a wa.me link to share with the user. |
| [send_email_resend](../apps/scope/product/backend/agent/peter_notify.py#L780) | to, subject, body_html, body_text, from_label, from_address | Send an email via Resend API. Returns {"ok": True, "id": ...} or {"ok": False, "error": ...}. |
| [patch_lead_structured](../apps/scope/product/backend/agent/peter_notify.py#L830) |  |  |

### apps/scope/product/backend/agent/tool_registry.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [register_leo_tools](../apps/scope/product/backend/agent/tool_registry.py#L46) | registry, create_custom_toolset | Register the leo-quote tool handlers + toolset. |

### apps/scope/product/backend/agent/tool_utils.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_dict](../apps/scope/product/backend/agent/tool_utils.py#L49) | self |  |
| [_new_state](../apps/scope/product/backend/agent/tool_utils.py#L62) |  | Return a fresh state dict using AgentTurnState defaults. |
| [_compact_tool_result](../apps/scope/product/backend/agent/tool_utils.py#L67) | tool_name, result | Trim verbose tool outputs before they enter the context window. |
| [_get_state](../apps/scope/product/backend/agent/tool_utils.py#L100) |  | Return the thread-local state dict, creating it if needed. |
| [_get_ctx_val](../apps/scope/product/backend/agent/tool_utils.py#L107) | key, default | Read a value from the thread-local context (set by run_leo_chat). |
| [_record_activity](../apps/scope/product/backend/agent/tool_utils.py#L114) | name, label |  |
| [_send_indicator](../apps/scope/product/backend/agent/tool_utils.py#L150) | tool_name, message | Send a human-readable italic indicator via WhatsApp (once per turn). |
| [_send_searching_indicator](../apps/scope/product/backend/agent/tool_utils.py#L194) | tool_name | Backward-compatible alias for _send_indicator. |
| [_now_iso](../apps/scope/product/backend/agent/tool_utils.py#L199) |  |  |
| [_run_async](../apps/scope/product/backend/agent/tool_utils.py#L204) | coro | Run an async coroutine from a sync Hermes tool handler. |
| [_create_job_async](../apps/scope/product/backend/agent/tool_utils.py#L214) |  |  |
| [_get_job_by_id_async](../apps/scope/product/backend/agent/tool_utils.py#L218) | job_id |  |
| [_update_job_async](../apps/scope/product/backend/agent/tool_utils.py#L222) | job_id, updates |  |
| [_add_response_async](../apps/scope/product/backend/agent/tool_utils.py#L226) | job_id, data |  |
| [_rank_responses_async](../apps/scope/product/backend/agent/tool_utils.py#L230) | job_id |  |

### apps/scope/product/backend/agent/tools/admin.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_skill_payload_from_skill_manage_args](../apps/scope/product/backend/agent/tools/admin.py#L20) | args |  |
| [_handle_founder_dashboard](../apps/scope/product/backend/agent/tools/admin.py#L30) | args | Founder-only: return a full ops snapshot (signups, jobs, pipeline, replies). |
| [_headers](../apps/scope/product/backend/agent/tools/admin.py#L47) | _key |  |
| [_get](../apps/scope/product/backend/agent/tools/admin.py#L54) | table, params |  |
| [_handle_skill_manage_gated](../apps/scope/product/backend/agent/tools/admin.py#L190) | args | skill_manage is gated: proposals go to Supabase + founder WhatsApp. |
| [_handle_propose_skill_change](../apps/scope/product/backend/agent/tools/admin.py#L249) | args | Explicit skill proposal with a clear reason. |
| [_handle_create_page](../apps/scope/product/backend/agent/tools/admin.py#L319) | args | Generate an ad-hoc branded HTML page and store it in Supabase. |
| [register](../apps/scope/product/backend/agent/tools/admin.py#L574) | registry |  |
| [register_skill_manage](../apps/scope/product/backend/agent/tools/admin.py#L599) | registry | Register the gated skill_manage tool. |

### apps/scope/product/backend/agent/tools/canvas.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_parse_contingency_drafts](../apps/scope/product/backend/agent/tools/canvas.py#L20) | raw | Structured 'if we discover X' drafts inserted between quote milestones. |
| [_handle_update_brief](../apps/scope/product/backend/agent/tools/canvas.py#L71) | args |  |
| [_handle_update_profile](../apps/scope/product/backend/agent/tools/canvas.py#L116) | args |  |
| [_handle_update_quote](../apps/scope/product/backend/agent/tools/canvas.py#L152) | args |  |
| [_can_show_drawer](../apps/scope/product/backend/agent/tools/canvas.py#L264) |  | check_fn for tools that require the web chat drawer UI. |
| [_handle_set_drawer](../apps/scope/product/backend/agent/tools/canvas.py#L273) | args | Control the action drawer — Hermes's dynamic UI surface. No trace emitted (internal). |
| [register](../apps/scope/product/backend/agent/tools/canvas.py#L553) | registry |  |

### apps/scope/product/backend/agent/tools/delivery.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_handle_send_whatsapp](../apps/scope/product/backend/agent/tools/delivery.py#L19) | args | Unified WhatsApp send tool. |
| [_store_referral_lead](../apps/scope/product/backend/agent/tools/delivery.py#L68) | phone, name, referrer_phone, purpose | Store a referral in cs_leads (fire-and-forget). |
| [_handle_send_email](../apps/scope/product/backend/agent/tools/delivery.py#L98) | args | Send an email via Resend. |
| [_handle_request_human](../apps/scope/product/backend/agent/tools/delivery.py#L116) | args | Escalate the conversation to a human (Peter). |
| [register](../apps/scope/product/backend/agent/tools/delivery.py#L224) | registry |  |

### apps/scope/product/backend/agent/tools/discovery.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_handle_find_houzz_contractors](../apps/scope/product/backend/agent/tools/discovery.py#L22) | args | Search Houzz directory for contractors matching a trade and city. |
| [_handle_search_fb_groups](../apps/scope/product/backend/agent/tools/discovery.py#L55) | args | Search Facebook groups for contractor recommendations. |
| [_handle_search_forums](../apps/scope/product/backend/agent/tools/discovery.py#L147) | args | Search Spanish forums (Forocoches, Mediavida, Reddit ES). |
| [_find_response_by_phone](../apps/scope/product/backend/agent/tools/discovery.py#L237) | phone |  |
| [_update_response_verification](../apps/scope/product/backend/agent/tools/discovery.py#L243) | response_id, trust_signals |  |
| [_handle_enrich_contractor](../apps/scope/product/backend/agent/tools/discovery.py#L249) | args | Run verification checks on a contractor using phone as the anchor. |
| [register](../apps/scope/product/backend/agent/tools/discovery.py#L451) | registry |  |

### apps/scope/product/backend/agent/tools/legal.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_handle_search_spanish_law](../apps/scope/product/backend/agent/tools/legal.py#L18) | args |  |
| [_handle_get_boe_norm_text](../apps/scope/product/backend/agent/tools/legal.py#L31) | args |  |
| [_handle_search_eu_law](../apps/scope/product/backend/agent/tools/legal.py#L42) | args |  |
| [register](../apps/scope/product/backend/agent/tools/legal.py#L130) | registry |  |

### apps/scope/product/backend/agent/tools/outreach.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_notify_founder_outreach](../apps/scope/product/backend/agent/tools/outreach.py#L23) | contractor_name, phone, source, title, location, job_id | Send Peter a WhatsApp heads-up when an outreach message goes out. |
| [_handle_outreach_contractor](../apps/scope/product/backend/agent/tools/outreach.py#L58) | args | Send a single WhatsApp cold outreach message to a contractor about a job. |
| [_handle_batch_outreach](../apps/scope/product/backend/agent/tools/outreach.py#L129) | args | Run full contractor discovery + outreach pipeline for a job. |
| [_handle_control_outreach](../apps/scope/product/backend/agent/tools/outreach.py#L185) | args | Pause, resume, or stop outreach for a specific job or all jobs. |
| [_headers](../apps/scope/product/backend/agent/tools/outreach.py#L198) | _key |  |
| [_handle_rank_job_responses](../apps/scope/product/backend/agent/tools/outreach.py#L258) | args | AI-rank all contractor responses for a job. |
| [register](../apps/scope/product/backend/agent/tools/outreach.py#L369) | registry |  |

### apps/scope/product/backend/agent/tools/pricing.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_handle_lookup_price](../apps/scope/product/backend/agent/tools/pricing.py#L19) | args | Look up renovation/construction prices from Habitissimo + CronoShare databases. |
| [_handle_estimate_cost](../apps/scope/product/backend/agent/tools/pricing.py#L35) | args | Multi-layer cost estimator: curated recipes → construction cost DB → market data. |
| [_handle_lookup_product](../apps/scope/product/backend/agent/tools/pricing.py#L70) | args | Search 199K Spanish construction products by name, brand, or model. |
| [register](../apps/scope/product/backend/agent/tools/pricing.py#L177) | registry |  |

### apps/scope/product/backend/agent/tools/user_flow.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_handle_save_signup](../apps/scope/product/backend/agent/tools/user_flow.py#L22) | args |  |
| [_handle_whatsapp_handoff](../apps/scope/product/backend/agent/tools/user_flow.py#L39) | args |  |
| [_handle_create_job](../apps/scope/product/backend/agent/tools/user_flow.py#L53) | args | Create a job from a homeowner brief and return the inbox token. |
| [_handle_start_job_intake](../apps/scope/product/backend/agent/tools/user_flow.py#L78) | args | Homeowner intake pipeline — Bar 1 met, fire discovery + enrichment. |
| [register](../apps/scope/product/backend/agent/tools/user_flow.py#L277) | registry |  |

### apps/scope/product/backend/config.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [postgres_url](../apps/scope/product/backend/config.py#L49) | self | Get Postgres connection URL for asyncpg. |
| [get_supabase_url](../apps/scope/product/backend/config.py#L142) |  |  |
| [get_supabase_key](../apps/scope/product/backend/config.py#L146) |  | Get service role key (preferred) or anon key. |

### apps/scope/product/backend/constants.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [peter_whatsapp](../apps/scope/product/backend/constants.py#L71) |  | Return ``PETER_WHATSAPP`` env var or the UK default. |

### apps/scope/product/backend/documents/agreements.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [template_name](../apps/scope/product/backend/documents/agreements.py#L40) | self |  |
| [render_html](../apps/scope/product/backend/documents/agreements.py#L43) | self | Render the agreement HTML. Memoised for the instance lifetime. |
| [render_pdf](../apps/scope/product/backend/documents/agreements.py#L51) | self | Render the agreement PDF. Not memoised — callers rarely render the same PDF twice, and a 200-800 KB byte cache on every doc instance is noise. |
| [content_hash](../apps/scope/product/backend/documents/agreements.py#L58) | self | sha256 hex digest of ``render_html()`` bytes. Memoised. |
| [filename](../apps/scope/product/backend/documents/agreements.py#L65) | self | Canonical download filename: ``leo-agreement-<12-char-token>.<ext>``. |
| [send_agreement_for_signature](../apps/scope/product/backend/documents/agreements.py#L72) | payload | End-to-end: render agreement PDF, submit to docuSeal. |

### apps/scope/product/backend/documents/consent.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_read_template_bytes](../apps/scope/product/backend/documents/consent.py#L26) | name |  |
| [template_fingerprint](../apps/scope/product/backend/documents/consent.py#L30) | template_name | sha256 fingerprint ``(_base + <template_name>)[:12]``. |
| [hash_document](../apps/scope/product/backend/documents/consent.py#L42) | html | Canonical consent-hash function. ``sha256(html.encode("utf-8")).hexdigest()``. |

### apps/scope/product/backend/documents/contexts.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_milestone_dict](../apps/scope/product/backend/documents/contexts.py#L33) | m |  |
| [build_agreement_context](../apps/scope/product/backend/documents/contexts.py#L45) | payload | Return the Jinja context dict for the agreement template. |
| [build_invoice_context](../apps/scope/product/backend/documents/contexts.py#L72) | payload | Return the Jinja context dict for the invoice template. |
| [build_variation_context](../apps/scope/product/backend/documents/contexts.py#L107) | payload | Return the Jinja context dict for the variation template (stub). |

### apps/scope/product/backend/documents/dates.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [format_date_es](../apps/scope/product/backend/documents/dates.py#L18) | d | Spanish long-form date. ``date(2026, 4, 18)`` → ``"18 de abril de 2026"``. |
| [format_date](../apps/scope/product/backend/documents/dates.py#L24) | d | Generic locale-aware ``long`` date formatting. Babel wrapper. |

### apps/scope/product/backend/documents/docuseal/client.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../apps/scope/product/backend/documents/docuseal/client.py#L40) | self |  |
| [_headers](../apps/scope/product/backend/documents/docuseal/client.py#L51) | self |  |
| [create_submission](../apps/scope/product/backend/documents/docuseal/client.py#L60) | self | Create a signature submission. Idempotent on ``external_id``. |
| [_send](../apps/scope/product/backend/documents/docuseal/client.py#L101) |  |  |
| [get_submission](../apps/scope/product/backend/documents/docuseal/client.py#L114) | self, submission_id |  |
| [_send](../apps/scope/product/backend/documents/docuseal/client.py#L116) |  |  |
| [get_document_urls](../apps/scope/product/backend/documents/docuseal/client.py#L128) | self, submission_id | Presigned URLs for the signed documents (post-completion). |
| [_send](../apps/scope/product/backend/documents/docuseal/client.py#L132) |  |  |
| [cancel_submission](../apps/scope/product/backend/documents/docuseal/client.py#L145) | self, submission_id |  |
| [_send](../apps/scope/product/backend/documents/docuseal/client.py#L147) |  |  |
| [_parse_iso](../apps/scope/product/backend/documents/docuseal/client.py#L158) | value |  |
| [_submission_from_payload](../apps/scope/product/backend/documents/docuseal/client.py#L165) | payload, default_submitters, default_template_id, default_external_id |  |
| [get_docuseal](../apps/scope/product/backend/documents/docuseal/client.py#L194) |  | Process-wide singleton. ``api_key`` read from ``DOCUSEAL_API_KEY``. |

### apps/scope/product/backend/documents/docuseal/webhook.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [verify_docuseal_webhook](../apps/scope/product/backend/documents/docuseal/webhook.py#L20) | body, signature, secret | HMAC-SHA256 verify the ``X-DocuSeal-Signature`` header. |
| [parse_webhook_event](../apps/scope/product/backend/documents/docuseal/webhook.py#L41) | body | Parse a docuSeal webhook body into :class:`DocusealWebhookEvent`. |
| [_parse_iso](../apps/scope/product/backend/documents/docuseal/webhook.py#L62) | value |  |

### apps/scope/product/backend/documents/invoices.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [template_name](../apps/scope/product/backend/documents/invoices.py#L30) | self |  |
| [render_html](../apps/scope/product/backend/documents/invoices.py#L33) | self |  |
| [render_pdf](../apps/scope/product/backend/documents/invoices.py#L37) | self |  |
| [filename](../apps/scope/product/backend/documents/invoices.py#L40) | self |  |

### apps/scope/product/backend/documents/payloads.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [from_cents](../apps/scope/product/backend/documents/payloads.py#L56) | cls, cents | Alternate constructor: ``Money.from_cents(1234)``. |
| [from_euros](../apps/scope/product/backend/documents/payloads.py#L62) | cls, euros | Alternate constructor: ``Money.from_euros("12.34")``. |
| [euros](../apps/scope/product/backend/documents/payloads.py#L68) | self | EUR value as ``Decimal`` at 2 dp. Wraps :func:`domain.money.from_cents`. |
| [__str__](../apps/scope/product/backend/documents/payloads.py#L73) | self | Human-readable ES-convention string, e.g. ``"1.234,56 €"``. |
| [__add__](../apps/scope/product/backend/documents/payloads.py#L78) | self, other |  |
| [__sub__](../apps/scope/product/backend/documents/payloads.py#L83) | self, other |  |
| [__mul__](../apps/scope/product/backend/documents/payloads.py#L88) | self, other |  |
| [__rmul__](../apps/scope/product/backend/documents/payloads.py#L91) | self, other |  |

### apps/scope/product/backend/documents/render.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [set_override_dir](../apps/scope/product/backend/documents/render.py#L50) | path | Register a per-app template override directory, or clear it. |
| [_build_env](../apps/scope/product/backend/documents/render.py#L66) |  |  |
| [_get_env](../apps/scope/product/backend/documents/render.py#L80) |  |  |
| [render_html](../apps/scope/product/backend/documents/render.py#L87) | template_name, context | Render a Jinja2 template to HTML string. |
| [render_pdf](../apps/scope/product/backend/documents/render.py#L100) | html | Convert HTML to PDF bytes via WeasyPrint. |
| [_do_convert](../apps/scope/product/backend/documents/render.py#L119) |  |  |

### apps/scope/product/backend/documents/storage.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../apps/scope/product/backend/documents/storage.py#L63) | self |  |
| [_supabase](../apps/scope/product/backend/documents/storage.py#L76) | self |  |
| [_client](../apps/scope/product/backend/documents/storage.py#L81) | self |  |
| [_key](../apps/scope/product/backend/documents/storage.py#L87) | self, doc |  |
| [put](../apps/scope/product/backend/documents/storage.py#L94) | self, doc | Upload document bytes to S3 + insert ``documents`` row. |
| [get_by_id](../apps/scope/product/backend/documents/storage.py#L147) | self, id |  |
| [find](../apps/scope/product/backend/documents/storage.py#L154) | self | Most recent ``StoredDocument`` for the (kind, quote_token) pair. |
| [get_url](../apps/scope/product/backend/documents/storage.py#L176) | self, stored | Presigned GET URL. Accepts :class:`StoredDocument` or raw S3 key. |
| [delete](../apps/scope/product/backend/documents/storage.py#L191) | self, stored |  |
| [get_storage](../apps/scope/product/backend/documents/storage.py#L203) |  | Process-wide factory. Bucket name derived from ``LEO_ENV``. |

### apps/scope/product/backend/documents/variations.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [template_name](../apps/scope/product/backend/documents/variations.py#L32) | self |  |
| [render_html](../apps/scope/product/backend/documents/variations.py#L35) | self |  |
| [render_pdf](../apps/scope/product/backend/documents/variations.py#L41) | self |  |
| [content_hash](../apps/scope/product/backend/documents/variations.py#L44) | self |  |
| [filename](../apps/scope/product/backend/documents/variations.py#L49) | self |  |

### apps/scope/product/backend/local_mode/seed.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [starter](../apps/scope/product/backend/local_mode/seed.py#L6) | identity |  |

### apps/scope/product/backend/local_mode/server.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [create_app](../apps/scope/product/backend/local_mode/server.py#L18) | state |  |
| [identity](../apps/scope/product/backend/local_mode/server.py#L34) |  |  |
| [current_user](../apps/scope/product/backend/local_mode/server.py#L40) |  |  |
| [contractor](../apps/scope/product/backend/local_mode/server.py#L45) |  |  |
| [homeowner](../apps/scope/product/backend/local_mode/server.py#L51) |  |  |
| [no_external_sandbox](../apps/scope/product/backend/local_mode/server.py#L57) |  |  |
| [domain_error](../apps/scope/product/backend/local_mode/server.py#L62) | _request, error |  |
| [workspace](../apps/scope/product/backend/local_mode/server.py#L66) | request, call_next |  |
| [session](../apps/scope/product/backend/local_mode/server.py#L131) |  |  |
| [language](../apps/scope/product/backend/local_mode/server.py#L135) | request |  |
| [logout](../apps/scope/product/backend/local_mode/server.py#L142) |  |  |
| [health](../apps/scope/product/backend/local_mode/server.py#L149) |  |  |
| [page](../apps/scope/product/backend/local_mode/server.py#L160) | path |  |

### apps/scope/product/backend/local_mode/store.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [now](../apps/scope/product/backend/local_mode/store.py#L16) |  |  |
| [__init__](../apps/scope/product/backend/local_mode/store.py#L21) | self, state |  |
| [connect](../apps/scope/product/backend/local_mode/store.py#L30) | self |  |
| [admit](../apps/scope/product/backend/local_mode/store.py#L37) | self, secret, role |  |
| [user](../apps/scope/product/backend/local_mode/store.py#L65) | self, identity |  |
| [reset](../apps/scope/product/backend/local_mode/store.py#L69) | self, identity |  |
| [language](../apps/scope/product/backend/local_mode/store.py#L74) | self, identity, language |  |
| [rows](../apps/scope/product/backend/local_mode/store.py#L83) | self, db, guest, table |  |
| [operation](../apps/scope/product/backend/local_mode/store.py#L86) | self, identity, table, method, params, payload |  |
| [matches](../apps/scope/product/backend/local_mode/store.py#L92) | row |  |
| [rest_app](../apps/scope/product/backend/local_mode/store.py#L163) | self |  |
| [records](../apps/scope/product/backend/local_mode/store.py#L167) | table, request |  |

### apps/scope/product/backend/main.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [lifespan](../apps/scope/product/backend/main.py#L62) | app |  |
| [_eviction_loop](../apps/scope/product/backend/main.py#L85) |  |  |
| [_cron_tick_loop](../apps/scope/product/backend/main.py#L100) |  |  |
| [_run_cron_tick](../apps/scope/product/backend/main.py#L119) |  | Run one cron tick: check due jobs, execute them, deliver via WhatsApp. |
| [_deliver_cron_whatsapp](../apps/scope/product/backend/main.py#L160) | job, content | Deliver cron job output via WhatsApp using unified send_wa_message. |
| [_app_error_handler](../apps/scope/product/backend/main.py#L220) | request, exc |  |
| [health_check](../apps/scope/product/backend/main.py#L354) |  |  |
| [root](../apps/scope/product/backend/main.py#L364) |  |  |

### apps/scope/product/backend/pricing/config.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_bundled](../apps/scope/product/backend/pricing/config.py#L59) | name | Return the path to a bundled artifact under ``pricing/data/``. |
| [_env_path](../apps/scope/product/backend/pricing/config.py#L71) | var |  |
| [configure](../apps/scope/product/backend/pricing/config.py#L78) |  | Override the process-wide defaults. |
| [close_connections](../apps/scope/product/backend/pricing/config.py#L150) |  | Close module-held SQLite connections (CYPE, prices, products). |
| [_reset_for_tests](../apps/scope/product/backend/pricing/config.py#L160) |  | Reset all settings to their dataclass defaults + drop caches. |
| [_invalidate_caches](../apps/scope/product/backend/pricing/config.py#L172) |  | Clear memoised loaders + close SQLite connections. |
| [_resolve_path](../apps/scope/product/backend/pricing/config.py#L196) | override, env_var, bundled_name, default_dir_name | Resolve a data artifact path. |
| [cype_db_path](../apps/scope/product/backend/pricing/config.py#L231) |  |  |
| [prices_db_path](../apps/scope/product/backend/pricing/config.py#L240) |  | Resolve the Habitissimo+CronoShare prices DB. Not bundled. |
| [products_db_path](../apps/scope/product/backend/pricing/config.py#L251) |  | Resolve the Leroy Merlin products DB. Not bundled (78 MB). |
| [recipes_path](../apps/scope/product/backend/pricing/config.py#L262) |  |  |
| [ine_index_path](../apps/scope/product/backend/pricing/config.py#L271) |  |  |
| [overhead_model_path](../apps/scope/product/backend/pricing/config.py#L280) |  |  |
| [regional_multipliers_override](../apps/scope/product/backend/pricing/config.py#L291) |  |  |
| [markup_by_chapter_override](../apps/scope/product/backend/pricing/config.py#L295) |  |  |
| [historical_lookback_months](../apps/scope/product/backend/pricing/config.py#L299) |  |  |
| [default_service_fee_percent](../apps/scope/product/backend/pricing/config.py#L303) |  |  |
| [default_iva_rate](../apps/scope/product/backend/pricing/config.py#L307) |  |  |

### apps/scope/product/backend/pricing/cype_index.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_conn](../apps/scope/product/backend/pricing/cype_index.py#L44) |  | Open (or reuse) the process-lifetime CYPE connection. |
| [close_connection](../apps/scope/product/backend/pricing/cype_index.py#L77) |  | Close the CYPE connection. Safe to call when no connection is open. |
| [_normalize_query](../apps/scope/product/backend/pricing/cype_index.py#L90) | query | Normalize query to match the CYPE FTS5 index content. |
| [_build_fts_query](../apps/scope/product/backend/pricing/cype_index.py#L118) | query_norm, original | Build an FTS5 MATCH expression. |
| [search_cype](../apps/scope/product/backend/pricing/cype_index.py#L134) | query | Search the CYPE FTS5 index, returning typed :class:`CypeItem` list. |
| [_fallback_search](../apps/scope/product/backend/pricing/cype_index.py#L218) | conn, query | LIKE-based fallback when the FTS5 expression can't parse. |
| [_row_to_item](../apps/scope/product/backend/pricing/cype_index.py#L263) | row |  |
| [_parse_json](../apps/scope/product/backend/pricing/cype_index.py#L280) | raw |  |

### apps/scope/product/backend/pricing/estimate.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_safe_lookup_market](../apps/scope/product/backend/pricing/estimate.py#L47) | query, city | Best-effort market lookup for cross-check; return "" on any error. |
| [_empty_estimate](../apps/scope/product/backend/pricing/estimate.py#L60) | query, note |  |
| [_apply_regional](../apps/scope/product/backend/pricing/estimate.py#L76) | base_eur, city | Apply the regional multiplier; return (adjusted, multiplier). |
| [_recipe_layer](../apps/scope/product/backend/pricing/estimate.py#L90) | recipe |  |
| [_find_ine_category](../apps/scope/product/backend/pricing/estimate.py#L176) | item, query | Map a CYPE item to an INE category slug, preferring material codes. |
| [_cype_layer](../apps/scope/product/backend/pricing/estimate.py#L190) | items |  |
| [_market_layer](../apps/scope/product/backend/pricing/estimate.py#L296) | query, city |  |
| [_safe_historical](../apps/scope/product/backend/pricing/estimate.py#L322) | trade, contractor_id | Run Layer 0 synchronously — fires the async query on a private loop. |
| [estimate_cost](../apps/scope/product/backend/pricing/estimate.py#L340) | query | Multi-layer estimate. See module docstring for resolution chain. |

### apps/scope/product/backend/pricing/historical.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_parse_datetime](../apps/scope/product/backend/pricing/historical.py#L44) | raw |  |
| [search_historical](../apps/scope/product/backend/pricing/historical.py#L55) | trade | Query the ``pricing_historical_jobs`` Supabase view. |
| [summarize](../apps/scope/product/backend/pricing/historical.py#L159) | jobs, lookback_months | Aggregate a list of historical jobs into a :class:`HistoricalSummary`. |
| [estimate_from_history](../apps/scope/product/backend/pricing/historical.py#L194) | trade | Resolve a query to an :class:`Estimate` via historical quotes. |

### apps/scope/product/backend/pricing/ine_categories.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ine_category_for_cype_code](../apps/scope/product/backend/pricing/ine_categories.py#L34) | material_code | Return the INE slug for a single CYPE material code, or None. |
| [ine_category_for_query](../apps/scope/product/backend/pricing/ine_categories.py#L51) | query | Best-match INE category slug from a free-text query. |

### apps/scope/product/backend/pricing/ine_drift.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_clear_cache](../apps/scope/product/backend/pricing/ine_drift.py#L33) |  |  |
| [load_ine_index](../apps/scope/product/backend/pricing/ine_drift.py#L38) |  | Return the INE category dict, lazy-loaded. |
| [compute_ine_material_drift](../apps/scope/product/backend/pricing/ine_drift.py#L69) | ine_category_slug | Return the material-price drift multiplier for an INE category. |

### apps/scope/product/backend/pricing/markup.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [markup_for_chapter](../apps/scope/product/backend/pricing/markup.py#L68) | chapter | Return the ``MarkupEntry`` for a CYPE chapter path. |
| [markup_for_chapter_strict](../apps/scope/product/backend/pricing/markup.py#L103) | chapter | Like :func:`markup_for_chapter` but raises on miss. |
| [material_fraction_for_chapter](../apps/scope/product/backend/pricing/markup.py#L119) | chapter | Return the ~material fraction of cost-of-inputs for a chapter. |
| [_coerce_entry](../apps/scope/product/backend/pricing/markup.py#L140) | value | Accept ``(min, mid, max)`` tuples from user-provided overrides. |

### apps/scope/product/backend/pricing/materials.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [lookup_live_price](../apps/scope/product/backend/pricing/materials.py#L25) | sku | STUB — raises ``NotImplementedError`` until ``scraping`` lands vendor-aware helpers. |

### apps/scope/product/backend/pricing/modifiers.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [normalise_modifiers](../apps/scope/product/backend/pricing/modifiers.py#L40) | modifiers | Coerce the many shapes hermes may pass into a clean list of keys. |
| [apply_modifiers](../apps/scope/product/backend/pricing/modifiers.py#L75) | base_eur, modifiers | Multiply ``base_eur`` by every recognised modifier. |
| [regional_multiplier](../apps/scope/product/backend/pricing/modifiers.py#L115) | city_or_province | Look up the regional cost multiplier for a Spanish city/province. |
| [_merged_regional_table](../apps/scope/product/backend/pricing/modifiers.py#L147) |  | Return the merged regional multiplier table (override over default). |
| [_normalise_city](../apps/scope/product/backend/pricing/modifiers.py#L159) | name |  |
| [_is_known_spanish_city](../apps/scope/product/backend/pricing/modifiers.py#L164) | name | Return True if the caller's name resolves to a canonical Spanish city. |

### apps/scope/product/backend/pricing/overhead.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_clear_cache](../apps/scope/product/backend/pricing/overhead.py#L30) |  |  |
| [overhead_model](../apps/scope/product/backend/pricing/overhead.py#L35) |  | Return the autónomo overhead model. |

### apps/scope/product/backend/pricing/price_lookup.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_index](../apps/scope/product/backend/pricing/price_lookup.py#L53) |  | Lazily open the prices DB as a :class:`fulltext.DomainIndex`. |
| [close_connection](../apps/scope/product/backend/pricing/price_lookup.py#L82) |  | Drop the cached DomainIndex. Safe to call when no index is open. |
| [_format_city_row](../apps/scope/product/backend/pricing/price_lookup.py#L90) | row | Format a ``city_prices`` row as LLM text. |
| [_format_fts_result](../apps/scope/product/backend/pricing/price_lookup.py#L104) | result, city_norm |  |
| [_dedupe_city_rows](../apps/scope/product/backend/pricing/price_lookup.py#L162) | city_rows, limit | Drop rows that share a price fingerprint (Habitissimo's recycled content). |
| [_extract_structured](../apps/scope/product/backend/pricing/price_lookup.py#L177) | city_rows, fts_results, city | Pull structured fields out of the same rows the text formatter uses. |
| [lookup_market](../apps/scope/product/backend/pricing/price_lookup.py#L209) | query | Search Habitissimo + CronoShare for market-price data. |

### apps/scope/product/backend/pricing/product_lookup.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_conn](../apps/scope/product/backend/pricing/product_lookup.py#L39) |  |  |
| [close_connection](../apps/scope/product/backend/pricing/product_lookup.py#L62) |  |  |
| [_build_fts_query](../apps/scope/product/backend/pricing/product_lookup.py#L73) | words |  |
| [_row_to_product](../apps/scope/product/backend/pricing/product_lookup.py#L78) | row |  |
| [_format_products](../apps/scope/product/backend/pricing/product_lookup.py#L98) | products, query |  |
| [lookup_product](../apps/scope/product/backend/pricing/product_lookup.py#L130) | query | Search the Spanish construction product catalog. |

### apps/scope/product/backend/pricing/quote.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_normalise_iva](../apps/scope/product/backend/pricing/quote.py#L45) | iva_rate, iva_percent | Return ``(fraction, integer_percent)`` after validation. |
| [_line_amount_eur](../apps/scope/product/backend/pricing/quote.py#L85) | item | Extract the numeric ``amount`` field from a ``line_items[]`` entry. |
| [compute_line](../apps/scope/product/backend/pricing/quote.py#L103) | description, amount_eur | Build a :class:`Line` from raw values. |
| [compute_quote](../apps/scope/product/backend/pricing/quote.py#L124) | draft | Compute quote financials deterministically from a :class:`QuoteDraft`. |
| [breakdown_from_quote_row](../apps/scope/product/backend/pricing/quote.py#L197) | row | Decode a stored ``quotes`` row into a typed :class:`QuoteBreakdown`. |

### apps/scope/product/backend/pricing/recipes.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_clear_cache](../apps/scope/product/backend/pricing/recipes.py#L48) |  | Drop the in-memory recipe cache. Called from :func:`pricing.configure`. |
| [load_recipes](../apps/scope/product/backend/pricing/recipes.py#L55) |  | Return the in-memory recipe list, loading once. |
| [_normalise](../apps/scope/product/backend/pricing/recipes.py#L86) | text |  |
| [recipe_score](../apps/scope/product/backend/pricing/recipes.py#L90) | recipe, query_normalized | Per-recipe relevance score against a normalised query. |
| [find_recipe](../apps/scope/product/backend/pricing/recipes.py#L119) | query, threshold | Best-match recipe for a free-text query. |

### apps/scope/product/backend/pricing/types.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_dict](../apps/scope/product/backend/pricing/types.py#L31) | self |  |
| [to_quote_row](../apps/scope/product/backend/pricing/types.py#L79) | self | Shape ready for Supabase ``quotes`` row INSERT/PATCH. |
| [format_total_eur](../apps/scope/product/backend/pricing/types.py#L95) | self | Spanish-locale total with the euro sign — ``core.money.format_eur``. |
| [from_dict](../apps/scope/product/backend/pricing/types.py#L149) | cls, data | Factory that copes with optional / extra fields in the JSON. |
| [to_dict](../apps/scope/product/backend/pricing/types.py#L220) | self |  |
| [to_dict](../apps/scope/product/backend/pricing/types.py#L291) | self | JSON-safe dict for the hermes tool envelope. |
| [as_llm_text](../apps/scope/product/backend/pricing/types.py#L368) | self | Formatted string — the LLM-context shape today's ``search_prices`` returns. |
| [as_llm_text](../apps/scope/product/backend/pricing/types.py#L398) | self |  |

### apps/scope/product/backend/project_access.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [is_project_homeowner](../apps/scope/product/backend/project_access.py#L6) | caller, quote | Match a verified auth subject, or a nonempty verified legacy email. |
| [project_party](../apps/scope/product/backend/project_access.py#L16) | caller, quote | Resolve the sender from verified identity and this quote's participants. |

### apps/scope/product/backend/records/conversations.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [add_message](../apps/scope/product/backend/records/conversations.py#L65) | user_id, role, text | Append a message row to ``whatsapp_messages`` or ``web_messages``. |
| [get_messages](../apps/scope/product/backend/records/conversations.py#L155) | user_id | Fetch messages for a user, newest-first, paginated. |
| [get_recent_window](../apps/scope/product/backend/records/conversations.py#L220) | user_id | Messages from the last ``hours``, capped at ``cap`` rows. |
| [summarize_recent](../apps/scope/product/backend/records/conversations.py#L250) | user_id | Recency-weighted summary of a user's conversation. |
| [_summarize_older](../apps/scope/product/backend/records/conversations.py#L325) | older | Group into 15-min buckets and summarize each via :func:`llm.chat`. |
| [_row_to_message](../apps/scope/product/backend/records/conversations.py#L383) | row | Adapt legacy + target schemas into the unified :class:`Message`. |
| [_parse_ts](../apps/scope/product/backend/records/conversations.py#L417) | raw |  |
| [_ensure_aware](../apps/scope/product/backend/records/conversations.py#L428) | ts | Supabase timestamps are UTC; guard against naive by coercing. |

### apps/scope/product/backend/records/dossier.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_upsert](../apps/scope/product/backend/records/dossier.py#L48) | row |  |
| [_patch](../apps/scope/product/backend/records/dossier.py#L73) | contractor_id, updates |  |
| [_select](../apps/scope/product/backend/records/dossier.py#L95) | column, value |  |
| [get_or_create_contractor](../apps/scope/product/backend/records/dossier.py#L112) | contractor_id | Idempotent. If a row with this id exists, patch missing fields. Otherwise upsert a new row. |
| [get_contractor_by_phone](../apps/scope/product/backend/records/dossier.py#L154) | phone | Index-hit lookup by unique ``phone`` column. Returns ``None`` if not found. |
| [get_contractor_by_token](../apps/scope/product/backend/records/dossier.py#L163) | canvas_token | Index-hit lookup by ``canvas_token``. |
| [set_contractor_phone](../apps/scope/product/backend/records/dossier.py#L176) | contractor_id, phone | Set or update the phone column on a contractor row. |
| [add_contractor_source](../apps/scope/product/backend/records/dossier.py#L187) | contractor_id, source_data | Append a scraped profile to ``dossier.sources[]``, deduplicating by ``(platform, source_url)``. |
| [update_trust_signals](../apps/scope/product/backend/records/dossier.py#L270) | contractor_id, signals | Write verification results to ``dossier.trust_signals``. |
| [add_conversation_note](../apps/scope/product/backend/records/dossier.py#L297) | contractor_id, note | Append ``{text, timestamp}`` to ``dossier.conversation_notes``. |
| [update_identity_overrides](../apps/scope/product/backend/records/dossier.py#L318) | contractor_id, overrides | Store conversation corrections (business_name, trade, NIF given verbally). |
| [recompute_canvas](../apps/scope/product/backend/records/dossier.py#L354) | dossier | Pure function: dossier in, canvas dict out. |
| [_best_source](../apps/scope/product/backend/records/dossier.py#L382) |  |  |
| [_field](../apps/scope/product/backend/records/dossier.py#L394) | key, override_key |  |
| [save_and_recompute](../apps/scope/product/backend/records/dossier.py#L516) | contractor_id | Read dossier, compute canvas, write canvas back, return canvas. |
| [_row_to_contractor](../apps/scope/product/backend/records/dossier.py#L557) | row |  |
| [_parse_ts](../apps/scope/product/backend/records/dossier.py#L572) | raw |  |

### apps/scope/product/backend/records/leads.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [save_lead](../apps/scope/product/backend/records/leads.py#L39) | name, whatsapp, location | Insert a new lead row. |
| [patch_lead_structured](../apps/scope/product/backend/records/leads.py#L128) | phone | Embed a JSON blob into ``cs_leads.chat_summary`` via the ``---LEO_STRUCTURED---`` marker. |
| [get_lead_by_phone](../apps/scope/product/backend/records/leads.py#L207) | phone | Fetch the most-recent ``cs_leads`` row for a phone number. |
| [_row_to_lead](../apps/scope/product/backend/records/leads.py#L239) | row |  |
| [_parse_ts](../apps/scope/product/backend/records/leads.py#L254) | raw |  |
| [_extract_id](../apps/scope/product/backend/records/leads.py#L265) | resp |  |

### apps/scope/product/backend/records/proposals.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [store_proposal](../apps/scope/product/backend/records/proposals.py#L53) | skill_name, action, reason | Insert a proposal row. |
| [get_similar_proposals](../apps/scope/product/backend/records/proposals.py#L131) | skill_name, action | Fetch pending + draft proposals for the same ``(skill_name, action)``. |
| [resolve_proposal](../apps/scope/product/backend/records/proposals.py#L165) | proposal_id, status | Set ``status`` + ``resolved_at`` (``None`` if ``status="draft"``). |
| [fetch_pending_proposals](../apps/scope/product/backend/records/proposals.py#L207) | limit | List pending proposals, newest first. |
| [fetch_proposal_by_id](../apps/scope/product/backend/records/proposals.py#L233) | proposal_id | Single proposal by full id. ``None`` if not found. |
| [resolve_proposal_for_founder](../apps/scope/product/backend/records/proposals.py#L259) | short_opt | Pick the pending proposal whose short-ref matches ``short_opt``. |
| [parse_founder_skill_reply](../apps/scope/product/backend/records/proposals.py#L278) | text | Pure parser. Classifies a founder's WA reply into one of four :class:`SkillReplyIntent.action` values. |
| [proposal_short_id](../apps/scope/product/backend/records/proposals.py#L323) | full_id | First 8 hex of a UUID (dashes stripped, lowercased). |
| [_row_to_proposal](../apps/scope/product/backend/records/proposals.py#L333) | row |  |
| [_as_dict](../apps/scope/product/backend/records/proposals.py#L362) | value |  |
| [_parse_ts](../apps/scope/product/backend/records/proposals.py#L368) | raw |  |

### apps/scope/product/backend/routes/admin.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [create_api_key](../apps/scope/product/backend/routes/admin.py#L44) | body | Generate a new API key and store it. Returns the key (only shown once). |
| [list_api_keys](../apps/scope/product/backend/routes/admin.py#L78) |  | List all active API keys (keys are masked). |
| [deactivate_api_key](../apps/scope/product/backend/routes/admin.py#L96) | key_id | Deactivate an API key by ID (soft delete). |
| [get_customer_360](../apps/scope/product/backend/routes/admin.py#L116) | phone | Aggregate all available data for a customer identified by phone number. |

### apps/scope/product/backend/routes/canvas.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_job_by_token](../apps/scope/product/backend/routes/canvas.py#L40) | token |  |
| [_get_contractor_display](../apps/scope/product/backend/routes/canvas.py#L53) | contractor_id | Fetch contractor name and trade for display in the tracking page. |
| [_get_quote_by_token](../apps/scope/product/backend/routes/canvas.py#L76) | token |  |
| [api_get_canvas](../apps/scope/product/backend/routes/canvas.py#L92) | token | Return canvas data for a shareable URL. |
| [api_finalize_quote](../apps/scope/product/backend/routes/canvas.py#L170) | req, ctx, caller | Persist a finalized quote to Supabase and return a shareable URL. |
| [api_list_quotes](../apps/scope/product/backend/routes/canvas.py#L257) | contractor_id | List all quotes for a contractor, most recent first. |
| [api_update_quote](../apps/scope/product/backend/routes/canvas.py#L329) | req, caller | Update an existing quote row by token. |
| [api_claim_profile](../apps/scope/product/backend/routes/canvas.py#L373) | req | Link a contractor profile to a Supabase auth user (claim flow). |
| [get_contractor_by_auth_user](../apps/scope/product/backend/routes/canvas.py#L430) | auth_user_id | Look up a claimed contractor by their Supabase auth user ID. |
| [api_set_phone](../apps/scope/product/backend/routes/canvas.py#L486) | req | Store phone number on a contractor record and kick off social proof. |
| [get_homeowner_quotes](../apps/scope/product/backend/routes/canvas.py#L515) | email, limit | Return all quotes for a homeowner email, ordered by created_at DESC. |

### apps/scope/product/backend/routes/chat.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [chat](../apps/scope/product/backend/routes/chat.py#L35) | request | Body: {   "messages": [{"role":"user","text":"...","images":[{"data":"b64","media_type":"image/jpeg"}]}, ...],   "mode": "early_access" / "general" / "scope_intake" / "sales"   (optional),   "audience": "homeowner" / "agent" / "professional"     (optional, default homeowner),   "lead_context": "..."                 (optional; location/flow hints),   "profile_context": "..."              (optional; |
| [_build_leo_messages](../apps/scope/product/backend/routes/chat.py#L174) | raw_msgs | Convert raw frontend messages to LeoMessages with media attachments. |
| [_lang_fallback](../apps/scope/product/backend/routes/chat.py#L215) | msgs |  |

### apps/scope/product/backend/routes/chatwoot.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_cw](../apps/scope/product/backend/routes/chatwoot.py#L50) | method, path | Make a Chatwoot API call. Returns parsed JSON or None on error. |
| [get_or_create_contact](../apps/scope/product/backend/routes/chatwoot.py#L65) | phone, name | Find or create a Chatwoot contact by phone number. Returns the Chatwoot contact ID. Normalises the phone to E.164 format (+34...) for consistency. |
| [get_or_create_conversation](../apps/scope/product/backend/routes/chatwoot.py#L104) | contact_id | Find the most recent open conversation for this contact in our inbox, or create a new one. Returns the Chatwoot conversation ID. |
| [push_message_to_chatwoot](../apps/scope/product/backend/routes/chatwoot.py#L132) | phone, name, text, message_type | Push a message to the Chatwoot conversation for this phone number. |
| [chatwoot_outbound_webhook](../apps/scope/product/backend/routes/chatwoot.py#L184) | request | Chatwoot fires this when any message is created on the WhatsApp inbox. We only care about 'outgoing' messages (agent replies) that aren't private notes. Those get forwarded to the customer via Meta WhatsApp Cloud API. |
| [_forward_to_whatsapp](../apps/scope/product/backend/routes/chatwoot.py#L252) | phone_digits, content, conv_id | Forward a Chatwoot agent reply to WhatsApp via Meta Cloud API. |

### apps/scope/product/backend/routes/dispute.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_quote](../apps/scope/product/backend/routes/dispute.py#L38) | token |  |
| [_get_contractor](../apps/scope/product/backend/routes/dispute.py#L50) | contractor_id |  |
| [open_dispute](../apps/scope/product/backend/routes/dispute.py#L74) | req, ctx | Open a dispute on a milestone. Creates a Chatwoot conversation with full context. |
| [_store_dispute](../apps/scope/product/backend/routes/dispute.py#L209) | quote_token, milestone_index, conversation_id, reason, homeowner_phone, is_sandbox | Store dispute record in Supabase for tracking. |
| [reply_to_dispute](../apps/scope/product/backend/routes/dispute.py#L247) | req, ctx | Send a message in a dispute conversation. |
| [get_disputes](../apps/scope/product/backend/routes/dispute.py#L285) | quote_token | Get all disputes for a quote. |

### apps/scope/product/backend/routes/documents.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_quote](../apps/scope/product/backend/routes/documents.py#L47) | quote_token |  |
| [_get_contractor](../apps/scope/product/backend/routes/documents.py#L59) | contractor_id |  |
| [_milestone_amount_cents](../apps/scope/product/backend/routes/documents.py#L71) | m |  |
| [_parse_release_date](../apps/scope/product/backend/routes/documents.py#L82) | value |  |
| [_quote_payload](../apps/scope/product/backend/routes/documents.py#L91) | quote, contractor | Build the typed :class:`QuotePayload` for :class:`AgreementDoc`. |
| [_invoice_payload](../apps/scope/product/backend/routes/documents.py#L143) | quote, contractor, milestone_updates | Typed :class:`InvoicePayload` for :class:`InvoiceDoc`. |
| [_base_url](../apps/scope/product/backend/routes/documents.py#L201) |  |  |
| [record_consent](../apps/scope/product/backend/routes/documents.py#L220) | quote_token, req, request | Record pre-payment consent for a scope agreement. |
| [get_agreement](../apps/scope/product/backend/routes/documents.py#L287) | quote_token, format | Render the construction agreement as HTML or PDF. |
| [get_invoice](../apps/scope/product/backend/routes/documents.py#L308) | quote_token, format | Render the job invoice as HTML or PDF. Only valid when scope is complete. |

### apps/scope/product/backend/routes/events.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [track_event](../apps/scope/product/backend/routes/events.py#L43) | req | Ingest an activity event from the frontend. |

### apps/scope/product/backend/routes/extract_doc.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [extract_doc](../apps/scope/product/backend/routes/extract_doc.py#L31) | file | Extract text from PDF/DOCX as Markdown (tables preserved). |

### apps/scope/product/backend/routes/job_inbox.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_generate_inbox_token](../apps/scope/product/backend/routes/job_inbox.py#L65) |  |  |
| [create_job](../apps/scope/product/backend/routes/job_inbox.py#L69) | brief, homeowner_phone, homeowner_user_id, brief_photos | Create a new job and return the row including inbox_token. |
| [get_job_by_token](../apps/scope/product/backend/routes/job_inbox.py#L104) | token |  |
| [get_job_by_id](../apps/scope/product/backend/routes/job_inbox.py#L119) | job_id |  |
| [update_job](../apps/scope/product/backend/routes/job_inbox.py#L134) | job_id, updates |  |
| [get_active_job_for_phone](../apps/scope/product/backend/routes/job_inbox.py#L146) | homeowner_phone | Return the most recent active job for a homeowner phone number. |
| [add_response](../apps/scope/product/backend/routes/job_inbox.py#L184) | job_id, data |  |
| [update_response](../apps/scope/product/backend/routes/job_inbox.py#L221) | response_id, updates |  |
| [get_responses_for_job](../apps/scope/product/backend/routes/job_inbox.py#L233) | job_id |  |
| [find_response_by_phone](../apps/scope/product/backend/routes/job_inbox.py#L251) | job_id, phone | Find an existing response for a contractor phone on a job. |
| [find_job_for_contractor_phone](../apps/scope/product/backend/routes/job_inbox.py#L273) | phone | Find the most recent active job that has an outreach to this contractor. |
| [rank_responses](../apps/scope/product/backend/routes/job_inbox.py#L300) | job_id | AI-rank all responses for a job against the brief. Returns updated responses. |
| [api_create_job](../apps/scope/product/backend/routes/job_inbox.py#L381) | req |  |
| [api_get_inbox](../apps/scope/product/backend/routes/job_inbox.py#L397) | token |  |
| [api_add_response](../apps/scope/product/backend/routes/job_inbox.py#L437) | job_id, req |  |
| [api_update_response](../apps/scope/product/backend/routes/job_inbox.py#L447) | job_id, response_id, updates |  |
| [api_rank_responses](../apps/scope/product/backend/routes/job_inbox.py#L465) | job_id |  |
| [api_update_job](../apps/scope/product/backend/routes/job_inbox.py#L471) | job_id, updates |  |
| [_get_ops_token](../apps/scope/product/backend/routes/job_inbox.py#L487) |  |  |
| [api_approve_outreach](../apps/scope/product/backend/routes/job_inbox.py#L498) | token | Homeowner approves a contractor's outreach — marks the job as 'contractor_selected' and updates the job status so the contractor knows they were chosen. Called from the homeowner inbox when they tap "Approve" on a response. |
| [api_ops_dashboard](../apps/scope/product/backend/routes/job_inbox.py#L530) | token | Founder-only ops view: all jobs, all outreach, all responses. |

### apps/scope/product/backend/routes/landing_leads.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_supabase_insert](../apps/scope/product/backend/routes/landing_leads.py#L39) | table, data | Insert a row via Supabase REST API. |
| [_normalize_phone_e164](../apps/scope/product/backend/routes/landing_leads.py#L59) | phone, require_spanish | Parse and normalise a phone number to E.164. |
| [_supabase_get_landing_lead](../apps/scope/product/backend/routes/landing_leads.py#L75) | lead_id |  |
| [_insert_cs_lead_onboarding](../apps/scope/product/backend/routes/landing_leads.py#L91) |  |  |
| [_supabase_update](../apps/scope/product/backend/routes/landing_leads.py#L132) | table, row_id, data | Update a row via Supabase REST API. |
| [_transcribe_audio](../apps/scope/product/backend/routes/landing_leads.py#L152) | audio_bytes, content_type | Transcribe audio via ``packages/voice``. |
| [_polish_and_update](../apps/scope/product/backend/routes/landing_leads.py#L182) | lead_id, raw_text | Background: polish transcript with LLM and update the DB row. |
| [submit_lead](../apps/scope/product/backend/routes/landing_leads.py#L205) | background_tasks, job_text, audio, transcript_polished |  |
| [add_phone](../apps/scope/product/backend/routes/landing_leads.py#L266) | request, lead_id, phone, audience, display_name, locale, location, job_description, chat_summary_extra, user_id |  |
| [upload_photos](../apps/scope/product/backend/routes/landing_leads.py#L458) | lead_id, photos | Upload one or more photos for a lead. Saves locally, stores URLs in Supabase. |
| [update_lead](../apps/scope/product/backend/routes/landing_leads.py#L503) | lead_id, location, chat_history, job_description | Update a lead with location, chat history, or refined job description. |
| [check_whatsapp](../apps/scope/product/backend/routes/landing_leads.py#L538) | request | Check whether a phone number is registered on WhatsApp. |

### apps/scope/product/backend/routes/marketplace.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_check_token](../apps/scope/product/backend/routes/marketplace.py#L36) | token |  |
| [_parse_skill](../apps/scope/product/backend/routes/marketplace.py#L106) | path |  |
| [_scan_skills](../apps/scope/product/backend/routes/marketplace.py#L140) | base, source |  |
| [_enabled_skill_dirs](../apps/scope/product/backend/routes/marketplace.py#L157) |  |  |
| [_toolset_config](../apps/scope/product/backend/routes/marketplace.py#L165) |  |  |
| [_leo_overlap](../apps/scope/product/backend/routes/marketplace.py#L175) | name | Return the Leo capability ID that covers this community skill, if any. |
| [marketplace_page](../apps/scope/product/backend/routes/marketplace.py#L187) | token |  |
| [marketplace_state](../apps/scope/product/backend/routes/marketplace.py#L196) | token |  |
| [marketplace_community](../apps/scope/product/backend/routes/marketplace.py#L242) | token, q, limit | Search community skills via skills.sh with real install counts + Leo overlap info. |
| [toggle_capability](../apps/scope/product/backend/routes/marketplace.py#L290) | token, id |  |
| [_toggle_skill](../apps/scope/product/backend/routes/marketplace.py#L297) | skill_dir |  |
| [_toggle_toolset](../apps/scope/product/backend/routes/marketplace.py#L317) | tid |  |

### apps/scope/product/backend/routes/messages.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [send_message](../apps/scope/product/backend/routes/messages.py#L42) | req, ctx, caller | Insert a message to job_messages. Supabase Realtime handles delivery. |
| [get_messages](../apps/scope/product/backend/routes/messages.py#L116) | quote_token, limit, caller | Return this authenticated project party’s message history. |

### apps/scope/product/backend/routes/meta_whatsapp.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_markdown_to_whatsapp](../apps/scope/product/backend/routes/meta_whatsapp.py#L85) | text | Convert common markdown to WhatsApp-native formatting. |
| [_split_wa_reply](../apps/scope/product/backend/routes/meta_whatsapp.py#L94) | text, max_chars | Split a long reply into natural WhatsApp-sized messages. |
| [_get_phone_lock](../apps/scope/product/backend/routes/meta_whatsapp.py#L162) | phone |  |
| [retry_orphaned_messages](../apps/scope/product/backend/routes/meta_whatsapp.py#L177) |  | Called on server startup. Finds user messages that never got a reply (server died mid-processing) and replays them. Returns count of retried conversations. |
| [_debounce_reply](../apps/scope/product/backend/routes/meta_whatsapp.py#L260) | phone, contact_name, msg | Buffer an inbound message.  After DEBOUNCE_WINDOW_SECS of quiet from this phone, fire one _auto_reply_wa with all accumulated messages merged. Typing indicator fires immediately on the first message so the user sees feedback during the debounce wait. |
| [_delayed_typing](../apps/scope/product/backend/routes/meta_whatsapp.py#L273) |  |  |
| [_fire](../apps/scope/product/backend/routes/meta_whatsapp.py#L282) |  |  |
| [_get_token](../apps/scope/product/backend/routes/meta_whatsapp.py#L325) |  |  |
| [_get_phone_id](../apps/scope/product/backend/routes/meta_whatsapp.py#L329) |  |  |
| [_download_meta_media](../apps/scope/product/backend/routes/meta_whatsapp.py#L333) | media_id | Download a media file from Meta Cloud API, save it to MEDIA_DIR, and return {"url": public_url, "mime": mime_type, "filename": fname}. Returns None on any failure. |
| [_store_message](../apps/scope/product/backend/routes/meta_whatsapp.py#L384) | phone_number, role, text, message_type, media_urls, media_types, wa_message_id, reply_to_wa_id, reply_to_text | Insert a message into whatsapp_messages via Supabase REST. Delegates to the unified send_wa.store_message() function. |
| [_onboarding_body_text](../apps/scope/product/backend/routes/meta_whatsapp.py#L420) | audience, display_name, locale, location_suffix | Short confirmation copy for the first WhatsApp message after phone capture. Goal: get the user to reply (opens 24-hour free messaging window). Rich follow-up details are sent by Hermes when the user replies. |
| [send_onboarding_wa_message](../apps/scope/product/backend/routes/meta_whatsapp.py#L458) | phone, audience, display_name, locale, location_suffix | First WhatsApp after user submits phone on the landing flow. Delegates to unified send_wa_message() for template/text routing. Stores outbound in whatsapp_messages and upserts whatsapp_user_profiles. |
| [_lookup_lead](../apps/scope/product/backend/routes/meta_whatsapp.py#L524) | phone | Look up a user in cs_leads by their WhatsApp number. |
| [_extract_contractor_voice_response](../apps/scope/product/backend/routes/meta_whatsapp.py#L550) | phone, transcript, voice_url | If this phone belongs to a contractor with an active job outreach, extract reaction/needs/availability from the transcript via LLM and update the response. |
| [_transcribe_local_file](../apps/scope/product/backend/routes/meta_whatsapp.py#L608) | fpath | Transcribe an audio file — delegates to the unified enrich module. |
| [_send_typing_indicator](../apps/scope/product/backend/routes/meta_whatsapp.py#L614) | wa_msg_id | Show 'typing...' in the user's WhatsApp chat for up to 25 seconds. |
| [_auto_reply_wa](../apps/scope/product/backend/routes/meta_whatsapp.py#L643) | phone, contact_name, user_text, msg_type, media_urls, media_types, wa_msg_id | Fetch full conversation history, call the CS agent, and send the reply back via WhatsApp. Runs as a background task so the webhook responds quickly to Meta. |
| [meta_whatsapp_verify](../apps/scope/product/backend/routes/meta_whatsapp.py#L947) | request | Meta sends a GET with hub.mode, hub.verify_token, hub.challenge. We echo back hub.challenge if the token matches. |
| [meta_whatsapp_webhook](../apps/scope/product/backend/routes/meta_whatsapp.py#L970) | request | Receive inbound WhatsApp messages from Meta Cloud API. Store in Supabase.  No AI processing — pure proxy. |
| [list_conversations](../apps/scope/product/backend/routes/meta_whatsapp.py#L1324) |  | List distinct phone numbers with their most recent message + display name. |
| [get_messages](../apps/scope/product/backend/routes/meta_whatsapp.py#L1370) | phone, limit, after | Get messages for a specific phone number, ordered by time. Pass `after` (ISO timestamp) for polling new messages. |
| [send_message](../apps/scope/product/backend/routes/meta_whatsapp.py#L1406) | request | Send a WhatsApp message from the Leo Copilot app. |
| [send_template](../apps/scope/product/backend/routes/meta_whatsapp.py#L1518) | request | Send a WhatsApp template message to initiate a conversation. |
| [serve_media](../apps/scope/product/backend/routes/meta_whatsapp.py#L1590) | filename | Serve a media file that was downloaded from Meta. |
| [upload_voice](../apps/scope/product/backend/routes/meta_whatsapp.py#L1602) | to, audio | Upload a voice note from the Leo Copilot app, save to disk, convert to OGG Opus (WhatsApp requirement), send via Meta Cloud API, and store in Supabase. |
| [upload_media](../apps/scope/product/backend/routes/meta_whatsapp.py#L1731) | to, media, caption | Upload any media from the Leo Copilot app, save to disk, send via Meta Cloud API, and store in Supabase. |

### apps/scope/product/backend/routes/milestone.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_quote](../apps/scope/product/backend/routes/milestone.py#L60) | quote_token |  |
| [_get_contractor](../apps/scope/product/backend/routes/milestone.py#L72) | contractor_id |  |
| [_patch_quote](../apps/scope/product/backend/routes/milestone.py#L84) | quote_token, data |  |
| [_insert_notification](../apps/scope/product/backend/routes/milestone.py#L94) | user_id, quote_token, notif_type, milestone_index | Insert a notification row (in-app bell). Table uses scope_token column. |
| [_send_whatsapp](../apps/scope/product/backend/routes/milestone.py#L109) | phone, message, suppress | Send WhatsApp message via the unified send_wa stack. |
| [send_notification](../apps/scope/product/backend/routes/milestone.py#L132) | user_id, quote_token, notif_type, milestone_index, phone, whatsapp_message, suppress_wa | Insert in-app notification and optionally send WhatsApp. |
| [_app_base_url](../apps/scope/product/backend/routes/milestone.py#L151) |  |  |
| [_tracking_url](../apps/scope/product/backend/routes/milestone.py#L155) | quote_token, homeowner_email | Build tracking page URL with optional email pre-fill for faster homeowner login. |
| [submit_proof](../apps/scope/product/backend/routes/milestone.py#L178) | req, ctx | Contractor submits proof photos + note for a milestone. |
| [release_milestone](../apps/scope/product/backend/routes/milestone.py#L273) | req, ctx | Homeowner approves a milestone and releases funds from escrow. |
| [create_variation](../apps/scope/product/backend/routes/milestone.py#L445) | req, ctx | Contractor proposes a change order / variation. |
| [approve_variation](../apps/scope/product/backend/routes/milestone.py#L501) | req, ctx | Homeowner approves a variation — creates new Stripe Checkout for the extra amount. |
| [decline_variation](../apps/scope/product/backend/routes/milestone.py#L579) | req, ctx | Homeowner declines a variation. |
| [cancel_job](../apps/scope/product/backend/routes/milestone.py#L643) | req, ctx | Cancel a job and issue full refund via Stripe. |
| [create_review](../apps/scope/product/backend/routes/milestone.py#L734) | req | Homeowner submits review after job completion. |
| [get_notifications](../apps/scope/product/backend/routes/milestone.py#L796) | user_id, limit | Returns notifications for a user, newest first. |
| [mark_notifications_read](../apps/scope/product/backend/routes/milestone.py#L817) | req | Mark notification IDs as read. |
| [get_milestone_updates](../apps/scope/product/backend/routes/milestone.py#L835) | quote_token | Return all milestone proof submissions for a scope. |
| [get_variation_orders](../apps/scope/product/backend/routes/milestone.py#L851) | quote_token | Return all variation orders for a scope. |

### apps/scope/product/backend/routes/milestones.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [submit_proof](../apps/scope/product/backend/routes/milestones.py#L53) | token, idx, body, caller, ctx | Contractor submits proof photos + note for a milestone. |
| [release_milestone](../apps/scope/product/backend/routes/milestones.py#L143) | token, idx, caller, ctx | Homeowner approves a milestone and releases funds from escrow. |

### apps/scope/product/backend/routes/notifications.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_insert_notification](../apps/scope/product/backend/routes/notifications.py#L32) | user_id, quote_token, notif_type, milestone_index | Insert a notification row (in-app bell). Table uses scope_token column. |
| [send_whatsapp](../apps/scope/product/backend/routes/notifications.py#L55) | phone, message, suppress | Send a WhatsApp message via the unified send_wa stack. |
| [send_notification](../apps/scope/product/backend/routes/notifications.py#L80) | user_id, quote_token, notif_type, milestone_index, phone, whatsapp_message, suppress_wa | Insert in-app notification and optionally deliver via WhatsApp. |
| [get_notifications](../apps/scope/product/backend/routes/notifications.py#L100) | caller, limit | Return notifications for the authenticated user, newest first. |
| [mark_notifications_read](../apps/scope/product/backend/routes/notifications.py#L130) | req, caller | Mark notification IDs as read. Caller must be authenticated. |

### apps/scope/product/backend/routes/pages.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_page](../apps/scope/product/backend/routes/pages.py#L35) | token |  |
| [serve_generated_page](../apps/scope/product/backend/routes/pages.py#L81) | token | Serve a dynamically generated HTML page by token. |

### apps/scope/product/backend/routes/payment.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [api_create_checkout](../apps/scope/product/backend/routes/payment.py#L62) | req, ctx | Create a Stripe Checkout Session for a scope payment. |

### apps/scope/product/backend/routes/profile_import.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_playwright_browser](../apps/scope/product/backend/routes/profile_import.py#L44) |  | Lazy-init a persistent Playwright Chromium browser for SPA scraping. |
| [_render_spa](../apps/scope/product/backend/routes/profile_import.py#L59) | url, wait_seconds, accept_cookies | Render a SPA page with Playwright headless. Returns (page_text, list_of_img_dicts). Each img dict has keys: src, alt, cls. |
| [detect_platform](../apps/scope/product/backend/routes/profile_import.py#L197) | url |  |
| [_discover_platform_links](../apps/scope/product/backend/routes/profile_import.py#L222) | profile | Scan page_chunks + raw_about + website field for links to known directory platforms. |
| [_merge_profile_data](../apps/scope/product/backend/routes/profile_import.py#L270) | target, source | Merge fields from source into target without losing existing data. |
| [cross_pollinate](../apps/scope/product/backend/routes/profile_import.py#L356) | profile | Discover links to other platforms in the profile data and scrape+merge them. |
| [_searxng_search](../apps/scope/product/backend/routes/profile_import.py#L399) | query, max_results | Run a SearXNG JSON search and return result dicts (title, url, content). |
| [enrich_credentials_from_web](../apps/scope/product/backend/routes/profile_import.py#L437) | profile | Search the web for company registration, licenses, and certifications via SearXNG. |
| [_extract_legal_identity](../apps/scope/product/backend/routes/profile_import.py#L628) | website_url | Fetch legal / privacy pages from a Spanish business website and extract NIF, razón social, etc. |
| [_company_name_is_specific](../apps/scope/product/backend/routes/profile_import.py#L677) | name | Check if a company name is specific enough to do a meaningful web credential search. |
| [_is_noise_image](../apps/scope/product/backend/routes/profile_import.py#L781) | src | True if src looks like UI chrome rather than profile/portfolio content. |
| [_image_fingerprint](../apps/scope/product/backend/routes/profile_import.py#L795) | url | Extract a stable fingerprint for dedup — strips resize params and CDN prefixes. |
| [_deduplicate_portfolio](../apps/scope/product/backend/routes/profile_import.py#L810) | profile | Remove noise images and fingerprint-based duplicates in-place. |
| [_is_noise_image_website_portfolio](../apps/scope/product/backend/routes/profile_import.py#L837) | src | Like `_is_noise_image` but keeps many CMS upload URLs that contain substrings like ``logo`` in filenames. |
| [_best_url_from_srcset](../apps/scope/product/backend/routes/profile_import.py#L851) | srcset | Pick the largest candidate URL from an HTML ``srcset`` (``url 400w`` …). |
| [_img_in_excluded_portfolio_region](../apps/scope/product/backend/routes/profile_import.py#L893) | img | True if this ``img`` node sits in aside/footer/nav or (optionally) a related-posts widget. |
| [_add_img_urls_from_node](../apps/scope/product/backend/routes/profile_import.py#L904) | img, base_domain, seen, out |  |
| [add](../apps/scope/product/backend/routes/profile_import.py#L907) | u |  |
| [_collect_image_urls_from_page](../apps/scope/product/backend/routes/profile_import.py#L926) | page, base_domain | Collect ``img`` URLs including lazy-load and ``srcset`` (best resolution). |
| [collect_with](../apps/scope/product/backend/routes/profile_import.py#L941) | related_widgets |  |
| [collect_noise_url_only](../apps/scope/product/backend/routes/profile_import.py#L994) |  | No DOM scoping — only ``_is_noise_image_website_portfolio`` filters URLs. |
| [_playwright_collect_project_detail_images](../apps/scope/product/backend/routes/profile_import.py#L1105) | page, url_allow | Images for a single project detail URL using heading/section cutoffs + fallbacks. |
| [_meta_content](../apps/scope/product/backend/routes/profile_import.py#L1155) | page |  |
| [_extract_jsonld_business_fields](../apps/scope/product/backend/routes/profile_import.py#L1165) | page | Pull name / phone / description / logo from JSON-LD Organization/LocalBusiness blocks. |
| [_should_skip_internal_path](../apps/scope/product/backend/routes/profile_import.py#L1239) | path |  |
| [_internal_path_priority](../apps/scope/product/backend/routes/profile_import.py#L1251) | path | Higher = crawl first (portfolio / about / services). |
| [_canonical_internal_url](../apps/scope/product/backend/routes/profile_import.py#L1285) | parsed | Same page identity: scheme + host + path + query, no fragment. |
| [_discover_internal_urls](../apps/scope/product/backend/routes/profile_import.py#L1296) | seed_url, page, base_parsed | Collect same-host links, filter junk, sort by relevance. |
| [_hostname](../apps/scope/product/backend/routes/profile_import.py#L1328) | url |  |
| [_is_noise_external_link](../apps/scope/product/backend/routes/profile_import.py#L1335) | href |  |
| [extract_business_website_from_habitissimo](../apps/scope/product/backend/routes/profile_import.py#L1342) | page, body_text | Find the pro's own website from the Habitissimo profile DOM + text. |
| [_parse_habitissimo_reviews_from_text](../apps/scope/product/backend/routes/profile_import.py#L1378) | rev_text | Parse reviews from the rendered text of a Habitissimo profile page. |
| [_discover_opinion_urls](../apps/scope/product/backend/routes/profile_import.py#L1441) | base, first_page | Follow pagination / opinion links on the first opinions page. |
| [scrape_habitissimo_reviews](../apps/scope/product/backend/routes/profile_import.py#L1460) | base_url, first_opiniones_page | Aggregate reviews from first page + linked opinion/pagination pages. |
| [add_batch](../apps/scope/product/backend/routes/profile_import.py#L1466) | revs |  |
| [_parse_habitissimo_project_page](../apps/scope/product/backend/routes/profile_import.py#L1517) | page_url |  |
| [scrape_habitissimo_projects](../apps/scope/product/backend/routes/profile_import.py#L1548) | base_url, proj_page | Collect project cards + per-project detail pages when links exist. |
| [merge_website_into_profile](../apps/scope/product/backend/routes/profile_import.py#L1590) | profile, website_url, max_pages | Crawl a business website and merge images + text into an existing profile. Used after Habitissimo/Houzz when a public website URL is known. |
| [_habi_render_page](../apps/scope/product/backend/routes/profile_import.py#L1670) | ctx, url, wait_seconds, keep_open | Render one Habitissimo page in an existing browser context. |
| [_habi_load_env_credentials](../apps/scope/product/backend/routes/profile_import.py#L1727) |  |  |
| [_habi_refresh_session_if_needed](../apps/scope/product/backend/routes/profile_import.py#L1744) | ctx | Ensure module-level _habi_session has a valid JWT. |
| [_habi_inject_cookies](../apps/scope/product/backend/routes/profile_import.py#L1860) | ctx, token, awsalb |  |
| [_habi_extract_phone_from_modal](../apps/scope/product/backend/routes/profile_import.py#L1884) | html | Parse real phone number from /do_ajax/business_modal_contact response HTML. |
| [_habi_reveal_phone](../apps/scope/product/backend/routes/profile_import.py#L1904) | page_or_slug, base_url_or_none | Reveal the real phone number via Habitissimo's AJAX endpoint. |
| [_habi_reveal_phone_httpx](../apps/scope/product/backend/routes/profile_import.py#L1942) | slug, token, awsalb, session_rh | Fire the Habitissimo AJAX contact endpoint via httpx to get the real phone. |
| [scrape_habitissimo](../apps/scope/product/backend/routes/profile_import.py#L1986) | url, merge_external_site |  |
| [_parse_habi_main_page](../apps/scope/product/backend/routes/profile_import.py#L2097) | profile, text, imgs_raw | Extract name, trade, location, rating, review count, description, Q&A from main page. |
| [_parse_habi_fotos](../apps/scope/product/backend/routes/profile_import.py#L2210) | profile, imgs_raw | Extract gallery images from the /fotos page. |
| [_parse_habi_proyectos](../apps/scope/product/backend/routes/profile_import.py#L2226) | profile, text, imgs_raw | Extract project titles and images from the /proyectos page. |
| [_habi_enrich_projects](../apps/scope/product/backend/routes/profile_import.py#L2276) | ctx, profile, base_url | Use the already-open Playwright context to fetch each Habi project detail page for its images. |
| [_habi_allow](../apps/scope/product/backend/routes/profile_import.py#L2320) | u |  |
| [_parse_habi_opiniones](../apps/scope/product/backend/routes/profile_import.py#L2339) | profile, text | Parse reviews from the rendered /opiniones page text. |
| [_extract_houzz_about_from_body](../apps/scope/product/backend/routes/profile_import.py#L2411) | body_text | Extract the 'Sobre nosotros' / 'About Us' blurb from Houzz profile body text. |
| [_houzz_fetch_about_playwright](../apps/scope/product/backend/routes/profile_import.py#L2447) | profile_url | Render the Houzz profile in a browser, open the About tab if needed, read full about text. |
| [_best_description_from_homepage](../apps/scope/product/backend/routes/profile_import.py#L2501) | page | Pick the longest useful homepage description (meta, og:, JSON-LD). |
| [_houzz_enrich_projects](../apps/scope/product/backend/routes/profile_import.py#L2520) | profile, max_projects | Use Playwright to discover project links from the profile page and scrape their images. |
| [_houzz_allow](../apps/scope/product/backend/routes/profile_import.py#L2584) | u |  |
| [_houzz_fetch_page](../apps/scope/product/backend/routes/profile_import.py#L2611) | url | Fetch a Houzz page via curl_cffi (TLS impersonation) — scrapling's Fetcher gets 404'd. |
| [scrape_houzz](../apps/scope/product/backend/routes/profile_import.py#L2620) | url |  |
| [scrape_cronoshare](../apps/scope/product/backend/routes/profile_import.py#L3045) | url | Scrape a CronoShare professional profile (cronoshare.com/croner-*). |
| [_parse_cronoshare_reviews](../apps/scope/product/backend/routes/profile_import.py#L3221) | profile, text, page | Parse client reviews from a CronoShare profile page. |
| [_hogami_slug_from_url](../apps/scope/product/backend/routes/profile_import.py#L3290) | url |  |
| [scrape_hogami](../apps/scope/product/backend/routes/profile_import.py#L3296) | url |  |
| [_extract_emails_from_page](../apps/scope/product/backend/routes/profile_import.py#L3423) | page | Pull email addresses from mailto: links and visible text. |
| [scrape_website](../apps/scope/product/backend/routes/profile_import.py#L3433) | url | Crawl the entry URL plus prioritized same-site pages; store per-page chunks for LLM structuring. |
| [_add_images](../apps/scope/product/backend/routes/profile_import.py#L3449) | urls |  |
| [_get_bedrock](../apps/scope/product/backend/routes/profile_import.py#L3608) |  |  |
| [_text_from_converse](../apps/scope/product/backend/routes/profile_import.py#L3612) | response |  |
| [_openrouter_chat](../apps/scope/product/backend/routes/profile_import.py#L3621) | system, user, max_tokens, temperature | Fallback LLM call via the ``llm`` package when Bedrock fails. |
| [_converse_with_fallback](../apps/scope/product/backend/routes/profile_import.py#L3701) | system, user | Try Bedrock Converse, fall back to OpenRouter on any failure. |
| [structure_profile_with_llm](../apps/scope/product/backend/routes/profile_import.py#L3742) | profile | Structure the raw crawl with LLM. Tries Bedrock first, falls back to OpenRouter. |
| [summarize_reviews_with_llm](../apps/scope/product/backend/routes/profile_import.py#L3874) | profile | Fill ``review_summary`` from ``profile.reviews`` via Bedrock (objective overview). |
| [_run_social_proof_background_by_id](../apps/scope/product/backend/routes/profile_import.py#L3935) | contractor_id, phone | Run social proof when we have a contractor ID + phone but no ProfileResult in memory. |
| [_run_social_proof_background](../apps/scope/product/backend/routes/profile_import.py#L3982) | result, contractor_id | Run the slow social proof search after canvas delivery. |
| [_stream_scrape](../apps/scope/product/backend/routes/profile_import.py#L4015) | url, contractor_id | Generator that yields SSE events during scraping. |
| [_strip_cc](../apps/scope/product/backend/routes/profile_import.py#L4142) | p |  |
| [profile_import](../apps/scope/product/backend/routes/profile_import.py#L4193) | req | Scrape a tradesperson profile. Returns SSE stream with progress + result. |
| [profile_import_sync](../apps/scope/product/backend/routes/profile_import.py#L4210) | req | Synchronous version — scrapes and returns profile JSON directly. |

### apps/scope/product/backend/routes/projects.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [get_quote](../apps/scope/product/backend/routes/projects.py#L42) | quote_token | Fetch a quote row by token. Raises 404 if not found. |
| [get_contractor](../apps/scope/product/backend/routes/projects.py#L55) | contractor_id | Fetch a contractor row by id. Raises 404 if not found. |
| [patch_quote](../apps/scope/product/backend/routes/projects.py#L68) | quote_token, data |  |
| [app_base_url](../apps/scope/product/backend/routes/projects.py#L78) |  |  |
| [tracking_url](../apps/scope/product/backend/routes/projects.py#L82) | quote_token, homeowner_email | Build the homeowner-facing project tracking URL with optional email pre-fill. |
| [get_project](../apps/scope/product/backend/routes/projects.py#L96) | token, caller | Return project data. Public read — auth resolves role-specific visibility. |
| [cancel_project](../apps/scope/product/backend/routes/projects.py#L142) | token, req, caller, ctx | Cancel a project and issue a full Stripe refund. |

### apps/scope/product/backend/routes/resend_inbound.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_b64decode_secret](../apps/scope/product/backend/routes/resend_inbound.py#L38) | secret |  |
| [_parse_svix_signatures](../apps/scope/product/backend/routes/resend_inbound.py#L46) | signature_header | Extract all v1 signatures from the svix-signature header. Format: "v1,BASE64SIG" or "v1,BASE64SIG v1,BASE64SIG2" |
| [_verify_resend_webhook](../apps/scope/product/backend/routes/resend_inbound.py#L63) |  |  |
| [_extract_email_address](../apps/scope/product/backend/routes/resend_inbound.py#L110) | from_field |  |
| [_clean_reply_text](../apps/scope/product/backend/routes/resend_inbound.py#L117) | body | Strip common email reply cruft (quoted text, signatures) to get the actual reply. |
| [_format_wa_notification](../apps/scope/product/backend/routes/resend_inbound.py#L136) | from_addr, subject, body | Format an inbound email as a WhatsApp notification to the founder. |
| [_send_wa_notification](../apps/scope/product/backend/routes/resend_inbound.py#L148) | phone, text | Send a WhatsApp text message via unified send_wa_message. |
| [_store_inbound_email](../apps/scope/product/backend/routes/resend_inbound.py#L163) | from_addr, to_addrs, subject, body, raw_payload | Store the inbound email in Supabase for audit trail. |
| [resend_inbound_webhook](../apps/scope/product/backend/routes/resend_inbound.py#L206) | request | Resend inbound MX webhook. |
| [_auto_reply_email](../apps/scope/product/backend/routes/resend_inbound.py#L269) | from_addr, from_field, subject, body | Process inbound email through Leo agent and send a reply email back. |

### apps/scope/product/backend/routes/reviews.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [create_review](../apps/scope/product/backend/routes/reviews.py#L32) | token, req, caller | Homeowner submits a review after job completion. |

### apps/scope/product/backend/routes/search_instagram.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_save_instagram_csv](../apps/scope/product/backend/routes/search_instagram.py#L28) | trade, city, profiles | Save Instagram profiles to CSV in the same reports/ dir the sales tracker reads. |
| [search_instagram_profiles](../apps/scope/product/backend/routes/search_instagram.py#L57) | trade, city, save_csv | Search Instagram for tradespeople profiles matching trade + city. Extract phone numbers from bios and linked websites. |
| [search_instagram_batch](../apps/scope/product/backend/routes/search_instagram.py#L96) | trades, cities | Batch search Instagram for multiple trade + city combinations. Runs them concurrently (up to 3 in parallel). |
| [_one](../apps/scope/product/backend/routes/search_instagram.py#L114) | trade, city |  |

### apps/scope/product/backend/routes/stripe_connect.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_stripe_key](../apps/scope/product/backend/routes/stripe_connect.py#L42) |  |  |
| [_get_webhook_secret](../apps/scope/product/backend/routes/stripe_connect.py#L50) |  |  |
| [_get_webhook_secret_test](../apps/scope/product/backend/routes/stripe_connect.py#L58) |  |  |
| [_get_contractor](../apps/scope/product/backend/routes/stripe_connect.py#L68) | contractor_id |  |
| [_patch_contractor](../apps/scope/product/backend/routes/stripe_connect.py#L83) | contractor_id, updates |  |
| [api_create_stripe_account](../apps/scope/product/backend/routes/stripe_connect.py#L105) | req, ctx | Create a Stripe Connect Express account for a contractor. |
| [api_create_account_link](../apps/scope/product/backend/routes/stripe_connect.py#L203) | req | Generate a Stripe Connect onboarding URL for a contractor. |
| [api_get_account_status](../apps/scope/product/backend/routes/stripe_connect.py#L249) | contractor_id | Check the Stripe Connect onboarding status for a contractor. |
| [api_stripe_webhook](../apps/scope/product/backend/routes/stripe_connect.py#L310) | request | Handle Stripe Connect webhook events (live + test/sandbox mode). |

### apps/scope/product/backend/routes/transcribe.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [transcribe_audio](../apps/scope/product/backend/routes/transcribe.py#L32) | audio, polish, provider, language |  |
| [polish_text](../apps/scope/product/backend/routes/transcribe.py#L81) | text | Polish raw Whisper text with Bedrock LLM. No re-transcription. |

### apps/scope/product/backend/routes/transcribe_stream.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_build_deepgram_url](../apps/scope/product/backend/routes/transcribe_stream.py#L62) | overrides |  |
| [transcribe_stream](../apps/scope/product/backend/routes/transcribe_stream.py#L68) | ws | WebSocket proxy: browser audio → Deepgram → transcript events back to browser. |
| [browser_to_deepgram](../apps/scope/product/backend/routes/transcribe_stream.py#L133) |  | Forward raw audio bytes from browser → Deepgram. |
| [deepgram_to_browser](../apps/scope/product/backend/routes/transcribe_stream.py#L163) |  | Forward Deepgram transcript events → browser. |

### apps/scope/product/backend/routes/variations.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [create_variation](../apps/scope/product/backend/routes/variations.py#L50) | token, body, caller, ctx | Contractor proposes a change order / variation. |
| [approve_variation](../apps/scope/product/backend/routes/variations.py#L112) | token, variation_id, caller, ctx | Homeowner approves a variation — creates a new Stripe Checkout for the extra amount. |
| [decline_variation](../apps/scope/product/backend/routes/variations.py#L195) | token, variation_id, caller, ctx | Homeowner declines a variation. |

### apps/scope/product/backend/scrapers/directories.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [phone_normalized](../apps/scope/product/backend/scrapers/directories.py#L60) | self | 9-digit dedup key from :func:`domain.phone.normalize`, or ``""``. |
| [is_valid_phone](../apps/scope/product/backend/scrapers/directories.py#L71) | self | True if ``phone`` parses as a valid Spanish mobile. |
| [_dispatch](../apps/scope/product/backend/scrapers/directories.py#L86) | platform, trade, city, limit | Lazy-import and invoke a single platform's search. |
| [_dedup](../apps/scope/product/backend/scrapers/directories.py#L110) | leads | Deduplicate by normalised phone. Leads with unparseable phones are dropped (audit §1.3 I1: invalid phones can't dedup reliably). |
| [search](../apps/scope/product/backend/scrapers/directories.py#L125) | trade, city | Search for contractors across one or more platforms. |

### apps/scope/product/backend/scrapers/facebook/expand.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [expand_comments](../apps/scope/product/backend/scrapers/facebook/expand.py#L37) | page, max_clicks | Click every matching "more comments" button up to ``max_clicks`` rounds. |

### apps/scope/product/backend/scrapers/facebook/groups.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [capture_graphql](../apps/scope/product/backend/scrapers/facebook/groups.py#L18) | page | Capture FB GraphQL responses matching ``op_name`` over ``timeout_ms`` milliseconds. |

### apps/scope/product/backend/scrapers/habitissimo/blast.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [submit_rfq](../apps/scope/product/backend/scrapers/habitissimo/blast.py#L13) | trade, city | Submit one RFQ to Habitissimo's ``/v1/serviceRequest`` endpoint. |
| [build_submissions](../apps/scope/product/backend/scrapers/habitissimo/blast.py#L38) | trades, cities, templates | Cartesian product of trades × cities × templates. |

### apps/scope/product/backend/scrapers/habitissimo/phones.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [extract_phone_from_modal_html](../apps/scope/product/backend/scrapers/habitissimo/phones.py#L51) | html | Parse a phone number out of Habitissimo's reveal-modal HTML. |
| [_clean](../apps/scope/product/backend/scrapers/habitissimo/phones.py#L92) | raw | Strip whitespace / dashes / parens from a raw phone string. |
| [_is_proxy](../apps/scope/product/backend/scrapers/habitissimo/phones.py#L100) | phone | True if ``phone`` starts with :data:`HABITISSIMO_PROXY_PREFIX` after stripping a leading ``+34`` if present. |
| [reveal_phone](../apps/scope/product/backend/scrapers/habitissimo/phones.py#L114) | slug | Reveal the phone for a Habitissimo company by slug. |

### apps/scope/product/backend/scrapers/habitissimo/search.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [list_companies](../apps/scope/product/backend/scrapers/habitissimo/search.py#L18) | trade, city | List companies on Habitissimo's directory for ``trade × city``. |
| [search](../apps/scope/product/backend/scrapers/habitissimo/search.py#L39) | trade, city | Search Habitissimo directory and optionally reveal phones. |

### apps/scope/product/backend/scrapers/habitissimo/session.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [refresh_session](../apps/scope/product/backend/scrapers/habitissimo/session.py#L46) |  | Log in via Playwright and write ``HABITISSIMO_SESSION_FILE``. |
| [get_session](../apps/scope/product/backend/scrapers/habitissimo/session.py#L72) |  | Return the cached session, refreshing if expired. |

### apps/scope/product/backend/scrapers/houzz/search.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [build_query](../apps/scope/product/backend/scrapers/houzz/search.py#L21) | trade, city | Construct a Houzz directory search URL. |
| [search](../apps/scope/product/backend/scrapers/houzz/search.py#L39) | trade, city | Houzz contractor directory search. |

### apps/scope/product/backend/scrapers/instagram/profile.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [extract_profile_fields](../apps/scope/product/backend/scrapers/instagram/profile.py#L26) | html | Parse the bio, website, name, and phones out of IG profile HTML. |
| [_first_match](../apps/scope/product/backend/scrapers/instagram/profile.py#L76) | pattern, text |  |
| [fetch_profile](../apps/scope/product/backend/scrapers/instagram/profile.py#L81) | username | Fetch an IG profile by username and return extracted fields. |

### apps/scope/product/backend/scrapers/instagram/scraper.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [search](../apps/scope/product/backend/scrapers/instagram/scraper.py#L14) | trade, city | IG contractor search (Google SERP → profile parse → leads). |

### apps/scope/product/backend/scrapers/instagram/search.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [google_search](../apps/scope/product/backend/scrapers/instagram/search.py#L46) | query | Execute a Google SERP query and return list of IG-profile hits. |

### apps/scope/product/backend/scrapers/instagram_scraper.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [instagram_handle_from_bio](../apps/scope/product/backend/scrapers/instagram_scraper.py#L76) | bio | Best-effort Instagram @handle from a Google snippet / Wallapop line / bio string. Used to backfill profile_url for PHONE-only scraper rows. |
| [_load_bd_key](../apps/scope/product/backend/scrapers/instagram_scraper.py#L123) |  |  |
| [_google_instagram_search](../apps/scope/product/backend/scrapers/instagram_scraper.py#L138) | query, start, bd_key, num | One paginated Google search for tradespeople with Instagram presence. |
| [_fetch_instagram_profile](../apps/scope/product/backend/scrapers/instagram_scraper.py#L249) | username, bd_key | Fetch an Instagram profile page and extract bio + phone. Returns dict. |
| [_extract_bio_from_html](../apps/scope/product/backend/scrapers/instagram_scraper.py#L310) | html | Extract bio text from Instagram page HTML. Tries meta description first. |
| [_extract_display_name](../apps/scope/product/backend/scrapers/instagram_scraper.py#L327) | html |  |
| [_extract_website](../apps/scope/product/backend/scrapers/instagram_scraper.py#L337) | html |  |
| [_extract_phone](../apps/scope/product/backend/scrapers/instagram_scraper.py#L346) | text | Extract first Spanish mobile phone number from text. |
| [_normalise_phone](../apps/scope/product/backend/scrapers/instagram_scraper.py#L354) | raw | Normalise to +34XXXXXXXXX format. |
| [_try_fetch_website_phone](../apps/scope/product/backend/scrapers/instagram_scraper.py#L368) | url, bd_key | Fetch a linked website (linktree, etc.) and look for a phone number. |
| [scrape_instagram_profiles](../apps/scope/product/backend/scrapers/instagram_scraper.py#L384) | trade, city, parallelize | Search Instagram for tradespeople profiles by trade + city. Returns:   {     "total_profiles": int,     "profiles_with_phone": int,     "profiles": [...],     "proxies_used": int,     "queries_run": int,   } |
| [_run_search](../apps/scope/product/backend/scrapers/instagram_scraper.py#L424) | q, start |  |
| [_bounded_search](../apps/scope/product/backend/scrapers/instagram_scraper.py#L439) | q, start |  |
| [_parse_synthetic_phone_row](../apps/scope/product/backend/scrapers/instagram_scraper.py#L455) | entry |  |
| [_bounded_fetch](../apps/scope/product/backend/scrapers/instagram_scraper.py#L519) | uname |  |

### apps/scope/product/backend/scrapers/whatsapp_checker.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_ws_url](../apps/scope/product/backend/scrapers/whatsapp_checker.py#L65) |  | Return the WebSocket debugger URL for any available browser tab. |
| [_cdp_send](../apps/scope/product/backend/scrapers/whatsapp_checker.py#L107) | ws, method, params, msg_id | Send a single CDP command over an open websockets connection and return result. |
| [check_number](../apps/scope/product/backend/scrapers/whatsapp_checker.py#L128) | phone_digits | Return True if ``phone_digits`` has a WhatsApp account. |
| [check_bulk](../apps/scope/product/backend/scrapers/whatsapp_checker.py#L235) | phones, concurrency, skip_check | Check WhatsApp presence for a list of phone numbers. |

### apps/scope/product/backend/state_machine.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_guard_no_work_started](../apps/scope/product/backend/state_machine.py#L112) | milestones | True iff every milestone is still ``pending`` / unset. |
| [can_transition](../apps/scope/product/backend/state_machine.py#L136) | entity, from_status, to_status, actor_role, milestones | Check whether a state transition is allowed. |
| [assert_transition](../apps/scope/product/backend/state_machine.py#L188) | entity, from_status, to_status, actor_role, milestones, status_code | :func:`can_transition` + raise ``HTTPException`` on failure. |

### apps/scope/product/backend/workflows/brief_enrichment.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_dict](../apps/scope/product/backend/workflows/brief_enrichment.py#L82) | self |  |
| [_assess_enrichment_gaps](../apps/scope/product/backend/workflows/brief_enrichment.py#L94) | brief, photos | Assess which Bar 2 gaps remain for this brief. |
| [run_brief_enrichment](../apps/scope/product/backend/workflows/brief_enrichment.py#L135) | job_id, homeowner_phone, brief, photos | Enrichment team pipeline. |

### apps/scope/product/backend/workflows/brief_intake.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__post_init__](../apps/scope/product/backend/workflows/brief_intake.py#L61) | self |  |
| [to_dict](../apps/scope/product/backend/workflows/brief_intake.py#L65) | self |  |
| [_assess_bar1](../apps/scope/product/backend/workflows/brief_intake.py#L78) | brief | Check if Bar 1 (discovery bar) is met. |
| [run_brief_intake](../apps/scope/product/backend/workflows/brief_intake.py#L100) | job_id, homeowner_phone, brief, photos | Intake team pipeline. |

### apps/scope/product/backend/workflows/contractor_discovery.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_dict](../apps/scope/product/backend/workflows/contractor_discovery.py#L92) | self |  |
| [run_contractor_discovery](../apps/scope/product/backend/workflows/contractor_discovery.py#L107) | job_id, max_send, stagger_seconds | Full contractor discovery pipeline for a job. |
| [on_contractor_reply](../apps/scope/product/backend/workflows/contractor_discovery.py#L357) | phone, job_id | Called by the WhatsApp webhook when a contacted contractor first replies. |
| [_expand_trade_slugs](../apps/scope/product/backend/workflows/contractor_discovery.py#L479) | trade, max_slugs | Map a trade/job description to multiple Houzz directory slugs. |
| [_search_houzz_expanded](../apps/scope/product/backend/workflows/contractor_discovery.py#L500) | trade, city | Search Houzz for the target city first. Only expand to nearby cities if the primary city returns fewer than _SPARSE_THRESHOLD results — because in small towns tradespeople often list under the nearest larger city. |
| [_search_houzz](../apps/scope/product/backend/workflows/contractor_discovery.py#L563) | trade, city | Scrape Houzz directory for contractors. Returns list of candidate dicts. |
| [_search_facebook](../apps/scope/product/backend/workflows/contractor_discovery.py#L602) | trade, city, days_back | Search Facebook groups for contractor recommendations via Bright Data. |
| [_search_forums](../apps/scope/product/backend/workflows/contractor_discovery.py#L665) | trade, city, days_back | Search Spanish forums (Forocoches, Mediavida, Reddit ES) via Bright Data. |
| [_scrape_fb_post_comments](../apps/scope/product/backend/workflows/contractor_discovery.py#L728) | urls, city, already_found | Fetch full FB post pages and extract phones + business names from comments. |
| [_fetch_one](../apps/scope/product/backend/workflows/contractor_discovery.py#L738) | url |  |
| [_extract_name_near_phone](../apps/scope/product/backend/workflows/contractor_discovery.py#L797) | text, phone_digits | Try to find a commenter name near a phone number in FB post text. |
| [_extract_phones_from_text](../apps/scope/product/backend/workflows/contractor_discovery.py#L832) | text | Extract phone numbers from a text snippet. |
| [_extract_business_names](../apps/scope/product/backend/workflows/contractor_discovery.py#L869) | text, phones_already_found | Find business name mentions in FB comments that don't have a phone number. |
| [_merge_and_deduplicate](../apps/scope/product/backend/workflows/contractor_discovery.py#L927) | houzz, facebook | Merge Houzz and Facebook candidates, deduplicate by phone, filter valid. |
| [_send_single_outreach](../apps/scope/product/backend/workflows/contractor_discovery.py#L976) | candidate, job_id, brief, humanized_summary, lang | Create HC record and send one outreach message. |
| [_humanize_brief](../apps/scope/product/backend/workflows/contractor_discovery.py#L1077) | brief, lang | Get a humanized job summary for template slot {{2}}. |
| [_send_first_reply](../apps/scope/product/backend/workflows/contractor_discovery.py#L1086) | phone_digits, contractor_id, provenance | Send a personalized follow-up when a contractor first replies. |
| [_background_profile_import](../apps/scope/product/backend/workflows/contractor_discovery.py#L1131) | contractor_id, profile_url | Kick off Profile Import workflow in background after a contractor replies. |
| [_write_workflow_signal](../apps/scope/product/backend/workflows/contractor_discovery.py#L1155) | job_id, sent, hc_ids | Write completion signal for Hermes to pick up on next turn. |
| [_write](../apps/scope/product/backend/workflows/contractor_discovery.py#L1173) |  |  |

### apps/scope/product/backend/workflows/copy.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_bedrock](../apps/scope/product/backend/workflows/copy.py#L38) |  |  |
| [_converse_sync](../apps/scope/product/backend/workflows/copy.py#L42) | system, user, max_tokens | Synchronous Bedrock Converse call. Used inside asyncio.to_thread(). |
| [humanize_job_summary](../apps/scope/product/backend/workflows/copy.py#L85) | brief, language | Turn a homeowner brief into a natural one-liner for WhatsApp template slot {{2}}. |
| [craft_first_reply](../apps/scope/product/backend/workflows/copy.py#L159) | brief, contractor_profile, language | Write a personal follow-up message when a contractor first replies to outreach. |
| [_build_profile_summary](../apps/scope/product/backend/workflows/copy.py#L221) | profile | Build a brief human-readable summary of contractor profile data. |
| [_build_brief_summary](../apps/scope/product/backend/workflows/copy.py#L242) | brief | Build a one-sentence summary of the job brief. |

### apps/scope/product/backend/workflows/profile_import.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_dict](../apps/scope/product/backend/workflows/profile_import.py#L70) | self |  |
| [run_profile_import](../apps/scope/product/backend/workflows/profile_import.py#L86) | contractor_id, source_url | Full Profile Import pipeline for a known contractor. |
| [run_profile_import_for_phone](../apps/scope/product/backend/workflows/profile_import.py#L270) | phone, source_url, name, trade, city | Look up or create a contractor record by phone, then run Profile Import. |
| [_write_workflow_signal](../apps/scope/product/backend/workflows/profile_import.py#L299) | contractor_id, source_url, trust_score, canvas_token, status | Append a workflow_signal to the contractor dossier. |

### apps/scope/product/web/src/App.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [CookieConsent](../apps/scope/product/web/src/App.tsx#L46) |  |  |
| [accept](../apps/scope/product/web/src/App.tsx#L56) |  |  |
| [decline](../apps/scope/product/web/src/App.tsx#L62) |  |  |
| [LegacyProjectRedirect](../apps/scope/product/web/src/App.tsx#L98) |  |  |
| [App](../apps/scope/product/web/src/App.tsx#L103) |  |  |

### apps/scope/product/web/src/components/ConsentDrawer.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ConsentDrawer](../apps/scope/product/web/src/components/ConsentDrawer.tsx#L36) | {
  open,
  onClose,
  quoteToken,
  scope,
  amountTotalCents,
  homeowner_email,
  onPaymentReady,
} |  |
| [handleConfirm](../apps/scope/product/web/src/components/ConsentDrawer.tsx#L53) |  |  |

### apps/scope/product/web/src/components/DocumentViewer.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [DocumentViewer](../apps/scope/product/web/src/components/DocumentViewer.tsx#L26) | { src, title, downloadUrl, className = '', fullHeight = false } |  |

### apps/scope/product/web/src/components/EditableQuoteCanvas.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [draftToChangeOrder](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L20) | d |  |
| [parseDuration](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L40) | label |  |
| [buildDuration](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L47) | n, unit |  |
| [ContingencyDraftRow](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L55) | {
  draft,
  lang,
  onRemove,
} | Inline contingency draft card between milestones. |
| [EditableQuoteCanvas](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L74) | { scope, onChange, lang = 'en' } |  |
| [updateMilestone](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L83) | i, field, value |  |
| [addMilestone](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L95) |  |  |
| [removeMilestone](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L99) | i |  |
| [removeContingency](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L103) | afterIdx, title |  |
| [setDuration](../apps/scope/product/web/src/components/EditableQuoteCanvas.tsx#L196) | newN, newUnit |  |

### apps/scope/product/web/src/components/ErrorBoundary.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [getDerivedStateFromError](../apps/scope/product/web/src/components/ErrorBoundary.tsx#L30) | error |  |
| [componentDidCatch](../apps/scope/product/web/src/components/ErrorBoundary.tsx#L34) | error, info |  |
| [render](../apps/scope/product/web/src/components/ErrorBoundary.tsx#L44) |  |  |

### apps/scope/product/web/src/components/FullScreenStep.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [FullScreenStep](../apps/scope/product/web/src/components/FullScreenStep.tsx#L23) | { icon, title, subtitle, children, footer } |  |

### apps/scope/product/web/src/components/GoogleSignInButton.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [GoogleLogo](../apps/scope/product/web/src/components/GoogleSignInButton.tsx#L15) |  |  |
| [GoogleSignInButton](../apps/scope/product/web/src/components/GoogleSignInButton.tsx#L24) | { label, onClick, disabled, variant = 'solid' } |  |

### apps/scope/product/web/src/components/LanguagePickerScreen.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [LanguagePickerScreen](../apps/scope/product/web/src/components/LanguagePickerScreen.tsx#L22) | { onDone } |  |
| [handleConfirm](../apps/scope/product/web/src/components/LanguagePickerScreen.tsx#L26) |  |  |

### apps/scope/product/web/src/components/LanguageToggle.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [LanguageToggle](../apps/scope/product/web/src/components/LanguageToggle.tsx#L16) | { variant = 'light' } |  |
| [handleToggle](../apps/scope/product/web/src/components/LanguageToggle.tsx#L22) |  |  |

### apps/scope/product/web/src/components/LeoLogo.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [LeoLogo](../apps/scope/product/web/src/components/LeoLogo.tsx#L24) | { variant = 'charcoal', mark = 'wordmark', height = 20, className } |  |

### apps/scope/product/web/src/components/LocationPickerModal.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [jitter](../apps/scope/product/web/src/components/LocationPickerModal.tsx#L45) | coord, maxDelta |  |
| [jitterCenter](../apps/scope/product/web/src/components/LocationPickerModal.tsx#L49) | lng, lat |  |
| [geocodeForward](../apps/scope/product/web/src/components/LocationPickerModal.tsx#L54) | q |  |
| [geocodeReverse](../apps/scope/product/web/src/components/LocationPickerModal.tsx#L67) | lng, lat |  |
| [LocationPickerModal](../apps/scope/product/web/src/components/LocationPickerModal.tsx#L77) | {
  lang,
  initialLocation,
  onConfirm,
  onClose,
} |  |
| [handleSearchChange](../apps/scope/product/web/src/components/LocationPickerModal.tsx#L155) | val |  |
| [handleGeolocate](../apps/scope/product/web/src/components/LocationPickerModal.tsx#L172) |  |  |
| [handleConfirm](../apps/scope/product/web/src/components/LocationPickerModal.tsx#L196) |  |  |

### apps/scope/product/web/src/components/PageLoading.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [PageLoading](../apps/scope/product/web/src/components/PageLoading.tsx#L17) | { label } |  |

### apps/scope/product/web/src/components/RequireAuth.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [RequireAuth](../apps/scope/product/web/src/components/RequireAuth.tsx#L34) | { children, role } |  |

### apps/scope/product/web/src/components/canvas/ClaimProfileDrawer.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ClaimProfileDrawer](../apps/scope/product/web/src/components/canvas/ClaimProfileDrawer.tsx#L11) | { canvasToken } |  |
| [handleClaim](../apps/scope/product/web/src/components/canvas/ClaimProfileDrawer.tsx#L15) |  |  |

### apps/scope/product/web/src/components/canvas/ProfileActionDrawer.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ProfileActionDrawer](../apps/scope/product/web/src/components/canvas/ProfileActionDrawer.tsx#L16) | { contractorId, onSubmit } |  |
| [handleEdit](../apps/scope/product/web/src/components/canvas/ProfileActionDrawer.tsx#L20) |  |  |

### apps/scope/product/web/src/components/canvas/ScopeActionBar.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ScopeEditOverlay](../apps/scope/product/web/src/components/canvas/ScopeActionBar.tsx#L21) | { token, contractorId, onClose } |  |
| [handleEditInChat](../apps/scope/product/web/src/components/canvas/ScopeActionBar.tsx#L24) |  |  |
| [ScopeActionBar](../apps/scope/product/web/src/components/canvas/ScopeActionBar.tsx#L66) | { token, contractorId, isContractor, isPaid, scope, amountTotalCents } |  |
| [handleNewQuote](../apps/scope/product/web/src/components/canvas/ScopeActionBar.tsx#L127) |  |  |
| [handleSendToCustomer](../apps/scope/product/web/src/components/canvas/ScopeActionBar.tsx#L134) |  |  |
| [handleCopyLink](../apps/scope/product/web/src/components/canvas/ScopeActionBar.tsx#L145) |  |  |

### apps/scope/product/web/src/components/chat/ActionBar.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ActionBar](../apps/scope/product/web/src/components/chat/ActionBar.tsx#L22) | {
  status,
  previewOpen,
  onTogglePreview,
  confirmLabel,
  onConfirm,
  confirmDisabled,
  confirmed = false,
  drawerState,
  onDrawerAction,
} |  |
| [handleActionClick](../apps/scope/product/web/src/components/chat/ActionBar.tsx#L44) |  |  |

### apps/scope/product/web/src/components/chat/AttachmentSheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [AttachmentSheet](../apps/scope/product/web/src/components/chat/AttachmentSheet.tsx#L15) | {
  open,
  onClose,
  onTakePhoto,
  onChooseGallery,
  onChooseFile,
} |  |
| [handleKey](../apps/scope/product/web/src/components/chat/AttachmentSheet.tsx#L27) | e |  |

### apps/scope/product/web/src/components/chat/ChatInput.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ChatInput](../apps/scope/product/web/src/components/chat/ChatInput.tsx#L27) | {
  onSendText,
  onSendVoice,
  onComposingChange,
  disabled,
  placeholder,
} |  |
| [measure](../apps/scope/product/web/src/components/chat/ChatInput.tsx#L61) |  |  |
| [update](../apps/scope/product/web/src/components/chat/ChatInput.tsx#L163) |  |  |
| [consumeStaged](../apps/scope/product/web/src/components/chat/ChatInput.tsx#L175) |  |  |
| [handleSendText](../apps/scope/product/web/src/components/chat/ChatInput.tsx#L182) |  |  |
| [handleStopRecording](../apps/scope/product/web/src/components/chat/ChatInput.tsx#L192) |  |  |

### apps/scope/product/web/src/components/chat/ChatMessage.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [PhotoThumbnails](../apps/scope/product/web/src/components/chat/ChatMessage.tsx#L13) | { urls } |  |
| [CopyBlock](../apps/scope/product/web/src/components/chat/ChatMessage.tsx#L70) | { text } |  |
| [handleCopy](../apps/scope/product/web/src/components/chat/ChatMessage.tsx#L74) |  |  |
| [ChatMessage](../apps/scope/product/web/src/components/chat/ChatMessage.tsx#L120) | { message } |  |

### apps/scope/product/web/src/components/chat/ChatMessages.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ChatMessages](../apps/scope/product/web/src/components/chat/ChatMessages.tsx#L14) | { messages, isThinking, bottomPadding = 180, afterFirstMessageSlot } |  |
| [handler](../apps/scope/product/web/src/components/chat/ChatMessages.tsx#L21) |  |  |

### apps/scope/product/web/src/components/chat/ChatShell.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [SubmitConfirmModal](../apps/scope/product/web/src/components/chat/ChatShell.tsx#L55) | {
  mode,
  onDismiss,
} | Post-submit confirmation modal — adapts to job post vs. profile save |
| [FullscreenOverlay](../apps/scope/product/web/src/components/chat/ChatShell.tsx#L136) | {
  drawerState,
  content,
  onAction,
  onDismiss,
} |  |
| [BannerOverlay](../apps/scope/product/web/src/components/chat/ChatShell.tsx#L203) | {
  drawerState,
  content,
  onAction,
  onDismiss,
} |  |
| [ChatShell](../apps/scope/product/web/src/components/chat/ChatShell.tsx#L256) | {
  title,
  headerLeft,
  headerRight,
  messages,
  isThinking,
  status,
  previewState,
  previewContent,
  placeholderContent,
  customDrawerContent,
  onSendText,
  onSendVoice,
  onConfirm,
  confirmLabel,
  previewLabelClosed = 'Preview',
  previewLabelOpen = 'Close preview',
  confirmed = false,
  drawerState,
  onDrawerAction,
  onComposingChange,
  emptyPreviewLabel,
  previewThinkingLabels,
  afterFirstMessageSlot,
  contained = false,
  initialPreviewOpen = false,
  confirmMode = 'job',
  closePreviewCount = 0,
} |  |
| [handleOverlayAction](../apps/scope/product/web/src/components/chat/ChatShell.tsx#L369) |  |  |
| [handleOverlayDismiss](../apps/scope/product/web/src/components/chat/ChatShell.tsx#L378) |  |  |

### apps/scope/product/web/src/components/chat/CustomDrawerBody.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [CustomDrawerBody](../apps/scope/product/web/src/components/chat/CustomDrawerBody.tsx#L3) | { ds } |  |

### apps/scope/product/web/src/components/chat/PreviewPanel.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [VellumOverlay](../apps/scope/product/web/src/components/chat/PreviewPanel.tsx#L32) | { pulse } | Brand Vellum overlay — identical DOM to brand-book.html. Visual styles from /brand-effects.css (shared, not processed by Vite). |
| [PreviewPanel](../apps/scope/product/web/src/components/chat/PreviewPanel.tsx#L60) | {
  previewState,
  children,
  placeholderContent,
  className,
  mobile = false,
  inline = false,
  open = true,
  overlayLabel,
  emptyLabel = 'Check back here as your brief builds up',
  thinkingLabels = DEFAULT_BUILDING_LABELS,
} |  |

### apps/scope/product/web/src/components/chat/ThinkingIndicator.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ThinkingIndicator](../apps/scope/product/web/src/components/chat/ThinkingIndicator.tsx#L4) |  | Typing dots while the agent is processing (shown when isThinking and no streaming text). |

### apps/scope/product/web/src/components/dashboard/JobCard.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [JobCard](../apps/scope/product/web/src/components/dashboard/JobCard.tsx#L22) | { scope, contractorId: _contractorId, onSubmitProof, onCreateVariation } |  |

### apps/scope/product/web/src/components/dashboard/SubmitProofSheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [reelAsset](../apps/scope/product/web/src/components/dashboard/SubmitProofSheet.tsx#L16) | f |  |
| [SubmitProofSheet](../apps/scope/product/web/src/components/dashboard/SubmitProofSheet.tsx#L28) | { open, onClose, quoteToken, contractorId, milestones } |  |
| [at](../apps/scope/product/web/src/components/dashboard/SubmitProofSheet.tsx#L48) | ms, fn |  |
| [handlePhotoChange](../apps/scope/product/web/src/components/dashboard/SubmitProofSheet.tsx#L71) | e |  |
| [handleSubmit](../apps/scope/product/web/src/components/dashboard/SubmitProofSheet.tsx#L82) |  |  |

### apps/scope/product/web/src/components/dashboard/VariationCreateSheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [VariationCreateSheet](../apps/scope/product/web/src/components/dashboard/VariationCreateSheet.tsx#L36) | { open, onClose, quoteToken, contractorId } |  |
| [onSubmit](../apps/scope/product/web/src/components/dashboard/VariationCreateSheet.tsx#L42) | data |  |

### apps/scope/product/web/src/components/project/CancelJobSheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [CancelJobSheet](../apps/scope/product/web/src/components/project/CancelJobSheet.tsx#L23) | {
  open, onClose, totalCents, contractorName, quoteToken, onCancelled, navigateToChat,
} |  |
| [handleCancel](../apps/scope/product/web/src/components/project/CancelJobSheet.tsx#L32) |  |  |

### apps/scope/product/web/src/components/project/DocumentSheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [DocumentSheet](../apps/scope/product/web/src/components/project/DocumentSheet.tsx#L17) | { open, onClose, src, title } |  |

### apps/scope/product/web/src/components/project/InlineLogin.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [InlineLogin](../apps/scope/product/web/src/components/project/InlineLogin.tsx#L18) | { prefillEmail } |  |
| [handleGoogle](../apps/scope/product/web/src/components/project/InlineLogin.tsx#L24) |  |  |
| [handleMagicLink](../apps/scope/product/web/src/components/project/InlineLogin.tsx#L35) |  |  |

### apps/scope/product/web/src/components/project/MilestoneDetailSheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [MilestoneDetailSheet](../apps/scope/product/web/src/components/project/MilestoneDetailSheet.tsx#L32) | {
  open, onClose, milestone, milestoneIndex, update, contractorName, quoteToken,
  onReleased, navigateToChat, onOpenLightbox, canRelease = true,
} |  |
| [handleRelease](../apps/scope/product/web/src/components/project/MilestoneDetailSheet.tsx#L52) |  |  |
| [statusLabel](../apps/scope/product/web/src/components/project/MilestoneDetailSheet.tsx#L74) |  |  |

### apps/scope/product/web/src/components/project/PageSkeleton.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [PageSkeleton](../apps/scope/product/web/src/components/project/PageSkeleton.tsx#L6) |  | PageSkeleton — Animated loading skeleton for ProjectDetail. Shows a charcoal header placeholder + content rows with pulse animations. |

### apps/scope/product/web/src/components/project/ReviewSheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ReviewSheet](../apps/scope/product/web/src/components/project/ReviewSheet.tsx#L18) | { open, onClose, quoteToken } |  |
| [handleSubmit](../apps/scope/product/web/src/components/project/ReviewSheet.tsx#L25) |  |  |

### apps/scope/product/web/src/components/project/VariationDetailSheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [VariationDetailSheet](../apps/scope/product/web/src/components/project/VariationDetailSheet.tsx#L25) | {
  variation, quoteToken, onClose, onActioned,
} |  |
| [handleApprove](../apps/scope/product/web/src/components/project/VariationDetailSheet.tsx#L35) |  |  |
| [handleDecline](../apps/scope/product/web/src/components/project/VariationDetailSheet.tsx#L57) |  |  |

### apps/scope/product/web/src/components/quote/FinalizeModal.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [FinalizeModal](../apps/scope/product/web/src/components/quote/FinalizeModal.tsx#L24) | { scope, contractorId, editToken, onConnectBank, onDismiss } |  |
| [handleConnectBank](../apps/scope/product/web/src/components/quote/FinalizeModal.tsx#L30) |  |  |

### apps/scope/product/web/src/context/AuthContext.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [useAuth](../apps/scope/product/web/src/context/AuthContext.tsx#L58) |  |  |
| [fetchContractorInfo](../apps/scope/product/web/src/context/AuthContext.tsx#L72) | authUserId |  |
| [AuthProvider](../apps/scope/product/web/src/context/AuthContext.tsx#L92) | { children } |  |
| [applyUser](../apps/scope/product/web/src/context/AuthContext.tsx#L101) | u |  |
| [signOut](../apps/scope/product/web/src/context/AuthContext.tsx#L195) |  |  |
| [getAccessToken](../apps/scope/product/web/src/context/AuthContext.tsx#L209) |  |  |

### apps/scope/product/web/src/context/SandboxContext.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [loadState](../apps/scope/product/web/src/context/SandboxContext.tsx#L38) |  |  |
| [saveState](../apps/scope/product/web/src/context/SandboxContext.tsx#L46) | state |  |
| [SandboxBadge](../apps/scope/product/web/src/context/SandboxContext.tsx#L107) |  |  |

### apps/scope/product/web/src/hooks/useCanvasQuery.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [canvasQueryKey](../apps/scope/product/web/src/hooks/useCanvasQuery.ts#L15) | token |  |
| [useCanvasQuery](../apps/scope/product/web/src/hooks/useCanvasQuery.ts#L19) | token |  |

### apps/scope/product/web/src/hooks/useChat.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [sessionKey](../apps/scope/product/web/src/hooks/useChat.ts#L59) | mode, audience, contractorId |  |
| [loadSession](../apps/scope/product/web/src/hooks/useChat.ts#L65) | mode, audience, contractorId |  |
| [stripHeavyFields](../apps/scope/product/web/src/hooks/useChat.ts#L83) | msgs | Strip base64 images and expired object URLs before persisting — they bloat storage and are invalid after refresh. |
| [saveSession](../apps/scope/product/web/src/hooks/useChat.ts#L90) | mode, audience, data, contractorId |  |
| [briefToUiStatus](../apps/scope/product/web/src/hooks/useChat.ts#L109) | b |  |
| [scopeToUiStatus](../apps/scope/product/web/src/hooks/useChat.ts#L116) | s |  |
| [scopeHasPreviewBody](../apps/scope/product/web/src/hooks/useChat.ts#L125) | scope | True when the scope preview should show real data (not just empty template). |
| [messagesToApiHistory](../apps/scope/product/web/src/hooks/useChat.ts#L138) | messages | Build chat history from UI messages (user + assistant turns only). |
| [isDocFile](../apps/scope/product/web/src/hooks/useChat.ts#L163) | f |  |
| [extractDocs](../apps/scope/product/web/src/hooks/useChat.ts#L169) | files | Extract text from document files, returning a combined markdown string. |
| [userLanguageHint](../apps/scope/product/web/src/hooks/useChat.ts#L182) | lastUserText |  |
| [useChat](../apps/scope/product/web/src/hooks/useChat.ts#L242) | options |  |
| [fire](../apps/scope/product/web/src/hooks/useChat.ts#L279) |  |  |

### apps/scope/product/web/src/hooks/useVoiceRecorder.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [pickMime](../apps/scope/product/web/src/hooks/useVoiceRecorder.ts#L9) |  |  |
| [useVoiceRecorder](../apps/scope/product/web/src/hooks/useVoiceRecorder.ts#L32) |  | Real MediaRecorder capture + Web Audio AnalyserNode waveform + timer. |
| [loop](../apps/scope/product/web/src/hooks/useVoiceRecorder.ts#L89) |  |  |
| [tick](../apps/scope/product/web/src/hooks/useVoiceRecorder.ts#L146) |  |  |

### apps/scope/product/web/src/i18n.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [setAppLanguage](../apps/scope/product/web/src/i18n.ts#L36) | lang | Convenience: change language and persist to localStorage. |

### apps/scope/product/web/src/lib/api.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [log](../apps/scope/product/web/src/lib/api.ts#L35) | msg, data |  |
| [logError](../apps/scope/product/web/src/lib/api.ts#L42) | msg, err |  |
| [setAuthTokenGetter](../apps/scope/product/web/src/lib/api.ts#L61) | fn | Called once by AuthProvider when it mounts. |
| [_sandboxHeaders](../apps/scope/product/web/src/lib/api.ts#L73) |  | Returns X-Sandbox header when sandbox mode is active. Uses the shared isSandbox() helper from utils to avoid key drift. |
| [jsonRequest](../apps/scope/product/web/src/lib/api.ts#L95) | url, init | Performs an apiFetch and parses JSON, returning a typed result. On HTTP error, returns { ok: false, error: message }. On network error, throws — callers should catch if needed. |
| [apiFetch](../apps/scope/product/web/src/lib/api.ts#L107) | url, init |  |
| [sendChatMessage](../apps/scope/product/web/src/lib/api.ts#L189) | params |  |
| [transcribeAudio](../apps/scope/product/web/src/lib/api.ts#L232) | blob, opts |  |
| [uploadPhotos](../apps/scope/product/web/src/lib/api.ts#L259) | leadId, photos |  |
| [importProfile](../apps/scope/product/web/src/lib/api.ts#L294) | url, contractorId | SSE stream from POST /api/profile-import — yields parsed event objects. |
| [signalComposing](../apps/scope/product/web/src/lib/api.ts#L368) | userId, composing, inputType | Fire-and-forget signal: user is composing (typing/recording) or stopped. Lightweight — no response needed. Backend uses this to hold off premature replies. |
| [extractDocument](../apps/scope/product/web/src/lib/api.ts#L380) | file |  |
| [fetchInbox](../apps/scope/product/web/src/lib/api.ts#L438) | token |  |
| [approveOutreach](../apps/scope/product/web/src/lib/api.ts#L466) | token |  |
| [fetchCanvas](../apps/scope/product/web/src/lib/api.ts#L512) | token |  |
| [finalizeScope](../apps/scope/product/web/src/lib/api.ts#L539) | contractorId, scopeData, authUserId |  |
| [claimProfile](../apps/scope/product/web/src/lib/api.ts#L568) | canvasToken, accessToken |  |
| [createStripeAccount](../apps/scope/product/web/src/lib/api.ts#L604) | contractorId, opts |  |
| [getStripeAccountLink](../apps/scope/product/web/src/lib/api.ts#L621) | contractorId |  |
| [getStripeAccountStatus](../apps/scope/product/web/src/lib/api.ts#L641) | contractorId |  |
| [fetchContractorScopes](../apps/scope/product/web/src/lib/api.ts#L676) | contractorId |  |
| [updateScope](../apps/scope/product/web/src/lib/api.ts#L699) | token, scopeData, contractorId |  |
| [fetchOps](../apps/scope/product/web/src/lib/api.ts#L764) | token |  |

### apps/scope/product/web/src/lib/handoff.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [consumeHandoff](../apps/scope/product/web/src/lib/handoff.ts#L30) |  | Read and delete the handoff payload. Returns an empty object if there's nothing (direct navigation, refresh, or already consumed). |

### apps/scope/product/web/src/lib/localAuth.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [session](../apps/scope/product/web/src/lib/localAuth.ts#L4) |  |  |
| [configured](../apps/scope/product/web/src/lib/localAuth.ts#L10) |  |  |
| [unsubscribe](../apps/scope/product/web/src/lib/localAuth.ts#L15) |  |  |

### apps/scope/product/web/src/lib/runtime.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [appPath](../apps/scope/product/web/src/lib/runtime.ts#L4) | path |  |

### apps/scope/product/web/src/lib/supabase.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [signInWithGoogleForClaim](../apps/scope/product/web/src/lib/supabase.ts#L26) | claimToken | Start Google OAuth flow, storing the claim token in the redirect URL. |
| [setLanguagePreference](../apps/scope/product/web/src/lib/supabase.ts#L41) | lang | Update the user's language preference in Supabase user_metadata. |

### apps/scope/product/web/src/lib/tracking.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [initTracking](../apps/scope/product/web/src/lib/tracking.ts#L43) |  | Initialise PostHog. Call this once after cookie consent is granted. Safe to call multiple times — only initialises on first call. |
| [identify](../apps/scope/product/web/src/lib/tracking.ts#L77) | userId, traits | Associate subsequent events with a user. Call after login / session restore. |
| [track](../apps/scope/product/web/src/lib/tracking.ts#L101) | event, properties | Fire a named event with optional properties. |
| [_sendToBackend](../apps/scope/product/web/src/lib/tracking.ts#L126) | event, properties |  |

### apps/scope/product/web/src/lib/utils.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [uid](../apps/scope/product/web/src/lib/utils.ts#L3) |  |  |
| [clsx](../apps/scope/product/web/src/lib/utils.ts#L5) | args |  |
| [eur](../apps/scope/product/web/src/lib/utils.ts#L9) | cents | Format cents as EUR with 0 decimals (e.g. 15000 → "€150"). |
| [eurFromEuros](../apps/scope/product/web/src/lib/utils.ts#L18) | euros | Format a euro amount (not cents) as EUR with 0 decimals (e.g. 150 → "€150"). |
| [computeQuoteTotals](../apps/scope/product/web/src/lib/utils.ts#L32) | scope | Canonical quote financial computation. All amounts are in euros (not cents). |
| [isSandbox](../apps/scope/product/web/src/lib/utils.ts#L47) |  | Returns true when sandbox mode is active (reads the shared localStorage key). |
| [getLeoAuth](../apps/scope/product/web/src/lib/utils.ts#L56) |  | Read the `leo_auth` session object, returning `{}` on missing/invalid JSON. |
| [mergeLeoAuth](../apps/scope/product/web/src/lib/utils.ts#L62) | patch | Shallow-merge a patch into the `leo_auth` session object. |
| [fileToBase64](../apps/scope/product/web/src/lib/utils.ts#L67) | file | Read a File (image) as a base64 data string (no data: prefix). |

### apps/scope/product/web/src/pages/AuthCallback.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [AuthCallback](../apps/scope/product/web/src/pages/AuthCallback.tsx#L25) |  |  |
| [handleCallback](../apps/scope/product/web/src/pages/AuthCallback.tsx#L37) |  |  |
| [processClaim](../apps/scope/product/web/src/pages/AuthCallback.tsx#L58) | accessToken |  |

### apps/scope/product/web/src/pages/Canvas.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ProfileSubmitModal](../apps/scope/product/web/src/pages/Canvas.tsx#L31) | { onDismiss } |  |
| [Canvas](../apps/scope/product/web/src/pages/Canvas.tsx#L96) |  |  |

### apps/scope/product/web/src/pages/ComponentLibrary.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [Section](../apps/scope/product/web/src/pages/ComponentLibrary.tsx#L216) | { title, children } |  |
| [Card](../apps/scope/product/web/src/pages/ComponentLibrary.tsx#L226) | { label, children, width } |  |
| [PhoneFrame](../apps/scope/product/web/src/pages/ComponentLibrary.tsx#L237) | { label, children } |  |
| [MiniResponseCard](../apps/scope/product/web/src/pages/ComponentLibrary.tsx#L248) | { r, rank } |  |
| [ComponentLibrary](../apps/scope/product/web/src/pages/ComponentLibrary.tsx#L285) |  |  |

### apps/scope/product/web/src/pages/Dashboard.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [Dashboard](../apps/scope/product/web/src/pages/Dashboard.tsx#L37) |  |  |
| [handleNewQuote](../apps/scope/product/web/src/pages/Dashboard.tsx#L90) |  |  |

### apps/scope/product/web/src/pages/DesignSystem.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [DesignSystem](../apps/scope/product/web/src/pages/DesignSystem.tsx#L44) |  |  |
| [TokensTab](../apps/scope/product/web/src/pages/DesignSystem.tsx#L102) |  |  |
| [Swatch](../apps/scope/product/web/src/pages/DesignSystem.tsx#L160) | { name, hex } |  |
| [GradientsTab](../apps/scope/product/web/src/pages/DesignSystem.tsx#L186) |  |  |
| [ThemesTab](../apps/scope/product/web/src/pages/DesignSystem.tsx#L219) |  |  |
| [ThemesDemo](../apps/scope/product/web/src/pages/DesignSystem.tsx#L227) |  |  |
| [Section](../apps/scope/product/web/src/pages/DesignSystem.tsx#L288) | { title, children } |  |

### apps/scope/product/web/src/pages/FirstQuote.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [generateChangeSummary](../apps/scope/product/web/src/pages/FirstQuote.tsx#L65) | before, after, lang |  |
| [EditModeWrapper](../apps/scope/product/web/src/pages/FirstQuote.tsx#L146) | {
  scope,
  lang,
  isEditMode,
  isThinking,
  onEnterEdit,
  onSaveEdits,
  onCancelEdit,
  onChange,
} |  |
| [ChatMode](../apps/scope/product/web/src/pages/FirstQuote.tsx#L213) | {
  contractorId,
  contractorName,
  lang,
  location,
  editToken,
  initialScope,
  isFirstQuote,
  onLangChange,
  onScopeReady,
  onStartFresh,
  onGoToDashboard,
} |  |
| [FirstQuote](../apps/scope/product/web/src/pages/FirstQuote.tsx#L531) |  |  |
| [handleScopeReady](../apps/scope/product/web/src/pages/FirstQuote.tsx#L561) | scope |  |
| [handleAfterChatLocationConfirm](../apps/scope/product/web/src/pages/FirstQuote.tsx#L583) | label |  |
| [handleConnectBank](../apps/scope/product/web/src/pages/FirstQuote.tsx#L589) | quoteToken |  |

### apps/scope/product/web/src/pages/ImportPro.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [adaptRawToCanvas](../apps/scope/product/web/src/pages/ImportPro.tsx#L61) | raw | Adapt raw ProfileResult (from SSE preview) into the ProfileUpdate shape that ProfileCanvas expects. The backend sends `result.model_dump()` for preview events — flat fields like `name`, `reviews[]`, `projects[]` at the top level. ProfileCanvas needs `business_name`, nested `sources[]` with per-platform reviews/projects, etc. |
| [advanceSteps](../apps/scope/product/web/src/pages/ImportPro.tsx#L114) | steps, activeId |  |
| [ImportPro](../apps/scope/product/web/src/pages/ImportPro.tsx#L124) |  |  |
| [handleNavigateToCanvas](../apps/scope/product/web/src/pages/ImportPro.tsx#L200) |  |  |
| [handlePhoneSubmit](../apps/scope/product/web/src/pages/ImportPro.tsx#L216) | e |  |

### apps/scope/product/web/src/pages/JobChat.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [useSenderInfo](../apps/scope/product/web/src/pages/JobChat.tsx#L44) |  |  |
| [formatGroupTime](../apps/scope/product/web/src/pages/JobChat.tsx#L52) | isoString | Format timestamp for display above message groups |
| [isSameGroup](../apps/scope/product/web/src/pages/JobChat.tsx#L67) | a, b | Returns true if two messages are in the same "group" (same sender, within 5 min) |
| [MessageBubble](../apps/scope/product/web/src/pages/JobChat.tsx#L73) | {
  message,
  myRole,
  showTimestamp,
} |  |
| [ChatSkeleton](../apps/scope/product/web/src/pages/JobChat.tsx#L122) |  | Skeleton loading state — alternating bubble placeholders |
| [JobChat](../apps/scope/product/web/src/pages/JobChat.tsx#L137) |  |  |

### apps/scope/product/web/src/pages/JobInbox.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [JobInbox](../apps/scope/product/web/src/pages/JobInbox.tsx#L12) |  |  |
| [handleViewProfile](../apps/scope/product/web/src/pages/JobInbox.tsx#L41) | idx |  |
| [handleViewBrief](../apps/scope/product/web/src/pages/JobInbox.tsx#L46) |  |  |
| [handleBack](../apps/scope/product/web/src/pages/JobInbox.tsx#L50) |  |  |
| [handleApproveOutreach](../apps/scope/product/web/src/pages/JobInbox.tsx#L55) |  |  |
| [waLink](../apps/scope/product/web/src/pages/JobInbox.tsx#L69) | r |  |
| [ResponseCard](../apps/scope/product/web/src/pages/JobInbox.tsx#L363) | {
  response: r,
  rank,
  onViewProfile,
  waLink,
} |  |

### apps/scope/product/web/src/pages/Login.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [GoogleIcon](../apps/scope/product/web/src/pages/Login.tsx#L28) |  |  |
| [EnvelopeIllustration](../apps/scope/product/web/src/pages/Login.tsx#L42) |  |  |
| [openMailApp](../apps/scope/product/web/src/pages/Login.tsx#L71) | email |  |
| [OAuthButton](../apps/scope/product/web/src/pages/Login.tsx#L97) | {
  icon, label, onClick, disabled, variant = 'light',
} |  |
| [Divider](../apps/scope/product/web/src/pages/Login.tsx#L120) | { label } |  |
| [Login](../apps/scope/product/web/src/pages/Login.tsx#L135) |  |  |
| [handleDevTap](../apps/scope/product/web/src/pages/Login.tsx#L147) |  |  |
| [handleOAuth](../apps/scope/product/web/src/pages/Login.tsx#L181) | provider |  |
| [handleContinue](../apps/scope/product/web/src/pages/Login.tsx#L191) |  |  |

### apps/scope/product/web/src/pages/MyQuotes.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ScopeCard](../apps/scope/product/web/src/pages/MyQuotes.tsx#L39) | { scope } |  |
| [handleCta](../apps/scope/product/web/src/pages/MyQuotes.tsx#L53) |  |  |
| [MyQuotes](../apps/scope/product/web/src/pages/MyQuotes.tsx#L112) |  |  |

### apps/scope/product/web/src/pages/OnboardHomeowner.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [collectPhotos](../apps/scope/product/web/src/pages/OnboardHomeowner.tsx#L25) | messages | Collect all user-attached photo object-URLs from message history. |
| [OnboardHomeowner](../apps/scope/product/web/src/pages/OnboardHomeowner.tsx#L35) |  |  |
| [handleConfirm](../apps/scope/product/web/src/pages/OnboardHomeowner.tsx#L82) |  |  |

### apps/scope/product/web/src/pages/OnboardPro.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [OnboardPro](../apps/scope/product/web/src/pages/OnboardPro.tsx#L45) |  |  |
| [wait](../apps/scope/product/web/src/pages/OnboardPro.tsx#L180) | ms |  |
| [loop](../apps/scope/product/web/src/pages/OnboardPro.tsx#L181) |  |  |
| [handleConfirm](../apps/scope/product/web/src/pages/OnboardPro.tsx#L208) |  |  |

### apps/scope/product/web/src/pages/OpsMonitor.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [OpsMonitor](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L7) |  |  |
| [toggleJob](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L35) | id |  |
| [StatCard](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L112) | { label, value } |  |
| [PipelineFunnel](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L136) | { pipeline, total } |  |
| [JobCard](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L171) | { job, expanded, onToggle } |  |
| [Metric](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L252) | { label, value, warn = false } |  |
| [ContractorRow](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L267) | { contractor: c } |  |
| [StatusDot](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L347) | { active, label, color } |  |
| [timeAgo](../apps/scope/product/web/src/pages/OpsMonitor.tsx#L358) | ts |  |

### apps/scope/product/web/src/pages/ProjectDetail.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [getMilestoneBarStyle](../apps/scope/product/web/src/pages/ProjectDetail.tsx#L42) | status |  |
| [useUnreadCount](../apps/scope/product/web/src/pages/ProjectDetail.tsx#L51) | token, milestoneUpdates |  |
| [OfflineBanner](../apps/scope/product/web/src/pages/ProjectDetail.tsx#L69) |  |  |
| [on](../apps/scope/product/web/src/pages/ProjectDetail.tsx#L72) |  |  |
| [off](../apps/scope/product/web/src/pages/ProjectDetail.tsx#L73) |  |  |
| [ProjectDetail](../apps/scope/product/web/src/pages/ProjectDetail.tsx#L95) |  |  |
| [GateLogo](../apps/scope/product/web/src/pages/ProjectDetail.tsx#L265) |  |  |

### apps/scope/product/web/src/pages/QuoteSent.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [QuoteSent](../apps/scope/product/web/src/pages/QuoteSent.tsx#L24) |  |  |
| [handleWhatsApp](../apps/scope/product/web/src/pages/QuoteSent.tsx#L37) |  |  |
| [handleCopy](../apps/scope/product/web/src/pages/QuoteSent.tsx#L44) |  |  |
| [handleNativeShare](../apps/scope/product/web/src/pages/QuoteSent.tsx#L54) |  |  |

### apps/scope/product/web/src/pages/SandboxDashboard.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [PersonaCard](../apps/scope/product/web/src/pages/SandboxDashboard.tsx#L26) | { persona, onDelete, onActivate, isActive } |  |
| [CreatePersonaSheet](../apps/scope/product/web/src/pages/SandboxDashboard.tsx#L72) | { role, onClose } |  |
| [handleCreate](../apps/scope/product/web/src/pages/SandboxDashboard.tsx#L83) |  |  |
| [SandboxDashboard](../apps/scope/product/web/src/pages/SandboxDashboard.tsx#L169) |  |  |
| [handleActivate](../apps/scope/product/web/src/pages/SandboxDashboard.tsx#L174) | persona |  |

### apps/scope/product/web/src/pages/Settings.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [Settings](../apps/scope/product/web/src/pages/Settings.tsx#L14) |  |  |
| [handleLogout](../apps/scope/product/web/src/pages/Settings.tsx#L32) |  |  |
| [LanguageSettingRow](../apps/scope/product/web/src/pages/Settings.tsx#L144) |  |  |
| [toggle](../apps/scope/product/web/src/pages/Settings.tsx#L149) | lang |  |

### apps/scope/product/web/src/pages/StripeKyc.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [StripeKyc](../apps/scope/product/web/src/pages/StripeKyc.tsx#L30) |  |  |
| [launch](../apps/scope/product/web/src/pages/StripeKyc.tsx#L44) |  |  |

### apps/scope/product/web/src/pages/StripeRefresh.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [StripeRefresh](../apps/scope/product/web/src/pages/StripeRefresh.tsx#L14) |  |  |
| [refresh](../apps/scope/product/web/src/pages/StripeRefresh.tsx#L25) |  |  |

### apps/scope/product/web/src/pages/StripeReturn.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [StripeReturn](../apps/scope/product/web/src/pages/StripeReturn.tsx#L19) |  |  |
| [checkStatus](../apps/scope/product/web/src/pages/StripeReturn.tsx#L35) |  |  |
| [handleViewScope](../apps/scope/product/web/src/pages/StripeReturn.tsx#L57) |  |  |
| [handleCompleteKyc](../apps/scope/product/web/src/pages/StripeReturn.tsx#L64) |  |  |

### apps/scope/product/web/src/reel/CaptionStrip.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [CaptionStrip](../apps/scope/product/web/src/reel/CaptionStrip.tsx#L9) |  |  |

### apps/scope/product/web/src/reel/ReelSwitcher.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ReelSwitcher](../apps/scope/product/web/src/reel/ReelSwitcher.tsx#L11) |  |  |

### apps/scope/product/web/src/reel/engine.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [chatUserBeats](../apps/scope/product/web/src/reel/engine.ts#L89) |  | Beats that carry a user line (the ones that trigger a /v1/chat round-trip). |
| [resetChatCursor](../apps/scope/product/web/src/reel/engine.ts#L93) |  |  |
| [delay](../apps/scope/product/web/src/reel/engine.ts#L97) | ms |  |
| [clone](../apps/scope/product/web/src/reel/engine.ts#L105) | v |  |
| [reelData](../apps/scope/product/web/src/reel/engine.ts#L117) |  | Current mutable data for the active flow, lazily seeded from initialData. |
| [setReelData](../apps/scope/product/web/src/reel/engine.ts#L127) | mutate | Mutate the current data in place. |
| [resetReelData](../apps/scope/product/web/src/reel/engine.ts#L132) |  | Reset to a fresh clone of initialData (used at the top of each loop). |
| [prefersReducedMotion](../apps/scope/product/web/src/reel/engine.ts#L142) |  |  |
| [jsonResponse](../apps/scope/product/web/src/reel/engine.ts#L154) | body |  |
| [reelHandle](../apps/scope/product/web/src/reel/engine.ts#L166) | url, init | Returns a canned Response when reel mode can serve this request, else null (the caller then proceeds — and with VITE_API_URL=reel.invalid in the vendored build, any unhandled call fails loudly instead of hitting a dead host). |

### apps/scope/product/web/src/reel/flag.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [isReelFlowId](../apps/scope/product/web/src/reel/flag.ts#L30) | v |  |
| [reelFlowId](../apps/scope/product/web/src/reel/flag.ts#L39) |  | Resolve the active reel flow, or null when reel mode is off. Order: `?reel=<id>` query param (sticks it to localStorage) -> localStorage. `?reel=off` / `?reel=0` clears it. Invalid ids are ignored (treated as off). |
| [isReel](../apps/scope/product/web/src/reel/flag.ts#L63) |  | True when the app is running as a portfolio reel (any flow). |

### apps/scope/product/web/src/reel/registry.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [activeScript](../apps/scope/product/web/src/reel/registry.ts#L23) |  | The script for the active reel flow, or undefined when reel mode is off. |

### apps/scope/product/web/src/reel/scripts/approve-release.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [asset](../apps/scope/product/web/src/reel/scripts/approve-release.ts#L14) | f | Resolve a reel public asset in both dev (/app/) and the vendored build (/scope/app/). |

### apps/scope/product/web/src/reel/useReelChatDriver.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [wait](../apps/scope/product/web/src/reel/useReelChatDriver.ts#L28) | ms |  |
| [useReelChatDriver](../apps/scope/product/web/src/reel/useReelChatDriver.ts#L30) | chat, flowId |  |
| [runOnce](../apps/scope/product/web/src/reel/useReelChatDriver.ts#L43) |  |  |
| [loop](../apps/scope/product/web/src/reel/useReelChatDriver.ts#L65) |  |  |

### apps/scope/product/web/src/reel/useReelStepDriver.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [wait](../apps/scope/product/web/src/reel/useReelStepDriver.ts#L23) | ms |  |
| [useReelStepDriver](../apps/scope/product/web/src/reel/useReelStepDriver.ts#L25) | flowId, buildSteps, deps |  |
| [once](../apps/scope/product/web/src/reel/useReelStepDriver.ts#L38) |  |  |
| [loop](../apps/scope/product/web/src/reel/useReelStepDriver.ts#L48) |  |  |

### apps/scope/product/web/src/store.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [AppProvider](../apps/scope/product/web/src/store.tsx#L21) | { children } |  |
| [useApp](../apps/scope/product/web/src/store.tsx#L60) |  |  |

### packages/brand/src/brand/build.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_camel](../packages/brand/src/brand/build.py#L125) | key | ``ink_dark`` → ``inkDark``. |
| [_kebab](../packages/brand/src/brand/build.py#L131) | key | ``ink_dark`` → ``ink-dark``. |
| [_to_js_lit](../packages/brand/src/brand/build.py#L136) | value | Escape a string for JS/TS single-quoted literal output. |
| [_themes_for_json](../packages/brand/src/brand/build.py#L141) |  | Serialise THEMES with camelCase keys for JS/TS consumers. |
| [_emit_tokens_json](../packages/brand/src/brand/build.py#L156) |  | Serialise the full token set as JSON (camelCase keys, sorted families). |
| [_emit_tokens_ts](../packages/brand/src/brand/build.py#L171) |  | Emit ``tokens.ts`` — typed TS re-export matching old brand.ts surface. |
| [_emit_theme_overrides_tailwind](../packages/brand/src/brand/build.py#L245) |  | Emit ``[data-theme="..."] { ... }`` blocks for Tailwind v4 consumers. |
| [_emit_theme_overrides_vars](../packages/brand/src/brand/build.py#L272) |  | Emit ``[data-theme="..."] { ... }`` blocks for plain-HTML vars.css. |
| [_emit_tokens_css](../packages/brand/src/brand/build.py#L310) |  | Emit Tailwind v4 ``@theme { ... }`` block + ``[data-theme]`` overrides. |
| [_emit_vars_css](../packages/brand/src/brand/build.py#L352) |  | Emit ``:root { ... }`` block + utility classes (replaces brand-vars.css). |
| [_render_all](../packages/brand/src/brand/build.py#L500) |  |  |
| [_write](../packages/brand/src/brand/build.py#L504) | name, body |  |
| [_app_artifact_body](../packages/brand/src/brand/build.py#L515) | app, name, rendered | Return the generated-artifact body that app ``app`` should sync. |
| [_canonical_bytes](../packages/brand/src/brand/build.py#L531) | key, app | Read canonical bytes for a sync key (``effects.css``, ``generated/vars.css``, ``assets/leo-charcoal.svg``, ...). |
| [_sync_public_copy](../packages/brand/src/brand/build.py#L551) | app, target_rel, body |  |
| [_check_public_copies](../packages/brand/src/brand/build.py#L559) |  | Return a list of public copies that drift from the canonical. |
| [main](../packages/brand/src/brand/build.py#L584) | argv |  |

### packages/brand/src/brand/fluid-gradient.js

| Function | Arguments | Purpose |
| --- | --- | --- |
| [compile](../packages/brand/src/brand/fluid-gradient.js#L13) | gl, type, src |  |
| [link](../packages/brand/src/brand/fluid-gradient.js#L25) | gl, vs, fs |  |
| [makePass](../packages/brand/src/brand/fluid-gradient.js#L499) | gl, fragSrc, name |  |
| [makePreviewProgram](../packages/brand/src/brand/fluid-gradient.js#L514) | gl |  |
| [_fbo](../packages/brand/src/brand/fluid-gradient.js#L537) | w, h, internalFormat, format, type, filter |  |
| [swap](../packages/brand/src/brand/fluid-gradient.js#L561) |  |  |
| [destroy](../packages/brand/src/brand/fluid-gradient.js#L566) | gl |  |
| [resize](../packages/brand/src/brand/fluid-gradient.js#L573) | w, h, internalFormat, format, type, filter |  |
| [_initGL](../packages/brand/src/brand/fluid-gradient.js#L649) |  |  |
| [_buildPrograms](../packages/brand/src/brand/fluid-gradient.js#L677) |  |  |
| [_initGradientFBO](../packages/brand/src/brand/fluid-gradient.js#L897) |  |  |
| [_renderGradient](../packages/brand/src/brand/fluid-gradient.js#L932) | t |  |
| [_quadSim](../packages/brand/src/brand/fluid-gradient.js#L961) |  |  |
| [_quadPreview](../packages/brand/src/brand/fluid-gradient.js#L974) |  |  |
| [_bindSim](../packages/brand/src/brand/fluid-gradient.js#L997) |  |  |
| [_bindPreview](../packages/brand/src/brand/fluid-gradient.js#L1003) |  |  |
| [_setTarget](../packages/brand/src/brand/fluid-gradient.js#L1009) | fbo |  |
| [_blit](../packages/brand/src/brand/fluid-gradient.js#L1020) | pass, setUniforms |  |
| [resize](../packages/brand/src/brand/fluid-gradient.js#L1027) |  |  |
| [_createBuffers](../packages/brand/src/brand/fluid-gradient.js#L1053) | sw, sh |  |
| [_recreateBuffers](../packages/brand/src/brand/fluid-gradient.js#L1067) | sw, sh |  |
| [_syntheticAudio](../packages/brand/src/brand/fluid-gradient.js#L1092) | t | Fake “audio” for the Eleven-style preview: slow swell + tide envelopes and low-frequency carriers (no fast beating). tanh soft-clips mixes for round peaks. |
| [soft](../packages/brand/src/brand/fluid-gradient.js#L1102) | x |  |
| [_staticPreviewAudio](../packages/brand/src/brand/fluid-gradient.js#L1139) | t | Constant band levels + linear cum only — preview shader stays balanced without frame-varying “audio” (removes micro-jitter on landing heroes). |
| [_smoothPreviewAudio](../packages/brand/src/brand/fluid-gradient.js#L1156) | au | Two-stage low-pass on avg / avgIn: fast stage follows target, slow stage trails for a longer decay tail (less frame-to-frame jitter from uniforms). |
| [_advanceVisualTime](../packages/brand/src/brand/fluid-gradient.js#L1179) | dt | Two-pole exponential toward sim time — no spring overshoot / snap-back (plastic drift). Convex combos only; cannot ring past the target like a damped oscillator. |
| [_tick](../packages/brand/src/brand/fluid-gradient.js#L1194) |  |  |
| [_step](../packages/brand/src/brand/fluid-gradient.js#L1232) |  |  |
| [initGradients](../packages/brand/src/brand/fluid-gradient.js#L1697) |  |  |

### packages/brand/src/brand/illustrations/generate.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_load_theme_style](../packages/brand/src/brand/illustrations/generate.py#L34) | theme | Resolve the ``IllustrationStyle`` for *theme* via dynamic import. |
| [generate](../packages/brand/src/brand/illustrations/generate.py#L48) |  | Generate an illustration of *scene* in the Leo house register. |
| [generate_with_references](../packages/brand/src/brand/illustrations/generate.py#L114) |  | Generate a raster illustration that preserves identity across refs. |

### packages/brand/src/brand/illustrations/post/chroma_key.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [process](../packages/brand/src/brand/illustrations/post/chroma_key.py#L17) | image | Make pixels within *tolerance* of *color* transparent. |

### packages/brand/src/brand/illustrations/post/luminosity_alpha.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [process](../packages/brand/src/brand/illustrations/post/luminosity_alpha.py#L35) | image | Knock white out, force black. Returns RGBA PNG bytes. |
| [_remap](../packages/brand/src/brand/illustrations/post/luminosity_alpha.py#L55) | v |  |

### packages/brand/src/brand/illustrations/providers/litellm_raster.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_load_template](../packages/brand/src/brand/illustrations/providers/litellm_raster.py#L32) |  |  |
| [_build_prompt](../packages/brand/src/brand/illustrations/providers/litellm_raster.py#L36) |  |  |
| [render](../packages/brand/src/brand/illustrations/providers/litellm_raster.py#L40) |  | Render a raster illustration of *scene* in the Leo house register. |

### packages/brand/src/brand/illustrations/providers/litellm_raster_refs.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [render](../packages/brand/src/brand/illustrations/providers/litellm_raster_refs.py#L24) |  | Render a raster illustration conditioned on reference images. |

### packages/brand/src/brand/illustrations/providers/vtracer_vector.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_flatten_on_white](../packages/brand/src/brand/illustrations/providers/vtracer_vector.py#L38) | rgba_png | Composite a transparent RGBA PNG onto pure white → opaque RGB PNG. |
| [render](../packages/brand/src/brand/illustrations/providers/vtracer_vector.py#L55) |  | Render a vector SVG for *scene* under *style*, raster-then-trace. |

### packages/brand/src/brand/motion/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [get](../packages/brand/src/brand/motion/__init__.py#L32) | name | Look up a motion style by name. Raises ``KeyError`` on miss. |
| [names](../packages/brand/src/brand/motion/__init__.py#L41) |  | Return the sorted list of registered motion names. |

### packages/brand/src/brand/motion/quiet.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_css](../packages/brand/src/brand/motion/quiet.py#L129) | self | Emit CSS variables under ``:root``. |
| [to_ts](../packages/brand/src/brand/motion/quiet.py#L162) | self | Emit a TypeScript export object — framer-motion-consumable. |

### packages/brand/src/brand/themes/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [get](../packages/brand/src/brand/themes/__init__.py#L30) | name | Return the theme module for *name*. Raises ``KeyError`` on miss. |
| [names](../packages/brand/src/brand/themes/__init__.py#L39) |  | Return the sorted list of registered theme names. |

### packages/brand/src/brand/translucency/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [get](../packages/brand/src/brand/translucency/__init__.py#L25) | name | Look up a translucency style by name. Raises ``KeyError`` on miss. |
| [names](../packages/brand/src/brand/translucency/__init__.py#L35) |  | Return the sorted list of registered style names. |

### packages/brand/src/brand/translucency/vellum.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_css](../packages/brand/src/brand/translucency/vellum.py#L37) | self, selector | Emit the full CSS block for *selector*. |

### packages/brand/src/brand/typography/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [get](../packages/brand/src/brand/typography/__init__.py#L23) | name | Look up a typography style by name. Raises ``KeyError`` on miss. |
| [names](../packages/brand/src/brand/typography/__init__.py#L32) |  | Return the sorted list of registered typography names. |

### packages/brand/src/brand/typography/default.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_css](../packages/brand/src/brand/typography/default.py#L32) | self | Emit CSS custom properties for the font families. |

### packages/brand/src/illustrations.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [generateIllustration](../packages/brand/src/illustrations.ts#L44) | req |  |

### packages/brand/src/translucency.ts

| Function | Arguments | Purpose |
| --- | --- | --- |
| [translucencyCss](../packages/brand/src/translucency.ts#L39) | style, selector |  |

### packages/core/src/core/auth/api_keys.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [verify_api_key](../packages/core/src/core/auth/api_keys.py#L39) | raw_key | Look up an API key; return the row (or ``None`` on miss / error). |
| [require_api_key_or_jwt](../packages/core/src/core/auth/api_keys.py#L77) | authorization, x_api_key | FastAPI dep: accept a JWT or an API key. |

### packages/core/src/core/auth/deps.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_contractor_id_for_auth_user](../packages/core/src/core/auth/deps.py#L46) | auth_user_id | Look up the claimed contractor row for a Supabase auth user. |
| [_resolve_current_user](../packages/core/src/core/auth/deps.py#L79) | access_token | Verify JWT, then resolve role + contractor_id. |
| [require_auth](../packages/core/src/core/auth/deps.py#L102) | authorization | Require any valid Supabase JWT (contractor or homeowner). |
| [optional_auth](../packages/core/src/core/auth/deps.py#L116) | authorization | Return the caller identity if a JWT is present, else ``None``. |
| [require_contractor](../packages/core/src/core/auth/deps.py#L134) | authorization | Require a JWT belonging to a claimed contractor. |
| [require_homeowner](../packages/core/src/core/auth/deps.py#L155) | authorization | Require a JWT belonging to a homeowner (non-contractor) account. |

### packages/core/src/core/auth/jwt.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/core/src/core/auth/jwt.py#L54) | self |  |
| [get](../packages/core/src/core/auth/jwt.py#L60) | self, key |  |
| [set](../packages/core/src/core/auth/jwt.py#L73) | self, key, payload |  |
| [clear](../packages/core/src/core/auth/jwt.py#L81) | self |  |
| [_cache_enabled](../packages/core/src/core/auth/jwt.py#L86) |  |  |
| [_ttl_seconds](../packages/core/src/core/auth/jwt.py#L90) |  |  |
| [_cache_size](../packages/core/src/core/auth/jwt.py#L97) |  |  |
| [clear_jwt_cache](../packages/core/src/core/auth/jwt.py#L107) |  | Drop every entry from the JWT cache. Used by tests. |
| [verify_supabase_jwt](../packages/core/src/core/auth/jwt.py#L117) | access_token | Verify a JWT via ``GET /auth/v1/user``. |

### packages/core/src/core/auth/tokens.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_is_dev_env](../packages/core/src/core/auth/tokens.py#L49) |  |  |
| [tracker_token_valid](../packages/core/src/core/auth/tokens.py#L53) | token | Predicate form of :func:`require_tracker_token` for routes that only *conditionally* require a valid ``X-Tracker-Token``. |
| [_check_token](../packages/core/src/core/auth/tokens.py#L72) | header_value, env_var, header_name, code_prefix |  |
| [require_ops_token](../packages/core/src/core/auth/tokens.py#L100) | x_ops_token | Require ``X-Ops-Token`` matching ``OPS_TOKEN`` env var. |
| [require_tracker_token](../packages/core/src/core/auth/tokens.py#L110) | x_tracker_token | Require ``X-Tracker-Token`` matching ``SALES_TRACKER_TOKEN`` env var. |

### packages/core/src/core/auth/webhooks.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [verify_webhook_signature](../packages/core/src/core/auth/webhooks.py#L33) | payload, signature, secret | Constant-time HMAC verification. |

### packages/core/src/core/aws.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_load_env_local](../packages/core/src/core/aws.py#L63) |  | Ensure ``.env.local`` is loaded before reading suffixed creds. |
| [normalize_leo_aws_account](../packages/core/src/core/aws.py#L68) | raw | Upper-case + underscore-normalise the account name. |
| [get_active_leo_aws_account](../packages/core/src/core/aws.py#L83) |  | Return the normalised active account name. |
| [_cached_pair](../packages/core/src/core/aws.py#L101) | account |  |
| [get_leo_aws_credentials](../packages/core/src/core/aws.py#L116) |  | Return ``(access_key_id, secret_access_key)`` for the active account. |
| [clear_leo_aws_credential_cache](../packages/core/src/core/aws.py#L125) |  | Reset the credential cache. Used by tests after env manipulation. |
| [leo_boto3_client](../packages/core/src/core/aws.py#L131) | service_name | boto3.client with explicit Leo account credentials. |
| [_bedrock_client_for](../packages/core/src/core/aws.py#L165) | region, read_timeout, connect_timeout, max_attempts |  |
| [bedrock_client](../packages/core/src/core/aws.py#L178) | region | Return a cached Bedrock client for the given region + timeouts. |
| [validate_leo_aws_for_bedrock](../packages/core/src/core/aws.py#L195) |  | Resolve credentials once; raise :class:`RuntimeError` if misconfigured. |
| [log_active_leo_aws_account](../packages/core/src/core/aws.py#L200) |  | Emit a safe startup log: account name + short key prefix, no secrets. |

### packages/core/src/core/bootstrap.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [repo_root](../packages/core/src/core/bootstrap.py#L55) |  | Return the repo root by walking parents for ``pyproject.toml`` + ``.git``. |
| [scope_backend_dir](../packages/core/src/core/bootstrap.py#L78) |  | Return the path to the scope-backend tree. |
| [backend_dir](../packages/core/src/core/bootstrap.py#L93) |  | Deprecated alias for :func:`scope_backend_dir`. |
| [init](../packages/core/src/core/bootstrap.py#L104) |  | Idempotent: add the backend dir to ``sys.path`` + load ``.env.local``. |
| [load_env_files](../packages/core/src/core/bootstrap.py#L136) | paths | Load one or more dotenv files; return the list of paths that loaded. |

### packages/core/src/core/db.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_supabase_url_base](../packages/core/src/core/db.py#L73) |  |  |
| [sb_url](../packages/core/src/core/db.py#L80) |  | Supabase REST base URL, i.e. ``{SUPABASE_URL}/rest/v1``. |
| [sb_auth_url](../packages/core/src/core/db.py#L85) |  | Supabase Auth API base URL, i.e. ``{SUPABASE_URL}/auth/v1``. |
| [sb_key](../packages/core/src/core/db.py#L90) |  | Service-role key if set, else anon key. |
| [sb_headers](../packages/core/src/core/db.py#L107) |  | Standard headers for Supabase REST calls. |
| [__init__](../packages/core/src/core/db.py#L140) | self, client |  |
| [client](../packages/core/src/core/db.py#L144) | self | The underlying :class:`httpx.AsyncClient`. |
| [select](../packages/core/src/core/db.py#L150) | self, table | Run ``GET /rest/v1/{table}`` with PostgREST-style query params. |
| [insert](../packages/core/src/core/db.py#L175) | self, table, row | Run ``POST /rest/v1/{table}`` with a single row payload. |
| [upsert](../packages/core/src/core/db.py#L197) | self, table, row | Run ``POST /rest/v1/{table}`` with ``Prefer: resolution=merge-duplicates``. |
| [update](../packages/core/src/core/db.py#L226) | self, table, patch | Run ``PATCH /rest/v1/{table}`` with PostgREST filters on the URL. |
| [delete](../packages/core/src/core/db.py#L249) | self, table | Run ``DELETE /rest/v1/{table}`` with PostgREST filters. |
| [request](../packages/core/src/core/db.py#L270) | self, method, path | Escape-hatch raw request. Returns the :class:`httpx.Response`. |
| [_build_client](../packages/core/src/core/db.py#L304) |  | Build a new pooled :class:`httpx.AsyncClient`. |
| [get_supabase](../packages/core/src/core/db.py#L319) |  | Return the process-wide :class:`Supabase` singleton. |
| [close_supabase_pool](../packages/core/src/core/db.py#L333) |  | Close the pooled client (call on FastAPI shutdown). |
| [check_supabase_health](../packages/core/src/core/db.py#L343) |  | Probe Supabase reachability. |

### packages/core/src/core/errors.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/core/src/core/errors.py#L74) | self, message |  |
| [to_detail](../packages/core/src/core/errors.py#L79) | self | Return the JSON-serialisable ``detail`` body for FastAPI. |
| [to_http](../packages/core/src/core/errors.py#L86) | self | Return an :class:`HTTPException` with this error's status + body. |
| [api_error](../packages/core/src/core/errors.py#L133) | status, message | Return an :class:`HTTPException` matching the unified error envelope. |

### packages/core/src/core/http.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [local_http_transport](../packages/core/src/core/http.py#L46) | transport | Bind a recipient-owned REST transport for only the current request. |
| [http_client](../packages/core/src/core/http.py#L66) | timeout | General-purpose async client with Leo's defaults. |
| [sb_request](../packages/core/src/core/http.py#L87) | timeout | Short-lived Supabase-scoped async client (base_url + auth headers). |
| [http_client_sync](../packages/core/src/core/http.py#L107) | timeout | Sync counterpart to :func:`http_client`. |

### packages/core/src/core/money.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_as_decimal](../packages/core/src/core/money.py#L49) | value | Coerce *value* to ``Decimal`` via ``str(value)`` to dodge float noise. |
| [_quantize](../packages/core/src/core/money.py#L63) | value | Round *value* to 2 dp, ROUND_HALF_UP (Spanish legal convention). |
| [to_cents](../packages/core/src/core/money.py#L73) | eur | Convert EUR amount to integer cents (HALF_UP at 2 dp). |
| [from_cents](../packages/core/src/core/money.py#L89) | cents | Convert integer cents to ``Decimal`` EUR (2 dp). |
| [add_iva](../packages/core/src/core/money.py#L109) | amount, rate | Return ``amount * (1 + rate)`` rounded 2 dp HALF_UP. |
| [strip_iva](../packages/core/src/core/money.py#L125) | gross, rate | Inverse of ``add_iva``: extract net from gross. |
| [iva_amount](../packages/core/src/core/money.py#L138) | amount, rate | Return only the VAT component: ``amount * rate`` rounded 2 dp. |
| [add_iva_percent](../packages/core/src/core/money.py#L157) | amount, percent | Like :func:`add_iva` but *percent* is an integer percentage. |
| [strip_iva_percent](../packages/core/src/core/money.py#L166) | gross, percent | Like :func:`strip_iva` but *percent* is an integer percentage. |
| [iva_amount_percent](../packages/core/src/core/money.py#L171) | amount, percent | Like :func:`iva_amount` but *percent* is an integer percentage. |
| [format_eur](../packages/core/src/core/money.py#L183) | amount | Format *amount* as EUR string. |

### packages/core/src/core/phone.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_digits](../packages/core/src/core/phone.py#L52) | s | Strip every non-digit char. |
| [normalize](../packages/core/src/core/phone.py#L63) | raw | Normalize a Spanish phone number to its 9-digit dedup key. |
| [extract_from_html](../packages/core/src/core/phone.py#L87) | html | Extract + normalize phones from ``tel:`` links in HTML. |
| [is_valid_spanish](../packages/core/src/core/phone.py#L99) | phone | Check if a *normalized* phone looks like a valid Spanish number. |
| [to_e164](../packages/core/src/core/phone.py#L115) | raw | Return E.164 form ("+CCNNNNNNNNN"). |
| [dedup_by_phone](../packages/core/src/core/phone.py#L191) | items | Drop duplicates from *items* where two records share a normalized phone. |
| [normalize](../packages/core/src/core/phone.py#L231) | self, raw |  |
| [to_e164](../packages/core/src/core/phone.py#L232) | self, raw |  |
| [is_valid_spanish](../packages/core/src/core/phone.py#L233) | self, phone |  |

### packages/core/src/core/resilience.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [retry](../packages/core/src/core/resilience.py#L60) |  | Sync retry decorator with exponential backoff + jitter. |
| [deco](../packages/core/src/core/resilience.py#L73) | fn |  |
| [wrapper](../packages/core/src/core/resilience.py#L75) |  |  |
| [async_retry](../packages/core/src/core/resilience.py#L101) |  | Async retry decorator with exponential backoff + jitter. |
| [deco](../packages/core/src/core/resilience.py#L114) | fn |  |
| [wrapper](../packages/core/src/core/resilience.py#L118) |  |  |
| [__init__](../packages/core/src/core/resilience.py#L157) | self |  |
| [acquire](../packages/core/src/core/resilience.py#L165) | self |  |
| [aacquire](../packages/core/src/core/resilience.py#L179) | self |  |
| [timed_cache](../packages/core/src/core/resilience.py#L199) | ttl | lru_cache with TTL. Thread-safe. Per-decorated-fn closure dict. |
| [deco](../packages/core/src/core/resilience.py#L210) | fn |  |
| [wrapper](../packages/core/src/core/resilience.py#L215) |  |  |
| [_invalidate](../packages/core/src/core/resilience.py#L231) |  |  |
| [shared_thread_pool](../packages/core/src/core/resilience.py#L249) |  | One process-wide :class:`ThreadPoolExecutor`. |
| [shutdown_thread_pool](../packages/core/src/core/resilience.py#L268) | wait | Shut down the shared pool (tests + FastAPI shutdown). |
| [run_sync](../packages/core/src/core/resilience.py#L282) | coro | Run an awaitable from sync code. Handles nested-loop case. |
| [_as_coro](../packages/core/src/core/resilience.py#L303) | awaitable |  |

### packages/core/src/core/text.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [strip_accents](../packages/core/src/core/text.py#L36) | text | Remove diacritical marks. |
| [normalize_spanish](../packages/core/src/core/text.py#L53) | text | Canonical form for Spanish search / equality comparison. |
| [slugify](../packages/core/src/core/text.py#L78) | text | Produce a URL-safe slug. |

### packages/fulltext/src/fulltext/_stemmer.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_stem_word_impl](../packages/fulltext/src/fulltext/_stemmer.py#L30) | w |  |
| [_identity](../packages/fulltext/src/fulltext/_stemmer.py#L37) | w |  |
| [stem_word](../packages/fulltext/src/fulltext/_stemmer.py#L43) | w | Return the Spanish Snowball stem of a single word. |

### packages/fulltext/src/fulltext/forum/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [set_provider](../packages/fulltext/src/fulltext/forum/__init__.py#L22) | provider | Inject a concrete async forum-search provider. |
| [forum_search](../packages/fulltext/src/fulltext/forum/__init__.py#L29) | query | Async forum-corpus search. |

### packages/fulltext/src/fulltext/index.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/fulltext/src/fulltext/index.py#L51) | self, name, db_path | :param name: Logical collection name (``"prices"``, ``"cype"``). :param db_path: Optional explicit path; if omitted, uses     ``<package_root>/data/indexes/{name}.db`` relative to the     consumer — pass one explicitly in production callers. |
| [_setup_tables](../packages/fulltext/src/fulltext/index.py#L71) | self |  |
| [add](../packages/fulltext/src/fulltext/index.py#L121) | self, doc_id, slug, title, body, meta | Insert or replace a document. All text fields are stemmed at index time — the ``documents`` table stores the post-tokenisation form, which the FTS triggers then index. This keeps index-time and query-time tokenisation in lock-step (D4). |
| [add_city_price](../packages/fulltext/src/fulltext/index.py#L147) | self, doc_id, city, prices, source, title, slug | Insert or replace a (doc_id, city) pricing row. |
| [commit](../packages/fulltext/src/fulltext/index.py#L179) | self | Flush pending writes. |
| [count](../packages/fulltext/src/fulltext/index.py#L184) | self | Return number of indexed documents. |
| [search](../packages/fulltext/src/fulltext/index.py#L190) | self, query, limit, city | Full-text search with BM25 ranking. |
| [search_city](../packages/fulltext/src/fulltext/index.py#L277) | self, city, query, limit | Flat city-price lookup, optionally narrowed by an FTS query. |
| [rebuild](../packages/fulltext/src/fulltext/index.py#L356) | self | Rebuild the FTS5 index from scratch (expensive). |
| [drop](../packages/fulltext/src/fulltext/index.py#L363) | self | Drop and recreate all tables. |
| [close](../packages/fulltext/src/fulltext/index.py#L376) | self | Close the underlying SQLite connection. |
| [__del__](../packages/fulltext/src/fulltext/index.py#L381) | self |  |

### packages/fulltext/src/fulltext/legal/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [set_provider](../packages/fulltext/src/fulltext/legal/__init__.py#L23) | provider | Inject a concrete async legal-search provider. |
| [legal_search](../packages/fulltext/src/fulltext/legal/__init__.py#L30) | query | Async legal-corpus search. |

### packages/fulltext/src/fulltext/protocols.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [search](../packages/fulltext/src/fulltext/protocols.py#L26) | self, query, limit, city | Return up to ``limit`` BM25-ranked results. |
| [count](../packages/fulltext/src/fulltext/protocols.py#L34) | self | Return total indexed document count. |
| [search](../packages/fulltext/src/fulltext/protocols.py#L42) | self, query | Return up to ``limit`` results; MAY raise :class:`~fulltext.errors.SearchError` subclasses. |

### packages/fulltext/src/fulltext/rerank.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [city_boost](../packages/fulltext/src/fulltext/rerank.py#L30) | city | Return a reranker that subtracts ``amount`` from the rank of any result whose ``meta["city_prices"]`` mentions ``city``. |
| [_run](../packages/fulltext/src/fulltext/rerank.py#L45) | results |  |
| [chain_reranks](../packages/fulltext/src/fulltext/rerank.py#L70) |  | Compose rerankers left-to-right. |
| [_run](../packages/fulltext/src/fulltext/rerank.py#L77) | results |  |

### packages/fulltext/src/fulltext/synonyms.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_make_or_group](../packages/fulltext/src/fulltext/synonyms.py#L143) | stems | Build an FTS5 OR group: single token or ``(a OR b OR c)``. |
| [expand_query](../packages/fulltext/src/fulltext/synonyms.py#L152) | raw_query | Expand a raw user query into an FTS5 MATCH expression. |

### packages/fulltext/src/fulltext/tokenizer.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [tokenize](../packages/fulltext/src/fulltext/tokenizer.py#L36) | text | Normalise + stem + filter a free-text string. |

### packages/fulltext/src/fulltext/web/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [set_provider](../packages/fulltext/src/fulltext/web/__init__.py#L29) | provider | Inject a concrete async provider. ``None`` reverts to the stub (empty-result) behaviour. Intended for app bootstrap + tests. |
| [web_search](../packages/fulltext/src/fulltext/web/__init__.py#L37) | query | Async open-web search. Returns ``[]`` unless a provider has been installed via :func:`set_provider`. |

### packages/llm/src/llm/chat.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_normalise](../packages/llm/src/llm/chat.py#L32) | messages_or_prompt | Accept ``str`` → wrap in single user :class:`Message`. |
| [_resolve_model_or_tier](../packages/llm/src/llm/chat.py#L41) | model, tier |  |
| [chat](../packages/llm/src/llm/chat.py#L61) | messages_or_prompt | Unified async chat entry point. Dispatches on provider. |
| [_invoke](../packages/llm/src/llm/chat.py#L83) | model_id |  |
| [chat_sync](../packages/llm/src/llm/chat.py#L129) | messages_or_prompt | Sync version of :func:`chat`. No fallback chain — sync callers (i18n_engine, sales_tracker, profile_import) run single-shot. |
| [_emit_usage](../packages/llm/src/llm/chat.py#L184) | resp | Dispatch the response to observability; swallow observer bugs. |

### packages/llm/src/llm/config.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [proxy_base_url](../packages/llm/src/llm/config.py#L39) |  | Return the proxy base URL. |
| [proxy_api_key](../packages/llm/src/llm/config.py#L48) |  | Return the proxy API key. See :func:`proxy_base_url` for rationale. |

### packages/llm/src/llm/embed.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_endpoint](../packages/llm/src/llm/embed.py#L27) |  |  |
| [_headers](../packages/llm/src/llm/embed.py#L31) |  |  |
| [_parse](../packages/llm/src/llm/embed.py#L38) | data |  |
| [embed](../packages/llm/src/llm/embed.py#L50) | texts | Async text embedding. |
| [embed_sync](../packages/llm/src/llm/embed.py#L79) | texts | Sync text embedding. One-shot ``httpx.Client`` per call. |

### packages/llm/src/llm/errors.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/llm/src/llm/errors.py#L37) | self, message |  |
| [__repr__](../packages/llm/src/llm/errors.py#L50) | self |  |

### packages/llm/src/llm/images.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_endpoint](../packages/llm/src/llm/images.py#L49) |  |  |
| [_headers](../packages/llm/src/llm/images.py#L53) |  |  |
| [_map_http_error](../packages/llm/src/llm/images.py#L60) | exc |  |
| [_parse_response](../packages/llm/src/llm/images.py#L99) | data |  |
| [_build_body](../packages/llm/src/llm/images.py#L135) |  |  |
| [generate_image](../packages/llm/src/llm/images.py#L155) | prompt | Generate an image via the LiteLLM proxy. Sync. |
| [generate_image_async](../packages/llm/src/llm/images.py#L234) | prompt | Async version of :func:`generate_image`. Same semantics and errors. |
| [_chat_endpoint](../packages/llm/src/llm/images.py#L270) |  |  |
| [_extract_image_from_chat](../packages/llm/src/llm/images.py#L274) | data | Parse an OpenRouter-style image response from chat-completions. |
| [generate_image_via_chat](../packages/llm/src/llm/images.py#L316) | prompt | Text-to-image via the chat-completions endpoint. |
| [generate_image_with_references](../packages/llm/src/llm/images.py#L370) | prompt | Generate an image conditioned on one or more reference images. |

### packages/llm/src/llm/models/pricing.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [estimate_cost](../packages/llm/src/llm/models/pricing.py#L68) | usage | Return USD cost of *usage* on *model*. |

### packages/llm/src/llm/models/registry.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_build_registry](../packages/llm/src/llm/models/registry.py#L295) |  | Index every model by id + every alias. Enforce invariants. |
| [resolve_model](../packages/llm/src/llm/models/registry.py#L334) | id_or_alias | Look up a model by id, alias, or ``bedrock/...`` prefix. |
| [by_tier](../packages/llm/src/llm/models/registry.py#L365) | tier | Return every model matching *tier*, ordered by registration. |
| [for_provider](../packages/llm/src/llm/models/registry.py#L379) | provider | Return every model for a given provider, in registration order. |

### packages/llm/src/llm/models/tiers.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [pick](../packages/llm/src/llm/models/tiers.py#L38) | tier | Return the canonical ``Model.id`` for *tier*'s default. |

### packages/llm/src/llm/prompts/loader.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [render](../packages/llm/src/llm/prompts/loader.py#L49) | self, variables | Render the template through Jinja with ``StrictUndefined``. |
| [_parse_frontmatter](../packages/llm/src/llm/prompts/loader.py#L69) | raw | Extract YAML frontmatter from a ``.md`` file. Missing → ``{}``. |
| [load_prompt](../packages/llm/src/llm/prompts/loader.py#L83) | path | Parse a ``.md + YAML frontmatter`` file into a :class:`Prompt`. |

### packages/llm/src/llm/prompts/registry.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/llm/src/llm/prompts/registry.py#L39) | self, root |  |
| [_load](../packages/llm/src/llm/prompts/registry.py#L44) | self | Walk the templates root, parse every ``.md``. Idempotent. |
| [register](../packages/llm/src/llm/prompts/registry.py#L54) | self, prompt | Inject a :class:`Prompt` into the registry. Idempotent on key. |
| [get](../packages/llm/src/llm/prompts/registry.py#L62) | self, prompt_id | Look up a prompt. *version* ``None`` ⇒ highest; *language* ``None`` ⇒ language-agnostic entry, else falls through to language-specific entry. |
| [list](../packages/llm/src/llm/prompts/registry.py#L95) | self | Every known prompt id, in registration order (deduplicated). |
| [render_prompt](../packages/llm/src/llm/prompts/registry.py#L112) | prompt_id | One-shot: look up *prompt_id* and :meth:`~Prompt.render` it. |
| [list_prompts](../packages/llm/src/llm/prompts/registry.py#L128) |  | Convenience wrapper around :meth:`PROMPTS.list`. |
| [get_prompt](../packages/llm/src/llm/prompts/registry.py#L133) | prompt_id | Return the raw :class:`Prompt` without rendering. |

### packages/llm/src/llm/providers/base.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [cost_usd](../packages/llm/src/llm/providers/base.py#L89) | self | Compute USD cost via :data:`llm.PRICING`. Returns 0.0 on unknown model. |

### packages/llm/src/llm/providers/bedrock.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_bedrock_client](../packages/llm/src/llm/providers/bedrock.py#L65) | region | Return a ``bedrock-runtime`` client for *region* with Leo billing discipline. |
| [_msg_to_converse](../packages/llm/src/llm/providers/bedrock.py#L103) | m | Leo :class:`Message` → Bedrock Converse API message shape. |
| [_parse_converse_response](../packages/llm/src/llm/providers/bedrock.py#L136) | data |  |
| [_map_botocore_error](../packages/llm/src/llm/providers/bedrock.py#L165) | exc | Translate a botocore ``ClientError`` → :mod:`llm.errors` hierarchy. |
| [complete_sync](../packages/llm/src/llm/providers/bedrock.py#L194) | messages | Sync Bedrock Converse call. Runs on the caller's thread — callers from async code MUST wrap in ``asyncio.to_thread`` (see :func:`llm.providers.bedrock.complete`). |
| [complete](../packages/llm/src/llm/providers/bedrock.py#L246) | messages | Async wrapper over :func:`complete_sync` via ``asyncio.to_thread``. |

### packages/llm/src/llm/providers/fallback.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [resolve_chain](../packages/llm/src/llm/providers/fallback.py#L49) | name_or_list | Resolve a named chain or raw list into an ordered model id list. |
| [run_with_fallback](../packages/llm/src/llm/providers/fallback.py#L82) | primary, fallback | Run *invoke(model_id)* against *primary*, falling through *fallback* on retryable errors. |

### packages/llm/src/llm/providers/gemini.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [complete](../packages/llm/src/llm/providers/gemini.py#L28) | messages | Async Gemini completion. Currently proxied; spec'd for native. |
| [complete_sync](../packages/llm/src/llm/providers/gemini.py#L52) | messages | Sync Gemini completion. Currently proxied; spec'd for native. |

### packages/llm/src/llm/providers/litellm_proxy.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_msg_to_wire](../packages/llm/src/llm/providers/litellm_proxy.py#L51) | m | Leo :class:`Message` → OpenAI Chat message dict. |
| [_tool_to_wire](../packages/llm/src/llm/providers/litellm_proxy.py#L66) | t | Leo :class:`Tool` → OpenAI function-calling schema. |
| [_parse_response](../packages/llm/src/llm/providers/litellm_proxy.py#L78) | data | OpenAI response JSON → :class:`ChatResponse`. Raises :exc:`InvalidResponseShape` on missing fields. |
| [_map_http_error](../packages/llm/src/llm/providers/litellm_proxy.py#L139) | exc | Translate httpx exceptions into :mod:`llm.errors` taxonomy. |
| [_build_body](../packages/llm/src/llm/providers/litellm_proxy.py#L183) |  |  |
| [_build_headers](../packages/llm/src/llm/providers/litellm_proxy.py#L216) |  |  |
| [_endpoint](../packages/llm/src/llm/providers/litellm_proxy.py#L223) |  |  |
| [complete](../packages/llm/src/llm/providers/litellm_proxy.py#L227) | messages | Async chat completion via the LiteLLM proxy. |
| [complete_sync](../packages/llm/src/llm/providers/litellm_proxy.py#L267) | messages | Sync chat completion via the LiteLLM proxy. |

### packages/llm/src/llm/stream.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [stream](../packages/llm/src/llm/stream.py#L25) | messages_or_prompt | Stream completion chunks. Terminal chunk carries ``usage``. |

### packages/llm/src/llm/structured.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_choose_mode](../packages/llm/src/llm/structured.py#L34) | model_id | Pick ``json_schema`` if the model supports strict schema; else ``json_object``. |
| [_parse](../packages/llm/src/llm/structured.py#L41) | raw_text |  |
| [complete_structured](../packages/llm/src/llm/structured.py#L60) | messages_or_prompt | Async structured-output call. Returns a validated *schema* instance. |
| [complete_structured_sync](../packages/llm/src/llm/structured.py#L83) | messages_or_prompt | Sync structured-output call. Returns a validated *schema* instance. |

### packages/llm/src/llm/tokens.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_tiktoken_encoder](../packages/llm/src/llm/tokens.py#L21) |  | Lazy-load a tiktoken encoder. Returns ``None`` if unavailable. |
| [count_tokens](../packages/llm/src/llm/tokens.py#L31) | text | Estimate the token count of *text*. |
| [count_message_tokens](../packages/llm/src/llm/tokens.py#L44) | messages | Estimate tokens for a whole :class:`Message` list. |

### packages/llm/src/llm/usage.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_default_log_observer](../packages/llm/src/llm/usage.py#L33) | resp | Log model, tokens, est cost at INFO. Installed by default. |
| [register_observer](../packages/llm/src/llm/usage.py#L54) | observer | Subscribe *observer* to every :func:`record_usage` event. |
| [unregister_observer](../packages/llm/src/llm/usage.py#L63) | observer | Remove *observer* from the subscription list. |
| [record_usage](../packages/llm/src/llm/usage.py#L74) | resp | Fan *resp* out to every registered observer. |

### packages/llm/src/llm/vision.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_to_data_url](../packages/llm/src/llm/vision.py#L31) | image | Normalise image input to a ``data:`` URL. |
| [_build_vision_message](../packages/llm/src/llm/vision.py#L63) | prompt, image | Assemble a single user :class:`Message` with text + image_url blocks. |
| [_ensure_vision](../packages/llm/src/llm/vision.py#L74) | model_id | Raise :exc:`ModelNotFound` if *model_id* doesn't support vision. |
| [complete_vision](../packages/llm/src/llm/vision.py#L84) | prompt, image | Async vision call. Default model is :data:`~llm.models.tiers.DEFAULT_VISION`. |
| [complete_vision_sync](../packages/llm/src/llm/vision.py#L108) | prompt, image | Sync vision call. No fallback — sync callers run single-shot. |

### packages/messaging/src/messaging/channel.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [copy](../packages/messaging/src/messaging/channel.py#L111) | self | Return a new :class:`ChannelCapabilities` with ``updates`` applied. |

### packages/messaging/src/messaging/comms.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [notify](../packages/messaging/src/messaging/comms.py#L73) |  | Send a notification via the appropriate channel(s). |
| [_resolve_channels](../packages/messaging/src/messaging/comms.py#L118) | channel, phone, email | Decide which real channels to dispatch to given the ``channel`` sentinel. |
| [_send_whatsapp](../packages/messaging/src/messaging/comms.py#L144) | phone, message, purpose, template_name, template_params | Delegate to the unified WhatsApp sender. |
| [_send_email](../packages/messaging/src/messaging/comms.py#L175) | to, subject, text, html | Delegate to :func:`messaging.email.send_email`. |
| [notify](../packages/messaging/src/messaging/comms.py#L205) | self |  |

### packages/messaging/src/messaging/email/resend.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_resolve_api_key](../packages/messaging/src/messaging/email/resend.py#L28) |  | Pull the Resend API key from env. |
| [send_email](../packages/messaging/src/messaging/email/resend.py#L40) | to, subject, body_html, body_text | Send an email via Resend. |
| [send_email_resend](../packages/messaging/src/messaging/email/resend.py#L107) | to, subject, body_html, body_text, from_label, from_address | Legacy alias for :func:`send_email`. |

### packages/messaging/src/messaging/frameworks/adapters.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [register_host_adapter](../packages/messaging/src/messaging/frameworks/adapters.py#L51) | name, fn | Register ``fn`` under ``name`` (called by the host at startup). |
| [get_adapter](../packages/messaging/src/messaging/frameworks/adapters.py#L60) | name | Look up a host adapter. When ``required`` is True, raises if missing. |
| [has_adapter](../packages/messaging/src/messaging/frameworks/adapters.py#L71) | name | True if ``name`` has been registered (useful in tests/dry-runs). |
| [clear_adapters](../packages/messaging/src/messaging/frameworks/adapters.py#L76) |  | Wipe the registry (only intended for test teardown). |

### packages/messaging/src/messaging/frameworks/hermes.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [is_available](../packages/messaging/src/messaging/frameworks/hermes.py#L38) |  | Return True if Hermes's modules can be imported from the current ``PYTHONPATH``. Hosts call this at startup to decide whether to wire Hermes-dependent tools. |
| [get_ai_agent_class](../packages/messaging/src/messaging/frameworks/hermes.py#L51) |  | Return the Hermes ``AIAgent`` class (lazy import so we don't force ``vendor/hermes-agent`` to be on path at package-import time). |
| [get_session_db_class](../packages/messaging/src/messaging/frameworks/hermes.py#L58) |  | Return the Hermes ``SessionDB`` class. |
| [get_tool_registry](../packages/messaging/src/messaging/frameworks/hermes.py#L64) |  | Return the singleton Hermes ``tools.registry.registry``. |
| [get_create_custom_toolset](../packages/messaging/src/messaging/frameworks/hermes.py#L74) |  | Return the Hermes ``toolsets.create_custom_toolset`` factory. |

### packages/messaging/src/messaging/frameworks/protocol.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [is_available](../packages/messaging/src/messaging/frameworks/protocol.py#L55) | self | Return ``True`` if the provider's dependencies are present on ``PYTHONPATH`` / installed. Hosts check this before wiring tools — an absent provider should degrade gracefully rather than crash on first agent call. |

### packages/messaging/src/messaging/media/enrich.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [enrich_message](../packages/messaging/src/messaging/media/enrich.py#L60) | msg | Convert all media attachments on ``msg`` into in-line text. |
| [_is_document_mime](../packages/messaging/src/messaging/media/enrich.py#L112) | mime | Catch document MIME variants not in the frozen set. |
| [_resolve_path](../packages/messaging/src/messaging/media/enrich.py#L122) | attachment | Get a local file path, writing base64 to a temp file if needed (web chat uploads). |
| [_enrich_image](../packages/messaging/src/messaging/media/enrich.py#L144) | attachment |  |
| [_enrich_audio](../packages/messaging/src/messaging/media/enrich.py#L159) | attachment | Transcribe audio via :func:`voice.transcribe`. Messaging never owns a codec. |
| [transcribe_file](../packages/messaging/src/messaging/media/enrich.py#L169) | fpath | Transcribe an audio file on disk using the best available STT provider. |
| [_enrich_document](../packages/messaging/src/messaging/media/enrich.py#L193) | attachment |  |

### packages/messaging/src/messaging/media/parse.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [parse_media](../packages/messaging/src/messaging/media/parse.py#L42) | fpath, mime_type, caption | Parse any media file into structured markdown text. |
| [parse_url](../packages/messaging/src/messaging/media/parse.py#L76) | url, max_chars | Fetch a URL and extract readable content as markdown via trafilatura. |
| [_bedrock_client](../packages/messaging/src/messaging/media/parse.py#L129) | region | Lazy boto3 client — matches old ``shared.aws.bedrock_client`` signature. |
| [_parse_image](../packages/messaging/src/messaging/media/parse.py#L136) | fpath, mime, caption |  |
| [_call_haiku](../packages/messaging/src/messaging/media/parse.py#L154) |  |  |
| [_call_qwen](../packages/messaging/src/messaging/media/parse.py#L195) |  |  |
| [_extract_pdf_sync](../packages/messaging/src/messaging/media/parse.py#L240) | path | Sync: PDF → markdown via ``pymupdf4llm`` (table-aware layout engine). |
| [_extract_docx_sync](../packages/messaging/src/messaging/media/parse.py#L247) | path | Sync: DOCX → markdown with tables preserved. |
| [_parse_pdf](../packages/messaging/src/messaging/media/parse.py#L292) | fpath |  |
| [_parse_docx](../packages/messaging/src/messaging/media/parse.py#L302) | fpath |  |
| [_parse_xlsx](../packages/messaging/src/messaging/media/parse.py#L312) | fpath |  |
| [_extract](../packages/messaging/src/messaging/media/parse.py#L315) |  |  |
| [_parse_csv](../packages/messaging/src/messaging/media/parse.py#L347) | fpath |  |
| [_extract](../packages/messaging/src/messaging/media/parse.py#L350) |  |  |
| [_parse_plaintext](../packages/messaging/src/messaging/media/parse.py#L382) | fpath |  |

### packages/messaging/src/messaging/verification/api.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_searxng_search](../packages/messaging/src/messaging/verification/api.py#L89) | query, max_results, days_back | SearXNG JSON search. Serialized — used only for the fast NIF/REA/review checks. |
| [_load_bd_key](../packages/messaging/src/messaging/verification/api.py#L151) |  | Load Bright Data API key from env or .env.local. |
| [_google_via_brightdata](../packages/messaging/src/messaging/verification/api.py#L173) | query, max_results, days_back | Run one Google search through Bright Data Web Unlocker. |
| [_handle_bd_credit_exhausted](../packages/messaging/src/messaging/verification/api.py#L312) |  | Send a WhatsApp alert when Bright Data credit runs out. Only fires once per session. |
| [_send_brightdata_credit_alert](../packages/messaging/src/messaging/verification/api.py#L324) |  | Send WhatsApp message to Peter warning that Bright Data credit is out. |
| [_social_search_parallel](../packages/messaging/src/messaging/verification/api.py#L375) | queries, max_results, days_back | Run multiple social proof queries in parallel via Bright Data Web Unlocker. |
| [_run](../packages/messaging/src/messaging/verification/api.py#L395) | idx, q |  |
| [check_brightdata_credit](../packages/messaging/src/messaging/verification/api.py#L415) | notify | Verify Bright Data Web Unlocker is working and has credit. |
| [validate_nif](../packages/messaging/src/messaging/verification/api.py#L468) | nif | Validate a Spanish NIF/CIF/NIE using the official checksum algorithm. |
| [check_vies](../packages/messaging/src/messaging/verification/api.py#L522) | nif | Check a Spanish VAT number against the EU VIES REST API. |
| [check_rea](../packages/messaging/src/messaging/verification/api.py#L559) | identifier, id_type | Check if a company is registered in Spain's REA (construction accreditation). |
| [search_review_signals](../packages/messaging/src/messaging/verification/api.py#L618) | name, city, phone, website | Search SearXNG for review/rating data about a tradesperson. |
| [expand_fb_queries](../packages/messaging/src/messaging/verification/api.py#L707) | query, max_queries | Generate query variations: English, Spanish, and related trade synonyms. |
| [search_fb_posts](../packages/messaging/src/messaging/verification/api.py#L726) | queries, max_results, days_back | Search Facebook groups for contractor mentions via Bright Data Web Unlocker (parallel). |
| [search_forum_posts](../packages/messaging/src/messaging/verification/api.py#L804) | queries, max_results, days_back | Search Spanish forums (Forocoches, Mediavida, Reddit ES) via Bright Data (parallel). |
| [search_social_proof](../packages/messaging/src/messaging/verification/api.py#L877) | name, city, phone | Search for Facebook group and forum mentions/recommendations of a contractor. |
| [_has_identifying_signal](../packages/messaging/src/messaging/verification/api.py#L914) | snippet, title | Return True if the text contains the phone or the city. |
| [run_verification_checks](../packages/messaging/src/messaging/verification/api.py#L978) | profile | Run the fast verification checks: NIF/VIES/REA + review signals. |
| [run_social_proof_checks](../packages/messaging/src/messaging/verification/api.py#L1049) | profile | Run the slow social proof searches: Facebook groups + forums (~15 SearXNG calls). |
| [enrich_contractor_from_phone](../packages/messaging/src/messaging/verification/api.py#L1098) | phone, name, trade, city | Standalone verification for a contractor we know by phone but may not have a profile URL for. |
| [_extract_legal_identity](../packages/messaging/src/messaging/verification/api.py#L1192) | website_url | Fetch legal / privacy pages and extract NIF, razón social, etc. |
| [_company_name_is_specific](../packages/messaging/src/messaging/verification/api.py#L1247) | name | Return True if the name is unambiguous enough for a web credential search. |
| [enrich_credentials_from_web](../packages/messaging/src/messaging/verification/api.py#L1277) | profile | Search the web for registrations/licenses/certifications via SearXNG. |

### packages/messaging/src/messaging/whatsapp/outreach_budget.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_headers](../packages/messaging/src/messaging/whatsapp/outreach_budget.py#L41) | key |  |
| [_today_utc](../packages/messaging/src/messaging/whatsapp/outreach_budget.py#L50) |  |  |
| [_tomorrow_utc](../packages/messaging/src/messaging/whatsapp/outreach_budget.py#L54) |  |  |
| [daily_sent_count](../packages/messaging/src/messaging/whatsapp/outreach_budget.py#L58) | waba_id | Count cold messages sent today from ``waba_id``. |
| [request_quota](../packages/messaging/src/messaging/whatsapp/outreach_budget.py#L100) | waba_id, n, daily_limit | Return ``(approved, queued)`` where ``approved + queued == n``. |
| [log_send](../packages/messaging/src/messaging/whatsapp/outreach_budget.py#L122) | waba_id, phone_digits, job_id, hc_id, purpose | Append one row to ``cold_outreach_log``. Fire-and-forget. |
| [enqueue_deferred](../packages/messaging/src/messaging/whatsapp/outreach_budget.py#L162) | entries, waba_id, job_id, humanized_summary, lang | Push overflow entries into ``cold_outreach_queue`` for tomorrow. |
| [flush_queue](../packages/messaging/src/messaging/whatsapp/outreach_budget.py#L218) | waba_id | Return + mark-sent all queue rows eligible today. |

### packages/messaging/src/messaging/whatsapp/send.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_wa_token](../packages/messaging/src/messaging/whatsapp/send.py#L34) |  |  |
| [_wa_phone_id](../packages/messaging/src/messaging/whatsapp/send.py#L38) |  |  |
| [_record_cold_send](../packages/messaging/src/messaging/whatsapp/send.py#L45) | purpose, phone_digits, job_id | Fire-and-forget: log a cold send to ``cold_outreach_log``. |
| [send_wa_message](../packages/messaging/src/messaging/whatsapp/send.py#L66) | phone, text, purpose, name, template_params, do_store, skip_window_check | Send a WhatsApp message — the canonical entry point. |
| [send_wa_message_sync](../packages/messaging/src/messaging/whatsapp/send.py#L270) | phone, text, purpose, name, template_params, do_store, skip_window_check | Sync wrapper for hermes tool handlers running in a thread executor. |

### packages/messaging/src/messaging/whatsapp/session.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_sb_auth_headers](../packages/messaging/src/messaging/whatsapp/session.py#L20) |  | Minimal read-auth headers for a Supabase REST GET. |
| [check_24h_window](../packages/messaging/src/messaging/whatsapp/session.py#L29) | phone | Return True if we have an inbound WA message from ``phone`` within 24h. |

### packages/messaging/src/messaging/whatsapp/storage.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [store_message](../packages/messaging/src/messaging/whatsapp/storage.py#L39) | phone_number, role, text, message_type, media_urls, media_types, wa_message_id, reply_to_wa_id, reply_to_text | Insert one row into ``whatsapp_messages`` via Supabase REST. |

### packages/messaging/src/messaging/whatsapp/templates.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_freeze_templates](../packages/messaging/src/messaging/whatsapp/templates.py#L19) | raw | Return a two-level read-only view of ``raw`` (purpose → lang → template name). |
| [detect_language](../packages/messaging/src/messaging/whatsapp/templates.py#L43) | phone_digits | Guess ``en_US`` vs ``es`` from the phone country code. |
| [get_template_name](../packages/messaging/src/messaging/whatsapp/templates.py#L54) | purpose, language | Look up a template name for a ``purpose`` + ``language`` combo. |

### packages/payments/src/payments/checkout.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [assert_can_accept](../packages/payments/src/payments/checkout.py#L51) | contractor | Raise if this contractor cannot accept a homeowner payment. |
| [maybe_reuse_open_session](../packages/payments/src/payments/checkout.py#L72) |  | If the Stripe Checkout Session with this id is still ``open``, return its URL. Otherwise return ``None`` (caller creates a new session). |
| [_amount_total_cents](../packages/payments/src/payments/checkout.py#L97) | quote | Read pre-computed ``amount_total_cents`` or fall back to the legacy in-process computation for pre-``finance`` rows. |
| [create_session](../packages/payments/src/payments/checkout.py#L107) |  | Create (or reuse) the homeowner escrow Stripe Checkout Session. |

### packages/payments/src/payments/client.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_build_client](../packages/payments/src/payments/client.py#L33) | api_key | Build a real ``stripe.StripeClient``. Import is lazy so tests can run without ``stripe`` installed (they inject a fake). |
| [get_stripe_client](../packages/payments/src/payments/client.py#L48) | ctx | Return a Stripe client keyed to this request's resolved Stripe secret. |
| [build_stripe_client_from_key](../packages/payments/src/payments/client.py#L61) | api_key | Explicit helper used by webhook dispatchers where we've already pulled the key out of the :class:`SandboxContext` tri-state verification. |

### packages/payments/src/payments/connect.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_call](../packages/payments/src/payments/connect.py#L55) | fn |  |
| [create_account](../packages/payments/src/payments/connect.py#L62) |  | Create a Stripe Express account for a contractor, idempotent per-contractor. |
| [create_onboarding_link](../packages/payments/src/payments/connect.py#L120) |  | Generate a Stripe AccountLink for contractor onboarding. |
| [get_account_status](../packages/payments/src/payments/connect.py#L157) |  | Read live Stripe account state and opportunistically mark onboarding complete. |
| [_get](../packages/payments/src/payments/connect.py#L179) | key, default |  |
| [_accepts_params_kwarg](../packages/payments/src/payments/connect.py#L207) | fn | Stripe 7.x+ clients expose ``.create(params={...})`` via a typed signature; legacy stubs may only accept ``**kwargs``. Probe once. |

### packages/payments/src/payments/disputes.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [open_dispute_state](../packages/payments/src/payments/disputes.py#L47) |  |  |
| [list_disputes](../packages/payments/src/payments/disputes.py#L112) |  |  |

### packages/payments/src/payments/errors.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/payments/src/payments/errors.py#L24) | self, message |  |

### packages/payments/src/payments/finance.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [to_dict](../packages/payments/src/payments/finance.py#L46) | self |  |
| [_as_decimal](../packages/payments/src/payments/finance.py#L58) | value |  |
| [build_milestones_tracking](../packages/payments/src/payments/finance.py#L67) | line_items | Build the milestones JSON array stored on ``quotes.milestones``. |
| [compute_quote_financials](../packages/payments/src/payments/finance.py#L92) | quote_data | Compute canonical financial fields from a ``quote_data`` blob. |
| [parse_euro_string](../packages/payments/src/payments/finance.py#L154) | raw | Parse a mixed-type EUR amount into integer cents. |

### packages/payments/src/payments/milestones.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_milestone](../packages/payments/src/payments/milestones.py#L73) | quote, idx |  |
| [_advance_milestone_status](../packages/payments/src/payments/milestones.py#L81) | milestones, idx | Return a new list with ``milestones[idx].status = new_status`` and a ``released_at``/``marked_complete_at`` timestamp stamped as appropriate. |
| [submit_proof](../packages/payments/src/payments/milestones.py#L108) |  | Contractor submits proof of work on a milestone. |
| [release](../packages/payments/src/payments/milestones.py#L171) |  | Homeowner releases funds for a milestone from escrow to the contractor. |
| [_stripe_call](../packages/payments/src/payments/milestones.py#L294) | fn, params | Invoke a Stripe client method with an idempotency key, mapping the SDK's ``IdempotencyError`` to our internal sentinel. |
| [_is_idempotency_error](../packages/payments/src/payments/milestones.py#L314) | exc |  |
| [_reconcile_transfer_id](../packages/payments/src/payments/milestones.py#L323) | client | Look up the original ``transfer_id`` via ``transfer_group`` so callers never receive the ``'idempotent-duplicate'`` sentinel. |

### packages/payments/src/payments/refunds.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_guard_no_work_started](../packages/payments/src/payments/refunds.py#L51) | quote |  |
| [cancel_project](../packages/payments/src/payments/refunds.py#L62) |  |  |
| [_refund_create](../packages/payments/src/payments/refunds.py#L154) | client |  |
| [_reconcile_refund](../packages/payments/src/payments/refunds.py#L175) | client |  |

### packages/payments/src/payments/repo.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [from_row](../packages/payments/src/payments/repo.py#L46) | cls, row |  |
| [from_row](../packages/payments/src/payments/repo.py#L80) | cls, row |  |
| [from_row](../packages/payments/src/payments/repo.py#L104) | cls, row |  |
| [from_row](../packages/payments/src/payments/repo.py#L130) | cls, row |  |
| [from_row](../packages/payments/src/payments/repo.py#L155) | cls, row |  |
| [_rename_fee](../packages/payments/src/payments/repo.py#L168) | patch | Rename ``leo_fee_cents`` -> ``stripe_fee_cents`` at the DB boundary. |
| [__init__](../packages/payments/src/payments/repo.py#L183) | self, sb |  |
| [get_quote_by_token](../packages/payments/src/payments/repo.py#L188) | self, token |  |
| [patch_quote](../packages/payments/src/payments/repo.py#L194) | self, token, patch |  |
| [record_checkout_session](../packages/payments/src/payments/repo.py#L202) | self, token |  |
| [mark_quote_paid](../packages/payments/src/payments/repo.py#L222) | self, token |  |
| [mark_quote_payment_failed](../packages/payments/src/payments/repo.py#L241) | self, token |  |
| [mark_quote_refunded](../packages/payments/src/payments/repo.py#L244) | self, token |  |
| [mark_quote_disputed](../packages/payments/src/payments/repo.py#L254) | self, token |  |
| [get_contractor](../packages/payments/src/payments/repo.py#L259) | self, contractor_id |  |
| [patch_contractor](../packages/payments/src/payments/repo.py#L267) | self, contractor_id, patch |  |
| [find_contractor_by_stripe_account](../packages/payments/src/payments/repo.py#L275) | self, stripe_account_id |  |
| [record_account_created](../packages/payments/src/payments/repo.py#L285) | self, contractor_id |  |
| [mark_onboarding_complete](../packages/payments/src/payments/repo.py#L297) | self, contractor_id |  |
| [insert_milestone_update](../packages/payments/src/payments/repo.py#L304) | self, row |  |
| [mark_milestone_released](../packages/payments/src/payments/repo.py#L309) | self |  |
| [list_milestone_updates](../packages/payments/src/payments/repo.py#L331) | self, token |  |
| [insert_variation](../packages/payments/src/payments/repo.py#L340) | self, row |  |
| [get_variation](../packages/payments/src/payments/repo.py#L345) | self, variation_id |  |
| [patch_variation](../packages/payments/src/payments/repo.py#L353) | self, variation_id, patch |  |
| [mark_variation_paid](../packages/payments/src/payments/repo.py#L361) | self, variation_id |  |
| [list_variations](../packages/payments/src/payments/repo.py#L372) | self, token |  |
| [insert_cancellation](../packages/payments/src/payments/repo.py#L381) | self, row |  |
| [insert_dispute](../packages/payments/src/payments/repo.py#L389) | self, row |  |
| [list_disputes](../packages/payments/src/payments/repo.py#L394) | self, token |  |

### packages/payments/src/payments/sandbox.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_env](../packages/payments/src/payments/sandbox.py#L35) | name |  |
| [resolve_sandbox](../packages/payments/src/payments/sandbox.py#L49) | x_sandbox, x_allow_whatsapp | FastAPI dependency. Returns a :class:`SandboxContext` for this request. |
| [resolve_for_quote](../packages/payments/src/payments/sandbox.py#L80) | quote_is_sandbox, ctx | If a quote row was created in sandbox mode but the request header wasn't, return a :class:`SandboxContext` with test keys; otherwise return ``ctx``. |

### packages/payments/src/payments/variations.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [create_variation](../packages/payments/src/payments/variations.py#L64) |  |  |
| [approve_variation](../packages/payments/src/payments/variations.py#L102) |  |  |
| [decline_variation](../packages/payments/src/payments/variations.py#L178) |  |  |

### packages/payments/src/payments/webhooks.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [verify_stripe_event](../packages/payments/src/payments/webhooks.py#L72) |  | Tri-state live/test verification. |
| [_event_data](../packages/payments/src/payments/webhooks.py#L112) | event |  |
| [_event_type](../packages/payments/src/payments/webhooks.py#L129) | event |  |
| [handle_checkout_completed](../packages/payments/src/payments/webhooks.py#L136) | event |  |
| [handle_account_updated](../packages/payments/src/payments/webhooks.py#L180) | event |  |
| [handle_payment_failed](../packages/payments/src/payments/webhooks.py#L202) | event |  |
| [handle_charge_refunded](../packages/payments/src/payments/webhooks.py#L213) | event |  |
| [handle_charge_dispute_created](../packages/payments/src/payments/webhooks.py#L235) | event |  |
| [dispatch_event](../packages/payments/src/payments/webhooks.py#L265) | event |  |

### packages/scraping/src/scraping/_cdp.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [get_cdp_ws_url](../packages/scraping/src/scraping/_cdp.py#L50) | port | Discover the CDP WebSocket URL for the given port. |
| [fetch_via_cdp](../packages/scraping/src/scraping/_cdp.py#L87) | url | Three-strategy browser fetch. |
| [_run_scrapling](../packages/scraping/src/scraping/_cdp.py#L161) | fetcher, url | Invoke scrapling.DynamicFetcher with our canonical kwargs. |
| [_httpx_fallback](../packages/scraping/src/scraping/_cdp.py#L182) | url | Last-resort static fetch. Returns ``""`` on any httpx error. |

### packages/scraping/src/scraping/browser.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [browser_context](../packages/scraping/src/scraping/browser.py#L79) | cookies, user_agent, viewport, headless, storage_state, extra_args | Async Playwright ``BrowserContext`` for multi-page sessions. |
| [browser_page](../packages/scraping/src/scraping/browser.py#L122) | cookies, user_agent, viewport, headless, auto_dismiss_gdpr, storage_state, extra_args | Async Playwright ``Page`` with sensible defaults. |
| [browser_page_sync](../packages/scraping/src/scraping/browser.py#L173) | cookies, user_agent, viewport, headless, storage_state, extra_args | Sync Playwright ``Page`` — used by login flows and session refresh scripts that don't live inside an asyncio loop. |
| [browser_context_sync](../packages/scraping/src/scraping/browser.py#L209) | cookies, user_agent, viewport, headless, locale, storage_state, extra_args | Sync Playwright ``BrowserContext`` for multi-page crawlers. |
| [dismiss_gdpr_async](../packages/scraping/src/scraping/browser.py#L244) | page, timeout_ms | Click the first visible GDPR/cookie consent button in :data:`GDPR_SELECTORS`. Returns ``True`` if one was dismissed. |
| [dismiss_gdpr](../packages/scraping/src/scraping/browser.py#L266) | page, timeout_ms | Sync analogue of :func:`dismiss_gdpr_async`. |
| [persistent_browser](../packages/scraping/src/scraping/browser.py#L283) |  | Attach to an already-running Chrome via CDP — skips the 3-5s cold-start cost of every ``browser.chromium.launch()``. |

### packages/scraping/src/scraping/cache.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_cache_key](../packages/scraping/src/scraping/cache.py#L46) | url, strategy | Deterministic hex key for ``(url, strategy)``. |
| [cache_path](../packages/scraping/src/scraping/cache.py#L53) | url | Return the HTML path (``<dir>/<key>.html``) for an entry. |
| [_meta_path](../packages/scraping/src/scraping/cache.py#L69) | html_path |  |
| [_atomic_write_text](../packages/scraping/src/scraping/cache.py#L73) | path, content | Write ``content`` to ``path`` via a tempfile rename. |
| [cached_fetch](../packages/scraping/src/scraping/cache.py#L93) | url | File-based TTL cache around :func:`fetch`. |

### packages/scraping/src/scraping/css.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_url_from_function](../packages/scraping/src/scraping/css.py#L35) | fn | Extract the URL from a `url(...)` FunctionBlock; returns None if dynamic/empty. |
| [_url_from_url_token](../packages/scraping/src/scraping/css.py#L48) | tok |  |
| [_walk_tokens](../packages/scraping/src/scraping/css.py#L56) | tokens, line_base | Yield (token, absolute_line, absolute_col). tinycss2 reports 1-indexed source_line/source_column on top-level tokens; for nested FunctionBlock children, the positions are relative to the function itself — we flatten. |
| [iter_css_refs](../packages/scraping/src/scraping/css.py#L68) | text | Return every external reference in a stylesheet text. |

### packages/scraping/src/scraping/errors.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/scraping/src/scraping/errors.py#L51) | self, url, user_agent |  |

### packages/scraping/src/scraping/fetch.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [extend_js_hosts](../packages/scraping/src/scraping/fetch.py#L76) | hosts | Add substrings to :data:`JS_HOSTS`. Idempotent. |
| [_is_js_host](../packages/scraping/src/scraping/fetch.py#L84) | url | True if any :data:`JS_HOSTS` entry is a substring of ``url``. |
| [fetch_static](../packages/scraping/src/scraping/fetch.py#L90) | url | Static httpx fetch. Raises :class:`FetchError` on upstream failure. |
| [fetch_browser](../packages/scraping/src/scraping/fetch.py#L129) | url | CDP-first Playwright fetch. Returns ``""`` on total failure. |
| [fetch](../packages/scraping/src/scraping/fetch.py#L175) | url | Auto-dispatched fetch. Raises :class:`RobotsDisallowed` on robots denial (when ``respect_robots=True``), otherwise delegates. |
| [fetch_many](../packages/scraping/src/scraping/fetch.py#L226) | urls | Fan-out fetch with a semaphore-capped concurrency. |
| [_one](../packages/scraping/src/scraping/fetch.py#L245) | url |  |
| [extract_text](../packages/scraping/src/scraping/fetch.py#L262) | url | Fetch + :func:`html_to_text` in one call (D9). |

### packages/scraping/src/scraping/html.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [is_external_url](../packages/scraping/src/scraping/html.py#L60) | url | True if `url` is not a repo-local reference worth resolving. |
| [parse_html](../packages/scraping/src/scraping/html.py#L70) | text | Parse HTML tolerantly. Preserves 1-indexed sourceline on every tag. |
| [iter_tags](../packages/scraping/src/scraping/html.py#L84) | parsed, names | Iterate tags in document order, optionally filtered by tag name(s). |
| [tag_attr](../packages/scraping/src/scraping/html.py#L94) | tag, name | Case-insensitive attribute lookup. Returns None if absent. |
| [tag_lineno](../packages/scraping/src/scraping/html.py#L106) | tag | 1-indexed line of the tag's opening bracket (0 if unknown). |
| [tag_text](../packages/scraping/src/scraping/html.py#L111) | tag | Inner text with no markup, whitespace-collapsed. |
| [parse_srcset](../packages/scraping/src/scraping/html.py#L120) | value | Return the URL portion of every candidate in a srcset string. |

### packages/scraping/src/scraping/robots.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/scraping/src/scraping/robots.py#L52) | self |  |
| [_parser_for](../packages/scraping/src/scraping/robots.py#L57) | self, host_root | Fetch + parse robots.txt for ``host_root`` (``scheme://host``). |
| [is_allowed](../packages/scraping/src/scraping/robots.py#L91) | self, url, user_agent | Check whether ``url`` is allowed for ``user_agent``. |
| [crawl_delay](../packages/scraping/src/scraping/robots.py#L134) | self, host, user_agent | Return the declared crawl-delay for ``host`` (seconds), or ``None`` if robots.txt is silent on the matter. |
| [is_allowed](../packages/scraping/src/scraping/robots.py#L156) | url, user_agent | Module-level convenience wrapper over a shared :class:`RobotsChecker`. |

### packages/scraping/src/scraping/soup.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [parse_soup](../packages/scraping/src/scraping/soup.py#L21) | html | Parse ``html`` into a :class:`bs4.BeautifulSoup` tree. |

### packages/scraping/src/scraping/text.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [html_to_text](../packages/scraping/src/scraping/text.py#L23) | html | Return the readable plain text of an HTML document. |

### packages/scraping/src/scraping/user_agents.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [pick_user_agent](../packages/scraping/src/scraping/user_agents.py#L57) |  | Return a random UA from the full pool. |
| [pick_desktop](../packages/scraping/src/scraping/user_agents.py#L63) |  | Return a random desktop UA. |
| [pick_mobile](../packages/scraping/src/scraping/user_agents.py#L69) |  | Return a random mobile UA (use for IG profile HTML, etc.). |

### packages/storage/src/storage/embeddings.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_content_hash](../packages/storage/src/storage/embeddings.py#L81) | text |  |
| [_validate_vector](../packages/storage/src/storage/embeddings.py#L85) | vec |  |
| [_parse_ts](../packages/storage/src/storage/embeddings.py#L94) | value |  |
| [_row_to_embedding](../packages/storage/src/storage/embeddings.py#L103) | row |  |
| [_embed_one](../packages/storage/src/storage/embeddings.py#L115) | text | Embed a single string via the LiteLLM proxy. |
| [_embed_many](../packages/storage/src/storage/embeddings.py#L133) | texts |  |
| [_fetch_existing](../packages/storage/src/storage/embeddings.py#L139) | chunk_id | Fetch the existing row for a chunk_id. Returns the raw JSON row or None. |
| [_upsert_row](../packages/storage/src/storage/embeddings.py#L160) |  | Upsert one row via ``Prefer: resolution=merge-duplicates`` on ``chunk_id``. |
| [index_text](../packages/storage/src/storage/embeddings.py#L198) | chunk_id, text | Upsert a chunk into ``knowledge_embeddings``. |
| [index_batch](../packages/storage/src/storage/embeddings.py#L245) | chunks | Bulk :func:`index_text`. One provider call per 96 chunks. |
| [search_similar](../packages/storage/src/storage/embeddings.py#L314) | query | Cosine-similarity top-k search. |
| [delete_chunk](../packages/storage/src/storage/embeddings.py#L378) | chunk_id | Delete one row by ``chunk_id``. Returns ``True`` on 200/204, else ``False``. |
| [prune_embeddings](../packages/storage/src/storage/embeddings.py#L404) | older_than | Delete rows with ``updated_at < older_than``, optional metadata filter. |

### packages/storage/src/storage/semantic.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_get_api_key](../packages/storage/src/storage/semantic.py#L82) |  |  |
| [is_mem0_configured](../packages/storage/src/storage/semantic.py#L86) |  | True iff ``MEM0_API_KEY`` is set in the environment. |
| [_get_client](../packages/storage/src/storage/semantic.py#L102) |  | Lazy-initialize the mem0 client. Returns ``None`` on failure. |
| [_auth_headers](../packages/storage/src/storage/semantic.py#L132) |  |  |
| [_normalize_user_id](../packages/storage/src/storage/semantic.py#L139) | user_id | Stable per-user namespace key. |
| [_parse_created_at](../packages/storage/src/storage/semantic.py#L165) | value |  |
| [_row_to_memory](../packages/storage/src/storage/semantic.py#L174) | row | Coerce a raw mem0 API row to a :class:`Memory` dataclass. |
| [_api_get_all](../packages/storage/src/storage/semantic.py#L197) | uid, limit | Raw v2 API call. The client's ``get_all`` is broken in v1.0.7. |
| [_api_search](../packages/storage/src/storage/semantic.py#L211) | uid, query, limit | Raw v2 API call. The client's ``search`` is broken in v1.0.7. |
| [recall](../packages/storage/src/storage/semantic.py#L225) | user_id, query | Retrieve memories for a user. |
| [remember](../packages/storage/src/storage/semantic.py#L262) | user_id, messages | Store conversation turns in mem0. The SaaS extracts facts server-side. |
| [forget](../packages/storage/src/storage/semantic.py#L309) | user_id, memory_id | Delete one memory by id. Returns True on success, False otherwise. |
| [migrate_user](../packages/storage/src/storage/semantic.py#L337) | old_id, new_id | Transfer all memories from ``old_id`` to ``new_id``. Non-atomic. |
| [format_memories_for_prompt](../packages/storage/src/storage/semantic.py#L425) | memories | Render memories as ``"Known facts about this user:\n- ..."`` text. |
| [get_user_context](../packages/storage/src/storage/semantic.py#L448) | user_id, current_message | Convenience: :func:`recall` + :func:`format_memories_for_prompt`. |

### packages/ui/src/AppleWalletButton.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [AppleWalletButton](../packages/ui/src/AppleWalletButton.tsx#L11) | { 
  className = '', 
  onClick 
} |  |

### packages/ui/src/BriefCanvas.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [BriefCanvas](../packages/ui/src/BriefCanvas.tsx#L4) | { b, photos = [] } |  |

### packages/ui/src/ChangeOrderCanvas.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [fmt](../packages/ui/src/ChangeOrderCanvas.tsx#L30) | n |  |
| [total](../packages/ui/src/ChangeOrderCanvas.tsx#L32) | co |  |
| [ChangeOrderStatusBadge](../packages/ui/src/ChangeOrderCanvas.tsx#L36) | { status } |  |
| [MarketBar](../packages/ui/src/ChangeOrderCanvas.tsx#L63) | { low, high, value } |  |
| [CompactRow](../packages/ui/src/ChangeOrderCanvas.tsx#L152) | { co } |  |
| [FullCard](../packages/ui/src/ChangeOrderCanvas.tsx#L205) | { co, onApprove, onGetHelp } |  |
| [ChangeOrderCanvas](../packages/ui/src/ChangeOrderCanvas.tsx#L359) | { co, mode = 'full', onApprove, onGetHelp } |  |

### packages/ui/src/ChatBubbles.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [LeoBubble](../packages/ui/src/ChatBubbles.tsx#L21) | { text, variant = 'light', className } |  |
| [UserBubble](../packages/ui/src/ChatBubbles.tsx#L50) | { text, variant = 'light', className } |  |

### packages/ui/src/ComposerActionStrip.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [cx](../packages/ui/src/ComposerActionStrip.tsx#L19) | parts |  |
| [ComposerActionStrip](../packages/ui/src/ComposerActionStrip.tsx#L23) | {
  children,
  highlight = false,
  elevated = false,
  innerClassName,
  className,
} |  |

### packages/ui/src/FluidGradient.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [loadRuntime](../packages/ui/src/FluidGradient.tsx#L72) | src |  |
| [FluidGradient](../packages/ui/src/FluidGradient.tsx#L105) | {
  preset = 'brendan',
  paletteKey,
  variant = 'v4',
  fpsCap = 24,
  overrides,
  scriptSrc = '/fluid-gradient-v4.js',
  skip = false,
  className,
  style,
  ariaLabel,
} |  |

### packages/ui/src/FullScreenStep.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [FullScreenStep](../packages/ui/src/FullScreenStep.tsx#L11) | { icon, title, subtitle, children, footer } |  |

### packages/ui/src/GlassCard.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [GlassCard](../packages/ui/src/GlassCard.tsx#L47) | {
  children,
  variant = 'dark',
  className = '',
  style,
  padding = 'md',
} |  |

### packages/ui/src/GlassFrame.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [GlassFrame](../packages/ui/src/GlassFrame.tsx#L29) | { url, dark = false, children, className } |  |

### packages/ui/src/GlassPill.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [GlassPill](../packages/ui/src/GlassPill.tsx#L19) | { children, dot = true, className } |  |

### packages/ui/src/GoogleWalletButton.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [GoogleWalletButton](../packages/ui/src/GoogleWalletButton.tsx#L11) | { 
  className = '', 
  onClick 
} |  |

### packages/ui/src/GradientScreen.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [GradientScreen](../packages/ui/src/GradientScreen.tsx#L59) | {
  children,
  preset = 'homeowner',
  style,
  className = '',
  noise = true,
} |  |

### packages/ui/src/MapAreaCard.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [MapAreaCard](../packages/ui/src/MapAreaCard.tsx#L12) | {
  mapImageSrc,
  mapImageAlt = '',
  areaName,
  radiusLabel,
  showApproxRing = true,
  privacyNote,
} |  |

### packages/ui/src/MaterialsCard.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [MaterialsCard](../packages/ui/src/MaterialsCard.tsx#L17) | { 
  cardHolder = 'J. MITCHELL',
  cardNumber = '•••• •••• •••• 4821',
  showSplit = true,
  showPayButtons = true,
  className = '' 
} |  |

### packages/ui/src/MilestoneList.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [MilestoneList](../packages/ui/src/MilestoneList.tsx#L36) | { milestones, gradientBg = false, gradientSrc } | Escrow milestone list — "Your money doesn't move until you're happy." |

### packages/ui/src/PayButtons.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [AppleLogo](../packages/ui/src/PayButtons.tsx#L19) | { size = 16, fill = 'currentColor' } | PayButton — Apple Pay and Google Pay standard buttons. |
| [GoogleGLogo](../packages/ui/src/PayButtons.tsx#L32) | { size = 16 } |  |
| [ApplePayButton](../packages/ui/src/PayButtons.tsx#L80) | { variant = 'pill', onClick } | Apple Pay button. Logo-only (no "Apple" text). "Pay" uses -apple-system (San Francisco) per Apple HIG. |
| [GooglePayButton](../packages/ui/src/PayButtons.tsx#L125) | { variant = 'pill', onClick } | Google Pay button. Google G logo (4-color) + "Pay" in Google Sans. No "Google" text. Google Sans loaded from fonts.gstatic.com (no extra font import needed in static pages that already load brand fonts; React app imports via index.css or ComponentLibrary). |

### packages/ui/src/PlatformLogo.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [PlatformLogo](../packages/ui/src/PlatformLogo.tsx#L33) | { 
  platform, 
  size = 'md', 
  variant = 'inline',
  className 
} |  |

### packages/ui/src/ProfileCanvas.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [Stars](../packages/ui/src/ProfileCanvas.tsx#L10) | { rating, size = 12 } |  |
| [PhotoViewer](../packages/ui/src/ProfileCanvas.tsx#L26) | { url, onClose } |  |
| [BackBar](../packages/ui/src/ProfileCanvas.tsx#L47) | { label, onBack } |  |
| [ProfileCanvas](../packages/ui/src/ProfileCanvas.tsx#L69) | { p } |  |
| [ProfileView](../packages/ui/src/ProfileCanvas.tsx#L131) | {
  p,
  onOpenReviews,
  onOpenProject,
  onOpenMentions,
  onViewPhoto,
} |  |
| [PlatformReviewCard](../packages/ui/src/ProfileCanvas.tsx#L427) | { source, onTap } |  |
| [sourcePill](../packages/ui/src/ProfileCanvas.tsx#L484) | source_name |  |
| [SocialMentionCard](../packages/ui/src/ProfileCanvas.tsx#L496) | { mention, onTap } |  |
| [SocialMentionDetailView](../packages/ui/src/ProfileCanvas.tsx#L527) | {
  mentions,
  onBack,
} |  |
| [PortfolioThumb](../packages/ui/src/ProfileCanvas.tsx#L653) | { project, onTap } |  |
| [ReviewsView](../packages/ui/src/ProfileCanvas.tsx#L684) | { source, onBack } |  |
| [ProjectView](../packages/ui/src/ProfileCanvas.tsx#L820) | {
  project,
  onBack,
  onViewPhoto,
} |  |

### packages/ui/src/QuoteCanvas.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [QuoteCanvas](../packages/ui/src/QuoteCanvas.tsx#L20) | { scope: rawScope } | ScopeCanvas — the Leo quote document. |
| [fmtEur](../packages/ui/src/QuoteCanvas.tsx#L46) | n |  |

### packages/ui/src/ShopMap.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ShopMap](../packages/ui/src/ShopMap.tsx#L24) | {
  accessToken,
  points,
  onSelect,
  center,
  height = '100%',
  className,
  pinClassName = 'scope-shop-map-pin',
} |  |

### packages/ui/src/StatusBadge.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [StatusBadge](../packages/ui/src/StatusBadge.tsx#L88) | { status, className = '' } |  |

### packages/ui/src/ThemeProvider.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ThemeProvider](../packages/ui/src/ThemeProvider.tsx#L50) | {
  children,
  defaultTheme = 'light',
  storageKey = STORAGE_KEY,
  element = 'html',
} |  |
| [setTheme](../packages/ui/src/ThemeProvider.tsx#L82) | next |  |
| [useTheme](../packages/ui/src/ThemeProvider.tsx#L93) |  |  |

### packages/ui/src/VoiceNoteBubble.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [fmtDuration](../packages/ui/src/VoiceNoteBubble.tsx#L15) | seconds |  |
| [PlayIcon](../packages/ui/src/VoiceNoteBubble.tsx#L25) |  | Play icon: bare rounded triangle (no circle wrapper). Uses SVG path with rounded stroke-linejoin for slightly soft corners. |
| [PauseIcon](../packages/ui/src/VoiceNoteBubble.tsx#L32) |  | Pause icon: two rounded bars |
| [VoiceNoteBubble](../packages/ui/src/VoiceNoteBubble.tsx#L48) | { durationSec, waveform, transcript, audioUrl } | Terra terracotta bubble: play button + waveform bars + duration + italic transcript. |

### packages/ui/src/primitives/Badge.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [Badge](../packages/ui/src/primitives/Badge.tsx#L24) | { variant = 'pill', color = 'ink', dot = true, children, className } |  |

### packages/ui/src/primitives/Sheet.tsx

| Function | Arguments | Purpose |
| --- | --- | --- |
| [Sheet](../packages/ui/src/primitives/Sheet.tsx#L18) | { open, onClose, children, maxHeight = '90dvh', showHandle = true, title, footer } |  |

### packages/voice/src/voice/audio.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [ext_for_content_type](../packages/voice/src/voice/audio.py#L43) | content_type | Return a filename extension for an audio MIME type. |
| [_run_ffmpeg](../packages/voice/src/voice/audio.py#L68) | src_path, dst_path | Invoke ``ffmpeg`` to convert ``src_path`` to ``dst_path`` at the given sample rate / channel count. Raises :class:`RuntimeError` on non-zero exit. |
| [to_wav](../packages/voice/src/voice/audio.py#L105) | audio | Convert audio bytes to WAV on disk, return the Path. |
| [wav_tempfile](../packages/voice/src/voice/audio.py#L156) | audio | Context-manager version of :func:`to_wav` with guaranteed cleanup. |

### packages/voice/src/voice/config.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [groq_api_key](../packages/voice/src/voice/config.py#L43) |  |  |
| [groq_whisper_model](../packages/voice/src/voice/config.py#L47) |  |  |
| [hf_token](../packages/voice/src/voice/config.py#L51) |  |  |
| [hf_whisper_model](../packages/voice/src/voice/config.py#L59) |  |  |
| [whisper_model_name](../packages/voice/src/voice/config.py#L63) |  | Model ID for local faster-whisper. Default: ``distil-large-v3`` — distilled Whisper large-v3 tuned for fast-whisper; ~2× faster on CPU than the full large-v3 with similar quality for short voice notes. |
| [whisper_device](../packages/voice/src/voice/config.py#L70) |  | Device for faster-whisper: ``cpu`` / ``cuda``. Default ``cpu``. |
| [whisper_compute_type](../packages/voice/src/voice/config.py#L77) |  | Compute type for faster-whisper. Default ``int8`` on CPU; override to ``float16`` on GPU for better quality. |
| [whisper_cpu_threads](../packages/voice/src/voice/config.py#L84) |  | CPU threads for faster-whisper. ``0`` = let CTranslate2 decide. Invalid inputs warn-and-default to 0 (symmetric with :func:`whisper_beam_size` — previously only beam size warned). |
| [whisper_beam_size](../packages/voice/src/voice/config.py#L95) |  | Beam size for faster-whisper. Clamped to [1, 10]. Default 5. Invalid inputs warn-and-default to 5. |
| [voice_concurrency](../packages/voice/src/voice/config.py#L106) |  | Max concurrent ``transcribe()`` calls. Default 8. Min 1. |
| [polish_enabled](../packages/voice/src/voice/config.py#L115) |  | Whether the Bedrock polish step runs by default. Default ``True``. |
| [polish_model_id](../packages/voice/src/voice/config.py#L123) |  | Bedrock model ID for polish. Default Claude Haiku 4.5 (cross-region inference profile). |
| [polish_api_style](../packages/voice/src/voice/config.py#L132) |  | Force ``anthropic`` (Messages API) or ``converse`` (Bedrock Converse) routing. |
| [voice_log_content](../packages/voice/src/voice/config.py#L141) |  | Whether to log the first 80 chars of transcripts at INFO (PII risk). |
| [aws_region](../packages/voice/src/voice/config.py#L150) |  |  |
| [elevenlabs_api_key](../packages/voice/src/voice/config.py#L154) |  |  |
| [deepgram_api_key](../packages/voice/src/voice/config.py#L158) |  |  |

### packages/voice/src/voice/detect.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [detect_language](../packages/voice/src/voice/detect.py#L29) | text | Return an ISO-639-1 code for ``text``. |

### packages/voice/src/voice/logging.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_content_level](../packages/voice/src/voice/logging.py#L24) |  | INFO if ``VOICE_LOG_CONTENT=1``, else DEBUG. |
| [log_transcript](../packages/voice/src/voice/logging.py#L32) | logger | Log an ASR result. |
| [log_polish](../packages/voice/src/voice/logging.py#L61) | logger | Log a polish invocation. |

### packages/voice/src/voice/pipeline.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [transcribe](../packages/voice/src/voice/pipeline.py#L40) | audio | Transcribe audio bytes to text. |

### packages/voice/src/voice/polish.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [polish_sync](../packages/voice/src/voice/polish.py#L61) | raw | Return lightly-edited transcript from the polish model. |
| [polish](../packages/voice/src/voice/polish.py#L127) | raw | Async counterpart to :func:`polish_sync`. |

### packages/voice/src/voice/resilience.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [voice_semaphore](../packages/voice/src/voice/resilience.py#L29) |  | Return the process-wide ``asyncio.Semaphore`` for voice concurrency. |
| [reset_semaphore_for_tests](../packages/voice/src/voice/resilience.py#L50) |  | Drop the cached semaphore. Test-only helper. |

### packages/voice/src/voice/stt/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [transcribe](../packages/voice/src/voice/stt/__init__.py#L50) | self, audio | Run ASR on the given audio bytes. Pre-polish result. |
| [normalize_language](../packages/voice/src/voice/stt/__init__.py#L62) | hint | Map language hint variants to a normalized form providers accept. |
| [resolve_provider](../packages/voice/src/voice/stt/__init__.py#L79) | requested | Resolve a requested provider name to a concrete backend. |
| [_register](../packages/voice/src/voice/stt/__init__.py#L133) | name, factory |  |
| [_groq_factory](../packages/voice/src/voice/stt/__init__.py#L137) |  |  |
| [_hf_factory](../packages/voice/src/voice/stt/__init__.py#L143) |  |  |
| [_local_factory](../packages/voice/src/voice/stt/__init__.py#L149) |  |  |
| [_deepgram_factory](../packages/voice/src/voice/stt/__init__.py#L155) |  |  |
| [get_provider](../packages/voice/src/voice/stt/__init__.py#L167) | name | Instantiate the provider registered under ``name``. |

### packages/voice/src/voice/stt/deepgram.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_deepgram_api_key](../packages/voice/src/voice/stt/deepgram.py#L77) |  |  |
| [_deepgram_model](../packages/voice/src/voice/stt/deepgram.py#L81) |  |  |
| [_build_params](../packages/voice/src/voice/stt/deepgram.py#L86) | language |  |
| [__init__](../packages/voice/src/voice/stt/deepgram.py#L111) | self |  |
| [_resolve_key](../packages/voice/src/voice/stt/deepgram.py#L115) | self |  |
| [transcribe](../packages/voice/src/voice/stt/deepgram.py#L125) | self, audio | Standard pipeline interface — returns flat text only. |
| [transcribe_diarized](../packages/voice/src/voice/stt/deepgram.py#L141) | self, audio | Transcribe with full speaker diarization. Returns ``DiarizedTranscript``. |
| [_transcribe_diarized_sync](../packages/voice/src/voice/stt/deepgram.py#L151) | self, audio, content_type, language |  |

### packages/voice/src/voice/stt/groq.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_filename_for_audio](../packages/voice/src/voice/stt/groq.py#L32) | content_type | Groq infers codec from filename extension (Whisper API convention). |
| [__init__](../packages/voice/src/voice/stt/groq.py#L51) | self |  |
| [_resolve_api_key](../packages/voice/src/voice/stt/groq.py#L62) | self |  |
| [_resolve_model](../packages/voice/src/voice/stt/groq.py#L68) | self |  |
| [transcribe](../packages/voice/src/voice/stt/groq.py#L71) | self, audio | POST audio bytes to Groq and parse the response. |
| [_transcribe_sync](../packages/voice/src/voice/stt/groq.py#L91) | self, audio, content_type, language, initial_prompt |  |

### packages/voice/src/voice/stt/huggingface.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [__init__](../packages/voice/src/voice/stt/huggingface.py#L41) | self |  |
| [_resolve_token](../packages/voice/src/voice/stt/huggingface.py#L51) | self |  |
| [_resolve_model](../packages/voice/src/voice/stt/huggingface.py#L57) | self |  |
| [_get_client](../packages/voice/src/voice/stt/huggingface.py#L60) | self |  |
| [transcribe](../packages/voice/src/voice/stt/huggingface.py#L67) | self, audio | Run ASR via HF Inference. See module docstring for the language / initial_prompt handling quirks. |
| [_transcribe_sync](../packages/voice/src/voice/stt/huggingface.py#L83) | self, audio, content_type, language, initial_prompt |  |

### packages/voice/src/voice/stt/local.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [_load_whisper_model](../packages/voice/src/voice/stt/local.py#L30) | model_name, device, compute_type, cpu_threads | Load and cache a faster-whisper model. One slot per process. |
| [__init__](../packages/voice/src/voice/stt/local.py#L68) | self |  |
| [_resolve_model_name](../packages/voice/src/voice/stt/local.py#L79) | self |  |
| [_resolve_device](../packages/voice/src/voice/stt/local.py#L82) | self |  |
| [_resolve_compute_type](../packages/voice/src/voice/stt/local.py#L85) | self |  |
| [_get_model](../packages/voice/src/voice/stt/local.py#L88) | self |  |
| [_transcribe_kwargs](../packages/voice/src/voice/stt/local.py#L96) | self | Transcribe-call kwargs for faster-whisper. |
| [transcribe](../packages/voice/src/voice/stt/local.py#L113) | self, audio | Convert audio to WAV via ffmpeg, then run faster-whisper inference. |
| [_transcribe_sync](../packages/voice/src/voice/stt/local.py#L128) | self, audio, content_type, language, initial_prompt |  |

### packages/voice/src/voice/tts/__init__.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [synthesize](../packages/voice/src/voice/tts/__init__.py#L43) | self, text | Synthesize ``text`` into audio bytes. |
| [synthesize](../packages/voice/src/voice/tts/__init__.py#L55) | text | Synthesize text to audio. Phase 3.5b stub — raises NotImplementedError. |
| [list_voices](../packages/voice/src/voice/tts/__init__.py#L71) | language | Return registered canonical voices, optionally filtered by language. |

### packages/voice/src/voice/tts/elevenlabs.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [synthesize](../packages/voice/src/voice/tts/elevenlabs.py#L21) | self, text |  |

### packages/voice/src/voice/tts/polly.py

| Function | Arguments | Purpose |
| --- | --- | --- |
| [synthesize](../packages/voice/src/voice/tts/polly.py#L21) | self, text |  |
