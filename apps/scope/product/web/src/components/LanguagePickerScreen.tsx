/**
 * LanguagePickerScreen — full-viewport language selection.
 *
 * Uses the shared FullScreenStep container (same layout as the phone-number
 * and location steps). No backdrop/modal — nothing behind it to peek at.
 *
 * Shown once after first login when no preferred_language is set.
 * Spanish pre-selected as default (market is Spain).
 */

import { useState } from 'react';
import { Globe } from 'lucide-react';
import { setAppLanguage } from '../i18n';
import { setLanguagePreference } from '../lib/supabase';
import { FullScreenStep } from './FullScreenStep';
import { Button } from '@scope/ui';

interface LanguagePickerScreenProps {
  onDone: () => void;
}

export function LanguagePickerScreen({ onDone }: LanguagePickerScreenProps) {
  const [selected, setSelected] = useState<'en' | 'es'>('es');
  const [saving, setSaving] = useState(false);

  const handleConfirm = async () => {
    setSaving(true);
    setAppLanguage(selected);
    await setLanguagePreference(selected).catch(() => {});
    setSaving(false);
    onDone();
  };

  return (
    <FullScreenStep
      icon={<Globe size={20} className="text-terracotta" />}
      title="¿En qué idioma prefieres Leo?"
      subtitle="Which language do you prefer?"
      footer={
        <Button variant="terracotta" fullWidth className="py-3.5 text-card disabled:opacity-40 active:scale-[0.98]" type="button"
          onClick={handleConfirm}
          disabled={saving}>{saving ? 'Guardando…' : 'Continuar →'}</Button>
      }
    >
      <div className="space-y-2.5">
        <Button
          type="button"
          onClick={() => setSelected('es')}
          className={`w-full flex items-center gap-4 px-4 py-4 rounded-sm border-2 transition-all ${
            selected === 'es'
              ? 'border-terracotta bg-terracotta/5'
              : 'border-border bg-card hover:border-stone/40'
          }`}
        >
          <span className="text-xl" role="img" aria-label="Español">🇪🇸</span>
          <div className="text-left flex-1">
            <p className="text-[15px] font-semibold text-ink">Español</p>
            <p className="text-xs text-stone">Continuar en español</p>
          </div>
          {selected === 'es' && (
            <svg className="w-5 h-5 text-terracotta shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          )}
        </Button>

        <Button
          type="button"
          onClick={() => setSelected('en')}
          className={`w-full flex items-center gap-4 px-4 py-4 rounded-sm border-2 transition-all ${
            selected === 'en'
              ? 'border-terracotta bg-terracotta/5'
              : 'border-border bg-card hover:border-stone/40'
          }`}
        >
          <span className="text-xl" role="img" aria-label="English">🇬🇧</span>
          <div className="text-left flex-1">
            <p className="text-[15px] font-semibold text-ink">English</p>
            <p className="text-xs text-stone">Continue in English</p>
          </div>
          {selected === 'en' && (
            <svg className="w-5 h-5 text-terracotta shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          )}
        </Button>
      </div>
    </FullScreenStep>
  );
}
