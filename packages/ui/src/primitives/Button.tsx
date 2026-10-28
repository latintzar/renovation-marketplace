import { forwardRef, type ComponentPropsWithRef, type ReactNode } from 'react';

const VARIANT_CLASSES = {
  primary:     'bg-ink text-cream font-semibold hover:bg-ink/90',
  secondary:   'border border-border text-stone bg-transparent font-medium hover:bg-cream-dark/40',
  terracotta:  'bg-terracotta text-cream font-semibold hover:bg-terracotta-dark',
  ghost:       'text-stone hover:text-ink hover:bg-cream-dark/30',
  danger:      'bg-red text-cream font-semibold hover:bg-red/90',
} as const;

const SIZE_CLASSES = {
  sm:   'h-8 px-3 text-sm gap-1.5',
  md:   'h-10 px-4 text-sm gap-2',
  lg:   'h-12 px-5 text-base gap-2',
  icon: 'w-11 h-11 p-0 justify-center',
} as const;

export type ButtonVariant = keyof typeof VARIANT_CLASSES;
export type ButtonSize = keyof typeof SIZE_CLASSES;

export interface ButtonProps extends Omit<ComponentPropsWithRef<'button'>, 'children'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
  icon?: ReactNode;
  iconRight?: ReactNode;
  children?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', fullWidth, loading, icon, iconRight, className, children, disabled, ...rest }, ref) => {
    const classes = [
      'inline-flex items-center rounded-[6px] transition-colors cursor-pointer select-none',
      VARIANT_CLASSES[variant],
      SIZE_CLASSES[size],
      fullWidth && 'w-full justify-center',
      (disabled || loading) && 'opacity-50 pointer-events-none',
      className,
    ].filter(Boolean).join(' ');

    return (
      <button ref={ref} className={classes} disabled={disabled || loading} {...rest}>
        {loading ? (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <>
            {icon && <span className="shrink-0">{icon}</span>}
            {children}
            {iconRight && <span className="shrink-0">{iconRight}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
