/**
 * FluidGradient — React wrapper for the WebGL fluid-gradient runtime.
 *
 * The underlying runtime is a framework-agnostic IIFE shipped by
 * `@scope/brand` (canonical at `packages/brand/src/brand/fluid-gradient.js`,
 * mirrored to `apps/scope/product/public/fluid-gradient-v4.js` by
 * `python -m brand.build`). It exposes four FluidGradient classes
 * (V4–V7), a palette library, and a per-story palette map on `window`.
 *
 * This component dynamically loads the runtime if it isn't already on the
 * page, then instantiates the requested variant against a managed canvas
 * element. Cleanup on unmount is best-effort — the runtime currently does
 * not expose a `.destroy()` hook, so we null-out the canvas reference and
 * let the browser reclaim the GL context.
 *
 * Usage:
 *   // Default Brendan palette on an auto-sized canvas:
 *   <FluidGradient preset="brendan" />
 *
 *   // Story hero with a per-story palette + FPS cap:
 *   <FluidGradient
 *     paletteKey="renovation-disputes-what-to-do"
 *     variant="v7"
 *     fpsCap={18}
 *     aspectRatio={16 / 9}
 *   />
 *
 *   // Custom palette override:
 *   <FluidGradient
 *     preset="terraCharcoal"
 *     overrides={{ shapeOrbit: 1.4, shapeLobe: 0.9 }}
 *   />
 */

import { useEffect, useRef, type CSSProperties } from 'react';

type Variant = 'v4' | 'v5' | 'v6' | 'v7';
type PalettePreset = 'brendan' | 'v5Grass' | 'blueWhite' | 'terraCharcoal';

export interface FluidGradientProps {
  /** Which built-in palette to use. Ignored if `paletteKey` is set. */
  preset?: PalettePreset;
  /** Story-specific palette key (looked up in `window.LeoStoryPalettes`). */
  paletteKey?: string;
  /** Which shader variant class to instantiate. Defaults to `v4`. */
  variant?: Variant;
  /** FPS cap (1-60). Lower = better battery life for bg animations. */
  fpsCap?: number;
  /** Arbitrary overrides merged into the preset/paletteKey options. */
  overrides?: Record<string, unknown>;
  /** Absolute URL or public path for the runtime script. Defaults to '/fluid-gradient-v4.js'. */
  scriptSrc?: string;
  /** Skip mounting (escape hatch for pages that inject their own canvas). */
  skip?: boolean;
  /** Extra className applied to the wrapping <div>. */
  className?: string;
  /** Inline style merged into the wrapping <div>. */
  style?: CSSProperties;
  /** ARIA label; defaults to none (decorative canvas). */
  ariaLabel?: string;
}

const VARIANT_TO_GLOBAL: Record<Variant, string> = {
  v4: 'FluidGradientV4',
  v5: 'FluidGradientV5',
  v6: 'FluidGradientV6',
  v7: 'FluidGradientV7',
} as const;

let runtimeLoader: Promise<void> | null = null;

function loadRuntime(src: string): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('FluidGradient requires a browser environment'));
  }
  if ((window as any).FluidGradientV4) {
    return Promise.resolve();
  }
  if (runtimeLoader) {
    return runtimeLoader;
  }
  runtimeLoader = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[data-fluid-gradient-src="${src}"]`
    );
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error(`FluidGradient script failed: ${src}`)), { once: true });
      return;
    }
    const tag = document.createElement('script');
    tag.src = src;
    tag.async = true;
    tag.dataset.fluidGradientSrc = src;
    tag.addEventListener('load', () => resolve(), { once: true });
    tag.addEventListener('error', () => {
      runtimeLoader = null;
      reject(new Error(`FluidGradient script failed: ${src}`));
    }, { once: true });
    document.head.appendChild(tag);
  });
  return runtimeLoader;
}

export function FluidGradient({
  preset = 'brendan',
  paletteKey,
  variant = 'v4',
  fpsCap = 24,
  overrides,
  scriptSrc = '/fluid-gradient-v4.js',
  skip = false,
  className,
  style,
  ariaLabel,
}: FluidGradientProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const instanceRef = useRef<unknown>(null);

  useEffect(() => {
    if (skip || typeof window === 'undefined') return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    let cancelled = false;

    loadRuntime(scriptSrc).then(() => {
      if (cancelled) return;
      const globals = window as any;
      const CtorName = VARIANT_TO_GLOBAL[variant];
      const Ctor = globals[CtorName];
      if (!Ctor) {
        console.warn(`FluidGradient: ${CtorName} not available on window`);
        return;
      }

      let opts: Record<string, unknown> = { fpsCap, useStaticAudio: true };
      if (paletteKey && globals.LeoStoryPalettes?.[paletteKey]) {
        opts = { ...opts, ...globals.LeoStoryPalettes[paletteKey] };
      } else if (globals.LeoFluidGradientPalettes?.[preset]) {
        opts = { ...opts, ...globals.LeoFluidGradientPalettes[preset] };
      }
      if (overrides) {
        opts = { ...opts, ...overrides };
      }

      try {
        instanceRef.current = new Ctor(canvas, opts);
      } catch (err) {
        console.warn('FluidGradient: failed to instantiate', err);
      }
    }).catch((err) => {
      if (!cancelled) {
        console.warn('FluidGradient: runtime load failed', err);
      }
    });

    return () => {
      cancelled = true;
      instanceRef.current = null;
      if (canvas && (canvas as any)._fluidGradient) {
        try {
          delete (canvas as any)._fluidGradient;
        } catch {
          (canvas as any)._fluidGradient = null;
        }
      }
    };
  }, [variant, preset, paletteKey, fpsCap, overrides, scriptSrc, skip]);

  return (
    <div
      className={className}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        ...style,
      }}
    >
      <canvas
        ref={canvasRef}
        className="el-gradient__canvas"
        data-leo-fluid={variant}
        data-leo-fluid-fps={fpsCap}
        data-leo-fluid-skip="1"
        aria-label={ariaLabel}
        aria-hidden={ariaLabel ? undefined : true}
        style={{
          display: 'block',
          width: '100%',
          height: '100%',
        }}
      />
    </div>
  );
}

export default FluidGradient;
