/**
 * Motion — movement recipes, named.
 *
 * Mirrors `packages/brand/src/brand/motion/quiet.py` for TypeScript /
 * framer-motion consumers. Today: one style, `quiet`.
 *
 * Python is the source of truth. Keep this file's numbers in sync with
 * `motion/quiet.py`. Promote to codegen if the catalog grows.
 */

export interface Durations {
  instant: number;
  fast: number;
  medium: number;
  slow: number;
  languid: number;
}

export interface Eases {
  outQuart: string;
  inOutCubic: string;
  springSubtle: string;
  linear: string;
}

export interface Spring {
  type: 'spring';
  stiffness: number;
  damping: number;
}

export interface Springs {
  subtle: Spring;
  default: Spring;
  bouncy: Spring;
  snappy: Spring;
}

export interface EntrancePair {
  initial: Record<string, number | string>;
  animate: Record<string, number | string>;
}

export interface Entrances {
  fade: EntrancePair;
  slideUp: EntrancePair;
  slideRight: EntrancePair;
  blurIn: EntrancePair;
  scaleIn: EntrancePair;
}

export interface Staggers {
  tight: number;
  default: number;
  generous: number;
}

export interface ScrollPhysics {
  parallaxSlow: number;
  parallaxDefault: number;
  parallaxFast: number;
  revealThreshold: number;
}

export interface MotionStyle {
  name: string;
  durations: Durations;
  eases: Eases;
  springs: Springs;
  entrances: Entrances;
  staggers: Staggers;
  scroll: ScrollPhysics;
}

export const QUIET: MotionStyle = {
  name: 'quiet',
  durations: { instant: 80, fast: 120, medium: 240, slow: 400, languid: 640 },
  eases: {
    outQuart: 'cubic-bezier(0.165, 0.84, 0.44, 1)',
    inOutCubic: 'cubic-bezier(0.645, 0.045, 0.355, 1)',
    springSubtle: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    linear: 'linear',
  },
  springs: {
    subtle: { type: 'spring', stiffness: 260, damping: 30 },
    default: { type: 'spring', stiffness: 180, damping: 22 },
    bouncy: { type: 'spring', stiffness: 120, damping: 10 },
    snappy: { type: 'spring', stiffness: 400, damping: 40 },
  },
  entrances: {
    fade: { initial: { opacity: 0 }, animate: { opacity: 1 } },
    slideUp: {
      initial: { opacity: 0, y: 8 },
      animate: { opacity: 1, y: 0 },
    },
    slideRight: {
      initial: { opacity: 0, x: -8 },
      animate: { opacity: 1, x: 0 },
    },
    blurIn: {
      initial: { opacity: 0, filter: 'blur(2px)' },
      animate: { opacity: 1, filter: 'blur(0px)' },
    },
    scaleIn: {
      initial: { opacity: 0, scale: 0.98 },
      animate: { opacity: 1, scale: 1 },
    },
  },
  staggers: { tight: 40, default: 80, generous: 160 },
  scroll: {
    parallaxSlow: 0.3,
    parallaxDefault: 0.5,
    parallaxFast: 0.8,
    revealThreshold: 0.15,
  },
};

export const MOTION_STYLES = { quiet: QUIET } as const;
export type MotionName = keyof typeof MOTION_STYLES;
