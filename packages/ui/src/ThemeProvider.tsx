/**
 * ThemeProvider — lightweight React context that writes `data-theme` to the
 * document root and exposes `useTheme()` / `setTheme()`.
 *
 * The data-theme mechanism itself is owned by @scope/brand (tokens.py +
 * brand.build emit `[data-theme="<name>"]` blocks in both vars.css and
 * tokens.css). This provider just manages the attribute on <html> and
 * persists the chosen theme to localStorage.
 *
 * Usage:
 *   // wrap your root:
 *   <ThemeProvider defaultTheme="light">
 *     <App />
 *   </ThemeProvider>
 *
 *   // consume:
 *   const { theme, setTheme } = useTheme();
 *
 * SSR-safe: the useEffect that reads localStorage + sets the attribute is
 * gated on typeof window; during SSR no attribute is set and children
 * render with the default theme.
 */

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { BRAND_THEMES } from './brand';

export type ThemeName = 'light' | keyof typeof BRAND_THEMES | (string & {});

interface ThemeContextValue {
  theme: ThemeName;
  setTheme: (next: ThemeName) => void;
  /** All available theme names (light + every key in BRAND_THEMES). */
  availableThemes: ThemeName[];
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const STORAGE_KEY = 'leo-theme';

export interface ThemeProviderProps {
  children: ReactNode;
  /** Initial theme. Defaults to 'light' (which clears `data-theme`). */
  defaultTheme?: ThemeName;
  /** localStorage key. Defaults to 'leo-theme'. */
  storageKey?: string;
  /** Element to set `data-theme` on. Defaults to `document.documentElement`. */
  element?: 'html' | 'body';
}

export function ThemeProvider({
  children,
  defaultTheme = 'light',
  storageKey = STORAGE_KEY,
  element = 'html',
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<ThemeName>(defaultTheme);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const stored = window.localStorage.getItem(storageKey);
      if (stored) {
        setThemeState(stored as ThemeName);
      }
    } catch {}
  }, [storageKey]);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const target = element === 'body' ? document.body : document.documentElement;
    if (!target) return;
    if (theme === 'light') {
      target.removeAttribute('data-theme');
    } else {
      target.setAttribute('data-theme', theme);
    }
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch {}
  }, [theme, element, storageKey]);

  const setTheme = (next: ThemeName) => setThemeState(next);

  const availableThemes: ThemeName[] = ['light', ...Object.keys(BRAND_THEMES)];

  return (
    <ThemeContext.Provider value={{ theme, setTheme, availableThemes }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme() must be used inside a <ThemeProvider>');
  }
  return ctx;
}
