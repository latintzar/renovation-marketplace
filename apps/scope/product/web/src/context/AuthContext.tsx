/**
 * AuthContext — Single source of truth for user identity
 * =======================================================
 *
 * Replaces the per-page sessionStorage parsing that was scattered across
 * Dashboard, Settings, FirstQuote, MyQuotes, MyProject, Canvas, etc.
 *
 * Usage:
 *   const { role, contractorId, contractorName, email, user, loading, signOut, getAccessToken } = useAuth();
 *
 * For route protection use RequireAuth (see RequireAuth.tsx):
 *   <RequireAuth role="contractor"><Dashboard /></RequireAuth>
 *
 * apiFetch() in api.ts automatically injects Authorization: Bearer <token>
 * on every call by calling getAccessToken() — no manual token plumbing needed.
 */

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import { API_BASE, apiFetch, setAuthTokenGetter } from '../lib/api';
import { mergeLeoAuth } from '../lib/utils';
import { setAppLanguage } from '../i18n';
import { isReel } from '../reel/flag';
import { activeScript } from '../reel/registry';

export type UserRole = 'contractor' | 'homeowner' | null;

interface AuthState {
  user: User | null;
  role: UserRole;
  /** Supabase contractor row ID — set only for contractors */
  contractorId: string | null;
  /** Human-readable contractor business name — set only for contractors */
  contractorName: string | null;
  /** Whether Stripe Connect onboarding is complete — contractors only */
  stripeConnected: boolean;
  /** Authenticated user email */
  email: string | null;
  loading: boolean;
  signOut: () => Promise<void>;
  /** Returns the current access token for Authorization headers. */
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthState>({
  user: null,
  role: null,
  contractorId: null,
  contractorName: null,
  stripeConnected: false,
  email: null,
  loading: true,
  signOut: async () => {},
  getAccessToken: async () => null,
});

export function useAuth() {
  return useContext(AuthContext);
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

interface ContractorInfo {
  contractor_id: string;
  contractor_name: string;
  stripe_onboarding_complete: boolean;
}

async function fetchContractorInfo(authUserId: string): Promise<ContractorInfo | null> {
  try {
    const resp = await apiFetch(`${API_BASE}/v1/contractor/by-auth-user/${authUserId}`);
    if (!resp.ok) return null;
    const data = await resp.json();
    if (!data.contractor_id) return null;
    return {
      contractor_id: data.contractor_id,
      contractor_name: data.contractor_name || '',
      stripe_onboarding_complete: Boolean(data.stripe_onboarding_complete),
    };
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<UserRole>(null);
  const [contractorId, setContractorId] = useState<string | null>(null);
  const [contractorName, setContractorName] = useState<string | null>(null);
  const [stripeConnected, setStripeConnected] = useState(false);
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function applyUser(u: User | null) {
    if (!u) {
      setUser(null);
      setRole(null);
      setContractorId(null);
      setContractorName(null);
      setStripeConnected(false);
      setEmail(null);
      setLoading(false);
      return;
    }
    setUser(u);
    setEmail(u.email ?? null);

    // Sync language preference from user_metadata → i18n + localStorage
    const prefLang = u.user_metadata?.preferred_language;
    if (prefLang === 'en' || prefLang === 'es') {
      setAppLanguage(prefLang);
    }

    const info = await fetchContractorInfo(u.id);
    if (info) {
      setRole('contractor');
      setContractorId(info.contractor_id);
      setContractorName(info.contractor_name || null);
      setStripeConnected(info.stripe_onboarding_complete);
      // Merge into sessionStorage so downstream code (FirstQuote, StripeReturn)
      // that writes extra fields like quote_token doesn't lose them on refresh.
      mergeLeoAuth({
        contractor_id: info.contractor_id,
        contractor_name: info.contractor_name,
        stripe_onboarding_complete: info.stripe_onboarding_complete,
        auth_user_id: u.id,
        email: u.email ?? '',
      });
    } else {
      setRole('homeowner');
      setContractorId(null);
      setContractorName(null);
      setStripeConnected(false);
      try {
        sessionStorage.setItem('leo_homeowner_auth', JSON.stringify({
          id: u.id,
          email: u.email ?? '',
        }));
      } catch { /* sessionStorage unavailable */ }
    }

    setLoading(false);
  }

  useEffect(() => {
    // Reel mode: synthesize the flow's identity and skip Supabase entirely, so
    // role-gated routes (RequireAuth, ProjectDetail) resolve against canned data.
    if (isReel()) {
      setAuthTokenGetter(async () => null);
      const ident = activeScript()?.auth;
      if (ident) {
        setUser({
          id: ident.id,
          email: ident.email,
          user_metadata: {},
          app_metadata: {},
          aud: 'reel',
          created_at: '',
        } as unknown as User);
        setEmail(ident.email);
        setRole(ident.role);
        setContractorId(ident.contractorId ?? null);
        setContractorName(ident.contractorName ?? null);
        setStripeConnected(Boolean(ident.stripeConnected));
      }
      setLoading(false);
      return;
    }

    // Register the token getter so apiFetch can inject Authorization headers
    setAuthTokenGetter(async () => {
      const { data } = await supabase.auth.getSession();
      return data.session?.access_token ?? null;
    });

    supabase.auth.getSession().then(({ data }) => {
      applyUser(data.session?.user ?? null);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      applyUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function signOut() {
    await supabase.auth.signOut();
    try {
      sessionStorage.removeItem('leo_auth');
      sessionStorage.removeItem('leo_homeowner_auth');
    } catch { /* sessionStorage unavailable */ }
    setUser(null);
    setRole(null);
    setContractorId(null);
    setContractorName(null);
    setStripeConnected(false);
    setEmail(null);
  }

  async function getAccessToken(): Promise<string | null> {
    try {
      const { data } = await supabase.auth.getSession();
      return data.session?.access_token ?? null;
    } catch {
      return null;
    }
  }

  return (
    <AuthContext.Provider value={{
      user,
      role,
      contractorId,
      contractorName,
      stripeConnected,
      email,
      loading,
      signOut,
      getAccessToken,
    }}>
      {children}
    </AuthContext.Provider>
  );
}
