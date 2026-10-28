import { useState, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './primitives';

interface VoiceNoteBubbleProps {
  durationSec: number;
  /** Array of amplitude values 0–1. Falls back to placeholder bars. */
  waveform?: number[];
  /** Transcript text — shown collapsed; tap to expand. Shows "Transcribing…" while undefined. */
  transcript?: string;
  /** Object URL for playback. Only available during the current session (stripped on refresh). */
  audioUrl?: string;
}

const fmtDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
};

/**
 * Play icon: bare rounded triangle (no circle wrapper).
 * Uses SVG path with rounded stroke-linejoin for slightly soft corners.
 */
const PlayIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M6 4.5C6 3.67 6.92 3.18 7.6 3.66l12 7.5c0.6.38.6 1.28 0 1.66l-12 7.5C6.92 20.82 6 20.33 6 19.5V4.5z" />
  </svg>
);

/** Pause icon: two rounded bars */
const PauseIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <rect x="5" y="4" width="4" height="16" rx="2" />
    <rect x="15" y="4" width="4" height="16" rx="2" />
  </svg>
);

/**
 * Terra terracotta bubble: play button + waveform bars + duration + italic transcript.
 *
 * React: import { VoiceNoteBubble } from '@scope/ui'
 * Static HTML: .lead-modal-user-vn in homeowners.html
 *
 * Design: play button is a bare triangle (no circle), waveform bars are clearly visible,
 * bubble max-width matches text bubbles (min(75%, 280px)).
 */
export function VoiceNoteBubble({ durationSec, waveform, transcript, audioUrl }: VoiceNoteBubbleProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Use real waveform or a visible fallback (varying heights so it doesn't look flat)
  const bars = waveform?.length
    ? waveform
    : Array.from({ length: 20 }, (_, i) => 0.3 + 0.25 * Math.sin(i * 0.8));

  const line = (transcript || '').trim();
  const COLLAPSE_AT = 90;
  const showExpand = line.length > COLLAPSE_AT;

  const handlePlayPause = useCallback(() => {
    if (!audioUrl) return;
    if (!audioRef.current) {
      audioRef.current = new Audio(audioUrl);
      audioRef.current.addEventListener('ended', () => setPlaying(false));
      audioRef.current.addEventListener('pause', () => setPlaying(false));
    }
    if (playing) {
      audioRef.current.pause();
    } else {
      void audioRef.current.play().catch(() => setPlaying(false));
      setPlaying(true);
    }
  }, [audioUrl, playing]);

  return (
    <div
      className="flex flex-col gap-2 rounded-sm bg-terracotta text-white px-3 py-2.5 shadow-sm self-end"
      style={{ maxWidth: 'min(75%, 280px)', width: 'fit-content' }}
    >
      {/* Waveform row: play button + bars + duration */}
      <div className="flex items-center gap-2">
        {/* Play/pause button — bare triangle, left-aligned (no centering wrapper) */}
        {audioUrl ? (
          <Button
            type="button"
            onClick={handlePlayPause}
            aria-label={playing ? t('aria_pause_voice') : t('aria_play_voice')}
            className="shrink-0 flex items-center text-white hover:text-white/80 active:scale-90 transition-transform"
          >
            {playing ? <PauseIcon /> : <PlayIcon />}
          </Button>
        ) : (
          <div className="shrink-0 flex items-center text-white/70">
            <PlayIcon />
          </div>
        )}

        {/* Static waveform bars — fill available space */}
        <div className="flex-1 flex items-center gap-0.5 h-8" style={{ minWidth: 80 }}>
          {bars.slice(0, 20).map((v, i) => (
            <span
              key={i}
              className="flex-1 rounded-full bg-white"
              style={{
                height: `${Math.max(10, 6 + v * 26)}px`,
                opacity: Math.max(0.5, 0.45 + v * 0.55),
                minWidth: 2,
              }}
            />
          ))}
        </div>

        {/* Duration */}
        <span className="shrink-0 tabular-nums text-xs text-white/80 font-medium">
          {fmtDuration(durationSec)}
        </span>
      </div>

      {/* Transcript — italic, collapsible */}
      {line ? (
        <Button
          type="button"
          onClick={() => showExpand && setExpanded((e) => !e)}
          className={[
            'text-left text-[13px] italic text-white/85 leading-snug',
            showExpand ? 'cursor-pointer' : 'cursor-default',
          ].filter(Boolean).join(' ')}
          aria-expanded={showExpand ? expanded : undefined}
        >
          {expanded || !showExpand ? `"${line}"` : `"${line.slice(0, COLLAPSE_AT)}…"`}
          {showExpand && (
            <span className="ml-1 not-italic text-white/60 text-[11px]">
              {expanded ? t('voice_note_collapse') : t('voice_note_expand')}
            </span>
          )}
        </Button>
      ) : (
        <p className="text-[13px] italic text-white/65">{t('voice_note_transcribing')}</p>
      )}
    </div>
  );
}
