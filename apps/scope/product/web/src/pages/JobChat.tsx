/**
 * JobChat — In-job messaging between homeowner and contractor.
 *
 * Uses the shared ChatInput (voice + attachments) and renders bubbles inline.
 * Supabase Realtime Broadcast delivers messages live; WhatsApp fallback is
 * handled server-side.
 *
 * Design: dark header (ink), cream body, own messages right-aligned in ink
 * bubbles, other messages left in white. Timestamps shown only above the first
 * message in each consecutive block from the same sender (WhatsApp/iMessage
 * style).
 *
 * Route: /app/job-chat/:token
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { API_BASE, apiFetch, transcribeAudio } from '../lib/api';
import {localMode} from '../lib/runtime';
import { track } from '../lib/tracking';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { LanguageToggle } from '../components/LanguageToggle';
import ChatInput from '../components/chat/ChatInput';
import { VoiceNoteBubble } from '@scope/ui';
import { Button } from '@scope/ui';

interface JobMessage {
  id: string;
  scope_token: string;
  sender_role: 'homeowner' | 'contractor';
  sender_id: string;
  body: string;
  created_at: string;
  /** Client-side only — blob URL for voice playback before server confirms */
  voiceUrl?: string;
  voiceDuration?: number;
  waveform?: number[];
  isVoice?: boolean;
}

function useSenderInfo(): { role: 'homeowner' | 'contractor'; id: string } {
  const { role: authRole, contractorId, user } = useAuth();
  if (authRole === 'contractor' && contractorId) return { role: 'contractor', id: contractorId };
  if (authRole === 'homeowner' && user?.id) return { role: 'homeowner', id: user.id };
  return { role: 'homeowner', id: 'anonymous' };
}

/** Format timestamp for display above message groups */
function formatGroupTime(isoString: string): string {
  const d = new Date(isoString);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = d.toDateString() === yesterday.toDateString();

  const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  if (isToday) return time;
  if (isYesterday) return `Yesterday · ${time}`;
  return `${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })} · ${time}`;
}

