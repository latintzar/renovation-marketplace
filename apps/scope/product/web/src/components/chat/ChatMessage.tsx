import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Message } from '../../types';
import { clsx } from '../../lib/utils';
import { VoiceNoteBubble } from '@scope/ui';
import { Button, LeoBubble, UserBubble } from '@scope/ui';
import { X, Copy, Check } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
}

const PhotoThumbnails = ({ urls }: { urls: string[] }) => {
  const [viewUrl, setViewUrl] = useState<string | null>(null);

  return (
    <>
      <div className={clsx('flex gap-1.5 mt-1.5 flex-wrap', urls.length === 1 && 'max-w-[200px]')}>
        {urls.map((url, i) => (
          <Button
            key={i}
            type="button"
            onClick={() => setViewUrl(url)}
            className="rounded-xs overflow-hidden focus:outline-none focus:ring-2 focus:ring-terracotta"
          >
            <img
              src={url}
              alt={`Attachment ${i + 1}`}
              className={clsx(
                'object-cover',
                urls.length === 1 ? 'w-full max-h-[200px] rounded-xs' : 'w-16 h-16',
              )}
            />
          </Button>
        ))}
      </div>

      {viewUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
          onClick={() => setViewUrl(null)}
          role="dialog"
          aria-modal="true"
          aria-label="View photo"
        >
          <Button
            type="button"
            onClick={() => setViewUrl(null)}
            className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/20 text-white flex items-center justify-center hover:bg-white/30 transition-colors"
            style={{ top: 'max(1rem, env(safe-area-inset-top, 1rem))' }}
            aria-label="Close"
          >
            <X size={22} />
          </Button>
          <img
            src={viewUrl}
            alt="Full size"
            className="max-w-[90vw] max-h-[85vh] object-contain rounded-sm"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
};

/** Internal signal messages — never show in the UI */
const SIGNAL_PATTERNS = /^\[(CONFIRMED_BRIEF|CONFIRMED_PROFILE|DRAWER_ACTION:[^\]]+)\]$/;

const CopyBlock = ({ text }: { text: string }) => {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for browsers without clipboard API
      const el = document.createElement('textarea');
      el.value = text;
      el.style.position = 'fixed';
      el.style.opacity = '0';
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="anim-fade-up w-full max-w-[min(100%,640px)] rounded-sm border border-border bg-cream-dark/60 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border bg-cream-dark/40">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-stone/70">{t('copy_to_send')}</span>
        <Button
          type="button"
          onClick={handleCopy}
          aria-label={copied ? t('copied') : t('copy_text')}
          className={clsx(
            'flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-xs transition-all duration-150',
            copied
              ? 'bg-teal/15 text-teal-dark'
              : 'bg-transparent text-stone hover:bg-terracotta/10 hover:text-terracotta',
          )}
        >
          {copied ? <Check size={13} strokeWidth={2.5} /> : <Copy size={13} strokeWidth={2} />}
          {copied ? t('copied') : t('copy')}
        </Button>
      </div>
      <pre className="px-3 py-2.5 text-sm text-ink leading-relaxed whitespace-pre-wrap font-sans m-0 select-all">
        {text}
      </pre>
    </div>
  );
};

const ChatMessage = ({ message }: ChatMessageProps) => {
  const { role, variant, content, transcription, voiceDuration, waveform, options, source, photoUrls, hidden } = message;

  // Hidden messages (silent triggers, language-switch signals) are never rendered
  if (hidden) return null;

  // Hide internal signal messages from the chat history
  if (role === 'user' && variant === 'text' && SIGNAL_PATTERNS.test(content.trim())) {
    return null;
  }

  if (variant === 'trace') {
    return (
      <div className="py-0.5">
        <span className="text-xs text-muted/70 italic">{content}</span>
      </div>
    );
  }

  if (variant === 'research') {
    return (
      <div className="anim-fade-up border-l-2 border-teal bg-teal-light/80 text-stone text-sm px-3 py-2.5 rounded-r-[6px] max-w-[min(100%,560px)]">
        {source ? (
          <p className="text-xs text-teal-dark font-medium mb-1">{source}</p>
        ) : null}
        <p className="leading-relaxed whitespace-pre-wrap">{content}</p>
      </div>
    );
  }

  if (variant === 'confirm' && role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="anim-fade-up border-2 border-teal bg-cream-dark/50 text-ink text-sm px-3 py-2.5 rounded-sm max-w-[min(100%,480px)]">
          <p className="leading-relaxed whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    );
  }

  if (variant === 'context') {
    return (
      <div className="anim-fade-up text-xs text-muted italic px-1 py-1 max-w-[min(100%,520px)]">
        {content}
      </div>
    );
  }

  if (variant === 'options' && options?.length) {
    return (
      <div className="anim-fade-up flex flex-col gap-2 max-w-[min(100%,400px)] ml-auto">
        {options.map((opt, i) => (
          <div
            key={i}
            className="bg-terracotta-light text-ink text-sm px-3 py-2 rounded-sm border border-border"
          >
            <span className="text-terracotta font-semibold mr-2">{i + 1}.</span>
            {opt}
          </div>
        ))}
      </div>
    );
  }

  if (role === 'user' && variant === 'voice') {
    return (
      <div className="flex flex-col items-end gap-1">
        {photoUrls?.length ? <PhotoThumbnails urls={photoUrls} /> : null}
        <VoiceNoteBubble
          durationSec={voiceDuration ?? 0}
          waveform={waveform}
          transcript={transcription || content}
          audioUrl={message.voiceUrl}
        />
      </div>
    );
  }

  if (role === 'user' && variant === 'text') {
    return (
      <div className="flex flex-col items-end gap-1">
        {photoUrls?.length ? <PhotoThumbnails urls={photoUrls} /> : null}
        <UserBubble text={content} className="anim-fade-up" />
      </div>
    );
  }

  if (role === 'leo' && (variant === 'text' || variant === 'confirm')) {
    return (
      <div className="anim-fade-up w-full max-w-[min(100%,640px)]">
        <LeoBubble text={content} />
      </div>
    );
  }

  if (role === 'leo' && variant === 'copy_block') {
    return <CopyBlock text={content} />;
  }

  return (
    <div className="text-muted text-sm py-1">
      <span className="sr-only">Message</span>
      {content}
    </div>
  );
};

export default ChatMessage;
