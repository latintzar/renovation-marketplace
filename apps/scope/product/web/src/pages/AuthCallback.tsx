/**
 * AuthCallback — handles Supabase OAuth/magic-link redirect.
 *
 * Flow:
 *   1. Supabase processes tokens from URL hash/params
 *   2. If `claim` param: call /v1/claim-profile
 *   3. If no preferred_language set: show full-screen language picker
 *   4. Route to destination (dashboard for contractors, my-projects for homeowners)
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { supabase } from '../lib/supabase';
import { claimProfile, apiFetch, API_BASE } from '../lib/api';
import { mergeLeoAuth } from '../lib/utils';
import { useSandboxStore } from '../context/SandboxContext';
import { LanguagePickerScreen } from '../components/LanguagePickerScreen';
import { Button } from '@scope/ui';

const SANDBOX_EMAIL_PATTERNS = ['operator@example.invalid', '+sandbox@', 'sandbox@test.leo.casa'];

type AuthState = 'processing' | 'claiming' | 'done' | 'language_pick' | 'error';

export default function AuthCallback() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<AuthState>('processing');
  const [errorMessage, setErrorMessage] = useState('');
  const [pendingDestination, setPendingDestination] = useState<string | null>(null);
  const enableSandbox = useSandboxStore((s) => s.enable);

  useEffect(() => {
    let cancelled = false;

    const handleCallback = async () => {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError || !session) {
        const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, newSession) => {
          subscription.unsubscribe();
          if (cancelled) return;

          if (event === 'SIGNED_IN' && newSession) {
            await processClaim(newSession.access_token);
          } else {
            setState('error');
            setErrorMessage(t('auth_callback_error_default'));
          }
        });
        return;
      }

      await processClaim(session.access_token);
    };

    const processClaim = async (accessToken: string) => {
      const claimToken = searchParams.get('claim');
      const returnUrl = searchParams.get('return');

      const { data: { user } } = await supabase.auth.getUser();
      const userEmail = user?.email || '';
      const isSandboxUser = SANDBOX_EMAIL_PATTERNS.some((p) => userEmail.includes(p));
      if (isSandboxUser && !cancelled) {
        enableSandbox();
        navigate('/sandbox', { replace: true });
        return;
      }

      const needsLanguage = !user?.user_metadata?.preferred_language;

      if (!claimToken) {
        if (returnUrl && !cancelled) {
          if (needsLanguage) {
            setPendingDestination(returnUrl);
            setState('language_pick');
          } else {
            navigate(returnUrl, { replace: true });
          }
          return;
        }

        try {
          const authUserId = user?.id;
          if (authUserId) {
            const res = await apiFetch(
              `${API_BASE}/v1/contractor/by-auth-user/${encodeURIComponent(authUserId)}`,
            );
            if (res.ok && !cancelled) {
              const data = await res.json();
              mergeLeoAuth({
                contractor_id: data.contractor_id,
                contractor_name: data.contractor_name,
                auth_user_id: authUserId,
                access_token: accessToken,
                stripe_onboarding_complete: data.stripe_onboarding_complete,
              });

              if (needsLanguage) {
                setPendingDestination('/dashboard');
                setState('language_pick');
              } else {
                navigate('/dashboard', { replace: true });
              }
              return;
            }
          }
        } catch { /* network error — fall through */ }

        if (!cancelled) {
          if (needsLanguage) {
            setPendingDestination('/my-projects');
            setState('language_pick');
          } else {
            navigate('/my-projects', { replace: true });
          }
        }
        return;
      }

      // Claim flow
      setState('claiming');
      const result = await claimProfile(claimToken, accessToken);
      if (cancelled) return;

      if (!result.ok || !result.contractor_id) {
        setState('error');
        setErrorMessage(result.error || 'Could not link your profile — please try again');
        return;
      }

      setState('done');

      mergeLeoAuth({
        contractor_id: result.contractor_id,
        auth_user_id: result.auth_user_id,
        access_token: accessToken,
      });

      const dest = `/quote/first?contractorId=${encodeURIComponent(result.contractor_id!)}`;

      setTimeout(() => {
        if (!cancelled) {
          if (needsLanguage) {
            setPendingDestination(dest);
            setState('language_pick');
          } else {
            navigate(dest, { replace: true });
          }
        }
      }, 800);
    };

    handleCallback();
    return () => { cancelled = true; };
  }, [navigate, searchParams, enableSandbox]);

  if (state === 'language_pick') {
    return (
      <LanguagePickerScreen
        onDone={() => navigate(pendingDestination || '/', { replace: true })}
      />
    );
  }

  return (
    <div className="flex flex-col items-center justify-center h-dvh bg-cream px-6">
      <div className="w-full max-w-sm text-center">

        {state === 'processing' && (
          <>
            <div className="w-10 h-10 border-2 border-terracotta/30 border-t-terracotta rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm text-stone">{t('auth_callback_processing')}</p>
          </>
        )}

        {state === 'claiming' && (
          <>
            <div className="w-10 h-10 border-2 border-terracotta/30 border-t-terracotta rounded-full animate-spin mx-auto mb-4" />
            <p className="text-base font-semibold text-ink mb-1">{t('auth_callback_claiming')}</p>
            <p className="text-sm text-stone">{t('auth_callback_moment')}</p>
          </>
        )}

        {state === 'done' && (
          <>
            <div className="w-16 h-16 rounded-full bg-green/10 flex items-center justify-center mx-auto mb-4">
              <svg viewBox="0 0 24 24" className="w-8 h-8 text-green" fill="none" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <p className="text-base font-semibold text-ink mb-1">{t('auth_callback_profile_claimed')}</p>
            <p className="text-sm text-stone">{t('auth_callback_opening_builder')}</p>
          </>
        )}

        {state === 'error' && (
          <>
            <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
              <svg viewBox="0 0 24 24" className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
            </div>
            <p className="text-base font-semibold text-ink mb-2">{t('auth_callback_error_title')}</p>
            <p className="text-sm text-stone mb-6">{errorMessage}</p>
            <Button
              type="button"
              onClick={() => window.history.back()}
              className="w-full py-3 rounded-sm bg-ink text-cream text-sm font-semibold hover:bg-stone transition-colors"
            >
              {t('auth_callback_go_back')}
            </Button>
          </>
        )}

      </div>
    </div>
  );
}
