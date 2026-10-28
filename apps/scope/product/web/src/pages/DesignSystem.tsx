/**
 * /design — The single visual page for Leo's design system.
 *
 * Tabs:
 *   • Tokens      — colours, radii, shadows, fonts (driven by @scope/brand)
 *   • Components  — the full Leo UI component gallery (ComponentLibrary)
 *   • Gradients   — WebGL fluid gradients (all four variants + story palettes)
 *   • Themes      — ThemeProvider demo (light / dark swap)
 *
 * Anything that's "branded" must be visible here. New apps that import
 * `@scope/brand` + `@scope/ui` can recreate this same page in one line:
 *
 *     export { default as DesignSystem } from '@scope/ui/DesignSystem';
 *
 * — except we haven't extracted the shell yet (deferred to a later wave);
 * for now this page lives in `apps/scope/product/web/src/pages/`.
 */

import { useState } from 'react';
import {
  BRAND_COLORS,
  BRAND_RADIUS,
  BRAND_SHADOWS,
  BRAND_FONTS,
  BRAND_THEMES,
  FluidGradient,
  ThemeProvider,
  useTheme,
  Button,
  Surface,
  Badge,
} from '@scope/ui';
import ComponentLibrary from './ComponentLibrary';

type Tab = 'tokens' | 'components' | 'gradients' | 'themes';

const TABS: { id: Tab; label: string; blurb: string }[] = [
  { id: 'tokens',     label: 'Tokens',     blurb: 'Colours, radii, shadows, fonts — straight from @scope/brand.' },
  { id: 'components', label: 'Components', blurb: 'Primitives + opinionated compounds from @scope/ui.' },
  { id: 'gradients',  label: 'Gradients',  blurb: 'Fluid WebGL gradients — v4 Brendan / v5 Grass / v6 BlueWhite / v7 Terra.' },
  { id: 'themes',     label: 'Themes',     blurb: 'Multi-theming via data-theme — flip light / dark without a rebuild.' },
];

