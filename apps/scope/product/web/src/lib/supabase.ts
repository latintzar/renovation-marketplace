/**
 * Supabase client singleton — used for auth only (Google OAuth + claim flow).
 * All database operations stay in the backend (service role key).
 * This client uses the anon key — safe to expose in the frontend.
 */

import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import {localMode} from './runtime';
import {localAuthClient} from './localAuth';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'http://127.0.0.1:54321';
// Anon key is safe to expose (client-side, row-level-security enforced server-side)
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  'local-reel-only-anon-key';

export const supabase: SupabaseClient = localMode ? localAuthClient as unknown as SupabaseClient : createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
});

/** Start Google OAuth flow, storing the claim token in the redirect URL. */
export async function signInWithGoogleForClaim(claimToken: string): Promise<{ error?: string }> {
  const redirectTo = `${window.location.origin}${import.meta.env.BASE_URL}auth/callback?claim=${encodeURIComponent(claimToken)}`;
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo },
  });
  if (error) return { error: error.message };
  return {};
}

// ---------------------------------------------------------------------------
// Language preference
// ---------------------------------------------------------------------------

/** Update the user's language preference in Supabase user_metadata. */
export async function setLanguagePreference(lang: 'en' | 'es'): Promise<void> {
  await supabase.auth.updateUser({ data: { preferred_language: lang } });
}
