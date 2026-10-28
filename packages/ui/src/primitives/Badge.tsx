import type { ReactNode } from 'react';

const COLOR_CLASSES = {
  terracotta: { bg: 'bg-terracotta-light', text: 'text-terracotta', border: 'border-terracotta/20', dot: 'bg-terracotta' },
  teal:       { bg: 'bg-teal-light',       text: 'text-teal',       border: 'border-teal/20',       dot: 'bg-teal' },
  ink:        { bg: 'bg-cream-dark',        text: 'text-ink',        border: 'border-border',        dot: 'bg-ink' },
  amber:      { bg: 'bg-amber/10',          text: 'text-amber',      border: 'border-amber/20',      dot: 'bg-amber' },
  green:      { bg: 'bg-green/10',          text: 'text-green',      border: 'border-green/20',      dot: 'bg-green' },
  red:        { bg: 'bg-red/10',            text: 'text-red',        border: 'border-red/20',        dot: 'bg-red' },
  muted:      { bg: 'bg-cream-dark',        text: 'text-muted',      border: 'border-border',        dot: 'bg-muted' },
} as const;

export type BadgeColor = keyof typeof COLOR_CLASSES;

export interface BadgeProps {
  variant?: 'pill' | 'outline' | 'status';
  color?: BadgeColor;
  /** Show a breathing dot (only for variant="status"). Defaults to true. */
  dot?: boolean;
  children: ReactNode;
  className?: string;
}

export function Badge({ variant = 'pill', color = 'ink', dot = true, children, className }: BadgeProps) {
  const c = COLOR_CLASSES[color];

  const base = 'inline-flex items-center gap-1.5 text-xs font-medium whitespace-nowrap';

  if (variant === 'status') {
    return (
      <span className={[base, 'rounded-full px-2.5 py-1', c.bg, c.text, className].filter(Boolean).join(' ')}>
        {dot && <span className={['w-1.5 h-1.5 rounded-full animate-pulse', c.dot].join(' ')} />}
        {children}
      </span>
    );
  }

  if (variant === 'outline') {
    return (
      <span className={[base, 'rounded-full px-2.5 py-1 border', c.border, c.text, className].filter(Boolean).join(' ')}>
        {children}
      </span>
    );
  }

  // pill (default)
  return (
    <span className={[base, 'rounded-full px-2.5 py-1', c.bg, c.text, className].filter(Boolean).join(' ')}>
      {children}
    </span>
  );
}
