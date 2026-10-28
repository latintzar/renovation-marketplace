/**
 * Flow 5 — "Import a profile": a tradesperson pastes their existing directory
 * link and Leo pulls their real profile (reviews, ratings, history) in seconds.
 *
 * Drives the real OnboardPro page (/onboard/pro). The data below is REAL public
 * information extracted from https://www.habitissimo.es/pro/todobarro (rating,
 * review count, member-since, description, a real review quote, service
 * categories) — no fabrication. Gallery/avatar image URLs are intentionally
 * omitted so the reel makes zero external requests.
 *
 * importProfile() (lib/api.ts) replays `sse` below when reel mode is on.
 */

import type { ReelScript } from '../engine';
import type { ProfileUpdate, ProfileImportEvent } from '../../lib/api';

const todoBarro: ProfileUpdate = {
  business_name: 'TodoBarro',
  trade: 'Albañilería · Restauración de suelos de barro y piedra',
  location: 'Málaga · servicio en toda España',
  service_area_km: '',
  services:
    'Restauración de suelos rústicos de barro y piedra\nLimpieza y tratamientos de protección\nFabricación artesanal de baldosas de barro cocido\nRehabilitación de pavimentos cerámicos',
  bio:
    'Empresa especializada en limpieza, tratamientos de protección, restauración y mantenimiento de suelos rústicos de barro y piedra. Equipo multidisciplinar de artesanos, arquitectos e interioristas apasionados por el estilo rústico moderno. Operamos en todo el territorio nacional.',
  years_experience: '15',
  languages: 'Español',
  certifications: '',
  website: 'https://www.habitissimo.es/pro/todobarro',
  review_summary: 'En Habitissimo desde 2009 · 11 trabajos · 3,8★ (4 opiniones)',
  sources: [
    {
      platform: 'Habitissimo',
      platform_url: 'https://www.habitissimo.es/pro/todobarro',
      // BASE_URL-relative so it resolves same-origin in dev and the vendored build.
      platform_logo: `${import.meta.env.BASE_URL}reel/logo-habitissimo.png`,
      rating: 3.8,
      review_count: 4,
      reviews: [
        {
          text: 'Otros me recomendaban cambiar el suelo. Conocí a TodoBarro y me lo dejaron mejor que al principio.',
        },
      ],
    },
  ],
};

const sse: ProfileImportEvent[] = [
  { type: 'status', message: 'Detected Habitissimo profile', platform: 'habitissimo' },
  { type: 'progress', step: 'Fetching profile…', percent: 20 },
  { type: 'progress', step: 'Reading reviews & ratings…', percent: 45 },
  { type: 'progress', step: 'Pulling past work…', percent: 70 },
  { type: 'progress', step: 'Building your Leo profile…', percent: 92 },
  { type: 'result', profile: todoBarro as unknown as Record<string, unknown> },
];

export const importProfileScript: ReelScript = {
  flowId: 'import-profile',
  label: 'Import a profile',
  route: '/onboard/pro',
  auth: null,
  sse,
};
