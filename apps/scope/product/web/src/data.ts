/**
 * @internal Dev-only fixture data — used exclusively by store.tsx → ComponentLibrary.tsx.
 * Do NOT import from production pages.
 */

export type UserRole = 'tradesperson' | 'homeowner';
export type JobStatus = 'draft' | 'sent' | 'approved' | 'in_progress' | 'dispute' | 'complete';
export interface User { id: string; name: string; email: string; role: UserRole; avatar?: string; trade?: string; phone?: string; }
export interface CostItem { description: string; amount: number; }
export interface Variation { id: string; reason: string; amount: number; photo?: string; status: 'pending' | 'approved' | 'declined'; createdAt: string; }
export interface StatusStep { label: string; completed: boolean; date?: string; }
export interface Job { id: string; title: string; tradesperson: { id: string; name: string; trade: string }; homeowner: { id: string; name: string }; status: JobStatus; amount: number; paid: number; held: number; address: string; createdAt: string; scopeText?: string; photos: string[]; costBreakdown: CostItem[]; variations: Variation[]; statusSteps: StatusStep[]; }

export const USERS: Record<string, User> = {
  peter: {
    id: 'peter',
    name: 'Peter',
    email: 'operator@example.invalid',
    role: 'homeowner',
  },
  james: {
    id: 'james',
    name: 'James Mitchell',
    email: 'james@plumbing.co',
    role: 'tradesperson',
    trade: 'Plumber',
  },
};

export const JOBS: Job[] = [
  {
    id: 'job-1',
    title: 'Hot Water Cylinder Replacement',
    tradesperson: { id: 'james', name: 'James Mitchell', trade: 'Plumber' },
    homeowner: { id: 'peter', name: 'Peter' },
    status: 'dispute',
    amount: 1240,
    paid: 496,
    held: 744,
    address: '14 Calle Luna, Marbella',
    createdAt: '2026-03-10',
    scopeText:
      'Remove existing hot water cylinder and replace with Megaflo Eco 170i unvented cylinder. Includes: disconnection of existing system, removal and disposal of old cylinder, installation of new cylinder with all required safety valves (PRV, TV, expansion vessel), connection to existing hot and cold water feeds, testing and commissioning. Excludes: any electrical work, any modifications to existing pipework beyond immediate connections.',
    photos: [`${import.meta.env.BASE_URL}sample-attachment.png`, `${import.meta.env.BASE_URL}sample-attachment.png`],
    costBreakdown: [
      { description: 'Megaflo Eco 170i cylinder (supply)', amount: 580 },
      { description: 'Installation labour (1.5 days)', amount: 480 },
      { description: 'Fittings, valves & sundries', amount: 120 },
      { description: 'Disposal of old cylinder', amount: 60 },
    ],
    variations: [
      {
        id: 'var-1',
        reason:
          'Additional copper pipework replacement \u2014 corroded pipes discovered behind wall during installation',
        amount: 180,
        photo: `${import.meta.env.BASE_URL}sample-attachment.png`,
        status: 'pending',
        createdAt: '2026-03-18',
      },
    ],
    statusSteps: [
      { label: 'Scope sent', completed: true, date: '10 Mar' },
      { label: 'Approved by Peter', completed: true, date: '11 Mar' },
      { label: 'Work started', completed: true, date: '14 Mar' },
      { label: 'Variation submitted', completed: true, date: '18 Mar' },
      { label: 'Work complete', completed: false },
    ],
  },
  {
    id: 'job-2',
    title: 'Kitchen Tile Backsplash',
    tradesperson: { id: 'james', name: 'James Mitchell', trade: 'Tiler' },
    homeowner: { id: 'sarah', name: 'Sarah Chen' },
    status: 'in_progress',
    amount: 850,
    paid: 340,
    held: 510,
    address: '7 Av. Ricardo Soriano',
    createdAt: '2026-03-15',
    scopeText:
      'Supply and fit ceramic subway tiles to kitchen backsplash area (approx 4m\u00B2). Includes: surface preparation, waterproof membrane, tile adhesive, grouting, silicone seal to worktop junction.',
    photos: [],
    costBreakdown: [
      { description: 'Tiles (supply)', amount: 280 },
      { description: 'Labour (1 day)', amount: 380 },
      { description: 'Materials & adhesive', amount: 120 },
      { description: 'Grouting & sealant', amount: 70 },
    ],
    variations: [],
    statusSteps: [
      { label: 'Scope sent', completed: true, date: '15 Mar' },
      { label: 'Approved by Sarah', completed: true, date: '16 Mar' },
      { label: 'Work started', completed: true, date: '19 Mar' },
      { label: 'Work complete', completed: false },
    ],
  },
  {
    id: 'job-3',
    title: 'Bathroom Leak Repair',
    tradesperson: { id: 'james', name: 'James Mitchell', trade: 'Plumber' },
    homeowner: { id: 'peter', name: 'Peter' },
    status: 'complete',
    amount: 320,
    paid: 320,
    held: 0,
    address: '22 Paseo Mar\u00EDtimo, Estepona',
    createdAt: '2026-03-01',
    scopeText:
      'Investigate and repair leak from shower tray. Replace damaged silicone seal and re-bed shower tray. Test for 24 hours.',
    photos: [],
    costBreakdown: [
      { description: 'Labour (half day)', amount: 240 },
      { description: 'Materials', amount: 80 },
    ],
    variations: [],
    statusSteps: [
      { label: 'Scope sent', completed: true, date: '1 Mar' },
      { label: 'Approved by Peter', completed: true, date: '1 Mar' },
      { label: 'Work started', completed: true, date: '3 Mar' },
      { label: 'Work complete', completed: true, date: '3 Mar' },
      { label: 'Payment released', completed: true, date: '4 Mar' },
    ],
  },
];