/** Returns true if two messages are in the same "group" (same sender, within 5 min) */
function isSameGroup(a: JobMessage, b: JobMessage): boolean {
  if (a.sender_role !== b.sender_role) return false;
  const diff = Math.abs(new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  return diff < 5 * 60 * 1000;
}

function MessageBubble({
  message,
  myRole,
  showTimestamp,
}: {
  message: JobMessage;
  myRole: string;
  showTimestamp: boolean;
}) {
  const isMe = message.sender_role === myRole;

  return (
    <div className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
      {showTimestamp && (
        <p className="text-[10px] text-muted mb-1.5 px-1">
          {formatGroupTime(message.created_at)}
        </p>
      )}

      {message.isVoice && message.voiceDuration !== undefined && message.waveform ? (
        <div className={`max-w-[78%] ${isMe ? 'self-end' : 'self-start'}`}>
          <VoiceNoteBubble
            durationSec={message.voiceDuration}
            waveform={message.waveform}
            transcript={message.body}
            audioUrl={message.voiceUrl}
          />
        </div>
      ) : (
        <div
          className={`max-w-[78%] px-4 py-2.5 rounded-sm text-sm leading-relaxed ${
            isMe
              ? 'bg-ink text-cream rounded-br-sm'
              : 'bg-white border border-border text-ink rounded-bl-sm'
          }`}
        >
          {          !isMe && (
            <p className="text-[10px] font-semibold mb-0.5" style={{ color: 'var(--color-terracotta)' }}>
              {message.sender_role === 'contractor' ? 'Contractor' : 'Homeowner'}
            </p>
          )}
          <p className="whitespace-pre-wrap">{message.body}</p>
        </div>
      )}
    </div>
  );
}

/** Skeleton loading state — alternating bubble placeholders */
function ChatSkeleton() {
  return (
    <div className="flex flex-col gap-3 px-4 py-4">
      {[false, true, false, false, true].map((isMe, i) => (
        <div key={i} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
          <div
            className="h-9 rounded-sm bg-border/60 animate-pulse"
            style={{ width: `${45 + (i % 3) * 15}%` }}
          />
        </div>
      ))}
    </div>
  );
}

export default function JobChat() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { role: myRole, id: senderId } = useSenderInfo();

  const [messages, setMessages] = useState<JobMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const bottomPadRef = useRef<HTMLDivElement>(null);
  const [bottomPad, setBottomPad] = useState(80);

  const scrollToBottom = useCallback((smooth = true) => {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'instant' });
  }, []);

  // Measure input bar height for scroll padding
  useEffect(() => {
    const el = bottomPadRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setBottomPad(el.getBoundingClientRect().height + 8);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Load message history
  useEffect(() => {
    if (!token) return;
    apiFetch(`${API_BASE}/v1/messages/${token}`)
      .then((r) => r.json())
      .then((data) => {
        setMessages(Array.isArray(data) ? data : []);
        setLoadingHistory(false);
        setTimeout(() => scrollToBottom(false), 50);
      })
      .catch(() => setLoadingHistory(false));
  }, [token, scrollToBottom]);

  // Supabase Realtime subscription
  useEffect(() => {
    if (!token) return;
    if (localMode) {
      const timer = window.setInterval(() => {
        apiFetch(`${API_BASE}/v1/messages/${token}`).then(r => r.json()).then(data => {
          if (Array.isArray(data)) setMessages(data);
        }).catch(() => {});
      }, 2500);
      return () => window.clearInterval(timer);
    }
    const channel = supabase.channel(`job:${token}`, {
      config: { broadcast: { self: false } },
    });
    channel
      .on('broadcast', { event: 'INSERT' }, (payload) => {
        const newMsg = payload.payload as JobMessage;
        setMessages((prev) => {
          if (prev.some((m) => m.id === newMsg.id)) return prev;
          return [...prev, newMsg];
        });
        setTimeout(() => scrollToBottom(), 50);
      })
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [token, scrollToBottom]);

  const handleSendText = useCallback(async (text: string) => {
    const body = text.trim();
    if (!body || !token) return;

    track('chat.message_sent', { token, sender_role: myRole });

    const optimistic: JobMessage = {
      id: `optimistic-${Date.now()}`,
      scope_token: token,
      sender_role: myRole,
      sender_id: senderId,
      body,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    setTimeout(() => scrollToBottom(), 50);

    try {
      const resp = await apiFetch(`${API_BASE}/v1/messages/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quote_token: token, sender_role: myRole, sender_id: senderId, body }),
      });
      if (!resp.ok) throw new Error('Send failed');
      const data = await resp.json();
      if (data.message?.id) {
        setMessages((prev) => prev.map((m) => m.id === optimistic.id ? data.message : m));
      }
    } catch {
      // Keep message visible but mark as failed — don't revert to input
      // (revert was the bug: message disappeared)
    }
  }, [token, myRole, senderId, scrollToBottom]);

  const handleSendVoice = useCallback(async (blob: Blob, duration: number, waveform: number[]) => {
    if (!token) return;
    track('chat.voice_sent', { token, sender_role: myRole });

    const voiceUrl = URL.createObjectURL(blob);
    const optimistic: JobMessage = {
      id: `optimistic-voice-${Date.now()}`,
      scope_token: token,
      sender_role: myRole,
      sender_id: senderId,
      body: '…',
      created_at: new Date().toISOString(),
      isVoice: true,
      voiceUrl,
      voiceDuration: duration,
      waveform,
    };
    setMessages((prev) => [...prev, optimistic]);
    setTimeout(() => scrollToBottom(), 50);

    try {
      // Transcribe then send as text message with voice marker
      const result = await transcribeAudio(blob, { polish: false });
      const transcript = result.text;
      const body = transcript || '[Voice note]';

      const resp = await apiFetch(`${API_BASE}/v1/messages/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quote_token: token, sender_role: myRole, sender_id: senderId, body }),
      });
      if (!resp.ok) throw new Error('Send failed');
      const data = await resp.json();
      if (data.message?.id) {
        // Preserve voice UI on the confirmed message
        setMessages((prev) => prev.map((m) =>
          m.id === optimistic.id
            ? { ...data.message, isVoice: true, voiceUrl, voiceDuration: duration, waveform, body }
            : m
        ));
      }
    } catch {
      // Keep voice bubble visible even if send fails
    }
  }, [token, myRole, senderId, scrollToBottom]);

  return (
    <div className="flex flex-col h-dvh bg-cream">
      {/* Dark header — matches MyProject */}
      <header
        className="shrink-0 flex items-center gap-3 px-4 h-14"
        style={{ background: 'var(--color-ink)', paddingTop: 'env(safe-area-inset-top, 0px)' }}
      >
        <Button
          type="button"
          onClick={() => navigate(`/project/${token}`)}
          className="text-cream/60 hover:text-cream transition-colors"
          aria-label="Back to project"
        >
          <ArrowLeft size={20} />
        </Button>
        <div className="flex-1">
          <h1 className="text-sm font-semibold text-cream">{t('jobchat_header_title')}</h1>
          <p className="text-[11px]" style={{ color: 'rgba(250,248,244,0.45)' }}>
            {myRole === 'contractor' ? t('jobchat_subtitle_contractor') : t('jobchat_subtitle_homeowner')}
          </p>
        </div>
        <LanguageToggle variant="dark" />
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto" style={{ paddingBottom: bottomPad }}>
        {loadingHistory ? (
          <ChatSkeleton />
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-stone text-center px-8 leading-relaxed">
              {myRole === 'contractor'
                ? 'Start the conversation with the homeowner.'
                : 'Message your contractor about what you need.'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-1.5 px-4 pt-4">
            {messages.map((msg, idx) => {
              const prev = idx > 0 ? messages[idx - 1] : null;
              const showTimestamp = !prev || !isSameGroup(prev, msg);
              return (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  myRole={myRole}
                  showTimestamp={showTimestamp}
                />
              );
            })}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar — shared ChatInput with voice support */}
      <div ref={bottomPadRef} className="shrink-0 border-t border-border bg-cream">
        {loadingHistory && (
          <div className="flex items-center justify-center py-3">
            <Loader2 size={16} className="text-muted animate-spin" />
          </div>
        )}
        {!loadingHistory && (
          <ChatInput
            onSendText={handleSendText}
            onSendVoice={handleSendVoice}
            placeholder="Type a message…"
          />
        )}
      </div>
    </div>
  );
}
