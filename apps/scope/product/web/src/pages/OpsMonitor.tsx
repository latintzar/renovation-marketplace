import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { RefreshCw, ExternalLink, Phone, ChevronDown, ChevronUp } from 'lucide-react';
import { fetchOps, type OpsData, type OpsJob, type OpsContractor } from '../lib/api';
import { Button } from '@scope/ui';

export default function OpsMonitor() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<OpsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    const result = await fetchOps(token);
    if (result.error) {
      setError(result.error);
    } else {
      setData(result);
      setLastRefresh(new Date());
    }
    setLoading(false);
  }, [token]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  const toggleJob = (id: string) => {
    setExpandedJobs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-dvh" style={{ background: 'var(--color-ink)' }}>
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-terra/30 border-t-terra rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm" style={{ color: 'var(--color-muted)' }}>Loading ops…</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-dvh" style={{ background: 'var(--color-ink)' }}>
        <div className="text-center px-6">
          <p className="text-lg font-display font-semibold text-white mb-2">Access denied</p>
          <p className="text-sm" style={{ color: 'var(--color-muted)' }}>{error || 'Invalid ops token.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh" style={{ background: '#0C0A09' }}>
      {/* Header */}
      <header className="sticky top-0 z-30 px-4 py-3 flex items-center justify-between" style={{ background: 'var(--color-ink)', borderBottom: '1px solid #292524' }}>
        <div>
          <h1 className="font-display text-[15px] font-semibold text-white">Contractor Ops</h1>
          <p className="text-[11px] mt-0.5" style={{ color: 'var(--color-muted)' }}>
            {lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString()}` : ''} · auto-refreshes
          </p>
        </div>
        <Button className="p-2" onClick={load}
          aria-label="Refresh"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} style={{ color: 'var(--color-muted)' }} /></Button>
      </header>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-px mx-4 mt-4 rounded-sm overflow-hidden" style={{ background: '#292524' }}>
        <StatCard label="Jobs" value={data.total_jobs} />
        <StatCard label="Outreach" value={data.total_outreach} />
        <StatCard label="Responses" value={data.total_responses} />
      </div>

      {/* Pipeline funnel */}
      <PipelineFunnel pipeline={data.pipeline} total={data.total_responses} />

      {/* Jobs list */}
      <div className="px-4 mt-4 pb-6 space-y-3">
        {data.jobs.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-sm" style={{ color: 'var(--color-muted)' }}>No jobs yet. Create one via Hermes.</p>
          </div>
        ) : (
          data.jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              expanded={expandedJobs.has(job.id)}
              onToggle={() => toggleJob(job.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}


function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="px-4 py-3 text-center" style={{ background: 'var(--color-ink)' }}>
      <p className="text-xl font-display font-bold text-white">{value}</p>
      <p className="text-[10px] uppercase tracking-wider mt-0.5" style={{ color: 'var(--color-muted)' }}>{label}</p>
    </div>
  );
}


const STAGE_ORDER = ['contacted', 'delivered', 'replied', 'voice_received', 'onboarded', 'matched', 'declined', 'ghosted'] as const;
const STAGE_COLORS: Record<string, string> = {
  discovered: 'var(--color-stone)',
  contacted: '#D97706',
  delivered: '#EAB308',
  replied: '#3B82F6',
  voice_received: '#14B8A6',
  onboarded: '#22C55E',
  matched: '#8B5CF6',
  declined: '#EF4444',
  ghosted: 'var(--color-muted)',
};


function PipelineFunnel({ pipeline, total }: { pipeline: Record<string, number>; total: number }) {
  if (total === 0) return null;

  return (
    <div className="mx-4 mt-3 p-3 rounded-sm" style={{ background: 'var(--color-ink)', border: '1px solid #292524' }}>
      <p className="text-[10px] uppercase tracking-wider mb-2.5" style={{ color: 'var(--color-muted)' }}>Sales Pipeline</p>
      <div className="space-y-1.5">
        {STAGE_ORDER.map((stage) => {
          const count = pipeline[stage] || 0;
          if (count === 0) return null;
          const pct = Math.round((count / total) * 100);
          const color = STAGE_COLORS[stage] || 'var(--color-stone)';
          return (
            <div key={stage} className="flex items-center gap-2">
              <span className="text-[10px] w-[90px] text-right truncate" style={{ color: 'var(--color-muted)' }}>
                {stage.replace(/_/g, ' ')}
              </span>
              <div className="flex-1 h-3 rounded-full overflow-hidden" style={{ background: '#292524' }}>
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${Math.max(pct, 3)}%`, background: color }}
                />
              </div>
              <span className="text-[10px] w-8 text-right font-semibold" style={{ color }}>
                {count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}


