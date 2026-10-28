/**
 * SandboxContext — Global sandbox mode state.
 *
 * When sandbox mode is active:
 * - All API calls include X-Sandbox: true header
 * - Test card hint shows on Canvas.tsx pay button
 * - Stripe uses STRIPE_SECRET_KEY_TEST on the backend
 * - Amber pill badge shows on all pages
 *
 * Sandbox mode persists in localStorage so it survives page refresh.
 */

import { create } from 'zustand';

export interface SandboxPersona {
  id: string;
  name: string;
  email: string;
  role: 'contractor' | 'homeowner';
  contractorId?: string;
  createdAt: string;
}

interface SandboxState {
  enabled: boolean;
  personas: SandboxPersona[];
  activePersonaId: string | null;

  enable: () => void;
  disable: () => void;
  addPersona: (persona: Omit<SandboxPersona, 'id' | 'createdAt'>) => string;
  removePersona: (id: string) => void;
  setActivePersona: (id: string | null) => void;
}

const STORAGE_KEY = 'leo_sandbox_state';

function loadState(): Partial<SandboxState> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* fall through */ }
  return {};
}

function saveState(state: Partial<SandboxState>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      enabled: state.enabled,
      personas: state.personas,
      activePersonaId: state.activePersonaId,
    }));
    // Also set the simple flag for Canvas.tsx to read
    localStorage.setItem('leo_sandbox_mode', String(state.enabled));
  } catch { /* fall through */ }
}

const persisted = loadState();

export const useSandboxStore = create<SandboxState>((set, get) => ({
  enabled: persisted.enabled ?? false,
  personas: persisted.personas ?? [],
  activePersonaId: persisted.activePersonaId ?? null,

  enable: () => {
    set({ enabled: true });
    saveState(get());
  },

  disable: () => {
    set({ enabled: false, activePersonaId: null });
    saveState(get());
  },

  addPersona: (persona) => {
    const id = `persona-${Date.now()}`;
    const newPersona: SandboxPersona = { ...persona, id, createdAt: new Date().toISOString() };
    set((state) => {
      const updated = { personas: [...state.personas, newPersona] };
      saveState({ ...state, ...updated });
      return updated;
    });
    return id;
  },

  removePersona: (id) => {
    set((state) => {
      const updated = {
        personas: state.personas.filter((p) => p.id !== id),
        activePersonaId: state.activePersonaId === id ? null : state.activePersonaId,
      };
      saveState({ ...state, ...updated });
      return updated;
    });
  },

  setActivePersona: (id) => {
    set({ activePersonaId: id });
    saveState(get());
  },
}));

// ---------------------------------------------------------------------------
// Amber "Sandbox" pill badge — shown on all pages when sandbox is active
// ---------------------------------------------------------------------------

export function SandboxBadge() {
  const enabled = useSandboxStore((s) => s.enabled);
  if (!enabled) return null;

  return (
    <div className="fixed top-3 right-3 z-[9999] pointer-events-none">
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 border border-amber-300 text-amber-800 shadow-sm">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        Sandbox
      </span>
    </div>
  );
}
