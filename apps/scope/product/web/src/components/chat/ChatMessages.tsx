import { useEffect, useRef, type ReactNode } from 'react';
import type { Message } from '../../types';
import ChatMessage from './ChatMessage';
import ThinkingIndicator from './ThinkingIndicator';

interface ChatMessagesProps {
  messages: Message[];
  isThinking: boolean;
  bottomPadding?: number;
  /** Rendered immediately after the first message — used for inline action chips (e.g. language switch) */
  afterFirstMessageSlot?: ReactNode;
}

const ChatMessages = ({ messages, isThinking, bottomPadding = 180, afterFirstMessageSlot }: ChatMessagesProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      stickRef.current = atBottom;
    };
    el.addEventListener('scroll', handler, { passive: true });
    return () => el.removeEventListener('scroll', handler);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !stickRef.current) return;
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }, [messages, isThinking, bottomPadding]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 overflow-y-auto px-4 pt-3 space-y-4"
      style={{ paddingBottom: bottomPadding }}
    >
      {messages.map((m, idx) => (
        <div key={m.id}>
          <ChatMessage message={m} />
          {idx === 0 && afterFirstMessageSlot ? (
            <div className="mt-2">{afterFirstMessageSlot}</div>
          ) : null}
        </div>
      ))}
      {isThinking ? (
        <div className="pl-0">
          <ThinkingIndicator />
        </div>
      ) : null}
    </div>
  );
};

export default ChatMessages;