function JobCard({ job, expanded, onToggle }: { job: OpsJob; expanded: boolean; onToggle: () => void }) {
  const statusColors: Record<string, { bg: string; text: string }> = {
    collecting: { bg: 'rgba(217,119,6,.15)', text: '#D97706' },
    ready: { bg: 'rgba(17,94,89,.15)', text: '#14B8A6' },
    sent_to_homeowner: { bg: 'rgba(59,130,246,.15)', text: '#60A5FA' },
    closed: { bg: 'rgba(120,113,108,.15)', text: 'var(--color-muted)' },
  };
  const sc = statusColors[job.status] || statusColors.collecting;

  const ago = timeAgo(job.created_at);

  return (
    <div className="rounded-sm overflow-hidden" style={{ background: 'var(--color-ink)', border: '1px solid #292524' }}>
      <Button fullWidth className="text-left pt-3.5 pb-3" onClick={onToggle}><div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
                style={{ background: sc.bg, color: sc.text }}
              >
                {job.status.replace(/_/g, ' ')}
              </span>
              <span className="text-[11px]" style={{ color: 'var(--color-muted)' }}>{ago}</span>
            </div>
            <h3 className="font-display text-sm font-semibold text-white truncate">{job.title || 'Untitled job'}</h3>
            {job.location ? (
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-muted)' }}>{job.location}</p>
            ) : null}
          </div>
          {expanded ? (
            <ChevronUp className="w-4 h-4 shrink-0 mt-1" style={{ color: 'var(--color-muted)' }} />
          ) : (
            <ChevronDown className="w-4 h-4 shrink-0 mt-1" style={{ color: 'var(--color-muted)' }} />
          )}
        </div>

        {/* Metric row */}
        <div className="flex gap-4 mt-2.5">
          <Metric label="Contacted" value={job.outreach_count} />
          <Metric label="Responded" value={job.responded} warn={job.outreach_count > 0 && job.responded === 0} />
          <Metric label="Onboarded" value={job.onboarded} />
        </div></Button>

      {/* Expanded: contractor list */}
      {expanded ? (
        <div style={{ borderTop: '1px solid #292524' }}>
          {/* Homeowner info */}
          <div className="px-4 py-2.5 flex items-center justify-between" style={{ background: '#0C0A09' }}>
            <span className="text-[11px]" style={{ color: 'var(--color-muted)' }}>
              Homeowner: {job.homeowner_phone || 'unknown'}
            </span>
            <a
              href={job.inbox_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] flex items-center gap-1 hover:underline"
              style={{ color: '#14B8A6' }}
            >
              <ExternalLink className="w-3 h-3" />
              Inbox link
            </a>
          </div>

          {job.contractors.length === 0 ? (
            <div className="px-4 py-4 text-center">
              <p className="text-xs" style={{ color: 'var(--color-muted)' }}>No contractors contacted yet</p>
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: '#292524' }}>
              {job.contractors.map((c) => (
                <ContractorRow key={c.id} contractor={c} />
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}


function Metric({ label, value, warn = false }: { label: string; value: number; warn?: boolean }) {
  return (
    <div>
      <p
        className="text-sm font-semibold"
        style={{ color: warn ? '#EF4444' : '#F5F5F4' }}
      >
        {value}
      </p>
      <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--color-muted)' }}>{label}</p>
    </div>
  );
}


function ContractorRow({ contractor: c }: { contractor: OpsContractor }) {
  const sourceLabel: Record<string, string> = { houzz: 'Houzz', facebook: 'FB', direct: 'Direct', habitissimo: 'Hab' };
  const ago = timeAgo(c.created_at);
  const stageColor = STAGE_COLORS[c.outreach_stage] || 'var(--color-stone)';

  return (
    <div className="px-4 py-3">
      <div className="flex items-start justify-between mb-1.5">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-white truncate">{c.name}</span>
            <span className="text-[9px] px-1 py-px rounded" style={{ background: '#292524', color: 'var(--color-muted)' }}>
              {sourceLabel[c.source] || c.source}
            </span>
            <span
              className="text-[9px] font-semibold px-1.5 py-px rounded"
              style={{ background: `${stageColor}20`, color: stageColor }}
            >
              {c.outreach_stage?.replace(/_/g, ' ') || 'discovered'}
              {c.followup_count > 0 ? ` (+${c.followup_count} FU)` : ''}
            </span>
            {c.ai_rank ? (
              <span className="text-[9px] font-semibold px-1 py-px rounded" style={{ background: 'rgba(217,119,6,.15)', color: '#D97706' }}>
                #{c.ai_rank}
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            {c.phone ? (
              <span className="text-[11px] flex items-center gap-1" style={{ color: 'var(--color-muted)' }}>
                <Phone className="w-3 h-3" />
                {c.phone}
              </span>
            ) : null}
            <span className="text-[11px]" style={{ color: 'var(--color-stone)' }}>{ago}</span>
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex items-center gap-1.5 shrink-0">
          <StatusDot
            active={c.has_voice}
            label={c.has_voice ? 'Voice received' : 'No voice yet'}
            color={c.has_voice ? '#14B8A6' : 'var(--color-stone)'}
          />
          {c.houzz_url ? (
            <a
              href={c.houzz_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] px-1.5 py-0.5 rounded hover:bg-white/5"
              style={{ color: 'var(--color-muted)', border: '1px solid #292524' }}
            >
              Houzz
            </a>
          ) : null}
        </div>
      </div>

      {/* Reaction / commentary */}
      {c.reaction ? (
        <p className="text-xs mt-1.5 leading-relaxed" style={{ color: 'var(--color-muted)' }}>
          "{c.reaction}"
        </p>
      ) : null}
      {c.availability ? (
        <p className="text-[11px] mt-1" style={{ color: 'var(--color-muted)' }}>
          Available: {c.availability}
        </p>
      ) : null}
      {c.ai_commentary ? (
        <p className="text-[11px] mt-1 italic" style={{ color: '#14B8A6' }}>
          {c.ai_commentary}
        </p>
      ) : null}
    </div>
  );
}


function StatusDot({ active, label, color }: { active: boolean; label: string; color: string }) {
  return (
    <span
      className="w-2 h-2 rounded-full shrink-0"
      style={{ background: color, opacity: active ? 1 : 0.4 }}
      title={label}
    />
  );
}


function timeAgo(ts: string): string {
  if (!ts) return '';
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
