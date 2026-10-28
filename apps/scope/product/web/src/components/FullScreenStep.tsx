/**
 * FullScreenStep — shared full-viewport container for single-question screens.
 *
 * Used by: LanguagePickerScreen, ImportPro phone collection, and any future
 * onboarding/data-collection step that needs a dedicated full-screen layout.
 *
 * Pattern matches LocationPickerModal: fixed full-viewport, cream bg,
 * safe-area-aware top/bottom padding, centred content card.
 */

import type { ReactNode } from 'react';

interface FullScreenStepProps {
  /** Icon rendered inside the tinted circle at the top */
  icon: ReactNode;
  title: string;
  subtitle?: string;
  children: ReactNode;
  /** Bottom CTA area — buttons, skip links, etc. */
  footer: ReactNode;
}

export function FullScreenStep({ icon, title, subtitle, children, footer }: FullScreenStepProps) {
  return (
    <div
      className="fixed inset-0 z-50 bg-cream flex flex-col"
      style={{ overscrollBehavior: 'none' }}
    >
      <div className="flex-1 flex items-center justify-center px-6 overflow-y-auto">
        <div className="w-full max-w-sm py-10">
          {/* Icon circle */}
          <div className="w-12 h-12 rounded-full bg-terracotta/10 flex items-center justify-center mb-5">
            {icon}
          </div>

          <h2 className="font-display text-[20px] font-semibold text-ink mb-1 leading-tight">
            {title}
          </h2>
          {subtitle && (
            <p className="text-sm text-stone mb-6">{subtitle}</p>
          )}

          {children}
        </div>
      </div>

      {/* Bottom CTA — safe area aware */}
      <div
        className="shrink-0 px-6 bg-cream border-t border-border"
        style={{ paddingBottom: 'calc(16px + env(safe-area-inset-bottom, 0px))', paddingTop: '16px' }}
      >
        <div className="max-w-sm mx-auto">
          {footer}
        </div>
      </div>
    </div>
  );
}
