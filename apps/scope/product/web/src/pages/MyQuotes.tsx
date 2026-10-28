/**
 * MyQuotes — Homeowner project hub.
 *
 * Shows all scopes the homeowner has been quoted for / paid for.
 * Auth is handled by the Login page — if no session, redirect there.
 *
 * Route: /app/my-projects (also aliased from /app/my-quotes for back-compat)
 */

import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { FileText, ChevronRight, Loader2, Settings } from 'lucide-react';
import { Button, StatusBadge } from '@scope/ui';
import { API_BASE, apiFetch } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { LanguageToggle } from '../components/LanguageToggle';
import { LeoLogo } from '../components/LeoLogo';
import { eur } from '../lib/utils';
import { PageLoading } from '../components/PageLoading';

// ---------------------------------------------------------------------------
// Scope card
// ---------------------------------------------------------------------------

interface HomeScopeRow {
  token: string;
  scope_data: { title?: string; location?: string };
  status: string;
  payment_status: string;
  amount_total_cents: number;
  milestones?: Array<{ title: string; status?: string }>;
  contractor_name: string;
  contractor_trade: string;
  contractor_photo_url: string;
  created_at: string;
}

function ScopeCard({ scope }: { scope: HomeScopeRow }) {
  const navigate = useNavigate();
  const status = scope.payment_status === 'paid' ? scope.status || 'paid' : scope.payment_status || 'sent';
  const totalLabel = eur(scope.amount_total_cents);

  const activeMilestone = scope.milestones?.find((m) => m.status === 'in_progress' || m.status === 'proof_submitted');

  const ctaLabel = (() => {
    if (status === 'sent') return 'View quote →';
    if (status === 'proof_submitted' || status === 'awaiting_final_approval') return 'Review proof →';
    if (status === 'complete') return 'View invoice →';
    return 'View project →';
  })();

  const handleCta = () => {
    if (status === 'sent') navigate(`/canvas/${scope.token}`);
    else navigate(`/project/${scope.token}`);
  };

  return (
    <div className="bg-white rounded-sm border border-border overflow-hidden">
      <div className="px-4 py-3.5">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-ink truncate">
              {scope.scope_data?.title || 'Project'}
            </p>
            {scope.contractor_name && (
              <p className="text-xs text-stone mt-0.5">
                {scope.contractor_name}{scope.contractor_trade ? ` · ${scope.contractor_trade}` : ''}
              </p>
            )}
          </div>
          <div className="shrink-0 text-right">
            <p className="text-sm font-bold text-ink">{totalLabel}</p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <StatusBadge status={status} />
          {activeMilestone && (
            <span className="text-xs text-stone truncate max-w-32">
              {activeMilestone.title}
            </span>
          )}
        </div>
      </div>

      {/* CTA row */}
      <div className="border-t border-border">
        <Button
          type="button"
          onClick={handleCta}
          className={`w-full flex items-center justify-center gap-1.5 py-2.5 text-xs font-semibold transition-colors ${
            status === 'sent'
              ? 'bg-ink text-cream hover:bg-stone'
              : status === 'proof_submitted'
              ? 'bg-terracotta text-white hover:bg-terracotta/90'
              : 'text-stone hover:text-ink'
          }`}
        >
          {ctaLabel}
          <ChevronRight size={12} />
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function MyQuotes() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { email, loading: authLoading } = useAuth();

  const { data: scopes = [], isLoading } = useQuery<HomeScopeRow[]>({
    queryKey: ['homeowner-scopes', email],
    queryFn: () => apiFetch(`${API_BASE}/v1/homeowner/quotes?email=${encodeURIComponent(email!)}`)
      .then((r) => r.json()),
    enabled: Boolean(email),
    staleTime: 30_000,
  });

  if (authLoading) return <PageLoading />;

  if (!email) {
    navigate('/', { replace: true });
    return null;
  }

  return (
    <div className="min-h-dvh bg-cream flex flex-col">
      <header className="shrink-0 sticky top-0 z-50 bg-cream/95 backdrop-blur-lg border-b border-border">
        <div className="flex items-center justify-between px-4 h-14 max-w-lg mx-auto">
          <LeoLogo variant="charcoal" height={16} />
          <h1 className="font-display text-base font-semibold text-ink">{t('myprojects_title')}</h1>
          <div className="flex items-center gap-2">
            <LanguageToggle variant="light" />
            <Button type="button" onClick={() => navigate('/settings')}>
              <Settings size={20} className="text-stone hover:text-ink transition-colors" />
            </Button>
          </div>
        </div>

      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4 max-w-lg mx-auto w-full">
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={24} className="text-terracotta/50 animate-spin" />
          </div>
        )}

        {!isLoading && scopes.length === 0 && (
          <div className="text-center py-16 px-4">
            <FileText size={32} className="text-border mx-auto mb-4" />
            <p className="text-base font-semibold text-ink mb-1">
              {t('myprojects_empty_state')}
            </p>
            <p className="text-sm text-stone leading-relaxed max-w-xs mx-auto">
              {t('myprojects_empty_desc')}
            </p>
          </div>
        )}

        {!isLoading && scopes.length > 0 && (
          <div className="space-y-3">
            {scopes.map((scope) => (
              <ScopeCard key={scope.token} scope={scope} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
