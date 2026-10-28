export type MessageRole = 'user' | 'leo' | 'system';

export type MessageVariant =
  | 'text'
  | 'voice'
  | 'trace'
  | 'confirm'
  | 'research'
  | 'context'
  | 'options'
  | 'copy_block';

export interface Message {
  id: string;
  role: MessageRole;
  variant: MessageVariant;
  content: string;
  timestamp: number;
  voiceUrl?: string;
  voiceDuration?: number;
  /** Amplitude snapshot (0–1 per bar) captured at recording stop, for VoiceNoteBubble */
  waveform?: number[];
  transcription?: string;
  confirmed?: boolean;
  source?: string;
  options?: string[];
  /** Local object-URL thumbnails for attached photos */
  photoUrls?: string[];
  /** Base64-encoded images to send to the LLM */
  images?: { media_type: string; data: string }[];
  /**
   * When true, the message is not rendered in the chat UI but IS included
   * in the history sent to Hermes. Used for silent triggers and language-switch signals.
   */
  hidden?: boolean;
}

export type LiveModeState = 'idle' | 'listening' | 'thinking' | 'speaking';
