/**
 * FirstQuote — Hermes-powered scope builder for contractors.
 *
 * Features:
 *   - Location picker shown upfront (before chat) — location pre-filled in leadContext
 *   - Full voice + photo Hermes chat with scope preview
 *   - editToken URL param for editing existing scopes (token stays the same)
 *   - FinalizeModal skips Stripe KYC if already verified (stripe_onboarding_complete flag)
 */

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowRight, ChevronLeft, Pencil, Check, X, Trash2 } from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { useReelChatDriver } from '../reel/useReelChatDriver';
import { isReel } from '../reel/flag';
import ChatShell from '../components/chat/ChatShell';
import { LanguageToggle } from '../components/LanguageToggle';
import EditableQuoteCanvas from '../components/EditableQuoteCanvas';
import LocationPickerModal from '../components/LocationPickerModal';
import { QuoteCanvas , Button } from '@scope/ui';
import { type QuoteUpdate, updateScope } from '../lib/api';
import {localMode} from '../lib/runtime';
import {toast} from 'sonner';
import i18n from '../i18n';
import { useAuth } from '../context/AuthContext';
import { getLeoAuth, mergeLeoAuth } from '../lib/utils';
import { useCanvasQuery } from '../hooks/useCanvasQuery';
import { FinalizeModal } from '../components/quote/FinalizeModal';

// ── Scope placeholder — shown behind vellum in empty/building states ─────────
// Needs real structure so shapes ghost through the blur properly.
const SCOPE_PLACEHOLDER: QuoteUpdate = {
  title: 'Bathroom Renovation — Marbella',
  description: 'Full renovation: strip-out, large-format tiling, sanitary installation, and final paintwork.',
  contractor_name: '',
  client_name: '',
  location: 'Marbella',
  line_items: [
    { description: 'Strip-out and debris removal', amount: 650, duration_label: '1 day' },
    { description: 'Large-format porcelain tiling (60×60)', amount: 1350, duration_label: '3 days' },
    { description: 'Sanitary ware and plumbing installation', amount: 1100, duration_label: '2 days' },
    { description: 'Paintwork and finishing', amount: 350, duration_label: '1 day' },
  ],
  service_fee_percent: 5,
  materials_upfront: 800,
  iva_rate: 10,
  terms: ['Completion time: 8 working days', 'Quote valid for 30 days'],
  status: 'draft',
  created_at: '',
  contingency_drafts: [],
};

// ── Spanish bank logos ────────────────────────────────────────────────────────


// ── Finalize screen (full-screen overlay) ─────────────────────────────────────


// ── Change summary for edit mode ─────────────────────────────────────────────
// Diffs two scope snapshots and returns a natural-language description of what
// changed. The string is sent to Hermes as a user message so it can acknowledge
// and continue the conversation.

function generateChangeSummary(before: QuoteUpdate, after: QuoteUpdate, lang: 'es' | 'en'): string {
  const changes: string[] = [];

  if (before.title !== after.title && after.title) {
    changes.push(lang === 'es'
      ? `cambié el título a "${after.title}"`
      : `changed the title to "${after.title}"`);
  }
  if (before.description !== after.description && after.description) {
    changes.push(lang === 'es' ? 'actualicé la descripción' : 'updated the description');
  }
  if (before.location !== after.location && after.location) {
    changes.push(lang === 'es'
      ? `cambié la ubicación a ${after.location}`
      : `changed the location to ${after.location}`);
  }

  const beforeItems = before.line_items || [];
  const afterItems = after.line_items || [];

  afterItems.forEach((item, i) => {
    const prev = beforeItems[i];
    if (!prev) {
      changes.push(lang === 'es'
        ? `añadí la fase "${item.description}"${item.duration_label ? ` (${item.duration_label})` : ''} por €${item.amount}`
        : `added phase "${item.description}"${item.duration_label ? ` (${item.duration_label})` : ''} for €${item.amount}`);
    } else {
      const subChanges: string[] = [];
      if (prev.description !== item.description)
        subChanges.push(lang === 'es' ? `nombre → "${item.description}"` : `name → "${item.description}"`);
      if (prev.amount !== item.amount)
        subChanges.push(lang === 'es' ? `precio → €${item.amount}` : `price → €${item.amount}`);
      if ((prev.duration_label ?? '') !== (item.duration_label ?? '') && item.duration_label)
        subChanges.push(lang === 'es' ? `duración → ${item.duration_label}` : `duration → ${item.duration_label}`);
      if (subChanges.length > 0) {
        changes.push(lang === 'es'
          ? `fase ${i + 1} ("${prev.description}"): ${subChanges.join(', ')}`
          : `phase ${i + 1} ("${prev.description}"): ${subChanges.join(', ')}`);
      }
    }
  });

  beforeItems.forEach((item, i) => {
    if (i >= afterItems.length) {
      changes.push(lang === 'es'
        ? `eliminé la fase "${item.description}"`
        : `removed phase "${item.description}"`);
    }
  });

  // Materials upfront
  if ((before.materials_upfront ?? 0) !== (after.materials_upfront ?? 0)) {
    const amt = after.materials_upfront ?? 0;
    changes.push(lang === 'es'
      ? amt > 0 ? `adelanto de materiales: €${amt}` : 'eliminé el adelanto de materiales'
      : amt > 0 ? `materials upfront: €${amt}` : 'removed materials upfront');
  }

  // IVA
  if ((before.iva_rate ?? null) !== (after.iva_rate ?? null)) {
    if (after.iva_rate) {
      changes.push(lang === 'es' ? `IVA al ${after.iva_rate}%` : `VAT at ${after.iva_rate}%`);
    } else {
      changes.push(lang === 'es' ? 'IVA ya incluido en los precios' : 'VAT included in prices');
    }
  }

  if (changes.length === 0) return '';
  const prefix = lang === 'es'
    ? 'He hecho cambios directamente en el presupuesto: '
    : 'I made some direct edits to the quote: ';
  return prefix + changes.join('; ') + '.';
}

