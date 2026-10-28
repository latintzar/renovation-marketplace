/**
 * Per-beat caption shown during a reel — a fixed strip that narrates what the
 * viewer is looking at ("AI drafts the scope live"). Renders only in reel mode.
 */

import { isReel } from './flag';
import { useReelUi } from './engine';

export function CaptionStrip() {
  const caption = useReelUi((s) => s.caption);
  if (!isReel() || !caption) return null;

  return (
    <div className="fixed bottom-5 left-1/2 z-[9500] -translate-x-1/2 px-4 pointer-events-none w-full max-w-[640px]">
      <div className="mx-auto w-fit max-w-full rounded-full bg-ink/90 px-4 py-2 text-center text-[13px] font-medium leading-snug text-cream shadow-lg backdrop-blur-sm">
        {caption}
      </div>
    </div>
  );
}
