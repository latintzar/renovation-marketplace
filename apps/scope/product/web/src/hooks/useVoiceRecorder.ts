import { useCallback, useEffect, useRef, useState } from 'react';

/** How many historical amplitude samples to keep — determines total scrollable history */
const HISTORY_BARS = 80;

/** Throttle: emit one new bar every N animation frames (~60fps → ~1 bar every 50ms with N=3) */
const FRAMES_PER_BAR = 3;

function pickMime(): string {
  if (typeof MediaRecorder === 'undefined') return '';
  if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
    return 'audio/webm;codecs=opus';
  }
  if (MediaRecorder.isTypeSupported('audio/webm')) return 'audio/webm';
  if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) return 'audio/ogg;codecs=opus';
  return '';
}

export interface UseVoiceRecorderResult {
  isRecording: boolean;
  elapsed: number;
  waveformData: number[];
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<{ blob: Blob; duration: number }>;
  cancelRecording: () => void;
}

/**
 * Real MediaRecorder capture + Web Audio AnalyserNode waveform + timer.
 */
export function useVoiceRecorder(): UseVoiceRecorderResult {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [waveformData, setWaveformData] = useState<number[]>(() => Array(HISTORY_BARS).fill(0));
  const [error, setError] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const mimeRef = useRef('');
  const timerRef = useRef<ReturnType<typeof requestAnimationFrame>>(0);
  const startedAtRef = useRef(0);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number>(0);

  const cleanupStream = useCallback(() => {
    if (streamRef.current) {
      for (const t of streamRef.current.getTracks()) {
        t.stop();
      }
      streamRef.current = null;
    }
  }, []);

  const cleanupAudio = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    if (audioCtxRef.current) {
      void audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    analyserRef.current = null;
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      cancelAnimationFrame(timerRef.current);
      timerRef.current = 0;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopTimer();
      cleanupAudio();
      cleanupStream();
    };
  }, [cleanupAudio, cleanupStream, stopTimer]);

  const tickWaveform = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const arr = new Uint8Array(analyser.frequencyBinCount);
    let frameCount = 0;
    const loop = () => {
      analyser.getByteFrequencyData(arr);
      frameCount++;
      if (frameCount % FRAMES_PER_BAR === 0) {
        // Collapse the frequency spectrum to a single RMS amplitude (0–1)
        let sum = 0;
        for (let i = 0; i < arr.length; i++) sum += arr[i];
        const amplitude = sum / arr.length / 255;
        setWaveformData((prev) => {
          const next = [...prev, amplitude];
          return next.length > HISTORY_BARS ? next.slice(next.length - HISTORY_BARS) : next;
        });
      }
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    chunksRef.current = [];
    mimeRef.current = pickMime();

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      tickWaveform();

      const options = mimeRef.current ? { mimeType: mimeRef.current } : undefined;
      const rec = new MediaRecorder(stream, options);
      recorderRef.current = rec;

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      rec.start(100);
      startedAtRef.current = Date.now();
      setElapsed(0);
      setIsRecording(true);

      stopTimer();
      // rAF-driven timer — never throttled by heavy animation loops
      let lastSec = -1;
      const tick = () => {
        const s = Math.floor((Date.now() - startedAtRef.current) / 1000);
        if (s !== lastSec) { lastSec = s; setElapsed(s); }
        timerRef.current = requestAnimationFrame(tick);
      };
      timerRef.current = requestAnimationFrame(tick);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Could not access microphone';
      setError(msg);
      cleanupStream();
      cleanupAudio();
    }
  }, [cleanupAudio, cleanupStream, stopTimer, tickWaveform]);

  const stopRecording = useCallback(async (): Promise<{ blob: Blob; duration: number }> => {
    const rec = recorderRef.current;
    const mime = mimeRef.current || 'audio/webm';
    stopTimer();
    cleanupAudio();
    setIsRecording(false);
    setWaveformData(Array(HISTORY_BARS).fill(0));

    const durationSec = startedAtRef.current
      ? Math.max(1, Math.round((Date.now() - startedAtRef.current) / 1000))
      : 0;

    return new Promise((resolve) => {
      if (!rec || rec.state === 'inactive') {
        cleanupStream();
        const blob = new Blob(chunksRef.current, { type: mime });
        chunksRef.current = [];
        resolve({ blob, duration: durationSec });
        return;
      }
      rec.onstop = () => {
        cleanupStream();
        const blob = new Blob(chunksRef.current, { type: mime });
        chunksRef.current = [];
        recorderRef.current = null;
        resolve({ blob, duration: durationSec });
      };
      rec.stop();
    });
  }, [cleanupAudio, cleanupStream, stopTimer]);

  const cancelRecording = useCallback(() => {
    stopTimer();
    cleanupAudio();
    setIsRecording(false);
    setElapsed(0);
    setWaveformData(Array(HISTORY_BARS).fill(0));
    const rec = recorderRef.current;
    recorderRef.current = null;
    chunksRef.current = [];
    if (rec && rec.state !== 'inactive') {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    cleanupStream();
  }, [cleanupAudio, cleanupStream, stopTimer]);

  return {
    isRecording,
    elapsed,
    waveformData,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
