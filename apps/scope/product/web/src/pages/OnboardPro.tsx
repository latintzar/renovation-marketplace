/**
 * OnboardPro — Professional (tradesperson) onboarding chat.
 *
 * Two modes:
 *  - Normal: starts the chat, optionally with an import URL already processed
 *    (importUrl in handoff, but this path is now handled by ImportPro.tsx).
 *  - Edit mode (handoff.edit = true): loads an existing profile from the canvas
 *    API, opens the chat with the preview pre-opened so the contractor can
 *    immediately see their profile and start editing via conversation.
 */

import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useChat } from '../hooks/useChat';
import { consumeHandoff } from '../lib/handoff';
import ChatShell from '../components/chat/ChatShell';
import { LanguageToggle } from '../components/LanguageToggle';
import { CustomDrawerBody } from '../components/chat/CustomDrawerBody';
import { importProfile, type ProfileUpdate } from '../lib/api';
import { useCanvasQuery } from '../hooks/useCanvasQuery';
import { isReel, reelFlowId } from '../reel/flag';
import { useReelUi, prefersReducedMotion } from '../reel/engine';
import { ProfileCanvas } from '@scope/ui';

const SAMPLE_PROFILE: ProfileUpdate = {
  business_name: 'Costa del Sol Renovations',
  trade: 'General Contractor — Renovations',
  location: 'Estepona, Málaga',
  service_area_km: '40',
  services: 'Full bathroom & kitchen renovations\nTiling & waterproofing\nPlumbing first & second fix\nElectrical upgrades',
  bio: 'Family-run renovation company since 2012. We specialise in coastal property renovations for both local and international clients.',
  years_experience: '14',
  languages: 'Spanish, English',
  certifications: 'Activity Licence · Public Liability Insurance',
};

const SHIMMER_STEPS_KEYS = [
  'shimmer_scanning',
  'shimmer_gallery',
  'shimmer_services',
  'shimmer_reviews',
  'shimmer_building',
] as const;

