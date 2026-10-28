/**
 * Typing dots while the agent is processing (shown when isThinking and no streaming text).
 */
const ThinkingIndicator = () => (
  <div className="flex items-center gap-1.5 py-2 px-1" aria-live="polite" aria-label="Leo is thinking">
    <span className="inline-block w-2 h-2 rounded-full bg-stone typing-dot" />
    <span className="inline-block w-2 h-2 rounded-full bg-stone typing-dot" />
    <span className="inline-block w-2 h-2 rounded-full bg-stone typing-dot" />
  </div>
);

export default ThinkingIndicator;
