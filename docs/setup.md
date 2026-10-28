# Setup and credentials

## Scripted first result

`make dev` runs the original interface with sample replies and records. Its default build points to local endpoints. [First result](get-started.md).

## Private configuration

```sh
python3 tools/configure.py init --features auth
python3 tools/configure.py doctor --features auth
python3 tools/configure.py frontend
python3 tools/build.py --env-file "$HOME/.config/renovation-marketplace/runtime.env"
```

Input is hidden. The helper writes `~/.config/renovation-marketplace/runtime.env` with mode 0600 in an owner-only directory. Configuration stays outside the checkout. `--env-file` selects another private recipient path.

The build helper exports only the public Vite allowlist. Server keys, payment credentials and model credentials remain in the private runtime context.

## Feature groups

| Group | Variables | Enables |
| --- | --- | --- |
| `auth` | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `APP_BASE_URL` | Recipient identity and database context |
| `stripe` | `STRIPE_SECRET_KEY_TEST`, `STRIPE_WEBHOOK_SECRET_TEST` | Explicit Stripe test-mode integration |
| `maps` | `VITE_MAPBOX_ACCESS_TOKEN` | Recipient Mapbox map access |
| `whatsapp` | `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` | Owned Meta sender and signed webhook setup |
| `voice` | `DEEPGRAM_API_KEY`, `GROQ_API_KEY` | Retained transcription adapters |
| `agent` | `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `LEO_PRIMARY_MODEL`, `HERMES_VENDOR_PATH`, named AWS account fields | Retained connected agent/runtime path |

Select several groups with `--features auth,stripe`. The account-suffix fields are derived from your selected `LEO_AWS_ACCOUNT`, preserving the original explicit billing-account resolver.

## Full backend

The original backend requirements are retained at `apps/scope/product/backend/requirements.txt`, with shared Python packages under `packages/*`. Install only the provider features you commission, using that source and the generated configuration reference. Its existing entrypoint validates the explicitly selected AWS account; the Hermes-dependent paths require a compatible upstream checkout.

The backend's complete legacy schema and external-runtime acceptance remain separate work. The new developer database is a tested core baseline, described in [Database and auth](database.md). Full connected deployment is a contributor/commissioning path, while the scripted UI is the verified starter.

## Callbacks and external effects

- Auth: `/app/auth/callback` on your app origin.
- Meta webhook: configure your own verify token and app secret/sender permissions from the retained Meta route.
- Stripe: configure your own test webhook endpoint and signing secret; Connect destinations belong to your contractor accounts.
- Document delivery, identity verification, email, outreach and live payments use their own recipient accounts and explicit feature setup.

Choose your platform terms and delivery policy before enabling live Checkout and messaging. Historical legal/marketing templates retain their original context.
