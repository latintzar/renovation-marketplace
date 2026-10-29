import { useCallback, useEffect, useRef, useState } from 'react';
import type { Message } from '../types';
import { uid, fileToBase64 } from '../lib/utils';
import { isReel } from '../reel/flag';
import {
  sendChatMessage,
  transcribeAudio,
  uploadPhotos,
  extractDocument,
  signalComposing,
  type BriefUpdate,
  type ChatApiMessage,
  type ChatAudience,
  type ChatMode,
  type DrawerState,
  type ProfileUpdate,
  type QuoteUpdate,
  type ToolActivityItem,
} from '../lib/api';

export type ChatUiStatus = 'needs-info' | 'workable' | 'solid';

export type PreviewState = 'empty' | 'building' | 'editing' | 'ready';

interface UseChatOptions {
  /** Existing persisted quote loaded by the normal edit route. */
  initialScope?: QuoteUpdate | null;
  mode: ChatMode;
  audience: ChatAudience;
  /** Starting locale — can be changed at runtime via setPageLocale() */
  pageLocale?: string;
  /** Optional landing lead id for photo uploads */
  leadId?: string | null;
  /** Extra context for the agent (location hints, etc.) */
  leadContext?: string;
  /** Imported profile summary for tradesperson flow */
  profileContext?: string;
  /** Contractor dossier ID (web-{uuid} or hc-{uuid}) */
  contractorId?: string;
}

// ---------------------------------------------------------------------------
// sessionStorage persistence — survives refresh, clears on tab close
// ---------------------------------------------------------------------------

interface PersistedSession {
  userId: string;
  messages: Message[];
  briefUpdate: BriefUpdate | null;
  profileUpdate: ProfileUpdate | null;
  scopeUpdate: QuoteUpdate | null;
  drawerState: DrawerState | null;
  confirmed: boolean;
  savedAt: number;
}

const SESSION_TTL_MS = 60 * 60 * 1000; // 1 hour — matches backend agent pool TTL

function sessionKey(mode: ChatMode, audience: ChatAudience, contractorId?: string): string {
  // Include contractorId so each contractor gets an isolated session.
  // This also ensures the greeting fires fresh when a new contractorId arrives.
  return `leo_chat_${mode}_${audience}${contractorId ? `_${contractorId}` : ''}`;
}

