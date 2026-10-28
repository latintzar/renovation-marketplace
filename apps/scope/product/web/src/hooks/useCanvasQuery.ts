/**
 * useCanvasQuery — React Query wrapper for fetchCanvas.
 *
 * Single source of truth for loading canvas data by token.
 * Provides shared cache, deduplication, and automatic retries
 * for Canvas, QuoteSent, FirstQuote, and OnboardPro.
 *
 * Usage:
 *   const { data, isLoading, error } = useCanvasQuery(token);
 */

import { useQuery } from '@tanstack/react-query';
import { fetchCanvas, type CanvasData } from '../lib/api';

export function canvasQueryKey(token: string | undefined) {
  return ['canvas', token] as const;
}

export function useCanvasQuery(token: string | undefined) {
  return useQuery<CanvasData, Error>({
    queryKey: canvasQueryKey(token),
    queryFn: () => fetchCanvas(token!),
    enabled: !!token,
    staleTime: 30_000,
    retry: 1,
  });
}
