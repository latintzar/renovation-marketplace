/**
 * PageSkeleton — Animated loading skeleton for ProjectDetail.
 * Shows a charcoal header placeholder + content rows with pulse animations.
 */

export function PageSkeleton() {
  return (
    <div className="flex flex-col h-dvh overflow-hidden">
      <div className="shrink-0 px-4 pt-4 pb-5" style={{ background: 'var(--color-ink)' }}>
        <div className="flex justify-between mb-4">
          <div className="w-16 h-4 rounded bg-white/10 animate-pulse" />
          <div className="flex gap-3">
            <div className="w-5 h-5 rounded-full bg-white/10 animate-pulse" />
            <div className="w-5 h-5 rounded-full bg-white/10 animate-pulse" />
          </div>
        </div>
        <div className="w-36 h-3 rounded bg-white/10 animate-pulse mb-2" />
        <div className="w-32 h-8 rounded bg-white/15 animate-pulse mb-4" />
        <div className="flex gap-1">
          {[1, 2].map((i) => <div key={i} className="flex-1 h-1.5 rounded-full bg-white/20 animate-pulse" />)}
        </div>
      </div>
      <div className="flex-1 bg-white overflow-y-auto rounded-t-xl shadow-[0_-4px_20px_rgba(0,0,0,0.12)]">
        <div className="px-5 pt-6 pb-8 space-y-6">
          <div className="w-24 h-6 rounded-full bg-border/60 animate-pulse" />
          {[1, 2].map((i) => (
            <div key={i} className="flex items-start gap-3 py-4 border-b border-border">
              <div className="w-8 h-8 rounded-full bg-border/60 animate-pulse shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="flex justify-between">
                  <div className="w-28 h-4 rounded bg-border/60 animate-pulse" />
                  <div className="w-16 h-4 rounded bg-border/60 animate-pulse" />
                </div>
                <div className="w-40 h-3 rounded bg-border/40 animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