function loadSession(mode: ChatMode, audience: ChatAudience, contractorId?: string): PersistedSession | null {
  // Reel mode always starts fresh so the scripted run + loop are deterministic.
  if (isReel()) return null;
  try {
    const raw = sessionStorage.getItem(sessionKey(mode, audience, contractorId));
    if (!raw) return null;
    const data = JSON.parse(raw) as PersistedSession;
    if (Date.now() - data.savedAt > SESSION_TTL_MS) {
      sessionStorage.removeItem(sessionKey(mode, audience, contractorId));
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

/** Strip base64 images and expired object URLs before persisting — they bloat storage and are invalid after refresh. */
function stripHeavyFields(msgs: Message[]): Message[] {
  return msgs.map((m) => {
    const { images, photoUrls, voiceUrl, ...rest } = m;
    return rest;
  });
}

function saveSession(
  mode: ChatMode,
  audience: ChatAudience,
  data: Omit<PersistedSession, 'savedAt'>,
  contractorId?: string,
) {
  if (isReel()) return;
  try {
    const payload: PersistedSession = {
      ...data,
      messages: stripHeavyFields(data.messages),
      savedAt: Date.now(),
    };
    sessionStorage.setItem(sessionKey(mode, audience, contractorId), JSON.stringify(payload));
  } catch {
    // sessionStorage full or unavailable — silently degrade
  }
}

function briefToUiStatus(b: BriefUpdate | null): ChatUiStatus {
  const s = (b?.status || '').toLowerCase();
  if (s === 'solid') return 'solid';
  if (s === 'workable') return 'workable';
  return 'needs-info';
}

function scopeToUiStatus(s: QuoteUpdate | null): ChatUiStatus {
  if (!s?.title) return 'needs-info';
  const hasAmounts = s.line_items?.some((li) => li.amount > 0);
  if (s.status === 'ready' || hasAmounts) return 'solid';
  if (s.line_items?.length > 0) return 'workable';
  return 'needs-info';
}

/** True when the scope preview should show real data (not just empty template). */
function scopeHasPreviewBody(scope: QuoteUpdate | null): boolean {
  if (!scope) return false;
  // A title alone means Hermes has started building — show real content
  if ((scope.title || '').trim().length > 0) return true;
  const lines = scope.line_items || [];
  if (lines.some((li) => (li.description || '').trim().length > 0 || (li.amount || 0) > 0)) return true;
  if ((scope.description || '').trim().length >= 8) return true;
  const drafts = scope.contingency_drafts || [];
  if (drafts.some((d) => (d.title || '').trim() || (d.reason || '').trim())) return true;
  return false;
}

/** Build chat history from UI messages (user + assistant turns only). */
function messagesToApiHistory(messages: Message[]): ChatApiMessage[] {
  const out: ChatApiMessage[] = [];
  for (const m of messages) {
    if (m.role === 'user') {
      if (m.variant === 'text' || m.variant === 'confirm' || m.variant === 'options') {
        const t = m.content.trim();
        if (t || m.images?.length) {
          out.push({ role: 'user', text: t || '(photo)', images: m.images });
        }
      } else if (m.variant === 'voice') {
        const t = (m.transcription || m.content || '').trim();
        if (t || m.images?.length) {
          out.push({ role: 'user', text: t || '(photo)', images: m.images });
        }
      }
    } else if (m.role === 'leo' && (m.variant === 'text' || m.variant === 'confirm')) {
      const t = m.content.trim();
      if (t) out.push({ role: 'assistant', text: t });
    }
  }
  return out;
}

const DOC_EXTENSIONS = new Set(['.pdf', '.doc', '.docx']);

function isDocFile(f: File): boolean {
  const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
  return DOC_EXTENSIONS.has(ext);
}

/** Extract text from document files, returning a combined markdown string. */
async function extractDocs(files: File[]): Promise<string> {
  const docFiles = files.filter(isDocFile);
  if (!docFiles.length) return '';
  const results = await Promise.all(docFiles.map(extractDocument));
  const parts: string[] = [];
  for (const r of results) {
    if (r.markdown) {
      parts.push(`📄 **${r.filename}**\n\n${r.markdown}`);
    }
  }
  return parts.join('\n\n---\n\n');
}

function userLanguageHint(lastUserText: string): string {
  const t = lastUserText.toLowerCase();
  if (/[áéíóúüñ¿¡]/.test(t) || /\b(hola|gracias|casa|reforma)\b/.test(t)) return 'es';
  return 'en';
}

interface UseChatResult {
  messages: Message[];
  isThinking: boolean;
  status: ChatUiStatus;
  briefUpdate: BriefUpdate | null;
  profileUpdate: ProfileUpdate | null;
  scopeUpdate: QuoteUpdate | null;
  previewState: PreviewState;
  drawerState: DrawerState | null;
  lastError: string | null;
  leadId: string | null;
  setLeadId: (id: string | null) => void;
  /** Whether the user has confirmed their brief/profile — unlocks phone collection phase */
  confirmed: boolean;
  /** Session ID for mem0 — generated once on mount, persisted across refresh */
  userId: string;
  /** True if this session was restored from a previous refresh — pages should skip auto-send */
  didRestore: boolean;
  sendTextMessage: (text: string, photoFiles?: File[]) => Promise<void>;
  sendVoiceMessage: (blob: Blob, duration: number, waveform: number[], photoFiles?: File[]) => Promise<void>;
  sendPhotos: (files: File[]) => Promise<void>;
  appendTrace: (text: string) => void;
  /** Clear all conversation state back to empty (used to loop the reel). */
  reset: () => void;
  /** Tapping "Post job" / "Save profile" — sends confirm signal, switches Hermes into phone-collection mode */
  confirmAction: (type: 'brief' | 'profile') => Promise<void>;
  /** Tapping a custom drawer action — sends the action_id back to Hermes as a user signal */
  handleDrawerAction: (actionId: string) => Promise<void>;
  /** Called by ChatInput when user starts/stops typing or recording */
  handleComposingChange: (composing: boolean, inputType: 'text' | 'voice' | null) => void;
  /** Inject a profile externally (e.g. edit mode loading from canvas API) */
  setProfileUpdate: (p: ProfileUpdate | null) => void;
  /**
   * Inject a Leo message directly into the conversation without any API call.
   * Used for instant hardcoded greetings — no latency, no LLM cost.
   */
  injectLeoMessage: (text: string) => void;
  /**
   * Fire a hidden trigger on session start — adds a hidden user message and calls Hermes,
   * so Leo generates the first greeting without the user having to type anything.
   * Only call this when !didRestore and messages.length === 0.
   */
  sendGreeting: (trigger?: string) => Promise<void>;
  /**
   * Update the locale for all subsequent Hermes turns (without remounting).
   * abortInFlight: cancel the current /v1/chat request (e.g. language toggle).
   * notifyHermes: append a hidden instruction and run the agent (extra API call).
   */
  setPageLocale: (
    locale: string,
    opts?: { notifyHermes?: boolean; abortInFlight?: boolean },
  ) => Promise<void>;
}

export function useChat(options: UseChatOptions): UseChatResult {
  const restored = useRef<PersistedSession | null>(null);
  if (restored.current === null) {
    restored.current = loadSession(options.mode, options.audience, options.contractorId) ?? ({} as PersistedSession);
  }
  const prev = restored.current?.userId ? restored.current : null;

  /** Mutable locale — updated by setPageLocale() without remounting the hook */
  const pageLocaleRef = useRef(options.pageLocale ?? '');
  const [messages, setMessages] = useState<Message[]>(prev?.messages ?? []);
  const [isThinking, setIsThinking] = useState(false);
  const isThinkingRef = useRef(false);
  const pendingRunRef = useRef(false);
  const chatAbortRef = useRef<AbortController | null>(null);
  const [briefUpdate, setBriefUpdate] = useState<BriefUpdate | null>(prev?.briefUpdate ?? null);
  const [profileUpdate, setProfileUpdate] = useState<ProfileUpdate | null>(prev?.profileUpdate ?? null);
  const [scopeUpdate, setQuoteUpdate] = useState<QuoteUpdate | null>(options.initialScope ?? prev?.scopeUpdate ?? null);
  const [drawerState, setDrawerState] = useState<DrawerState | null>(prev?.drawerState ?? null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [leadId, setLeadId] = useState<string | null>(options.leadId ?? null);
  const [userId] = useState<string>(() => prev?.userId ?? uid());
  const [confirmed, setConfirmed] = useState(prev?.confirmed ?? false);
  /** True when the hook restored a previous session — pages can use this to skip auto-send */
  const didRestore = Boolean(prev);

  // Composing signal — debounce network calls so we send at most once per 2s
  const lastSignalRef = useRef<{ composing: boolean; ts: number }>({ composing: false, ts: 0 });
  const composingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleComposingChange = useCallback((composing: boolean, inputType: 'text' | 'voice' | null) => {
    const now = Date.now();
    const last = lastSignalRef.current;

    if (composing === last.composing && now - last.ts < 2000) return;

    if (composingTimerRef.current) clearTimeout(composingTimerRef.current);

    const fire = () => {
      lastSignalRef.current = { composing, ts: Date.now() };
      signalComposing(userId, composing, inputType);
    };

    if (!composing) {
      fire();
    } else {
      composingTimerRef.current = setTimeout(fire, 300);
    }
  }, [userId]);

  useEffect(() => {
    return () => { if (composingTimerRef.current) clearTimeout(composingTimerRef.current); };
  }, []);

  // Persist state to sessionStorage after every meaningful change
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const briefRef = useRef(briefUpdate);
  briefRef.current = briefUpdate;
  const profileRef = useRef(profileUpdate);
  profileRef.current = profileUpdate;
  const scopeRef = useRef(scopeUpdate);
  scopeRef.current = scopeUpdate;
  const drawerRef = useRef(drawerState);
  drawerRef.current = drawerState;
  const confirmedRef = useRef(confirmed);
  confirmedRef.current = confirmed;

  useEffect(() => {
    saveSession(options.mode, options.audience, {
      userId,
      messages: messagesRef.current,
      briefUpdate: briefRef.current,
      profileUpdate: profileRef.current,
      scopeUpdate: scopeRef.current,
      drawerState: drawerRef.current,
      confirmed: confirmedRef.current,
    }, options.contractorId);
  }, [messages, briefUpdate, profileUpdate, scopeUpdate, drawerState, confirmed, userId, options.mode, options.audience, options.contractorId]);

  const derivePreviewState = useCallback(
    (
      thinking: boolean,
      brief: BriefUpdate | null,
      profile: ProfileUpdate | null,
      scope: QuoteUpdate | null,
      /** At least one real user message has been sent — prevents shimmer on lang-toggle etc. */
      userHasSentMessage: boolean,
    ): PreviewState => {
      const hasBriefOrProfile = Boolean(
        brief?.title ||
          brief?.description ||
          profile?.business_name ||
          profile?.trade,
      );
      const hasScopeCard = scopeHasPreviewBody(scope);
      const hasCard = hasBriefOrProfile || hasScopeCard;
      if (!hasCard) {
        // 'building' only when the user has actually sent something and we're waiting
        return thinking && userHasSentMessage ? 'building' : 'empty';
      }
      if (thinking) return 'editing';
      return 'ready';
    },
    [],
  );

  // True once the user has sent at least one non-hidden message
  const userHasSentMessage = messages.some(
    (m) => m.role === 'user' && !m.hidden && m.variant !== 'trace',
  );

  const previewState = derivePreviewState(isThinking, briefUpdate, profileUpdate, scopeUpdate, userHasSentMessage);

  // In scope mode, always derive status from scopeUpdate — briefUpdate must never hijack it.
  // (The agent should only call update_scope in scope mode, but this is a safety net.)
  const status: ChatUiStatus = options.mode === 'quote'
    ? scopeToUiStatus(scopeUpdate)
    : briefUpdate
      ? briefToUiStatus(briefUpdate)
      : profileUpdate?.business_name || profileUpdate?.trade
        ? 'workable'
        : 'needs-info';

  const runAgent = useCallback(
    async (history: Message[], isConfirmed?: boolean) => {
      if (isThinkingRef.current) {
        pendingRunRef.current = true;
        return;
      }

      const apiHist = messagesToApiHistory(history);
      const lastUser = [...history].reverse().find((m) => m.role === 'user');
      let lastText = '';
      if (lastUser?.variant === 'voice') {
        lastText = lastUser.transcription || lastUser.content || '';
      } else if (lastUser) {
        lastText = lastUser.content || '';
      }
      const hint = userLanguageHint(lastText);

      // Inject a live "working" trace BEFORE the API call so users see immediate
      // feedback instead of staring at three dots. Replaced by real traces when done.
      const preMsgId = uid();
      const hasExistingScope = Boolean(scopeRef.current?.title);
      const preTraceLabel =
        options.mode === 'quote'
          ? hasExistingScope
            ? 'Updating your scope…'
            : 'Creating your first scope draft…'
          : null;
      if (preTraceLabel) {
        setMessages((prev) => [
          ...prev,
          {
            id: preMsgId,
            role: 'system' as const,
            variant: 'trace' as const,
            content: preTraceLabel,
            timestamp: Date.now(),
          },
        ]);
      }

      setIsThinking(true);
      isThinkingRef.current = true;
      setLastError(null);

      chatAbortRef.current?.abort();
      const ac = new AbortController();
      chatAbortRef.current = ac;

      const res = await sendChatMessage({
        messages: apiHist,
        mode: options.mode,
        audience: options.audience,
        leadContext: options.leadContext,
        profileContext: options.profileContext,
        pageLocale: pageLocaleRef.current,
        userLanguageHint: hint,
        userId,
        confirmed: isConfirmed ?? confirmed,
        contractorId: options.contractorId,
        signal: ac.signal,
      });

      if (chatAbortRef.current === ac) chatAbortRef.current = null;

      if (res.aborted) {
        // Remove pre-trace on abort
        if (preTraceLabel) setMessages((prev) => prev.filter((m) => m.id !== preMsgId));
        setIsThinking(false);
        isThinkingRef.current = false;
        pendingRunRef.current = false;
        return;
      }

      if (res.error) {
        if (preTraceLabel) setMessages((prev) => prev.filter((m) => m.id !== preMsgId));
        setIsThinking(false);
        isThinkingRef.current = false;
        setLastError(res.error);
        const errMsg: Message = {
          id: uid(),
          role: 'leo',
          variant: 'text',
          content: `Sorry — something went wrong (${res.error}). Try again.`,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, errMsg]);
        return;
      }

      // Set data BEFORE clearing isThinking — ensures previewState transitions
      // directly from 'building' to 'ready' without a flash of 'empty'.
      if (res.brief_update) setBriefUpdate(res.brief_update);
      if (res.profile_update) setProfileUpdate(res.profile_update);
      if (res.quote_update) setQuoteUpdate(res.quote_update);
      if (res.drawer_state) {
        if (res.drawer_state.content_type === 'reset') {
          setDrawerState(null);
        } else {
          setDrawerState(res.drawer_state);
        }
      }

      setIsThinking(false);
      isThinkingRef.current = false;

      const traceMsgs: Message[] = [];
      const acts: ToolActivityItem[] = res.tool_activity || [];
      for (const a of acts) {
        traceMsgs.push({
          id: uid(),
          role: 'system',
          variant: 'trace',
          content: a.label || a.tool,
          timestamp: Date.now(),
        });
      }

      const leoMsg: Message = {
        id: uid(),
        role: 'leo',
        variant: 'text',
        content: res.reply,
        timestamp: Date.now(),
      };

      const copyBlockMsgs: Message[] = (res.copy_blocks ?? []).map((block: string) => ({
        id: uid(),
        role: 'leo' as const,
        variant: 'copy_block' as const,
        content: block,
        timestamp: Date.now(),
      }));

      // Replace the pre-trace with real traces + Leo's reply atomically
      setMessages((prev) => {
        const withoutPreTrace = preTraceLabel ? prev.filter((m) => m.id !== preMsgId) : prev;
        const next = [...withoutPreTrace, ...traceMsgs, leoMsg, ...copyBlockMsgs];
        if (pendingRunRef.current) {
          pendingRunRef.current = false;
          queueMicrotask(() => void runAgent(next, isConfirmed));
        }
        return next;
      });
    },
    [options, userId, confirmed],
  );

  const uploadStagedPhotos = useCallback(
    async (files: File[]) => {
      if (!files.length || !leadId) return;
      const up = await uploadPhotos(leadId, files);
      if (!up.ok && up.error) setLastError(up.error);
    },
    [leadId],
  );

  const sendTextMessage = useCallback(
    async (text: string, photoFiles?: File[]) => {
      const trimmed = text.trim();
      const photos = photoFiles ?? [];
      if (!trimmed && !photos.length) return;

      const photoUrls = photos.map((f) => URL.createObjectURL(f));

      const imageFiles = photos.filter((f) => f.type.startsWith('image/'));
      const images = await Promise.all(imageFiles.map(fileToBase64));

      const docText = await extractDocs(photos);
      const fullContent = docText
        ? `${trimmed}\n\n[Attached document content]\n${docText}`.trim()
        : trimmed || (photos.length === 1 ? 'Sent a photo' : `Sent ${photos.length} photos`);

      const userMsg: Message = {
        id: uid(),
        role: 'user',
        variant: 'text',
        content: fullContent,
        timestamp: Date.now(),
        photoUrls: photoUrls.length ? photoUrls : undefined,
        images: images.length ? images : undefined,
      };

      // Re-open for editing — if user sends a new message after confirming, drop confirmed flag
      // so the backend treats this as an edit turn, not a phone-collection turn.
      if (confirmed) setConfirmed(false);

      setMessages((prev) => {
        const next = [...prev, userMsg];
        queueMicrotask(async () => {
          if (photos.length) await uploadStagedPhotos(photos);
          await runAgent(next, false);
        });
        return next;
      });
    },
    [runAgent, uploadStagedPhotos, confirmed],
  );

  const sendVoiceMessage = useCallback(
    async (blob: Blob, duration: number, waveform: number[], photoFiles?: File[]) => {
      const photos = photoFiles ?? [];
      const photoUrls = photos.map((f) => URL.createObjectURL(f));
      const imageFiles = photos.filter((f) => f.type.startsWith('image/'));
      const images = await Promise.all(imageFiles.map(fileToBase64));
      const voiceId = uid();
      // Create a local object URL so VoiceNoteBubble can play back the recording.
      // Stripped from persisted sessions (object URLs don't survive page refresh).
      const voiceUrl = URL.createObjectURL(blob);
      const placeholder: Message = {
        id: voiceId,
        role: 'user',
        variant: 'voice',
        content: '',
        timestamp: Date.now(),
        voiceDuration: duration,
        waveform: waveform.length ? waveform : undefined,
        voiceUrl,
        photoUrls: photoUrls.length ? photoUrls : undefined,
        images: images.length ? images : undefined,
      };
      setMessages((prev) => [...prev, placeholder]);

      // Re-open for editing if user sends after confirming
      if (confirmed) setConfirmed(false);

      if (photos.length) void uploadStagedPhotos(photos);

      const { text, error } = await transcribeAudio(blob, { polish: false });
      if (error || !text.trim()) {
        setLastError(error || 'empty transcript');
        setMessages((prev) =>
          prev.map((m) =>
            m.id === voiceId
              ? {
                  ...m,
                  transcription: error ? `(Transcription failed: ${error})` : '(No speech detected)',
                  content: error ? `(Transcription failed: ${error})` : '(No speech detected)',
                }
              : m,
          ),
        );
        return;
      }

      setMessages((prev) => {
        const next = prev.map((m) =>
          m.id === voiceId ? { ...m, transcription: text, content: text } : m,
        );
        queueMicrotask(() => void runAgent(next, false));
        return next;
      });
    },
    [runAgent, uploadStagedPhotos, confirmed],
  );

  const sendPhotos = useCallback(
    async (files: File[]) => {
      if (!files.length) return;

      const photoUrls = files.map((f) => URL.createObjectURL(f));
      const imageFiles = files.filter((f) => f.type.startsWith('image/'));
      const images = await Promise.all(imageFiles.map(fileToBase64));
      const label =
        files.length === 1
          ? `Sent a photo`
          : `Sent ${files.length} photos`;
      const userMsg: Message = {
        id: uid(),
        role: 'user',
        variant: 'text',
        content: label,
        timestamp: Date.now(),
        photoUrls,
        images: images.length ? images : undefined,
      };

      setMessages((prev) => {
        const next = [...prev, userMsg];
        queueMicrotask(async () => {
          if (leadId) {
            const up = await uploadPhotos(leadId, files);
            if (!up.ok && up.error) {
              setLastError(up.error);
            }
          }
          await runAgent(next);
        });
        return next;
      });
    },
    [runAgent, leadId],
  );

  const appendTrace = useCallback((text: string) => {
    const m: Message = {
      id: uid(),
      role: 'system',
      variant: 'trace',
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, m]);
  }, []);

  const reset = useCallback(() => {
    chatAbortRef.current?.abort();
    chatAbortRef.current = null;
    isThinkingRef.current = false;
    pendingRunRef.current = false;
    setMessages([]);
    setIsThinking(false);
    setBriefUpdate(null);
    setProfileUpdate(null);
    setQuoteUpdate(null);
    setDrawerState(null);
    setLastError(null);
    setConfirmed(false);
  }, []);

  /**
   * Called when user taps "Post job" / "Save profile".
   * Marks the session as confirmed, then sends a special user message that
   * Hermes recognises as the signal to switch into phone-collection mode.
   */
  const confirmAction = useCallback(
    async (type: 'brief' | 'profile') => {
      setConfirmed(true);
      const signal = type === 'brief' ? '[CONFIRMED_BRIEF]' : '[CONFIRMED_PROFILE]';
      const userMsg: Message = {
        id: uid(),
        role: 'user',
        variant: 'text',
        content: signal,
        timestamp: Date.now(),
      };
      setMessages((prev) => {
        const next = [...prev, userMsg];
        queueMicrotask(() => void runAgent(next, true));
        return next;
      });
    },
    [runAgent],
  );

  const handleDrawerAction = useCallback(
    async (actionId: string) => {
      if (actionId === 'confirm_brief') {
        return confirmAction('brief');
      }
      if (actionId === 'confirm_profile') {
        return confirmAction('profile');
      }
      const signal = `[DRAWER_ACTION:${actionId}]`;
      const userMsg: Message = {
        id: uid(),
        role: 'user',
        variant: 'text',
        content: signal,
        timestamp: Date.now(),
      };
      setMessages((prev) => {
        const next = [...prev, userMsg];
        queueMicrotask(() => void runAgent(next));
        return next;
      });
    },
    [runAgent, confirmAction],
  );

  /**
   * Send a hidden trigger to Hermes so it generates the first greeting.
   * The trigger message is added to history (for context) but not rendered.
   * Default trigger: "Start" — enough for the scope context to fire question 1.
   */
  const injectLeoMessage = useCallback((text: string) => {
    const msg: Message = {
      id: uid(),
      role: 'leo',
      variant: 'text',
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, msg]);
  }, []);

  const sendGreeting = useCallback(
    async (trigger = 'Start') => {
      const triggerMsg: Message = {
        id: uid(),
        role: 'user',
        variant: 'text',
        content: trigger,
        timestamp: Date.now(),
        hidden: true,
      };
      setMessages((prev) => {
        const next = [...prev, triggerMsg];
        queueMicrotask(() => void runAgent(next));
        return next;
      });
    },
    [runAgent],
  );

  /**
   * Update the locale for all future Hermes turns.
   * If notifyHermes=true (default), sends a hidden language-switch instruction
   * so Hermes switches mid-conversation rather than waiting for the next user message.
   */
  const setPageLocale = useCallback(
    async (locale: string, opts?: { notifyHermes?: boolean; abortInFlight?: boolean }) => {
      if (opts?.abortInFlight) {
        chatAbortRef.current?.abort();
        chatAbortRef.current = null;
        setIsThinking(false);
        isThinkingRef.current = false;
        pendingRunRef.current = false;
      }
      pageLocaleRef.current = locale;
      if (!opts?.notifyHermes) return;
      const instruction =
        locale === 'es'
          ? 'Por favor, continúa esta conversación en español a partir de ahora.'
          : 'Please continue this conversation in English from now on.';
      const switchMsg: Message = {
        id: uid(),
        role: 'user',
        variant: 'text',
        content: instruction,
        timestamp: Date.now(),
        hidden: true,
      };
      setMessages((prev) => {
        const next = [...prev, switchMsg];
        queueMicrotask(() => void runAgent(next));
        return next;
      });
    },
    [runAgent],
  );

  return {
    messages,
    isThinking,
    status,
    briefUpdate,
    profileUpdate,
    scopeUpdate,
    previewState,
    drawerState,
    lastError,
    leadId,
    setLeadId,
    confirmed,
    userId,
    didRestore,
    sendTextMessage,
    sendVoiceMessage,
    sendPhotos,
    appendTrace,
    reset,
    confirmAction,
    handleDrawerAction,
    handleComposingChange,
    setProfileUpdate,
    injectLeoMessage,
    sendGreeting,
    setPageLocale,
  };
}
