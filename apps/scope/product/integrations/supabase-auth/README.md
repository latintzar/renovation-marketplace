# Supabase Auth — Authentication Layer Exploration

**Last updated:** 2026-04-02
**Project ref:** `yrkxosaxxgjfwhegopod`
**Project URL:** `https://yrkxosaxxgjfwhegopod.supabase.co`
**Auth status:** Completely unused — zero auth code in the codebase
**Docs:** `https://supabase.com/docs/guides/auth`

---

## Table of Contents

- [1. Current State: Database Only, No Auth](#1-current-state-database-only-no-auth)
- [2. What Supabase Auth Offers](#2-what-supabase-auth-offers)
- [3. Phone-First Auth Pattern for Leo](#3-phone-first-auth-pattern-for-leo)
- [4. Row Level Security (RLS)](#4-row-level-security-rls)
- [5. Migration Path: Adding Auth Without Breaking Anything](#5-migration-path-adding-auth-without-breaking-anything)
- [6. Supabase Auth + React Native / Expo](#6-supabase-auth--react-native--expo)
- [7. Session Management](#7-session-management)
- [8. Deep Link Callbacks for OAuth](#8-deep-link-callbacks-for-oauth)
- [9. Cost Model](#9-cost-model)
- [10. Alternatives Considered](#10-alternatives-considered)
- [11. Gotchas and Limitations](#11-gotchas-and-limitations)

---

## 1. Current State: Database Only, No Auth

Leo uses Supabase as a **database with an HTTP API** — nothing else. Here is exactly what we use and don't use:

### What we use

| Feature | How | Where |
|---------|-----|-------|
| PostgREST (CRUD) | Raw `httpx` calls with `apikey` + `Authorization` headers | `backend/database.py` |
| Service Role Key | Bypasses RLS, used for ALL operations | `backend/config.py` → `.env.local` |
| 13 tables | `cs_leads`, `contractors`, `jobs`, `job_responses`, `whatsapp_messages`, etc. | Supabase Dashboard |

### What we DON'T use

| Feature | Status |
|---------|--------|
| **Supabase Auth** | Zero `signIn`, `signUp`, `signOut` calls anywhere |
| **Supabase JS SDK** | Not installed (`@supabase/supabase-js` not in any `package.json`) |
| **Supabase Python SDK** | Not installed (no `supabase` in `requirements.txt`) |
| **Row Level Security** | Enabled on 3 tables but policies are service-role-bypass-only |
| **Realtime** | Not used |
| **Storage** | Not used (photos go to local filesystem) |
| **Edge Functions** | Not used |

### Current user identification

Users are identified by **phone number** (from WhatsApp) or **lead_id** (generated on landing page). There is no concept of a "user account" or "session":

| Entry point | Identifier | Stored where |
|-------------|-----------|--------------|
| Landing page chat | `lead_id` (generated UUID) | `cs_leads.id` |
| WhatsApp message | Phone number (`00000000000`) | `whatsapp_messages.from_number` |
| Contractor | Phone number | `contractors.phone` |
| Job posting | `landing_leads.id` → `jobs.id` | Supabase tables |

### Current RLS state (audited 2026-04-02)

| Table | RLS enabled? | Policies |
|-------|-------------|----------|
| `jobs` | Yes | `Service role full access on jobs` → `true` (bypass) |
| `job_responses` | Yes | `Service role full access on job_responses` → `true` (bypass) |
| `leo_inbound_emails` | Yes | `service_role_all` → `auth.role() = 'service_role'` |
| All other 10 tables | **No** | None |

**Translation:** RLS is technically enabled on 3 tables but offers no real security. Every policy says "if you're the service role, do anything." The anon key could read/write 10 unprotected tables directly.

---

## 2. What Supabase Auth Offers

Supabase Auth is a full user management system built on GoTrue (open source). It provides:

### Auth methods (all built-in, no external service needed)

| Method | How it works | Relevant to Leo? |
|--------|-------------|------------------|
| **Phone OTP** | SMS code to phone number → creates user | Primary — matches our phone-first model |
| **Email + Password** | Traditional signup/login | Secondary — for web dashboard access |
| **Magic Link** | Passwordless email link | Nice for homeowner re-login |
| **Social Login** | Google, Apple, Facebook, etc. | Good for reducing friction |
| **Anonymous Auth** | Create user without credentials, upgrade later | Perfect for landing page → WhatsApp flow |

### What auth gives you

| Capability | Without auth (current) | With auth |
|-----------|----------------------|-----------|
| User identity | Phone string or UUID | `auth.uid()` (Supabase-managed UUID) |
| Session management | None (stateless) | JWT tokens, auto-refresh |
| RLS policies | Pointless (service key bypasses) | Real per-user data isolation |
| Multi-device | Not possible | Same user, any device |
| Password reset | N/A | Built-in |
| MFA / 2FA | Not possible | TOTP, phone, WebAuthn |
| Rate limiting | Manual | Built-in per-user |

---

## 3. Phone-First Auth Pattern for Leo

Leo's users arrive via WhatsApp (phone number) or a landing page (anonymous). The ideal auth flow matches this:

### Flow 1: WhatsApp user (contractor or homeowner)

```
User sends WhatsApp message
  → Backend receives phone number from Meta API
  → Backend calls supabase.auth.admin.create_user({ phone: "+34612345678" })
     (or finds existing user by phone)
  → User gets a Supabase auth UID
  → All subsequent data keyed by auth.uid(), not raw phone string
```

No login required from the user's perspective — they're already authenticated by WhatsApp (Meta verified the phone number).

### Flow 2: Landing page user (anonymous → phone)

```
User visits leo.casa
  → App calls supabase.auth.signInAnonymously()
  → Anonymous user gets a temp auth.uid()
  → User enters phone number in the chat
  → App calls supabase.auth.updateUser({ phone: "+34612345678" })
     and sends OTP for verification
  → User confirms OTP → anonymous user upgraded to phone-verified user
  → Same auth.uid() persists (no data migration needed)
```

### Flow 3: Returning user (app)

```
User opens app
  → Supabase SDK loads session from storage (AsyncStorage on mobile)
  → If valid → auto-logged in
  → If expired → auto-refresh with refresh token
  → If no session → biometric prompt + re-auth with phone
```

### Backend: admin operations

The backend (FastAPI) would use the **service role key** for admin operations (creating users from WhatsApp, assigning roles) and the **anon key** for client-facing operations:

```python
from supabase import create_client

supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

user = supabase_admin.auth.admin.create_user({
    "phone": "+34612345678",
    "phone_confirm": True,  # skip OTP — WhatsApp already verified
    "user_metadata": {"role": "contractor", "name": "Carlos"}
})
```

---

## 4. Row Level Security (RLS)

RLS is the main reason to add auth. With real user UIDs, we can lock tables down so users only see their own data.

### What RLS policies would look like

```sql
-- Contractors can only see their own profile
CREATE POLICY "contractors_own_data" ON contractors
  FOR ALL USING (auth.uid() = user_id);

-- Homeowners can only see their own jobs
CREATE POLICY "homeowners_own_jobs" ON jobs
  FOR ALL USING (auth.uid() = homeowner_id);

-- Contractors can see jobs they've responded to
CREATE POLICY "contractors_see_assigned_jobs" ON jobs
  FOR SELECT USING (
    auth.uid() IN (
      SELECT contractor_id FROM job_responses WHERE job_id = jobs.id
    )
  );

-- Job responses are visible to the job owner and the responder
CREATE POLICY "response_parties_only" ON job_responses
  FOR ALL USING (
    auth.uid() = contractor_id
    OR auth.uid() = (SELECT homeowner_id FROM jobs WHERE id = job_id)
  );
```

### Migration: adding `user_id` columns

Every table that needs per-user access needs a `user_id` column (UUID referencing `auth.users.id`):

| Table | Current identifier | New column | Migration |
|-------|-------------------|------------|-----------|
| `contractors` | `phone` (text) | `user_id` (uuid, FK → auth.users) | Backfill from phone lookup |
| `jobs` | `id` (uuid) | `homeowner_id` (uuid, FK → auth.users) | Backfill from landing_leads |
| `job_responses` | `contractor_id` (text) | Keep + add `user_id` | Backfill |
| `cs_leads` | `id` (uuid) | `user_id` (uuid, nullable) | Nullable — anonymous users |
| `landing_leads` | `id` (uuid) | `user_id` (uuid, nullable) | Nullable — pre-auth leads |
| `whatsapp_messages` | `from_number` (text) | `user_id` (uuid) | Backfill from phone lookup |

### The non-breaking migration strategy

1. **Add `user_id` columns as nullable** — no existing queries break
2. **Keep service role key for backend** — backend can still do everything
3. **Start creating auth users** for new signups
4. **Backfill `user_id`** for existing records (match by phone number)
5. **Enable RLS with dual policies** — allow both service role and user-level access
6. **Gradually move client calls to anon key** — frontend uses user's JWT
7. **Remove service-role-only escape hatches** once migration is complete

---

## 5. Migration Path: Adding Auth Without Breaking Anything

### Phase 1: Install SDK + create users (zero breaking changes)

```bash
# Backend
pip install supabase

# Frontend (React)
npm install @supabase/supabase-js

# Mobile (Expo)
npx expo install @supabase/supabase-js @react-native-async-storage/async-storage
```

Backend creates auth users for every new WhatsApp contact and every new landing page lead. Existing `httpx` code continues working unchanged.

### Phase 2: Add phone OTP on frontend

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Send OTP
const { error } = await supabase.auth.signInWithOtp({
  phone: '+34612345678'
})

// Verify OTP
const { data, error } = await supabase.auth.verifyOtp({
  phone: '+34612345678',
  token: '123456',
  type: 'sms'
})
```

### Phase 3: Add `user_id` columns and backfill

```sql
ALTER TABLE contractors ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE jobs ADD COLUMN homeowner_id UUID REFERENCES auth.users(id);

-- Backfill: match existing phone numbers to auth users
UPDATE contractors c
SET user_id = u.id
FROM auth.users u
WHERE u.phone = c.phone;
```

### Phase 4: Enable real RLS

```sql
ALTER TABLE contractors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own_data" ON contractors
  FOR ALL USING (
    auth.uid() = user_id
    OR auth.role() = 'service_role'
  );
```

The `OR auth.role() = 'service_role'` escape hatch ensures the backend keeps working during transition.

### Phase 5: Frontend uses JWT

```typescript
// After user is authenticated, all Supabase calls use their JWT
const { data } = await supabase
  .from('jobs')
  .select('*')
  // RLS automatically filters to user's own jobs
```

---

## 6. Supabase Auth + React Native / Expo

Supabase has first-class React Native support via `@supabase/supabase-js` + `@react-native-async-storage/async-storage`:

```typescript
import { createClient } from '@supabase/supabase-js'
import AsyncStorage from '@react-native-async-storage/async-storage'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: AsyncStorage,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false, // important for React Native
  },
})
```

### What works out of the box

| Feature | Support |
|---------|---------|
| Phone OTP | Full — SMS delivery via Supabase |
| Email/password | Full |
| Magic link | Full (needs deep link handling) |
| Social login (Google, Apple) | Full — via deep link callback |
| Anonymous auth | Full |
| Session persistence | Via AsyncStorage |
| Auto token refresh | Automatic |
| MFA (TOTP) | Supported |

### Biometric integration

Supabase Auth doesn't do biometrics directly, but the pattern is:

1. User authenticates once via phone OTP → session stored
2. On subsequent app opens, prompt for biometric (Face ID / fingerprint)
3. On biometric success, load session from AsyncStorage
4. If session expired, use refresh token transparently

```typescript
import * as LocalAuthentication from 'expo-local-authentication'

const authenticate = async () => {
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Unlock Leo',
    fallbackLabel: 'Use phone number',
  })
  if (result.success) {
    // Session already in AsyncStorage, Supabase auto-refreshes
    const { data: { session } } = await supabase.auth.getSession()
  }
}
```

---

## 7. Session Management

### How Supabase sessions work

| Token | Lifetime | Purpose |
|-------|---------|---------|
| Access token (JWT) | 1 hour (configurable) | Passed with every API call |
| Refresh token | 1 week (configurable) | Used to get new access token |

The SDK handles refresh automatically. On mobile, tokens persist in AsyncStorage across app restarts.

### Server-side session validation

Backend can verify JWTs without calling Supabase:

```python
import jwt

def verify_user_token(token: str) -> dict:
    """Verify a Supabase JWT and extract user info."""
    payload = jwt.decode(
        token,
        SUPABASE_JWT_SECRET,  # from Dashboard → Settings → API
        algorithms=["HS256"],
        audience="authenticated",
    )
    return {
        "user_id": payload["sub"],
        "phone": payload.get("phone"),
        "role": payload.get("role"),
    }
```

This means the FastAPI backend can validate user identity from the JWT without making a network call to Supabase on every request.

---

## 8. Deep Link Callbacks for OAuth

For social login (Google Sign-In, Apple Sign-In) on mobile, Supabase needs a callback URL. With Expo:

```typescript
import * as Linking from 'expo-linking'
import * as WebBrowser from 'expo-web-browser'

const signInWithGoogle = async () => {
  const redirectUrl = Linking.createURL('auth/callback')
  
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: redirectUrl,
      skipBrowserRedirect: true,
    },
  })
  
  if (data?.url) {
    const result = await WebBrowser.openAuthSessionAsync(data.url, redirectUrl)
    if (result.type === 'success') {
      const { url } = result
      // Extract tokens from URL and set session
      await supabase.auth.setSession(extractTokensFromUrl(url))
    }
  }
}
```

### Deep link configuration

```json
// app.json (Expo)
{
  "expo": {
    "scheme": "leoscope",
    "ios": {
      "associatedDomains": ["applinks:leo.casa"]
    },
    "android": {
      "intentFilters": [{
        "action": "VIEW",
        "data": [{ "scheme": "leoscope" }],
        "category": ["DEFAULT", "BROWSABLE"]
      }]
    }
  }
}
```

---

## 9. Cost Model

### Supabase Auth pricing (as of 2026)

| Tier | Monthly | MAUs included | Extra MAU cost |
|------|---------|--------------|----------------|
| Free | $0 | 50,000 | N/A |
| Pro | $25 | 100,000 | $0.00325/MAU |
| Team | $599 | 100,000 | $0.00325/MAU |

### SMS OTP costs

Supabase uses Twilio for SMS delivery. Costs are pass-through:

| Region | Approximate cost per SMS |
|--------|------------------------|
| Spain (+34) | ~$0.06 |
| UK (+44) | ~$0.04 |
| US (+1) | ~$0.01 |

At Leo's current scale (< 100 users), SMS costs are negligible. At 10,000 users with monthly re-auth: ~$600/month for Spain.

### Leo's current Supabase plan

We are on the **Pro plan** ($25/month). Auth is included — no additional cost to enable it.

---

## 10. Alternatives Considered

| Alternative | Why not |
|------------|---------|
| **Firebase Auth** | Would add Google dependency alongside Supabase. Auth and DB should be from same provider for RLS integration. |
| **Auth0** | Expensive ($23/month for 1,000 MAUs). Supabase Auth is free to 50K MAUs. |
| **Clerk** | Good UX but adds another vendor. Doesn't integrate with Supabase RLS. |
| **Custom JWT** | Reinventing the wheel. Supabase Auth is battle-tested GoTrue under the hood. |
| **Didit for auth** | Didit is for identity verification, not session management. They complement each other. |
| **Stripe Identity for auth** | Stripe Identity verifies who someone is, doesn't manage sessions or issue JWTs. |

**Decision:** Supabase Auth is the obvious choice — we already pay for Supabase, it's included in our plan, it integrates natively with RLS, and it supports phone-first auth.

---

## 11. Gotchas and Limitations

### Phone number format
Supabase requires E.164 format (`+34612345678`). WhatsApp also uses E.164. Our current data stores phone numbers inconsistently — some with `+` prefix, some without. Needs normalization during migration.

### SMS rate limits
Supabase enforces rate limits on OTP sends (default: 1 per 60 seconds per phone). This is configurable in the Dashboard under Auth → Rate Limits.

### Service role key exposure
The service role key bypasses RLS. It must **never** be exposed to the frontend. Currently it's only in backend `.env.local`, which is correct. When adding the frontend SDK, use only the anon key.

### Anonymous → authenticated migration
When an anonymous user verifies their phone, `auth.uid()` stays the same. But if they already have an account from WhatsApp, you get a **conflict**. Supabase doesn't auto-merge. You need to handle this:

```typescript
const { error } = await supabase.auth.updateUser({ phone: '+34612345678' })
if (error?.message.includes('already registered')) {
  // Phone already has an account — prompt user to sign in with OTP instead
  // Then merge anonymous user's data into the existing account
}
```

### Supabase Auth + existing `httpx` code
The backend can keep using `httpx` with the service role key indefinitely. Adding Auth doesn't force an SDK migration. The SDK is only needed for:
- Creating/managing users (`auth.admin.*`)
- Client-side auth flows (`signIn`, `signUp`)

### No SMS provider in free tier
Supabase Pro plan includes Twilio integration for SMS. Free tier requires you to bring your own SMS provider. We're on Pro, so this isn't an issue.

---

## Related Documents

| Document | What it covers |
|----------|---------------|
| `backend/database.py` | Current Supabase HTTP client (no auth) |
| `backend/config.py` | Supabase connection settings |
| `.cursor/rules/supabase-access.mdc` | Supabase credentials and access patterns |
| `internal/service-integrations/didit/README.md` | Identity verification (complements auth) |
| `internal/service-integrations/native-app/README.md` | Expo/React Native integration patterns |
