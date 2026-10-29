/**
 * InlineLogin — Compact auth form shown inside the project tracking page.
 * Google primary + email magic link fallback (matches universal Login.tsx).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Mail } from 'lucide-react';
import { Button, GlassCard, Input } from '@scope/ui';
import { GoogleSignInButton } from '../GoogleSignInButton';
import { supabase } from '../../lib/supabase';
import { track } from '../../lib/tracking';

interface InlineLoginProps {
  prefillEmail: string;
}

export function InlineLogin({ prefillEmail }: InlineLoginProps) {
  const { t } = useTranslation();
  const [email, setEmail] = useState(prefillEmail);
  const [step, setStep] = useState<'form' | 'sending' | 'sent'>('form');
  const [error, setError] = useState('');

  const handleGoogle = async () => {
    track('tracking.login_google', { source: 'inline' });
    const returnUrl = window.location.pathname;
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}${import.meta.env.BASE_URL}auth/callback?return=${encodeURIComponent(returnUrl)}`,
      },
    });
  };

  const handleMagicLink = async () => {
    if (!email.includes('@')) { setError(t('login_email_invalid')); return; }
    setStep('sending');
    setError('');
    track('tracking.login_magic_link_sent', { email });

    const { error: sendError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: window.location.href,
        shouldCreateUser: true,
      },
    });

    if (sendError) { setError(sendError.message); setStep('form'); return; }
    setStep('sent');
  };

  if (step === 'sent') {
    return (
      <div className="w-full space-y-3">
        <GlassCard className="space-y-3 text-center">
          <Mail size={20} className="text-cream mx-auto" />
          <p className="text-sm font-medium text-cream">
            {t('login_magic_link_sent_title')}
          </p>
          <p className="text-xs text-cream/60">
            {t('login_magic_link_sent_desc', { email })}
          </p>
          <Button
            type="button"
            onClick={() => { setStep('form'); setEmail(''); }}
            className="text-xs text-cream/45 hover:text-cream/80 transition-colors"
          >
            {t('login_use_different_email')}
          </Button>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="w-full space-y-3">
      <p className="text-[13px] text-center text-cream/60">
        {t('inline_login_prompt')}
      </p>
      <GlassCard className="space-y-3">
        {/* Google (primary) */}
        <GoogleSignInButton
          label={t('login_google_button')}
          onClick={handleGoogle}
          variant="glass"
        />

        <div className="flex items-center gap-2">
          <div className="flex-1 h-px bg-cream/15" />
          <span className="text-[10px] text-cream/35">{t('login_or')}</span>
          <div className="flex-1 h-px bg-cream/15" />
        </div>

        {/* Email magic link */}
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleMagicLink()}
          placeholder={t('login_email_placeholder')}
          autoFocus={!prefillEmail}
          className="w-full px-4 py-3 rounded-sm text-sm text-ink bg-white focus:outline-none focus:ring-2 focus:ring-white/30"
        />
        <Button fullWidth className="text-cream/85 active:scale-[0.98] transition-transform" type="button"
          onClick={handleMagicLink}
          disabled={step === 'sending'}
          style={{ background: 'rgba(255,255,255,0.08)' }}>{step === 'sending' ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
          {step === 'sending' ? t('login_sending') : t('login_send_magic_link')}</Button>

        {error && <p className="text-xs text-red-300 text-center">{error}</p>}
      </GlassCard>
    </div>
  );
}