const OnboardPro = () => {
  const { t } = useTranslation();
  const SHIMMER_STEPS = SHIMMER_STEPS_KEYS.map((k) => t(k));
  const handoff = useMemo(() => consumeHandoff(), []);

  const importUrl = handoff.import || '';
  const phone = handoff.phone || '';
  const locale = handoff.lang || '';
  const jobId = handoff.jobId || '';
  /** Edit mode: skip import, load existing profile, open preview immediately */
  const isEditMode = handoff.edit === true;
  const editContractorId = handoff.contractorId || '';
  const phoneDiscrepancy = handoff.phone_discrepancy as { habitissimo_phone: string; known_phone: string } | undefined;

  const [importRunning, setImportRunning] = useState(false);
  const [shimmerStep, setShimmerStep] = useState('');
  const [importedProfile, setImportedProfile] = useState<ProfileUpdate | null>(null);
  const [contractorId] = useState(() => editContractorId || `web-${globalThis.crypto?.randomUUID?.() ?? Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('')}`);

  const pageLocale = locale || (
    typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('es')
      ? 'es'
      : 'en'
  );

  const profileContext = useMemo(() => {
    if (!importedProfile) return undefined;
    const parts: string[] = [];
    if (importedProfile.business_name) parts.push(`Business: ${importedProfile.business_name}`);
    if (importedProfile.trade) parts.push(`Trade: ${importedProfile.trade}`);
    if (importedProfile.location) parts.push(`Location: ${importedProfile.location}`);
    if (importedProfile.services) parts.push(`Services: ${importedProfile.services}`);
    return parts.length ? parts.join('. ') : undefined;
  }, [importedProfile]);

  const leadContext = useMemo(() => {
    const parts: string[] = [];
    if (jobId) {
      parts.push(`This contractor arrived via a job outreach. Job ID: ${jobId}. After they confirm their profile, link it to this job.`);
    }
    if (phoneDiscrepancy) {
      parts.push(
        `PHONE DISCREPANCY: We found two different phone numbers for this contractor. ` +
        `Habitissimo shows "${phoneDiscrepancy.habitissimo_phone}", but they contacted us on "${phoneDiscrepancy.known_phone}". ` +
        `Early in the conversation, ask them in a friendly, natural way which number they'd like to use — ` +
        `something like "By the way, we spotted two numbers — which one is best to reach you on?" ` +
        `Update the profile phone once they confirm.`
      );
    }
    return parts.length ? parts.join(' ') : undefined;
  }, [jobId, phoneDiscrepancy]);

  const chat = useChat({
    mode: 'quote_intake',
    audience: 'professional',
    pageLocale,
    profileContext,
    leadContext,
    contractorId,
  });

  /** In edit mode, pre-load the profile from the canvas API, inject into chat state, and send a greeting */
  const { data: editCanvasData } = useCanvasQuery(isEditMode && editContractorId ? editContractorId : undefined);
  const editLoadedRef = useRef(false);
  useEffect(() => {
    if (!isEditMode || !editCanvasData || editLoadedRef.current) return;
    editLoadedRef.current = true;
    const profile = editCanvasData.profile;
    if (profile && (profile.business_name || profile.trade)) {
      setImportedProfile(profile);
      chat.setProfileUpdate(profile);
      const name = profile.business_name || 'your business';
      void chat.sendTextMessage(
        `I'd like to review and edit my profile. My business is ${name}.`,
      );
    } else {
      void chat.sendTextMessage("I'd like to review and edit my profile.");
    }
  }, [isEditMode, editCanvasData]); // eslint-disable-line react-hooks/exhaustive-deps

  const runImport = useCallback(async (url: string) => {
    setImportRunning(true);
    setShimmerStep(SHIMMER_STEPS[0]);
    let stepIdx = 0;
    const shimmerInterval = setInterval(() => {
      stepIdx = Math.min(stepIdx + 1, SHIMMER_STEPS.length - 1);
      setShimmerStep(SHIMMER_STEPS[stepIdx]);
    }, 2400);

    try {
      let lastProfile: ProfileUpdate | null = null;
      for await (const evt of importProfile(url, contractorId)) {
        if (evt.type === 'progress') {
          const step = (evt as { step?: string }).step;
          if (step) setShimmerStep(step);
        }
        if (evt.type === 'result') {
          const profile = (evt as { profile?: Record<string, unknown> }).profile;
          if (profile) lastProfile = profile as unknown as ProfileUpdate;
        }
        if (evt.type === 'error') {
          const msg = (evt as { message?: string }).message || 'Unknown error';
          chat.appendTrace(`Import error: ${msg}`);
        }
      }
      if (lastProfile) {
        setImportedProfile(lastProfile);
        // Reel: push into chat state too so the preview un-blurs to 'ready'.
        if (isReel()) chat.setProfileUpdate(lastProfile);
        chat.appendTrace('Profile imported successfully');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Import failed';
      chat.appendTrace(`Import failed: ${msg}`);
    } finally {
      clearInterval(shimmerInterval);
      setImportRunning(false);
      setShimmerStep('');
    }
  }, [chat, contractorId]);

  useEffect(() => {
    if (importUrl && !isEditMode && !importRunning && !importedProfile && !chat.didRestore) {
      void runImport(importUrl);
    }
    // Only fire once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reel mode: loop the "paste your link → real profile imported" walkthrough.
  useEffect(() => {
    if (!isReel() || reelFlowId() !== 'import-profile') return;
    let cancelled = false;
    const reduced = prefersReducedMotion();
    const setCaption = useReelUi.getState().setCaption;
    const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
    async function loop() {
      do {
        if (cancelled) return;
        setImportedProfile(null);
        chat.reset();
        setCaption('A tradesperson pastes their existing Habitissimo link.');
        await wait(reduced ? 0 : 1600);
        if (cancelled) return;
        setCaption('Leo imports their real profile — reviews, ratings, history.');
        await runImport('https://www.habitissimo.es/pro/todobarro');
        if (cancelled) return;
        setCaption('Done in seconds. Refine it by chatting — no forms to fill.');
        await wait(reduced ? 0 : 7000);
      } while (!reduced && !cancelled);
    }
    void loop();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (phone && chat.messages.length === 0 && !importUrl && !chat.didRestore) {
      void chat.sendTextMessage(`My phone number is ${phone}. I'd like to create my profile.`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleConfirm = () => {
    void chat.confirmAction('profile');
  };

  const displayProfile = importedProfile || chat.profileUpdate;

  const customDrawerContent =
    chat.drawerState?.content_type === 'custom' ? (
      <CustomDrawerBody ds={chat.drawerState} />
    ) : undefined;

  return (
    <>
      {importRunning && shimmerStep && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-cream/95 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-6 max-w-xs text-center">
            <div className="w-12 h-12 rounded-full border-2 border-terracotta border-t-transparent animate-spin" />
            <p className="text-ink font-medium text-lg animate-pulse">{shimmerStep}</p>
            <p className="text-muted text-sm">{t('import_time_estimate')}</p>
          </div>
        </div>
      )}
      <ChatShell
        title={isEditMode ? t('pro_title_edit') : t('pro_title_create')}
        headerRight={<LanguageToggle variant="light" />}
        messages={chat.messages}
        isThinking={chat.isThinking}
        status={chat.status}
        previewState={chat.previewState}
        previewContent={<ProfileCanvas p={displayProfile} />}
        placeholderContent={<ProfileCanvas p={SAMPLE_PROFILE} />}
        emptyPreviewLabel={t('pro_empty_preview')}
        customDrawerContent={customDrawerContent}
        onSendText={chat.sendTextMessage}
        onSendVoice={chat.sendVoiceMessage}
        onComposingChange={chat.handleComposingChange}
        onConfirm={handleConfirm}
        confirmLabel={t('pro_save_profile')}
        confirmed={chat.confirmed}
        confirmMode="profile"
        previewLabelClosed={t('pro_preview_closed')}
        previewLabelOpen={t('pro_preview_open')}
        drawerState={chat.drawerState}
        onDrawerAction={chat.handleDrawerAction}
        initialPreviewOpen={isEditMode}
      />
    </>
  );
};

export default OnboardPro;
