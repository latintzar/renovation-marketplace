/**
 * JobCard — Single scope card in the contractor's job list.
 * Shows status badge, current milestone, total amount, and quick action buttons.
 */

import { Link, useNavigate } from 'react-router-dom';
import { ChevronRight, Camera, MessageCircle } from 'lucide-react';
import { Button, StatusBadge } from '@scope/ui';
import type { ScopeSummary } from '../../lib/api';
import { eur } from '../../lib/utils';
import type { Milestone as FullMilestone } from '../project/types';

type Milestone = Pick<FullMilestone, 'title' | 'status'>;

interface JobCardProps {
  scope: ScopeSummary;
  contractorId: string;
  onSubmitProof: (token: string, milestones: Milestone[]) => void;
  onCreateVariation: (token: string) => void;
}

export function JobCard({ scope, contractorId: _contractorId, onSubmitProof, onCreateVariation }: JobCardProps) {
  const navigate = useNavigate();
  const date = scope.created_at
    ? new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' }).format(new Date(scope.created_at))
    : '';
  const totalCents = scope.amount_total_cents ?? (scope.total != null ? scope.total * 100 : null);
  const milestones: Milestone[] = (scope as unknown as { milestones?: Milestone[] }).milestones ?? [];
  const currentMilestone = milestones.find((m) => m.status === 'in_progress' || m.status === 'pending' || !m.status);
  const currentIndex = milestones.findIndex((m) => m === currentMilestone);
  const isPaid = scope.payment_status === 'paid';

  return (
    <div className="rounded-sm border border-border bg-white overflow-hidden">
      <Link to={`/canvas/${scope.token}`} className="flex items-center px-4 py-3 gap-3 hover:bg-cream/50 transition-colors group">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink truncate group-hover:text-terracotta transition-colors">
            {scope.title}
          </p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <StatusBadge status={scope.payment_status === 'paid' ? (scope as unknown as { status?: string }).status || 'paid' : scope.payment_status || 'draft'} />
            {currentMilestone && (
              <span className="text-xs text-stone">
                Phase {currentIndex + 1} · {currentMilestone.title}
              </span>
            )}
            {date && <span className="text-[11px] text-muted">{date}</span>}
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2">
          {totalCents != null && totalCents > 0 && (
            <span className="text-sm font-bold text-ink">
              {eur(totalCents)}
            </span>
          )}
          <ChevronRight size={15} className="text-stone/40" />
        </div>
      </Link>

      {isPaid && (
        <div className="flex border-t border-border">
          <Button
            type="button"
            onClick={() => onSubmitProof(scope.token, milestones)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium text-ink hover:bg-terracotta/5 hover:text-terracotta transition-colors border-r border-border"
          >
            <Camera size={13} />
            Submit proof
          </Button>
          <Button
            type="button"
            onClick={() => onCreateVariation(scope.token)}
            className="flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium text-stone hover:bg-cream/60 hover:text-ink transition-colors border-r border-border"
          >
            + Change
          </Button>
          <Button
            type="button"
            onClick={() => navigate(`/job-chat/${scope.token}`)}
            className="flex items-center justify-center px-3 py-2.5 text-stone hover:text-ink transition-colors"
          >
            <MessageCircle size={14} />
          </Button>
        </div>
      )}
    </div>
  );
}
