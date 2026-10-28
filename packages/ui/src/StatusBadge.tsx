export type ScopeStatus =
  | 'draft'
  | 'sent'
  | 'paid'
  | 'in_progress'
  | 'proof_submitted'
  | 'awaiting_final_approval'
  | 'complete'
  | 'cancelled'
  | 'disputed'
  | 'released';

interface StatusConfig {
  label: string;
  bg: string;
  text: string;
  dot: string;
}

const STATUS_MAP: Record<ScopeStatus, StatusConfig> = {
  draft: {
    label: 'Borrador',
    bg: 'rgba(87, 83, 78, 0.12)',
    text: 'var(--color-stone)',
    dot: 'var(--color-stone)',
  },
  sent: {
    label: 'Pendiente de pago',
    bg: 'rgba(217, 119, 6, 0.12)',
    text: '#92400E',
    dot: '#D97706',
  },
  paid: {
    label: 'Pagado · En custodia',
    bg: 'rgba(17, 94, 89, 0.12)',
    text: 'var(--color-teal)',
    dot: '#0D9488',
  },
  in_progress: {
    label: 'En progreso',
    bg: 'rgba(17, 94, 89, 0.12)',
    text: 'var(--color-teal)',
    dot: '#0D9488',
  },
  proof_submitted: {
    label: 'Pendiente de revisión',
    bg: 'rgba(218, 101, 77, 0.12)',
    text: '#9A3412',
    dot: 'var(--color-terracotta)',
  },
  awaiting_final_approval: {
    label: 'Aprobación final',
    bg: 'rgba(218, 101, 77, 0.12)',
    text: '#9A3412',
    dot: 'var(--color-terracotta)',
  },
  released: {
    label: 'Completado',
    bg: 'rgba(22, 163, 74, 0.12)',
    text: '#15803D',
    dot: '#16A34A',
  },
  complete: {
    label: 'Completado',
    bg: 'rgba(22, 163, 74, 0.12)',
    text: '#15803D',
    dot: '#16A34A',
  },
  cancelled: {
    label: 'Cancelado',
    bg: 'rgba(87, 83, 78, 0.12)',
    text: 'var(--color-stone)',
    dot: 'var(--color-stone)',
  },
  disputed: {
    label: 'En disputa',
    bg: 'rgba(220, 38, 38, 0.12)',
    text: '#DC2626',
    dot: '#DC2626',
  },
};

interface StatusBadgeProps {
  status: ScopeStatus | string;
  className?: string;
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = STATUS_MAP[status as ScopeStatus] ?? {
    label: status,
    bg: 'rgba(87, 83, 78, 0.12)',
    text: 'var(--color-stone)',
    dot: 'var(--color-stone)',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${className}`}
      style={{ backgroundColor: config.bg, color: config.text }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ backgroundColor: config.dot }}
      />
      {config.label}
    </span>
  );
}
