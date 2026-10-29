/**
 * Login — universal auth for contractors AND homeowners.
 *
 * Two-step flow:
 *   Step 1 — Google / Apple / Microsoft OAuth + email → Continue
 *   Step 2 — "Check your email" full-screen (Monzo-style)
 *
 * All colours from theme.css tokens (bg-cream, text-ink, bg-terracotta, …).
 * No hardcoded hex values.
 * Sandbox: 5-tap "Leo · Beta" footer.
 */

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { LeoLogo } from '../components/LeoLogo';
import { LanguageToggle } from '../components/LanguageToggle';
import { supabase } from '../lib/supabase';
import { API_BASE, apiFetch } from '../lib/api';
import { mergeLeoAuth } from '../lib/utils';
import { identify, track } from '../lib/tracking';
import { useSandboxStore } from '../context/SandboxContext';
import { Button, Input } from '@scope/ui';

// ─── Icons (inline SVG — no external deps) ───────────────────────────────────

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908C16.658 14.013 17.64 11.705 17.64 9.2z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  );
}

// ─── Envelope illustration ────────────────────────────────────────────────────
// Seal uses the real Playfair L monogram SVG — no font dependency.

function EnvelopeIllustration() {
  return (
    <div className="relative w-40 h-[120px]">
      <svg width="160" height="120" viewBox="0 0 160 120" fill="none" aria-hidden="true" className="absolute inset-0">
        {/* Drop shadow */}
        <ellipse cx="80" cy="116" rx="52" ry="4" fill="var(--color-border)"/>
        {/* Envelope body */}
        <rect x="8" y="24" width="144" height="88" rx="12" fill="var(--color-card)" stroke="var(--color-border)" strokeWidth="1.5"/>
        {/* Flap */}
        <path d="M8 40 L80 80 L152 40 L152 24 Q152 24 140 24 L80 66 L20 24 Q8 24 8 24 Z" fill="var(--color-cream-dark)"/>
        {/* Terracotta seal rings */}
        <circle cx="80" cy="78" r="24" fill="var(--color-terracotta-light)"/>
        <circle cx="80" cy="78" r="17" fill="var(--color-terracotta)"/>
      </svg>
      {/* Real Playfair L monogram — cream on terracotta seal */}
      <img
        src={`${import.meta.env.BASE_URL}brand/leo-L-cream.svg`}
        alt=""
        aria-hidden="true"
        className="absolute"
        style={{ width: 13, height: 16, left: 73, top: 61 }}
        draggable={false}
      />
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function openMailApp(email: string) {
  const domain = (email.split('@')[1] ?? '').toLowerCase();

  // Provider-specific deep links open directly to the inbox.
  // Fallback: `mailto:` opens the OS default mail app (compose view, but user is in their app).
  // There is no universal cross-platform "open inbox" URI — this is the best achievable on web.
  let url = 'mailto:';
  if (domain.includes('gmail') || domain.includes('googlemail')) {
    url = 'googlegmail://';      // Gmail on Android + iOS → inbox
  } else if (['hotmail', 'outlook', 'live', 'msn'].some((d) => domain.includes(d))) {
    url = 'ms-outlook://';       // Outlook on Android + iOS → inbox
  } else if (domain.includes('yahoo')) {
    url = 'ymail://';            // Yahoo Mail → inbox
  } else if (domain.includes('hey.com')) {
    url = 'hey://';
  } else if (/iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase())) {
    url = 'message://';          // Apple Mail on iOS → inbox (for iCloud, custom domains, etc.)
  }

  const a = document.createElement('a');
  a.href = url;
  a.click();
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function OAuthButton({
  icon, label, onClick, disabled, variant = 'light',
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: 'light' | 'dark';
}) {
  return (
    <Button
      variant={variant === 'dark' ? 'primary' : 'secondary'}
      fullWidth
      onClick={onClick}
      disabled={disabled}
      icon={icon}
      className="py-3.5 text-[15px] active:scale-[0.98]"
    >
      {label}
    </Button>
  );
}

function Divider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-1">
      <div className="flex-1 h-px bg-border" />
      <span className="text-muted text-xs">{label}</span>
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

type AuthState = 'checking' | 'ready' | 'oauth';
type EmailStep = 'idle' | 'sending' | 'sent';

export default function Login() {
  const nav = useNavigate();
  const { t } = useTranslation();
  const [authState, setAuthState] = useState<AuthState>('checking');
  const [email, setEmail] = useState('');
  const [emailStep, setEmailStep] = useState<EmailStep>('idle');
  const [error, setError] = useState('');

  const enableSandbox = useSandboxStore((s) => s.enable);
  const taps = useRef(0);
  const tapTimer = useRef<number | undefined>(undefined);

  const handleDevTap = () => {
    taps.current++;
    window.clearTimeout(tapTimer.current);
    if (taps.current >= 5) { taps.current = 0; enableSandbox(); nav('/sandbox'); return; }
    tapTimer.current = window.setTimeout(() => { taps.current = 0; }, 1500);
  };

  // Session restore
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.user) { if (!cancelled) setAuthState('ready'); return; }
      try {
        const res = await apiFetch(`${API_BASE}/v1/contractor/by-auth-user/${encodeURIComponent(session.user.id)}`);
        if (res.ok) {
          const d = await res.json();
          mergeLeoAuth({ contractor_id: d.contractor_id, contractor_name: d.contractor_name, auth_user_id: session.user.id, access_token: session.access_token, stripe_onboarding_complete: d.stripe_onboarding_complete });
          identify(d.contractor_id, { name: d.contractor_name, role: 'contractor' });
          track('login.session_restored', { role: 'contractor' });
          if (!cancelled) nav('/dashboard', { replace: true });
          return;
        }
        if (res.status === 404) {
          track('login.session_restored', { role: 'homeowner' });
          if (!cancelled) nav('/my-projects', { replace: true });
          return;
        }
      } catch { /* network error */ }
      if (!cancelled) setAuthState('ready');
    })();
    return () => { cancelled = true; };
  }, [nav]);

  const handleOAuth = async (provider: 'google' | 'apple' | 'azure') => {
    setAuthState('oauth');
    track(`login.${provider}_started`);
    const { error: err } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${window.location.origin}${import.meta.env.BASE_URL}auth/callback` },
    });
    if (err) { setAuthState('ready'); setError(err.message); }
  };

  const handleContinue = async () => {
    if (!email.includes('@')) { setError(t('login_email_invalid')); return; }
    setEmailStep('sending');
    setError('');
    track('login.magic_link_started', { email });
    const { error: err } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}${import.meta.env.BASE_URL}auth/callback`, shouldCreateUser: true },
    });
    if (err) { setError(err.message); setEmailStep('idle'); return; }
    setEmailStep('sent');
  };

  const busy = authState === 'oauth' || emailStep === 'sending';

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (authState === 'checking') {
    return (
      <div className="flex items-center justify-center h-dvh bg-cream">
        <div className="w-8 h-8 border-2 border-terracotta/30 border-t-terracotta rounded-full animate-spin" />
      </div>
    );
  }

  // ── Step 2: Check your email ────────────────────────────────────────────────
  if (emailStep === 'sent') {
    return (
      <div className="min-h-dvh flex flex-col bg-cream relative">
        <div className="absolute top-4 right-4 z-10">
          <LanguageToggle variant="light" />
        </div>
        {/* Nav header */}
        <div className="px-4 pt-14 pb-2">
          <Button
            variant="ghost"
            onClick={() => { setEmailStep('idle'); setError(''); }}
            icon={<ArrowLeft size={20} />}
            className="-ml-1 py-2 pr-4"
            aria-label="Back"
          >
            <span className="text-[17px] font-medium text-ink">Sign in</span>
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col items-center justify-center px-8 text-center pb-24">
          <div className="mb-8">
            <EnvelopeIllustration />
          </div>

          <h2 className="font-display text-[26px] font-semibold text-ink mb-5 leading-snug">
            {t('login_check_email_title')}
          </h2>

          <p className="text-stone text-[15px]">{t('login_check_email_sent')}</p>
          <p className="text-ink font-semibold text-[15px] mt-0.5 mb-2">{email}</p>
          <p className="text-muted text-sm mb-10">{t('login_check_email_desc')}</p>

          <Button
            variant="terracotta"
            size="lg"
            onClick={() => openMailApp(email)}
            className="w-full max-w-xs py-4 text-[15px] active:scale-[0.98] mb-5"
          >
            {t('login_open_mail_app')}
          </Button>

          <Button
            variant="ghost"
            onClick={() => { setEmailStep('idle'); setError(''); }}
            className="text-terracotta text-sm hover:text-terracotta-dark"
          >
            {t('login_resend')}
          </Button>
        </div>
      </div>
    );
  }

  // ── Step 1: Method picker ───────────────────────────────────────────────────
  return (
    <div className="min-h-dvh flex flex-col bg-cream relative">
      <div className="absolute top-4 right-4 z-10">
        <LanguageToggle variant="light" />
      </div>
      {/* Logo */}
      <div className="flex-1 flex items-center justify-center pt-16 pb-6">
        <div className="text-center">
          <LeoLogo variant="charcoal" height={44} className="block mx-auto mb-2" />
          <p className="text-stone text-sm max-w-[200px] mx-auto leading-snug">{t('login_subtitle')}</p>
        </div>
      </div>

      {/* Auth options */}
      <div className="px-6 pb-10">
        <div className="w-full max-w-sm mx-auto space-y-3">
          <OAuthButton icon={<GoogleIcon />} label={busy ? t('login_google_loading') : t('login_google_button')} onClick={() => handleOAuth('google')} disabled={busy} />

          <Divider label={t('login_or')} />

          <Input
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(''); }}
            onKeyDown={(e) => e.key === 'Enter' && handleContinue()}
            placeholder={t('login_email_placeholder')}
            className="py-3.5 text-[15px]"
            autoComplete="email"
            inputMode="email"
          />

          {error && <p className="text-red text-xs text-center">{error}</p>}

          <Button variant="terracotta" fullWidth className="py-3.5 text-card text-[15px] active:scale-[0.98]" type="button"
            onClick={handleContinue}
            disabled={busy}>{emailStep === 'sending'
              ? <><Loader2 size={16} className="animate-spin" />{t('login_sending')}</>
              : t('login_continue')}</Button>
        </div>

        <div className="mt-8 flex flex-col items-center gap-2">
          <p className="text-muted text-xs">{t('login_no_account')}</p>
          <div className="flex gap-4 text-xs">
            <a href="/professionals" className="text-stone hover:text-ink underline underline-offset-2 transition-colors">{t('login_im_tradesperson')}</a>
            <span className="text-muted">&middot;</span>
            <a href="/en" className="text-stone hover:text-ink underline underline-offset-2 transition-colors">{t('login_im_homeowner')}</a>
          </div>
        </div>
      </div>

      <div className="pb-6 text-center">
        <p className="text-muted text-xs select-none cursor-default" onClick={handleDevTap}>Leo &middot; Beta</p>
      </div>
    </div>
  );
}
