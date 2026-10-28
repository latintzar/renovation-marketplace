import { forwardRef, type ComponentPropsWithRef, type ReactNode } from 'react';

const BASE_INPUT = 'w-full px-4 py-3 rounded-sm border border-border bg-white text-ink placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-terracotta focus:border-terracotta transition-colors';

/* ── Input ──────────────────────────────────────────────────────────────── */

export interface InputProps extends Omit<ComponentPropsWithRef<'input'>, 'size'> {
  label?: string;
  error?: string;
  icon?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, className, id, ...rest }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-ink">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={[BASE_INPUT, icon && 'pl-10', error && 'border-red focus:ring-red', className].filter(Boolean).join(' ')}
            {...rest}
          />
        </div>
        {error && <p className="text-xs text-red">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';

/* ── Textarea ───────────────────────────────────────────────────────────── */

export interface TextareaProps extends ComponentPropsWithRef<'textarea'> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className, id, ...rest }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-ink">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          className={[BASE_INPUT, 'min-h-[80px] resize-none', error && 'border-red focus:ring-red', className].filter(Boolean).join(' ')}
          {...rest}
        />
        {error && <p className="text-xs text-red">{error}</p>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