export default function DesignSystem() {
  const [tab, setTab] = useState<Tab>('tokens');

  const activeMeta = TABS.find((t) => t.id === tab)!;

  return (
    <div className="min-h-dvh bg-cream text-ink font-sans" style={{ maxWidth: '1400px', margin: '0 auto' }}>
      <header className="px-4 sm:px-8 pt-8 pb-4 border-b border-border">
        <h1 className="font-display text-3xl font-bold tracking-tight">Leo Design System</h1>
        <p className="text-sm text-muted mt-1 max-w-2xl">
          One page to see every token, primitive, compound, and gradient the Leo family
          of apps inherits from <code className="font-mono text-[12px]">@scope/brand</code> and{' '}
          <code className="font-mono text-[12px]">@scope/ui</code>. Edit once, propagates everywhere.
        </p>

        <nav role="tablist" className="mt-6 flex flex-wrap gap-1.5">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className="px-4 py-2 rounded-sm font-medium text-sm transition-all"
              style={{
                background: tab === t.id ? 'var(--ink)' : 'var(--card)',
                color:      tab === t.id ? 'var(--cream)' : 'var(--ink)',
                border:     `1px solid ${tab === t.id ? 'var(--ink)' : 'var(--border)'}`,
              }}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <p className="text-xs text-muted mt-3">{activeMeta.blurb}</p>
      </header>

      <main className="px-4 sm:px-8 py-6">
        {tab === 'tokens'     && <TokensTab />}
        {tab === 'components' && <ComponentLibrary />}
        {tab === 'gradients'  && <GradientsTab />}
        {tab === 'themes'     && <ThemesTab />}
      </main>

      <footer className="px-4 sm:px-8 py-8 border-t border-border text-xs text-muted">
        <p>
          Canonical source: <code className="font-mono">packages/brand/src/brand/tokens.py</code>.
          Rebuild: <code className="font-mono">python3 -m brand.build</code>.
          Full static brand book (legacy, still live): <a href="/design/brand-book.html" className="underline hover:text-ink">/design/brand-book.html</a>.
        </p>
      </footer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Tokens tab
// ────────────────────────────────────────────────────────────────────────────

function TokensTab() {
  return (
    <div className="flex flex-col gap-10">
      <Section title="Colours">
        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
          {Object.entries(BRAND_COLORS).map(([name, hex]) => (
            <Swatch key={name} name={name} hex={hex} />
          ))}
        </div>
      </Section>

      <Section title="Radii">
        <div className="flex flex-wrap gap-4">
          {Object.entries(BRAND_RADIUS).map(([name, value]) => (
            <div key={name} className="flex flex-col items-center gap-1">
              <div
                className="bg-terracotta"
                style={{ width: 96, height: 96, borderRadius: value }}
              />
              <code className="font-mono text-[11px] text-ink">{name}</code>
              <code className="font-mono text-[10px] text-muted">{value}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Shadows">
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
          {Object.entries(BRAND_SHADOWS).map(([name, value]) => (
            <div
              key={name}
              className="bg-card rounded-sm p-4"
              style={{ boxShadow: value as string, border: '1px solid var(--border)' }}
            >
              <code className="font-mono text-[11px] text-ink block mb-1">{name}</code>
              <code className="font-mono text-[10px] text-muted break-all">{value}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Fonts">
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {Object.entries(BRAND_FONTS).map(([name, stack]) => (
            <Surface key={name} variant="flat" className="p-4">
              <code className="font-mono text-[11px] text-muted uppercase tracking-wide block mb-2">{name}</code>
              <p style={{ fontFamily: stack, fontSize: '1.5rem', color: 'var(--ink)' }}>
                The quick brown fox jumps over the lazy dog
              </p>
              <code className="font-mono text-[10px] text-muted break-all block mt-2">{stack}</code>
            </Surface>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Swatch({ name, hex }: { name: string; hex: string }) {
  return (
    <div className="rounded-sm overflow-hidden border border-border bg-card text-ink">
      <div style={{ background: hex, height: 64 }} />
      <div className="px-2 py-1.5 text-[11px]">
        <div className="font-semibold text-ink">{name}</div>
        <code className="font-mono text-[10px] text-stone">{hex}</code>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Gradients tab
// ────────────────────────────────────────────────────────────────────────────

type GradientVariant = 'v4' | 'v5' | 'v6' | 'v7';
type GradientPreset = 'brendan' | 'v5Grass' | 'blueWhite' | 'terraCharcoal';

const GRADIENT_SHOWCASES: { variant: GradientVariant; preset: GradientPreset; label: string; note: string }[] = [
  { variant: 'v4', preset: 'brendan',       label: 'v4 Brendan',        note: 'Terracotta + teal + cream. Default hero palette.' },
  { variant: 'v5', preset: 'v5Grass',       label: 'v5 Grass',          note: 'Brendan + grass lobe. Homeowner hero.' },
  { variant: 'v6', preset: 'blueWhite',     label: 'v6 Blue+White',     note: 'Soft cool palette. Secondary hero.' },
  { variant: 'v7', preset: 'terraCharcoal', label: 'v7 Terra+Charcoal', note: 'Terra-first + charcoal trim. Tradesperson hero.' },
];

function GradientsTab() {
  return (
    <div className="flex flex-col gap-8">
      <div className="text-sm text-stone">
        All four variants run off the same canonical shader at{' '}
        <code className="font-mono text-[12px]">packages/brand/src/brand/fluid-gradient.js</code>.
        They&apos;re rendered here via <code className="font-mono text-[12px]">&lt;FluidGradient&gt;</code>{' '}
        from <code className="font-mono text-[12px]">@scope/ui</code>.
      </div>
      <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))' }}>
        {GRADIENT_SHOWCASES.map((g) => (
          <div key={g.variant} className="flex flex-col gap-2">
            <div style={{ aspectRatio: '16 / 9', borderRadius: 'var(--r-md)', overflow: 'hidden' }}>
              <FluidGradient variant={g.variant} preset={g.preset} fpsCap={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <strong className="font-sans text-sm text-ink">{g.label}</strong>
                <Badge color="muted" variant="outline">{g.variant}</Badge>
              </div>
              <p className="text-xs text-muted mt-0.5">{g.note}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Themes tab
// ────────────────────────────────────────────────────────────────────────────

function ThemesTab() {
  return (
    <ThemeProvider defaultTheme="light" element="body">
      <ThemesDemo />
    </ThemeProvider>
  );
}

function ThemesDemo() {
  const { theme, setTheme, availableThemes } = useTheme();
  return (
    <div className="flex flex-col gap-6">
      <div className="text-sm text-stone max-w-3xl">
        <p className="mb-2">
          Themes are declared in <code className="font-mono text-[12px]">packages/brand/src/brand/tokens.py</code>{' '}
          (the <code className="font-mono text-[12px]">THEMES</code> dict). Each theme emits a{' '}
          <code className="font-mono text-[12px]">[data-theme=&quot;&lt;name&gt;&quot;]</code> CSS block
          in both <code className="font-mono text-[12px]">vars.css</code> and{' '}
          <code className="font-mono text-[12px]">tokens.css</code>.
        </p>
        <p>
          Flip themes by setting <code className="font-mono text-[12px]">data-theme</code> on any
          element (we apply it to <code className="font-mono text-[12px]">&lt;body&gt;</code> in this
          demo so only this tab changes). Zero JS, zero rebuild. Adding a new theme is a one-file edit.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {availableThemes.map((t) => (
          <Button
            key={t as string}
            variant={t === theme ? 'primary' : 'secondary'}
            onClick={() => setTheme(t)}
          >
            {t === 'light' ? 'light (no data-theme)' : `data-theme="${t as string}"`}
          </Button>
        ))}
      </div>

      <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))' }}>
        {['ink', 'cream', 'card', 'border', 'muted', 'stone'].map((key) => (
          <Surface key={key} variant="flat" className="p-4" style={{ background: 'var(--card)' }}>
            <div
              className="mb-2 rounded-sm"
              style={{
                background: `var(--${key})`,
                height: 40,
                border: '1px solid var(--border)',
              }}
            />
            <code className="font-mono text-[11px] text-ink block">--{key}</code>
            <span className="text-[10px] text-muted">current theme: <strong>{theme as string}</strong></span>
          </Surface>
        ))}
      </div>

      <div className="text-xs text-muted max-w-3xl">
        Currently shipped themes: {Object.keys(BRAND_THEMES).join(', ') || '(none besides default)'} — add
        more by editing <code className="font-mono text-[12px]">tokens.THEMES</code> and running{' '}
        <code className="font-mono text-[12px]">python3 -m brand.build</code>.
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Shared
// ────────────────────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-display text-xl text-ink">{title}</h2>
      {children}
    </section>
  );
}