// ── EditModeWrapper ───────────────────────────────────────────────────────────
// Wraps the canvas with a read-only / edit-mode toggle bar at the bottom.
// Read-only shows QuoteCanvas; edit mode shows EditableQuoteCanvas with
// Save / Cancel controls. Saving sends the diff summary to Hermes as a message.

// Edit button floats inside the dark canvas header (top-right corner).
// Save/Cancel appear in a small bottom bar only while editing.
function EditModeWrapper({
  scope,
  lang,
  isEditMode,
  isThinking,
  onEnterEdit,
  onSaveEdits,
  onCancelEdit,
  onChange,
}: {
  scope: QuoteUpdate;
  lang: 'es' | 'en';
  isEditMode: boolean;
  isThinking: boolean;
  onEnterEdit: () => void;
  onSaveEdits: () => void;
  onCancelEdit: () => void;
  onChange: (updated: QuoteUpdate) => void;
}) {
  return (
    <div className="flex flex-col h-full">
      {/* Canvas — edit button floats in top-right of dark header */}
      <div className="flex-1 min-h-0 overflow-hidden relative">
        {isEditMode
          ? <EditableQuoteCanvas scope={scope} onChange={onChange} lang={lang} />
          : <QuoteCanvas scope={scope} />
        }

        {/* Edit / Save pill — floats over the dark header area */}
        {!isEditMode ? (
          <Button size="sm" className="absolute top-3 right-3 text-[11px] transition-opacity disabled:opacity-0" type="button"
            onClick={onEnterEdit}
            disabled={isThinking}
            style={{
              background: 'rgba(250,248,244,0.12)',
              color: 'rgba(250,248,244,0.75)',
              border: '1px solid rgba(250,248,244,0.15)',
              backdropFilter: 'blur(4px)',
            }}><Pencil size={10} strokeWidth={2.5} />
            {lang === 'es' ? 'Editar' : 'Edit'}</Button>
        ) : (
          <Button size="sm" className="absolute top-3 right-3 text-[11px] transition-opacity" type="button"
            onClick={onSaveEdits}
            style={{
              background: 'rgba(198,93,58,0.85)',
              color: 'var(--color-cream)',
              border: '1px solid rgba(198,93,58,0.4)',
              backdropFilter: 'blur(4px)',
            }}><Check size={10} strokeWidth={2.5} />
            {lang === 'es' ? 'Guardar' : 'Save'}</Button>
        )}
      </div>

      {/* Cancel bar — only shown during edit mode */}
      {isEditMode && (
        <div className="shrink-0 border-t border-border bg-cream/95 backdrop-blur-sm px-4 py-2 flex items-center justify-end">
          <Button variant="ghost" size="sm" className="text-stone" type="button"
            onClick={onCancelEdit}><X size={11} strokeWidth={2} />
            {lang === 'es' ? 'Cancelar edición' : 'Cancel edit'}</Button>
        </div>
      )}
    </div>
  );
}

