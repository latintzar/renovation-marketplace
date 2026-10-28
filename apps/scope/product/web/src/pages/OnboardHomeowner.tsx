import { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useChat } from '../hooks/useChat';
import { useReelChatDriver } from '../reel/useReelChatDriver';
import { consumeHandoff } from '../lib/handoff';
import ChatShell from '../components/chat/ChatShell';
import { LanguageToggle } from '../components/LanguageToggle';
import { CustomDrawerBody } from '../components/chat/CustomDrawerBody';
import type { BriefUpdate } from '../lib/api';
import type { Message } from '../types';
import { BriefCanvas } from '@scope/ui';

const SAMPLE_BRIEF: BriefUpdate = {
  title: 'Bathroom Renovation',
  description: 'Strip existing tiles & fittings. Relocate waste pipes for new walk-in shower position. Supply and fit wall-hung vanity, rimless WC, and thermostatic shower valve. Full-height tiling in wet areas, half-height elsewhere.',
  location: 'Marbella, Málaga',
  urgency: 'Next 2–3 weeks',
  materials_mentioned: 'Porcelanosa large-format tiles, Roca Inspira suite',
  measurements: '2.4 m × 3.1 m (approx. 7.4 m²)',
  budget_indication: '€6,500 – €9,000',
  status: 'solid',
};

/** Collect all user-attached photo object-URLs from message history. */
function collectPhotos(messages: Message[]): string[] {
  const urls: string[] = [];
  for (const m of messages) {
    if (m.role === 'user' && m.photoUrls?.length) {
      for (const u of m.photoUrls) urls.push(u);
    }
  }
  return urls;
}

const OnboardHomeowner = () => {
  const { t } = useTranslation();
  const handoff = useMemo(() => consumeHandoff(), []);

  const initialText = handoff.text || '';
  const locale = handoff.lang || '';
  const locationHint = handoff.location || '';
  const phoneHint = handoff.phone || '';

  const pageLocale = locale || (
    typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('es')
      ? 'es'
      : 'en'
  );

  const leadContext = useMemo(() => {
    const parts: string[] = [];
    if (locationHint) {
      parts.push(`Location: ${locationHint}`);
      parts.push('Location already confirmed in the popup before chat.');
    }
    if (phoneHint) {
      parts.push(`WhatsApp number already collected: ${phoneHint}`);
    }
    return parts.join('. ');
  }, [locationHint, phoneHint]);

  const chat = useChat({
    mode: 'quote_intake',
    audience: 'homeowner',
    pageLocale,
    leadContext: leadContext || undefined,
  });

  // Reel mode: auto-play the scripted "post a job" walkthrough (no-op otherwise).
  useReelChatDriver(chat, 'post-job');

  useEffect(() => {
    if (initialText && chat.messages.length === 0 && !chat.didRestore) {
      void chat.sendTextMessage(initialText);
    }
    // Only fire once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const userPhotos = useMemo(() => collectPhotos(chat.messages), [chat.messages]);

  const handleConfirm = () => {
    void chat.confirmAction('brief');
  };

  const customDrawerContent =
    chat.drawerState?.content_type === 'custom' ? (
      <CustomDrawerBody ds={chat.drawerState} />
    ) : undefined;

  return (
    <ChatShell
      title={t('homeowner_title')}
      headerRight={<LanguageToggle variant="light" />}
      messages={chat.messages}
      isThinking={chat.isThinking}
      status={chat.status}
      previewState={chat.previewState}
      previewContent={<BriefCanvas b={chat.briefUpdate} photos={userPhotos} />}
      placeholderContent={<BriefCanvas b={SAMPLE_BRIEF} />}
      emptyPreviewLabel={t('homeowner_empty_preview')}
      customDrawerContent={customDrawerContent}
      onSendText={chat.sendTextMessage}
      onSendVoice={chat.sendVoiceMessage}
      onComposingChange={chat.handleComposingChange}
      onConfirm={handleConfirm}
      confirmLabel={t('homeowner_post_job')}
      confirmed={chat.confirmed}
      previewLabelClosed={t('homeowner_preview_closed')}
      previewLabelOpen={t('homeowner_preview_open')}
      drawerState={chat.drawerState}
      onDrawerAction={chat.handleDrawerAction}
    />
  );
};

export default OnboardHomeowner;
