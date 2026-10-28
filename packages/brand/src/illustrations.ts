/**
 * Illustrations — theme-aware black-pencil generator (client shim).
 *
 * The real work happens in Python (`packages/brand/src/brand/illustrations/`).
 * Browser + Node clients should not hold Anthropic / LiteLLM API keys, so
 * this shim posts the request to a backend endpoint that proxies to
 * `brand.illustrations.generate`.
 *
 * Backend route contract (implement per-app):
 *   POST /api/brand/illustrate
 *     body: { theme: string, scene: string, lane: "svg" | "raster", width?: number, height?: number }
 *     responds: { format: "svg", svg: string } | { format: "png", pngBase64: string }
 *
 * Hosting apps are responsible for wiring that route to the Python surface
 * (see `apps/scope/product/backend/` for the expected pattern). This file stays a
 * thin shim so theme/lane plumbing lives in one place.
 */

export type IllustrationLane = 'svg' | 'raster';

export interface IllustrationRequest {
  theme: string;
  scene: string;
  lane?: IllustrationLane;
  width?: number;
  height?: number;
  endpoint?: string;
}

export interface SvgResult {
  format: 'svg';
  svg: string;
}

export interface RasterResult {
  format: 'png';
  pngBase64: string;
}

export type IllustrationResult = SvgResult | RasterResult;

const DEFAULT_ENDPOINT = '/api/brand/illustrate';

export async function generateIllustration(
  req: IllustrationRequest,
): Promise<IllustrationResult> {
  const endpoint = req.endpoint ?? DEFAULT_ENDPOINT;
  const { theme, scene } = req;
  const lane: IllustrationLane = req.lane ?? 'svg';

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ theme, scene, lane, width: req.width, height: req.height }),
  });

  if (!res.ok) {
    throw new Error(
      `brand.illustrations: ${endpoint} returned ${res.status} ${res.statusText}`,
    );
  }
  const data = (await res.json()) as IllustrationResult;
  if (data.format !== 'svg' && data.format !== 'png') {
    throw new Error(`brand.illustrations: unexpected response shape ${JSON.stringify(data)}`);
  }
  return data;
}
