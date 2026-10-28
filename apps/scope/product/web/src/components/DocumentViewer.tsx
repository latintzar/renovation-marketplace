/**
 * DocumentViewer — Reusable inline HTML document display.
 *
 * Renders trusted server HTML in a Leo-branded document card.
 * Used in ConsentDrawer (agreement preview) and ProjectDetail (view agreement/invoice).
 *
 * NO react-pdf / PDF.js / iframes — we own the HTML, render it directly.
 * This is what Stripe and Airbnb do for their terms/receipts.
 */

import { useState, useEffect } from 'react';
import { FileText, Download, ExternalLink, Loader2 } from 'lucide-react';
import { API_BASE, apiFetch } from '../lib/api';

interface DocumentViewerProps {
  /** The API endpoint to fetch, e.g. `/v1/documents/{token}/agreement` */
  src: string;
  title: string;
  /** URL for the PDF download link. Defaults to src + ?format=pdf */
  downloadUrl?: string;
  className?: string;
  /** When true, removes the max-height cap so the viewer fills its container */
  fullHeight?: boolean;
}

export function DocumentViewer({ src, title, downloadUrl, className = '', fullHeight = false }: DocumentViewerProps) {
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const pdfUrl = downloadUrl ?? `${API_BASE}${src}?format=pdf`;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    setHtml(null);

    apiFetch(`${API_BASE}${src}?format=html`)
      .then((res: Response) => {
        if (!res.ok) throw new Error(`Failed to load document (${res.status})`);
        return res.text();
      })
      .then((text: string) => {
        if (cancelled) return;
        // Extract <body> content and inline <style> blocks for self-contained rendering
        const bodyMatch = text.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
        const styleMatches = [...text.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)];
        const styles = styleMatches.map((m) => `<style>${m[1]}</style>`).join('\n');
        setHtml(styles + (bodyMatch ? bodyMatch[1] : text));
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load document');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [src]);

  return (
    <div className={`bg-white rounded-sm shadow-sm overflow-hidden border border-border ${className}`}>
      {/* Title bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-cream/60">
        <div className="flex items-center gap-2">
          <FileText size={15} className="text-stone" />
          <span className="text-sm font-medium text-ink">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-stone hover:text-ink transition-colors py-1 px-2 rounded-sm hover:bg-border/50"
          >
            <Download size={12} />
            PDF
          </a>
          <a
            href={`${API_BASE}${src}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-stone hover:text-ink transition-colors py-1 px-2 rounded-sm hover:bg-border/50"
          >
            <ExternalLink size={12} />
          </a>
        </div>
      </div>

      {/* Document body */}
      <div className={fullHeight ? 'overflow-y-auto flex-1' : 'max-h-96 overflow-y-auto'}>
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={20} className="text-muted animate-spin" />
          </div>
        )}

        {error && (
          <div className="px-5 py-8 text-center">
            <p className="text-sm text-stone">{error}</p>
          </div>
        )}

        {html && !loading && (
          <div
            className="px-5 py-6 text-[13px] leading-relaxed text-ink [&_*]:max-w-full [&_table]:w-full [&_img]:max-w-full"
            style={{ fontFamily: "'Source Sans 3', system-ui, sans-serif", wordBreak: 'break-word' }}
            // We own this HTML — it's rendered by our own Jinja2 templates
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )}
      </div>
    </div>
  );
}
