/**
 * In-app flow switcher for the portfolio reel — a segmented control to jump
 * between the five flows. Each flow lives at its own route, so a click navigates
 * there with the ?reel=<flowId> param. Renders only in reel mode.
 */

import { reelFlowId, REEL_FLOWS } from './flag';
import { REEL_SCRIPTS } from './registry';
import type { ReelScript } from './engine';

export function ReelSwitcher() {
  const active = reelFlowId();
  if (!active) return null;

  const base = import.meta.env.BASE_URL;
  const flows = REEL_FLOWS.map((id) => REEL_SCRIPTS[id]).filter(Boolean) as ReelScript[];

  return (
    <div className="fixed top-3 left-1/2 z-[9500] -translate-x-1/2 px-2 w-full max-w-[760px] pointer-events-none">
      <div className="mx-auto flex w-fit max-w-full gap-1 overflow-x-auto rounded-full border border-ink/10 bg-cream/90 p-1 shadow-md backdrop-blur-sm pointer-events-auto [scrollbar-width:none]">
        {flows.map((f) => {
          const on = active === f.flowId;
          return (
            <button
              key={f.flowId}
              type="button"
              onClick={() => {
                window.location.href = `${base}${f.route.replace(/^\//, '')}?reel=${f.flowId}`;
              }}
              className={[
                'whitespace-nowrap rounded-full px-3 py-1.5 text-[12px] font-medium transition-colors',
                on ? 'bg-terracotta text-white' : 'text-ink/60 hover:text-ink hover:bg-white/70',
              ].join(' ')}
            >
              {f.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
