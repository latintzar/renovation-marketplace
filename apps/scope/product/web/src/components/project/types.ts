/** Shared types for the project detail components. */

export interface Milestone {
  title: string;
  description?: string;
  amount: number;
  amount_cents?: number;
  status?: string;
}

export interface VariationOrder {
  id: string;
  title: string;
  description?: string;
  photos: string[];
  amount_cents: number;
  reason?: string;
  status: 'pending' | 'approved' | 'declined' | 'paid';
  created_at: string;
}

export interface MilestoneUpdate {
  id: string;
  milestone_index: number;
  photos: string[];
  note?: string;
  status: string;
  created_at: string;
  released_at?: string;
}

export interface TimelineEvent {
  icon: string;
  label: string;
  date: string;
}
