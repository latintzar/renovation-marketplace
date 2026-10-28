let _counter = 0;

export const uid = () => `${++_counter}-${Date.now().toString(36)}`;

export const clsx = (...args: (string | false | null | undefined)[]) =>
  args.filter(Boolean).join(' ');

/** Format cents as EUR with 0 decimals (e.g. 15000 → "€150"). */
export const eur = (cents: number) =>
  new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(cents / 100);

/** Format a euro amount (not cents) as EUR with 0 decimals (e.g. 150 → "€150"). */
export const eurFromEuros = (euros: number) =>
  new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(euros);

/**
 * Canonical quote financial computation.
 * All amounts are in euros (not cents).
 *
 * Formula: labour (milestones sum) + materials upfront + Leo fee (% of labour) + IVA (% of work+fee)
 */
export function computeQuoteTotals(scope: {
  line_items?: { amount?: number }[];
  materials_upfront?: number;
  service_fee_percent?: number;
  iva_rate?: number;
}) {
  const labour = (scope.line_items ?? []).reduce((s, li) => s + (li.amount || 0), 0);
  const materials = scope.materials_upfront ?? 0;
  const fee = labour * ((scope.service_fee_percent || 0) / 100);
  const iva = scope.iva_rate ? ((labour + materials) * scope.iva_rate) / 100 : 0;
  const total = labour + materials + fee + iva;
  return { labour, materials, fee, iva, total };
}

/** Returns true when sandbox mode is active (reads the shared localStorage key). */
export function isSandbox(): boolean {
  try {
    return localStorage.getItem('leo_sandbox_mode') === 'true';
  } catch {
    return false;
  }
}

/** Read the `leo_auth` session object, returning `{}` on missing/invalid JSON. */
export function getLeoAuth(): Record<string, unknown> {
  try { return JSON.parse(sessionStorage.getItem('leo_auth') || '{}'); }
  catch { return {}; }
}

/** Shallow-merge a patch into the `leo_auth` session object. */
export function mergeLeoAuth(patch: Record<string, unknown>): void {
  sessionStorage.setItem('leo_auth', JSON.stringify({ ...getLeoAuth(), ...patch }));
}

/** Read a File (image) as a base64 data string (no data: prefix). */
export const fileToBase64 = (file: File): Promise<{ media_type: string; data: string }> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const commaIdx = result.indexOf(',');
      resolve({
        media_type: file.type || 'image/jpeg',
        data: commaIdx >= 0 ? result.slice(commaIdx + 1) : result,
      });
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
