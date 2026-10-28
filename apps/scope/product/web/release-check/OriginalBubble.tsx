import { useMemo } from 'react';
import { marked } from 'marked';

marked.setOptions({ breaks: true, gfm: true });

/* ─── Leo response text ──────────────────────────────────
 * No bubble shell. Plain prose text, left-aligned.
 * Markdown is rendered inline (bold, italic, code, links).
 *
 * 'dark' variant: used on dark background (landing pages)
 * 'light' variant: used on light background (app, default)
 * ───────────────────────────────────────────────────── */
interface LeoBubbleProps {
  text: string;
  /** 'light' = stone text on cream (app, default), 'dark' = stone-ish on dark (landing) */
  variant?: 'light' | 'dark';
  className?: string;
}

export function OriginalLeoBubble({ text, variant = 'light', className }: LeoBubbleProps) {
  const html = useMemo(() => marked.parse(text) as string, [text]);

  return (
    <div
      className={[
        'leo-chat-leo',
        variant === 'dark' ? 'leo-chat-leo--dark' : '',
        className,
      ].filter(Boolean).join(' ')}
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/* ─── User message bubble ────────────────────────────────
 * Terra terracotta bubble, right-aligned.
 *
 * 'dark' variant: semi-transparent white glass (landing pages on dark bg)
 * 'light' variant: solid terra (app, default)
 * ───────────────────────────────────────────────────── */
interface UserBubbleProps {
  text: string;
  /** 'light' = solid terra (app, default), 'dark' = glass white (landing on dark bg) */
  variant?: 'light' | 'dark';
  className?: string;
}

export function UserBubble({ text, variant = 'light', className }: UserBubbleProps) {
  return (
    <div
      className={[
        'leo-chat-user',
        variant === 'dark' ? 'leo-chat-user--dark' : '',
        className,
      ].filter(Boolean).join(' ')}
    >
      {text}
    </div>
  );
}
