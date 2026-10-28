import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import en from './locales/en.json';
import es from './locales/es.json';

// Single source of truth: apps/web/src/locales/{en,es}.json
// Managed by: pnpm run i18n:extract (i18next-cli scan + Bedrock translate)
// Covers all strings from apps/web/src/ AND packages/ui/src/
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en as Record<string, string> },
      es: { translation: es as Record<string, string> },
    },
    fallbackLng: 'en',
    // EN is always complete (code-first language). ES is auto-translated by
    // `tools/i18n_engine.py ship` — fallback to EN ensures missing ES keys
    // show English rather than raw key names.
    // Detection order: stored preference → browser language → HTML tag.
    // On login, AuthContext syncs user_metadata.preferred_language → localStorage
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'leo_language',
    },
    interpolation: { escapeValue: false },
    react: { useSuspense: false },
  });

export default i18n;

/** Convenience: change language and persist to localStorage. */
export function setAppLanguage(lang: 'en' | 'es') {
  i18n.changeLanguage(lang);
  try { localStorage.setItem('leo_language', lang); } catch { /* noop */ }
}