// ── ChatMode (scope builder chat) ─────────────────────────────────────────────

function ChatMode({
  contractorId,
  contractorName,
  lang,
  location,
  editToken,
  initialScope,
  isFirstQuote,
  onLangChange,
  onScopeReady,
  onStartFresh,
  onGoToDashboard,
}: {
  contractorId: string;
  contractorName: string;
  lang: 'es' | 'en';
  location: string;
  editToken?: string;
  initialScope?: QuoteUpdate | null;
  isFirstQuote?: boolean;
  onLangChange: (l: 'es' | 'en') => void;
  onScopeReady: (scope: QuoteUpdate) => void;
  onStartFresh?: () => void;
  onGoToDashboard?: () => void;
})
 {
  const [langSwitchDone, setLangSwitchDone] = useState(false);
  const leadContext = useMemo(() => {
    const parts: string[] = [];
    if (contractorName) parts.push(`Contractor: ${contractorName}`);
    if (location) parts.push(`Location: ${location}`);
    parts.push('Quote builder mode: creating a quote for an upcoming job.');
    return parts.join(' ');
  }, [contractorName, location]);

  const chat = useChat({
    mode: 'quote',
    audience: 'professional',
    pageLocale: lang,
    leadContext,
    contractorId,
    initialScope,
  });

  // Reel mode: auto-play the scripted "build a scope" walkthrough (no-op otherwise).
  useReelChatDriver(chat, 'set-milestones');

  // Local editable scope — starts as chat.scopeUpdate (or initialScope in edit mode).
  // When Hermes pushes an update, merge Hermes fields over local state.
  // While in edit mode we hold off Hermes merges so the user's in-progress edits aren't clobbered.
  const [localScope, setLocalScope] = useState<QuoteUpdate | null>(initialScope ?? null);
  const prevHermesScopeRef = useRef<QuoteUpdate | null>(null);

  // Edit mode state
  const [isEditMode, setIsEditMode] = useState(false);
  const preEditSnapshotRef = useRef<QuoteUpdate | null>(null);

  // When incremented, ChatShell closes the mobile preview panel
  const [closePreviewCount, setClosePreviewCount] = useState(0);

  useEffect(() => {
    if (!chat.scopeUpdate) return;
    // Don't clobber in-progress user edits
    if (isEditMode) return;
    const hermes = chat.scopeUpdate;
    if (localScope === null) {
      setLocalScope(hermes);
    } else {
      const prev = prevHermesScopeRef.current;
      if (!prev || JSON.stringify(hermes) !== JSON.stringify(prev)) {
        setLocalScope((local) => {
          if (!local) return hermes;
          return {
            ...local,
            ...(hermes.title !== prev?.title ? { title: hermes.title } : {}),
            ...(hermes.description !== prev?.description ? { description: hermes.description } : {}),
            ...(hermes.location !== prev?.location ? { location: hermes.location } : {}),
            ...(hermes.status !== prev?.status ? { status: hermes.status } : {}),
            ...(JSON.stringify(hermes.line_items) !== JSON.stringify(prev?.line_items)
              ? { line_items: hermes.line_items }
              : {}),
            ...(JSON.stringify(hermes.contingency_drafts) !== JSON.stringify(prev?.contingency_drafts)
              ? { contingency_drafts: hermes.contingency_drafts }
              : {}),
            ...(JSON.stringify(hermes.terms) !== JSON.stringify(prev?.terms) ? { terms: hermes.terms } : {}),
            ...(hermes.service_fee_percent !== prev?.service_fee_percent
              ? { service_fee_percent: hermes.service_fee_percent }
              : {}),
            ...(hermes.materials_upfront !== prev?.materials_upfront
              ? { materials_upfront: hermes.materials_upfront }
              : {}),
            ...(hermes.iva_rate !== prev?.iva_rate
              ? { iva_rate: hermes.iva_rate }
              : {}),
            ...(JSON.stringify(hermes.payment_schedule) !== JSON.stringify(prev?.payment_schedule)
              ? { payment_schedule: hermes.payment_schedule }
              : {}),
            ...(hermes.contractor_name !== prev?.contractor_name
              ? { contractor_name: hermes.contractor_name }
              : {}),
            ...(hermes.client_name !== prev?.client_name ? { client_name: hermes.client_name } : {}),
          };
        });
      }
    }
    prevHermesScopeRef.current = hermes;
  }, [chat.scopeUpdate, isEditMode]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleEnterEdit = useCallback(() => {
    preEditSnapshotRef.current = localScope ?? chat.scopeUpdate ?? null;
    setIsEditMode(true);
  }, [localScope, chat.scopeUpdate]);

  const handleCancelEdit = useCallback(() => {
    if (preEditSnapshotRef.current) {
      setLocalScope(preEditSnapshotRef.current);
    }
    setIsEditMode(false);
  }, []);

  const handleSaveEdits = useCallback(async () => {
    const before = preEditSnapshotRef.current;
    const after = localScope ?? chat.scopeUpdate;
    if (localMode && editToken && after) {
      try {
        const saved = await updateScope(editToken, after, contractorId);
        if (!saved.ok) throw new Error();
      } catch {toast.error('Save the quote again.');return;}
    }
    setIsEditMode(false);
    // Close the mobile preview panel so the contractor sees the chat response
    setClosePreviewCount((c) => c + 1);
    if (!before || !after) return;
    const summary = generateChangeSummary(before, after, lang);
    if (summary && !localMode) {
      void chat.sendTextMessage(summary);
    }
  }, [localScope, chat.scopeUpdate, lang, chat.sendTextMessage, editToken, contractorId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Instant greeting — shown immediately on fresh sessions, no LLM call.
  const greetingFiredRef = useRef(false);
  useEffect(() => {
    if (isReel()) return; // reel driver owns the greeting + conversation
    if (greetingFiredRef.current || chat.didRestore || chat.messages.length > 0) return;
    greetingFiredRef.current = true;
    let greeting: string;
    if (editToken) {
      greeting = lang === 'es'
        ? 'Aquí tienes tu presupuesto actual. Dime qué quieres cambiar.'
        : "Here's your current scope — tell me what to change.";
    } else {
      greeting = lang === 'es'
        ? 'Para hacer tu presupuesto necesito saber: qué trabajo es, dónde, y las fases con precio y tiempo aproximado de cada una. Dímelo todo de golpe si quieres — incluso con una nota de voz. Puedes ver el presupuesto construirse en tiempo real pulsando el ojo 👁.'
        : "Tell me about the job — what it is, where, the phases with price and rough duration for each. You can give it all at once, even with a voice note. Tap 👁 to see the quote build in real time.";
    }
    chat.injectLeoMessage(greeting);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Language change — abort in-flight /v1/chat so a stale Spanish reply never lands after toggling to EN.
  const prevLangRef = useRef(lang);
  useEffect(() => {
    if (prevLangRef.current === lang) return;
    prevLangRef.current = lang;
    void chat.setPageLocale(lang, { abortInFlight: true, notifyHermes: false });
  }, [lang, chat.setPageLocale]);

  const handleSwitchToEnglish = useCallback(() => {
    setLangSwitchDone(true);
    onLangChange('en');
    chat.injectLeoMessage("Got it — English from here. Tell me about the job: what it is, where, and the phases with price and rough duration for each.");
  }, [onLangChange, chat.injectLeoMessage]);

  const handleConfirm = useCallback(() => {
    if (localScope) onScopeReady(localScope);
    else if (chat.scopeUpdate) onScopeReady(chat.scopeUpdate);
  }, [localScope, chat.scopeUpdate, onScopeReady]);

  const handleDrawerAction = useCallback(
    async (actionId: string) => {
      if (actionId === 'finalize_scope') {
        handleConfirm();
        return;
      }
      await chat.handleDrawerAction(actionId);
    },
    [chat.handleDrawerAction, handleConfirm],
  );

  const displayScope = localScope ?? chat.scopeUpdate;
  const previewContent = displayScope ? (
    <EditModeWrapper
      scope={displayScope}
      lang={lang}
      isEditMode={isEditMode}
      isThinking={chat.isThinking}
      onEnterEdit={handleEnterEdit}
      onSaveEdits={handleSaveEdits}
      onCancelEdit={handleCancelEdit}
      onChange={setLocalScope}
    />
  ) : (
    <QuoteCanvas scope={SCOPE_PLACEHOLDER} />
  );

  const placeholderContent = <QuoteCanvas scope={SCOPE_PLACEHOLDER} />;

  const hasUserMessage = chat.messages.some((m) => m.role === 'user');
  const langSwitchSlot = lang === 'es' && !langSwitchDone && !hasUserMessage ? (
    <Button variant="secondary" size="sm" className="text-stone bg-border/60 rounded-full duration-200 anim-fade-up" type="button"
      onClick={handleSwitchToEnglish}
      aria-label="Switch to English">Switch to English <ArrowRight size={13} strokeWidth={2} /></Button>
  ) : null;

  const previewThinkingLabels = useMemo(
    () =>
      lang === 'es'
        ? [
            'Actualizando tu presupuesto…',
            'Redactando partidas…',
            'Consultando precios de mercado…',
          ]
        : ['Updating your quote…', 'Drafting line items…', 'Checking market rates…'],
    [lang],
  );

  // "Mis trabajos" back button — always visible, greyed out on first scope with tooltip
  const [showJobsTooltip, setShowJobsTooltip] = useState(false);
  const tooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleJobsClick = useCallback(() => {
    if (isFirstQuote) {
      setShowJobsTooltip(true);
      if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
      tooltipTimerRef.current = setTimeout(() => setShowJobsTooltip(false), 3200);
    } else {
      onGoToDashboard?.();
    }
  }, [isFirstQuote, onGoToDashboard]);

  useEffect(() => () => {
    if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
  }, []);

  /* ── Header left: back icon ── */
  const headerLeft = (
    <div className="relative">
      <Button variant="ghost" size="icon"
        type="button"
        onClick={handleJobsClick}
        className={`flex items-center justify-center w-8 h-8 rounded-sm transition-colors ${
          isFirstQuote
            ? 'text-stone/25 cursor-default'
            : 'text-stone hover:text-ink hover:bg-border/60'
        }`}
        aria-label={lang === 'es' ? 'Mis trabajos' : 'My Jobs'}
      >
        <ChevronLeft size={20} strokeWidth={2} />
      </Button>
      {showJobsTooltip && (
        <div
          className="absolute top-full left-0 mt-2 z-50 px-3 py-2 text-xs text-white shadow-lg pointer-events-none"
          style={{ background: 'var(--color-ink)', borderRadius: 'var(--radius-sm)', width: 220, lineHeight: '1.45' }}
        >
          {lang === 'es'
            ? 'Podrás ver tu lista de trabajos cuando crees tu primer presupuesto'
            : "You'll see your Jobs list once you create your first scope"}
        </div>
      )}
    </div>
  );

  /* ── Header right: language toggle + optional trash icon ── */
  const headerRight = (
    <div className="flex items-center gap-1.5">
      <LanguageToggle variant="light" />
      {chat.didRestore && onStartFresh && (
        <Button variant="danger" className="p-1.5 text-stone/50 hover:text-red-500" type="button"
          onClick={onStartFresh}
          aria-label={lang === 'es' ? 'Empezar de nuevo' : 'Start over'}
          title={lang === 'es' ? 'Empezar de nuevo' : 'Start over'}><Trash2 size={15} strokeWidth={2} /></Button>
      )}
    </div>
  );

  return (
    <ChatShell
      title={lang === 'es' ? 'Crear presupuesto' : 'Create quote'}
      headerLeft={headerLeft}
      headerRight={headerRight}
      messages={chat.messages}
      afterFirstMessageSlot={langSwitchSlot}
      isThinking={chat.isThinking}
      status={chat.status}
      previewState={chat.previewState}
      previewContent={previewContent}
      placeholderContent={placeholderContent}
      emptyPreviewLabel={lang === 'es'
        ? 'El presupuesto se va construyendo aquí'
        : 'Your quote appears here as you answer'}
      previewThinkingLabels={previewThinkingLabels}
      onSendText={chat.sendTextMessage}
      onSendVoice={chat.sendVoiceMessage!}
      onComposingChange={chat.handleComposingChange}
      onConfirm={handleConfirm}
      confirmLabel={lang === 'es' ? 'Finalizar' : 'Finalize'}
      confirmed={chat.confirmed}
      previewLabelClosed={lang === 'es' ? 'Ver presupuesto 👁' : 'Preview quote 👁'}
      previewLabelOpen={lang === 'es' ? 'Cerrar vista' : 'Close preview'}
      drawerState={chat.drawerState}
      onDrawerAction={handleDrawerAction}
      initialPreviewOpen={!!editToken}
      closePreviewCount={closePreviewCount}
    />
  );
}

// ── Main FirstQuote page ──────────────────────────────────────────────────────

export default function FirstQuote() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { contractorName: authContractorName, contractorId: authContractorId } = useAuth();

  const contractorId = searchParams.get('contractorId') ?? authContractorId ?? '';
  const editToken = searchParams.get('editToken') ?? '';
  const isFirstQuote = searchParams.get('first') === 'true';

  const [lang, setLang] = useState<'es' | 'en'>(isReel() || i18n.language?.startsWith('en') ? 'en' : 'es');

  // Location — confirmed before chat starts.
  // null = picker not yet shown/confirmed; string = confirmed (empty string = skipped).
  // In edit mode the scope already has a location — skip the picker entirely.
  // Reel mode skips the upfront location picker so the chat starts immediately.
  const [chatLocation, setChatLocation] = useState<string | null>(
    editToken ? '' : isReel() ? 'Marbella, Málaga' : null,
  );
  const showLocationPicker = chatLocation === null;

  // In edit mode: load existing scope via shared React Query cache
  const { data: editCanvasData, isLoading: editLoading } = useCanvasQuery(editToken || undefined);
  const initialScope = editCanvasData?.scope ?? null;

  const [pendingScope, setPendingScope] = useState<QuoteUpdate | null>(null);
  const [showAfterChatLocation, setShowAfterChatLocation] = useState(false);
  const [showFinalizeModal, setShowFinalizeModal] = useState(false);

  const contractorName = authContractorName || '';

  const handleScopeReady = (scope: QuoteUpdate) => {
    setPendingScope(scope);
    const hasLocation = scope.location && scope.location.trim().length > 2;
    if (!hasLocation) {
      setShowAfterChatLocation(true);
    } else {
      setShowFinalizeModal(true);
    }
  };

  const handleStartFresh = useCallback(() => {
    // Clear the persisted chat session so the scope builder starts blank for a new quote
    try {
      sessionStorage.removeItem(`leo_chat_scope_professional_${contractorId}`);
    } catch { /* continue */ }
    window.location.href = `${import.meta.env.BASE_URL}quote/first?contractorId=${encodeURIComponent(contractorId)}`;
  }, [contractorId]);

  const handleGoToDashboard = useCallback(() => {
    navigate('/dashboard');
  }, [navigate]);

  const handleAfterChatLocationConfirm = (label: string) => {
    setShowAfterChatLocation(false);
    if (pendingScope) setPendingScope({ ...pendingScope, location: label });
    setShowFinalizeModal(true);
  };

  const handleConnectBank = (quoteToken: string) => {
    setShowFinalizeModal(false);
    mergeLeoAuth({ quote_token: quoteToken });
    const auth = getLeoAuth();

    // Skip KYC if already verified in this session
    if (auth.stripe_onboarding_complete) {
      navigate(`/quote/sent/${encodeURIComponent(quoteToken)}`);
      return;
    }
    navigate(`/stripe/kyc?contractor=${encodeURIComponent(contractorId)}&scope=${encodeURIComponent(quoteToken)}`);
  };

  if (editLoading) {
    return (
      <div className="flex items-center justify-center h-dvh bg-cream">
        <div className="w-8 h-8 border-2 border-terracotta/30 border-t-terracotta rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-dvh bg-cream overflow-hidden">

      {/* Location picker — full-screen, shown before chat starts */}
      {showLocationPicker && (
        <div className="absolute inset-0 z-40">
          <LocationPickerModal
            lang={lang}
            onConfirm={(label) => setChatLocation(label)}
            onClose={() => setChatLocation('')}
          />
        </div>
      )}

      {/* Chat — rendered once location is confirmed or skipped */}
      {!showLocationPicker && (
        <div className="flex-1 min-h-0">
          <div className="h-full">
            <ChatMode
              key={contractorId + editToken}
              contractorId={contractorId}
              contractorName={contractorName}
              lang={lang}
              location={chatLocation ?? ''}
              editToken={editToken || undefined}
              initialScope={initialScope}
              isFirstQuote={isFirstQuote}
              onLangChange={setLang}
              onScopeReady={handleScopeReady}
              onStartFresh={handleStartFresh}
              onGoToDashboard={handleGoToDashboard}
            />
          </div>
        </div>
      )}

      {/* Location picker after chat (if scope has no location) */}
      {showAfterChatLocation && (
        <LocationPickerModal
          lang={lang}
          initialLocation={pendingScope?.location}
          onConfirm={handleAfterChatLocationConfirm}
          onClose={() => setShowAfterChatLocation(false)}
        />
      )}

      {/* Finalize modal */}
      {showFinalizeModal && pendingScope && (
        <FinalizeModal
          scope={pendingScope}
          contractorId={contractorId}
          editToken={editToken || undefined}
          onConnectBank={handleConnectBank}
          onDismiss={() => setShowFinalizeModal(false)}
        />
      )}
    </div>
  );
}
