/**
 * Settings — Account page for both contractors and homeowners.
 */

import { useNavigate } from 'react-router-dom';
import { ChevronLeft, LogOut, User, Landmark, CheckCircle2, Mail, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { LanguageToggle } from '../components/LanguageToggle';
import { setAppLanguage } from '../i18n';
import { setLanguagePreference } from '../lib/supabase';
import { Button } from '@scope/ui';

export default function Settings() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user, role, contractorId, contractorName: authContractorName, stripeConnected: authStripeConnected, signOut, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-cream">
        <div className="w-6 h-6 border-2 border-stone/30 border-t-terracotta rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    navigate('/', { replace: true });
    return null;
  }

  const handleLogout = async () => {
    await signOut();
    navigate('/', { replace: true });
  };

  const isContractor = role === 'contractor';
  const contractorName = authContractorName || '';
  const stripeConnected = authStripeConnected;

  const displayName = isContractor ? contractorName : '';
  const displayEmail = user.email || '';
  const initials = displayName
    ? displayName.split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()
    : displayEmail ? displayEmail[0].toUpperCase() : '?';

  const backPath = isContractor ? '/dashboard' : '/my-projects';
  const backLabel = isContractor ? t('settings_back_contractor') : t('settings_back_homeowner');

  return (
    <div className="min-h-dvh bg-cream">
      <header className="sticky top-0 z-50 bg-cream/95 backdrop-blur-lg border-b border-border pt-safe">
        <div className="flex items-center gap-3 px-4 h-14 max-w-lg mx-auto">
          <Button
            type="button"
            onClick={() => navigate(backPath)}
            className="flex items-center gap-0.5 text-xs font-medium text-stone hover:text-ink transition-colors"
          >
            <ChevronLeft size={14} strokeWidth={2.5} />
            {backLabel}
          </Button>
          <h1 className="font-display text-base font-semibold text-ink flex-1 text-center">{t('settings_title')}</h1>
          <div className="w-16 flex justify-end">
            <LanguageToggle variant="light" />
          </div>
        </div>
      </header>

      <div className="px-4 pt-8 pb-24 max-w-lg mx-auto">
        {/* Profile card */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-20 h-20 rounded-full bg-terracotta/15 flex items-center justify-center mb-3">
            {displayName
              ? <span className="text-terracotta text-2xl font-bold">{initials}</span>
              : <User size={36} className="text-terracotta/60" strokeWidth={1.5} />
            }
          </div>
          {displayName && (
            <p className="text-lg font-semibold text-ink">{displayName}</p>
          )}
          {displayEmail && (
            <p className="text-sm text-stone mt-0.5 flex items-center gap-1">
              <Mail size={12} />
              {displayEmail}
            </p>
          )}
          <p className="text-xs text-muted mt-2 px-3 py-1 rounded-full bg-stone/5">
            {isContractor ? t('settings_contractor_badge') : t('settings_homeowner_badge')}
          </p>
        </div>

        {/* Bank account — contractors only */}
        {isContractor && (
          <div className="rounded-sm border border-border bg-white/60 overflow-hidden mb-4">
            <div className="px-4 py-3.5">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-sm text-stone">{t('settings_bank_account')}</span>
                {stripeConnected ? (
                  <span className="flex items-center gap-1 text-xs font-semibold text-green-600">
                    <CheckCircle2 size={13} strokeWidth={2.5} />
                    {t('settings_bank_connected')}
                  </span>
                ) : (
                  <span className="text-xs font-medium text-amber-600">{t('settings_bank_pending')}</span>
                )}
              </div>
              {!stripeConnected && (
                <p className="text-xs text-muted leading-relaxed mb-3 mt-1">
                  {t('settings_bank_pending_desc')}
                </p>
              )}
              {!stripeConnected && contractorId && (
                <Button
                  type="button"
                  onClick={() => navigate(`/stripe/kyc?contractor=${encodeURIComponent(contractorId)}`)}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-sm text-sm font-semibold transition-colors active:scale-[0.98] duration-150"
                  style={{ background: 'var(--color-ink)', color: 'var(--color-cream)' }}
                >
                  <Landmark size={14} strokeWidth={2} />
                  {t('settings_bank_connect_btn')}
                </Button>
              )}
              {stripeConnected && (
                <p className="text-xs text-muted mt-0.5">
                  {t('settings_bank_connected_desc')}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Language */}
        <LanguageSettingRow />

        {/* Sign out */}
        <Button variant="danger" fullWidth className="py-3.5 border-red-200 text-red-500" type="button"
          onClick={handleLogout}><LogOut size={15} strokeWidth={2} />
          {t('settings_sign_out')}</Button>
      </div>
    </div>
  );
}

function LanguageSettingRow() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const current = i18n.language?.startsWith('es') ? 'es' : 'en';

  const toggle = (lang: 'en' | 'es') => {
    setAppLanguage(lang);
    if (user) setLanguagePreference(lang).catch(() => {});
  };

  return (
    <div className="rounded-sm border border-border bg-white/60 overflow-hidden mb-4">
      <div className="px-4 py-3.5">
        <div className="flex items-center gap-2 mb-3">
          <Globe size={15} className="text-stone" />
          <span className="text-sm text-stone">{t('settings_language')}</span>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            onClick={() => toggle('en')}
            className={`flex-1 py-2.5 rounded-sm text-sm font-medium transition-colors ${
              current === 'en' ? 'bg-ink text-cream' : 'bg-stone/5 text-stone hover:bg-stone/10'
            }`}
          >
            🇬🇧 English
          </Button>
          <Button
            type="button"
            onClick={() => toggle('es')}
            className={`flex-1 py-2.5 rounded-sm text-sm font-medium transition-colors ${
              current === 'es' ? 'bg-ink text-cream' : 'bg-stone/5 text-stone hover:bg-stone/10'
            }`}
          >
            🇪🇸 Español
          </Button>
        </div>
      </div>
    </div>
  );
}
