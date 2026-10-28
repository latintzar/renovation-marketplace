interface Milestone {
  id: string;
  label: string;
  amount: string;
  /** 'done' = ticked circle, 'active' = empty terra circle, 'pending' = grey circle */
  status: 'done' | 'active' | 'pending';
  /** Optional sub-note under the label */
  note?: string;
}

interface MilestoneListProps {
  milestones: Milestone[];
  /** Optional gradient bg card wrapper — true on landing pages, false (plain white) in app */
  gradientBg?: boolean;
  /** src for gradient background image (webp). Only used when gradientBg=true */
  gradientSrc?: string;
}

/**
 * Escrow milestone list — "Your money doesn't move until you're happy."
 *
 * Three phase states:
 * - done    → solid ink tick circle (money released)
 * - active  → empty terra circle (in progress / approval pending)
 * - pending → greyed out (future phase)
 *
 * Context variants:
 * - Landing page: wrap in a gradient card (gradientBg=true, gradientSrc="/app/sample-attachment.png")
 * - App: plain white card (gradientBg=false, default)
 *
 * Both share the exact same milestone list DOM — only the outer card shell differs.
 *
 * React: import { MilestoneList } from '@scope/ui'
 * Static HTML: see H4 "Money protected" section in homeowners.html + professionals.html
 */
export function MilestoneList({ milestones, gradientBg = false, gradientSrc }: MilestoneListProps) {
  const list = (
    <div className="bg-white rounded-[8px_8px_0_0] mx-[-6px] shadow-[0_-4px_20px_rgba(0,0,0,.15)]">
      {milestones.map((m, i) => (
        <div
          key={m.id}
          className={[
            'flex items-center gap-2.5 px-3.5 py-2.5',
            i < milestones.length - 1 ? 'border-b border-black/[0.06]' : '',
            m.status === 'pending' ? 'opacity-40' : '',
          ].filter(Boolean).join(' ')}
        >
          {/* Status circle */}
          <div
            className="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center border-2"
            style={{
              background: '#fff',
              borderColor: m.status === 'done' ? 'var(--color-ink)' : m.status === 'active' ? 'var(--color-terracotta)' : 'var(--color-muted)',
            }}
          >
            {m.status === 'done' && (
              <svg viewBox="0 0 24 24" width={10} height={10} aria-hidden="true">
                <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </div>

          {/* Label + note */}
          <div className="flex-1 min-w-0">
            <div className="text-[12px] font-semibold text-ink">{m.label}</div>
            {m.note && (
              <div className="text-[11px] text-muted mt-1 leading-[1.45]">{m.note}</div>
            )}
          </div>

          {/* Amount */}
          <div className="text-[12px] font-semibold text-ink flex-shrink-0">{m.amount}</div>
        </div>
      ))}
    </div>
  );

  if (!gradientBg) {
    return (
      <div className="bg-white rounded-sm overflow-hidden border border-border">
        {list}
      </div>
    );
  }

  return (
    <div
      className="rounded-[var(--r,8px)] overflow-hidden relative"
      style={{ isolation: 'isolate', padding: '20px 20px 0', boxShadow: '0 8px 32px rgba(0,0,0,.25)' }}
    >
      {gradientSrc && (
        <img
          src={gradientSrc}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover"
          style={{ zIndex: -2 }}
        />
      )}
      {/* Noise overlay */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          zIndex: -1,
          mixBlendMode: 'overlay',
          opacity: 0.5,
          backgroundImage: "none",
          backgroundSize: '128px',
        }}
      />
      {list}
    </div>
  );
}
