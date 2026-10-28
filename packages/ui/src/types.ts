/**
 * Leo Document types — the data shapes for each canvas template.
 * These types are the contract between the backend (Hermes tools) and
 * the Leo Documents rendered by BriefCanvas, ProfileCanvas, QuoteCanvas.
 *
 * Re-exported by apps/web/src/lib/api.ts for backwards compatibility.
 */

export interface BriefUpdate {
  title: string;
  description: string;
  location: string;
  urgency: string;
  materials_mentioned: string;
  measurements: string;
  budget_indication: string;
  status: 'needs_more_info' | 'workable' | 'solid' | string;
}

export interface ProfileProject {
  title: string;
  description?: string;
  images?: string[];
  url?: string;
  source?: string;
}

export interface ProfileReview {
  author?: string;
  rating?: number;
  date?: string;
  text?: string;
}

export interface ProfileSource {
  platform: string;
  platform_url?: string;
  platform_logo?: string;
  rating?: number;
  review_count?: number;
  reviews?: ProfileReview[];
  projects?: ProfileProject[];
  scraped_at?: string;
  badges?: string[];
}

export interface SocialMention {
  /** "Facebook group", "Forocoches", "Mediavida", "Reddit ES" */
  source_name: string;
  /** Thread permalink — always present */
  url: string;
  /** 250-char excerpt from the thread */
  snippet: string;
  /** Recommender's display name (if scraped) */
  author_name?: string;
  /** Link to recommender's profile (Facebook only) */
  author_url?: string;
  /** Profile picture URL (Facebook only) */
  author_avatar?: string;
  /** Post date if available */
  date?: string;
}

export interface ProfileUpdate {
  business_name: string;
  trade: string;
  location: string;
  service_area_km: string;
  services: string;
  bio: string;
  years_experience: string;
  languages: string;
  certifications: string;
  avatar_url?: string;
  website?: string;
  portfolio_images?: string[];
  sources?: ProfileSource[];
  review_summary?: string;
  verified?: boolean;
  trust_score?: number;
  nif_verified?: boolean;
  leo_jobs_completed?: number;
  leo_rating?: number;
  social_mentions?: SocialMention[];
}

export interface QuoteLineItem {
  description: string;
  amount: number;
  /** Rough duration shown on the milestone row — e.g. "2 días", "1 semana" */
  duration_label?: string;
}

/**
 * Provisional “if we discover X” pricing shown between milestones on the quote.
 * Shown to the client as a draft change-order so everyone knows possible extra cost.
 */
export interface QuoteContingencyDraft {
  /** -1 = before first phase; 0 = after first line item, etc. */
  after_phase_index: number;
  title: string;
  reason: string;
  line_items: QuoteLineItem[];
  market_range_low?: number;
  market_range_high?: number;
}

export interface QuoteUpdate {
  [key: string]: unknown;
  title: string;
  description: string;
  contractor_name: string;
  client_name: string;
  location: string;
  line_items: QuoteLineItem[];
  service_fee_percent: number;
  /**
   * Amount the contractor needs upfront to buy materials.
   * This is the ONLY money paid before work starts.
   * All other payments happen per milestone on completion.
   */
  materials_upfront?: number;
  /**
   * IVA rate for this job.
   * 10% = residential renovation (most common for tradespeople)
   * 21% = commercial, new builds, general services
   * If omitted, amounts are treated as including IVA.
   */
  iva_rate?: 10 | 21;
  /**
   * Legacy field — kept for backwards compat.
   * New scopes use milestones + materials_upfront instead.
   */
  payment_schedule?: { upfront_percent: number; completion_percent: number };
  terms: string[];
  status: 'draft' | 'ready' | 'sent' | 'approved' | 'complete';
  created_at: string;
  contingency_drafts?: QuoteContingencyDraft[];
}

export interface ChangeOrderLineItem {
  description: string;
  amount: number;
}

export interface ChangeOrderUpdate {
  title: string;
  reason: string;
  /** Items added to the scope */
  line_items: ChangeOrderLineItem[];
  /** Optional photo evidence from the tradesperson */
  photo_urls?: string[];
  /** Market range for the total — used to show fairness */
  market_range_low?: number;
  market_range_high?: number;
  /** Current status of the change order */
  status: 'pending' | 'approved' | 'rejected';
  /** Reference to the parent scope */
  scope_ref?: string;
  /** Tradesperson name */
  contractor_name?: string;
}

