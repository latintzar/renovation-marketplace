import { useRef, useState, useCallback, useEffect } from 'react';
import { Mic, ArrowUp, Trash2, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { BRAND_COLORS, Button, Input } from '@scope/ui';
import { useVoiceRecorder } from '../../hooks/useVoiceRecorder';
import { clsx } from '../../lib/utils';
import AttachmentSheet from './AttachmentSheet';

interface StagedFile {
  id: string;
  file: File;
  preview: string;
}

export type ComposingType = 'text' | 'voice' | null;

interface ChatInputProps {
  onSendText: (text: string, photoFiles?: File[]) => void;
  onSendVoice: (blob: Blob, duration: number, waveform: number[], photoFiles?: File[]) => void;
  onComposingChange?: (composing: boolean, type: ComposingType) => void;
  disabled?: boolean;
  placeholder?: string;
}

let nextFileId = 0;

const ChatInput = ({
  onSendText,
  onSendVoice,
  onComposingChange,
  disabled,
  placeholder,
}: ChatInputProps) => {
  const { t } = useTranslation();
  const resolvedPlaceholder = placeholder ?? t('input_placeholder');
  const [text, setText] = useState('');
  const [sheetOpen, setSheetOpen] = useState(false);
  const [staged, setStaged] = useState<StagedFile[]>([]);
  const [kbPad, setKbPad] = useState(0);
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const waveContainerRef = useRef<HTMLDivElement>(null);
  const waveCanvasRef = useRef<HTMLCanvasElement>(null);
  const composingRef = useRef(false);
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const {
    isRecording,
    elapsed,
    waveformData,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecorder();

  // Measure the wave container and resize canvas whenever recording starts (or layout changes)
  useEffect(() => {
    if (!isRecording || !waveContainerRef.current) return;
    const measure = () => {
      const el = waveContainerRef.current;
      if (!el) return;
      const w = el.getBoundingClientRect().width;
      // Size the canvas to physical pixels
      const cvs = waveCanvasRef.current;
      if (!cvs) return;
      const dpr = window.devicePixelRatio || 1;
      const h = el.getBoundingClientRect().height || 30;
      if (cvs.width !== Math.round(w * dpr) || cvs.height !== Math.round(h * dpr)) {
        cvs.width = Math.round(w * dpr);
        cvs.height = Math.round(h * dpr);
      }
    };
    // rAF so layout is settled after the +btn disappears
    const id = requestAnimationFrame(measure);
    const ro = new ResizeObserver(measure);
    ro.observe(waveContainerRef.current);
    return () => { cancelAnimationFrame(id); ro.disconnect(); };
  }, [isRecording]);

  const emitComposing = useCallback((composing: boolean, type: ComposingType) => {
    if (composing === composingRef.current && !composing) return;
    composingRef.current = composing;
    onComposingChange?.(composing, type);
  }, [onComposingChange]);

  const handleTextChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setText(val);

    if (val.trim()) {
      emitComposing(true, 'text');
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      idleTimerRef.current = setTimeout(() => emitComposing(false, null), 8000);
    } else {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      emitComposing(false, null);
    }
  }, [emitComposing]);

  useEffect(() => {
    if (isRecording) {
      emitComposing(true, 'voice');
    } else if (composingRef.current && !text.trim()) {
      emitComposing(false, null);
    }
  }, [isRecording, emitComposing, text]);

  useEffect(() => {
    return () => { if (idleTimerRef.current) clearTimeout(idleTimerRef.current); };
  }, []);

  // Draw waveform to canvas — zero DOM churn, no layout thrash.
  // IMPORTANT: canvas.width/height attributes are in PHYSICAL pixels (CSS px × DPR).
  // We must ctx.scale(dpr, dpr) so we can draw in CSS pixel coordinates; otherwise
  // bars end up tiny in the top-left corner of the much-larger physical canvas.
  useEffect(() => {
    const cvs = waveCanvasRef.current;
    if (!cvs || !isRecording) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    // Work in CSS pixels; scale the context to map to physical pixels
    const cw = cvs.width / dpr;
    const ch = cvs.height / dpr;
    const BAR_W = 2.5, BAR_GAP = 2;
    const maxVis = Math.max(10, Math.floor((cw + BAR_GAP) / (BAR_W + BAR_GAP)));
    const bars = waveformData.slice(-maxVis);

    // Clear full physical canvas, then draw in CSS space
    ctx.clearRect(0, 0, cvs.width, cvs.height);
    ctx.save();
    ctx.scale(dpr, dpr);

    // Right-align bars (newest on right)
    const n = bars.length;
    const totalW = n * BAR_W + Math.max(0, n - 1) * BAR_GAP;
    const startX = cw - totalW;
    for (let j = 0; j < n; j++) {
      const amp = bars[j]; // 0–1
      const bh = Math.max(3, Math.round(4 + amp * (ch - 8)));
      const op = amp < 0.04 ? 0.18 : 0.38 + amp * 0.62;
      const x = startX + j * (BAR_W + BAR_GAP);
      const y = (ch - bh) / 2;
      ctx.globalAlpha = op;
      ctx.fillStyle = BRAND_COLORS.terracotta;
      ctx.beginPath();
      const r = Math.min(1.5, bh / 2);
      if (ctx.roundRect) {
        ctx.roundRect(x, y, BAR_W, bh, r);
      } else {
        ctx.rect(x, y, BAR_W, bh);
      }
      ctx.fill();
    }
    ctx.restore();
  }, [waveformData, isRecording]);

  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const update = () => {
      const keyboardHeight = window.innerHeight - vv.height;
      setKbPad(keyboardHeight > 80 ? 12 : 0);
    };
    vv.addEventListener('resize', update);
    vv.addEventListener('scroll', update);
    return () => {
      vv.removeEventListener('resize', update);
      vv.removeEventListener('scroll', update);
    };
  }, []);

  const consumeStaged = (): File[] => {
    const files = staged.map((s) => s.file);
    staged.forEach((s) => URL.revokeObjectURL(s.preview));
    setStaged([]);
    return files;
  };

  const handleSendText = () => {
    const t = text.trim();
    if (!t && staged.length === 0) return;
    const photos = consumeStaged();
    setText('');
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    emitComposing(false, null);
    void onSendText(t, photos.length ? photos : undefined);
  };

  const handleStopRecording = async () => {
    const rawSnapshot = [...waveformData];
    const { blob, duration } = await stopRecording();
    emitComposing(false, null);
    if (blob.size > 0) {
      // Downsample history to ~20 bars for VoiceNoteBubble
      const TARGET = 20;
      const trimmed = rawSnapshot.filter((v) => v > 0);
      const src = trimmed.length >= TARGET ? trimmed : rawSnapshot;
      const step = src.length / TARGET;
      const snapshot = Array.from({ length: TARGET }, (_, i) => src[Math.floor(i * step)] ?? 0);
      const photos = consumeStaged();
      void onSendVoice(blob, duration, snapshot, photos.length ? photos : undefined);
    }
  };

  const stageFiles = useCallback((files: File[]) => {
    const newStaged: StagedFile[] = files.map((f) => ({
      id: `sf-${++nextFileId}`,
      file: f,
      preview: URL.createObjectURL(f),
    }));
    setStaged((prev) => [...prev, ...newStaged]);
  }, []);

  const removeStaged = useCallback((id: string) => {
    setStaged((prev) => {
      const item = prev.find((s) => s.id === id);
      if (item) URL.revokeObjectURL(item.preview);
      return prev.filter((s) => s.id !== id);
    });
  }, []);

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      e.target.value = '';
      if (files.length) stageFiles(files);
    },
    [stageFiles],
  );

  const hasText = text.trim().length > 0;
  const hasStaged = staged.length > 0;

  return (
    <div className="shrink-0 relative">
      {/* Content layer */}
      <div
        className="relative pointer-events-auto px-3 pt-2"
        style={{ paddingBottom: `max(${10 + kbPad}px, calc(${10 + kbPad}px + env(safe-area-inset-bottom, 0px)))` }}
      >
        {error ? (
          <p className="text-xs text-red mb-2 px-1" role="alert">
            {error}
          </p>
        ) : null}

        {/* Hidden file inputs */}
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleFileInput} />
        <input ref={galleryRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileInput} />
        <input ref={fileRef} type="file" accept="image/*,.pdf,.doc,.docx" multiple className="hidden" onChange={handleFileInput} />

        <div className="flex items-center gap-1.5">
          {/* Input bar — plus button is inside on the left */}
          <div
            className={clsx(
              'flex-1 min-w-0 flex flex-col border-[1.5px] bg-card rounded-sm relative',
              isRecording ? 'border-terracotta/40' : 'border-border',
              !isRecording && 'focus-within:border-terracotta focus-within:shadow-[0_0_0_3px_rgba(218,101,77,0.08)]',
            )}
          >
            {/* Staged file thumbnails */}
            {hasStaged && (
              <div className="flex items-center gap-2 px-2 pt-2 pb-1 overflow-x-auto">
                {staged.map((s) => (
                  <div key={s.id} className="relative shrink-0 group">
                    <img
                      src={s.preview}
                      alt={s.file.name}
                      className="w-14 h-14 rounded-xs object-cover"
                    />
                    {!isRecording && (
                      <Button
                        type="button"
                        onClick={() => removeStaged(s.id)}
                        className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-ink/80 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 active:opacity-100 transition-opacity"
                        aria-label={`Remove ${s.file.name}`}
                      >
                        <Trash2 size={10} />
                      </Button>
                    )}
                  </div>
                ))}
                {!isRecording && (
                  <Button
                    type="button"
                    onClick={() => setSheetOpen(true)}
                    className="w-14 h-14 rounded-xs border border-dashed border-border flex items-center justify-center text-muted hover:text-ink hover:border-stone transition-colors shrink-0"
                  aria-label="Add more"
                  >
                    <Plus size={20} />
                  </Button>
                )}
              </div>
            )}

            {/* Bottom row: [+] text input / waveform */}
            <div className="flex items-center h-[44px] overflow-hidden" style={{ minHeight: isRecording ? 44 : undefined }}>
              {!isRecording && (
                <Button
                  type="button"
                  disabled={disabled}
                  onClick={() => setSheetOpen(true)}
                  className="shrink-0 flex items-center justify-center w-[44px] h-[44px] text-muted hover:text-ink transition-colors"
                  aria-label="Add attachment"
                >
                  <Plus size={26} strokeWidth={1.8} />
                </Button>
              )}

              {!isRecording && (
                <Input
                  ref={inputRef}
                  type="text"
                  value={text}
                  onChange={handleTextChange}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendText();
                    }
                  }}
                  placeholder={hasStaged ? t('input_add_comment') : resolvedPlaceholder}
                  disabled={disabled}
                  className="flex-1 min-w-0 bg-transparent text-[15px] text-ink placeholder:text-muted outline-none py-[9px] pr-3 leading-[1.45]"
                  name="leo-chat-msg"
                  autoComplete="off"
                  autoCorrect="on"
                  autoCapitalize="sentences"
                  enterKeyHint="send"
                  spellCheck
                  data-form-type="other"
                  data-lpignore="true"
                  data-1p-ignore
                />
              )}

              {isRecording && (
                <div className="flex-1 flex items-center gap-[8px] px-3 h-[44px]">
                  {/* Pulsing red recording dot */}
                  <span
                    className="w-[7px] h-[7px] rounded-full bg-red-500 shrink-0 animate-[recDot_1.1s_ease-in-out_infinite]"
                    aria-hidden="true"
                  />
                  <span className="text-xs text-muted tabular-nums shrink-0">
                    {Math.floor(elapsed / 60)}:{(elapsed % 60).toString().padStart(2, '0')}
                  </span>
                  {/* Canvas waveform — fills available space, vertically centred */}
                  <div
                    ref={waveContainerRef}
                    className="flex-1 min-w-0 self-stretch overflow-hidden flex items-center"
                    style={{
                      maskImage: 'linear-gradient(90deg, rgba(0,0,0,0.1) 0, rgba(0,0,0,0.5) 14px, rgba(0,0,0,1) 36px)',
                      WebkitMaskImage: 'linear-gradient(90deg, rgba(0,0,0,0.1) 0, rgba(0,0,0,0.5) 14px, rgba(0,0,0,1) 36px)',
                    }}
                  >
                    <canvas
                      ref={waveCanvasRef}
                      className="w-full block"
                      style={{ height: '100%' }}
                      aria-hidden="true"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Cancel recording button */}
          {isRecording && (
            <Button
              type="button"
              onClick={() => cancelRecording()}
              className="w-[44px] h-[44px] rounded-sm bg-black/[0.06] hover:bg-black/[0.1] flex items-center justify-center text-stone transition-colors shrink-0"
              aria-label="Discard recording"
            >
              <Trash2 size={18} />
            </Button>
          )}

          {/* Action button (mic / send / stop) */}
          <Button
            type="button"
            disabled={disabled}
            onClick={() => {
              if (isRecording) {
                void handleStopRecording();
                return;
              }
              if (hasText) {
                handleSendText();
                return;
              }
              void startRecording();
            }}
            className={clsx(
              'shrink-0 w-[44px] h-[44px] rounded-sm flex items-center justify-center text-white transition-colors',
              isRecording && 'bg-terracotta hover:bg-terracotta-dark',
              !isRecording && hasText && 'bg-ink hover:bg-stone',
              !isRecording && !hasText && 'bg-terracotta hover:bg-terracotta-dark',
            )}
            aria-label={isRecording ? t('aria_send_voice') : hasText ? t('aria_send_message') : t('aria_record_voice')}
          >
            {isRecording ? (
              <ArrowUp size={20} strokeWidth={2.5} />
            ) : hasText ? (
              <ArrowUp size={20} strokeWidth={2.5} />
            ) : (
              <Mic size={20} />
            )}
          </Button>
        </div>

        <AttachmentSheet
          open={sheetOpen}
          onClose={() => setSheetOpen(false)}
          onTakePhoto={() => cameraRef.current?.click()}
          onChooseGallery={() => galleryRef.current?.click()}
          onChooseFile={() => fileRef.current?.click()}
        />
      </div>
    </div>
  );
};

export default ChatInput;
