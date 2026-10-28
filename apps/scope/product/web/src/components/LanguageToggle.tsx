/**
 * LanguageToggle — Compact pill that switches between EN/ES.
 * Persists to localStorage + Supabase user_metadata if logged in.
 */

import { useTranslation } from 'react-i18next';
import { setAppLanguage } from '../i18n';
import { setLanguagePreference } from '../lib/supabase';
import { useAuth } from '../context/AuthContext';
import { Button } from '@scope/ui';

interface LanguageToggleProps {
  variant?: 'light' | 'dark';
}

export function LanguageToggle({ variant = 'light' }: LanguageToggleProps) {
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const current = i18n.language?.startsWith('es') ? 'es' : 'en';
  const next = current === 'en' ? 'es' : 'en';

  const handleToggle = () => {
    setAppLanguage(next);
    if (user) setLanguagePreference(next).catch(() => {});
  };

  const isLight = variant === 'light';

  return (
    <Button
      type="button"
      onClick={handleToggle}
      aria-label={`Switch to ${next === 'es' ? 'Español' : 'English'}`}
      className={`
        flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-medium uppercase tracking-wide
        transition-colors active:scale-95
        ${isLight
          ? 'bg-border/60 text-stone hover:bg-border hover:text-ink'
          : 'bg-white/10 text-cream/70 hover:bg-white/20 hover:text-cream'
        }
      `}
    >
      <span className="text-[10px]">{current === 'en' ? '🇬🇧' : '🇪🇸'}</span>
      {current.toUpperCase()}
    </Button>
  );
}
