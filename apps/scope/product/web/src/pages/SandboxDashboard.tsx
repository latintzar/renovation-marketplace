/**
 * SandboxDashboard — Persona management for sandbox testing.
 *
 * Route: /app/sandbox
 * Access: Only via AuthCallback after detecting sandbox email (operator@example.invalid)
 * or via direct URL when sandbox mode is already active.
 *
 * Allows creating homeowner and contractor test personas.
 * Contractor personas get KYC auto-bypassed on the backend.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, User, Home, Trash2, ArrowRight, Check, Loader2 } from 'lucide-react';
import { useSandboxStore, type SandboxPersona } from '../context/SandboxContext';
import { API_BASE, apiFetch } from '../lib/api';
import { mergeLeoAuth } from '../lib/utils';
import { track } from '../lib/tracking';
import { Button, Input } from '@scope/ui';

interface CreatePersonaModal {
  open: boolean;
  role: 'contractor' | 'homeowner';
}

function PersonaCard({ persona, onDelete, onActivate, isActive }: {
  persona: SandboxPersona;
  onDelete: (id: string) => void;
  onActivate: (persona: SandboxPersona) => void;
  isActive: boolean;
}) {
  return (
    <div className={`rounded-sm border p-4 ${isActive ? 'border-amber-300 bg-amber-50' : 'border-border bg-white'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${persona.role === 'contractor' ? 'bg-teal/10 text-teal' : 'bg-terracotta/10 text-terracotta'}`}>
            {persona.role === 'contractor' ? <User size={15} /> : <Home size={15} />}
          </div>
          <div>
            <p className="text-sm font-semibold text-ink">{persona.name}</p>
            <p className="text-xs text-stone">{persona.email}</p>
            {persona.contractorId && (
              <p className="text-[10px] text-muted font-mono mt-0.5">{persona.contractorId.slice(0, 12)}…</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isActive ? (
            <span className="text-xs text-amber-700 font-medium">Active</span>
          ) : (
            <Button
              type="button"
              onClick={() => onActivate(persona)}
              className="text-xs text-stone hover:text-ink flex items-center gap-1"
            >
              Use <ArrowRight size={11} />
            </Button>
          )}
          <Button
            type="button"
            onClick={() => onDelete(persona.id)}
            className="text-stone/50 hover:text-red-400 transition-colors"
          >
            <Trash2 size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
}

function CreatePersonaSheet({ role, onClose }: { role: 'contractor' | 'homeowner'; onClose: () => void }) {
  const addPersona = useSandboxStore((s) => s.addPersona);
  const setActivePersona = useSandboxStore((s) => s.setActivePersona);
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const emailSlug = name.toLowerCase().replace(/\s+/g, '.').replace(/[^a-z0-9.]/g, '');
  const email = `sandbox.${emailSlug}@test.leo.casa`;

  const handleCreate = async () => {
    if (!name.trim()) return;
    setLoading(true);

    if (role === 'contractor') {
      // Create contractor via backend (with KYC auto-bypass via X-Sandbox)
      try {
        const resp = await apiFetch(`${API_BASE}/v1/stripe/create-account`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Sandbox': 'true' },
          body: JSON.stringify({ email, name, trade: 'Sandbox Contractor', phone: '+34000000000' }),
        });
        const data = await resp.json();
        const personaId = addPersona({ name, email, role: 'contractor', contractorId: data.contractor_id });
        setActivePersona(personaId);

        // Store in sessionStorage for the app to use
        if (data.contractor_id) {
          mergeLeoAuth({
            contractor_id: data.contractor_id,
            contractor_name: name,
            stripe_onboarding_complete: true, // KYC bypassed
          });
        }
      } catch (e) {
        console.error('Failed to create sandbox contractor:', e);
      }
    } else {
      const personaId = addPersona({ name, email, role: 'homeowner' });
      setActivePersona(personaId);
      sessionStorage.setItem('leo_homeowner_auth', JSON.stringify({ id: `sandbox-ho-${Date.now()}`, email }));
    }

    setLoading(false);
    setDone(true);
    setTimeout(() => {
      onClose();
      if (role === 'contractor') navigate('/dashboard');
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end" onClick={onClose}>
      <div
        className="w-full bg-cream rounded-t-3xl p-6 shadow-2xl animate-in slide-in-from-bottom duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-ink mb-4">
          Create test {role === 'contractor' ? 'contractor' : 'homeowner'}
        </h3>

        {done ? (
          <div className="flex items-center justify-center gap-2 py-6 text-green">
            <Check size={20} />
            <span className="font-medium">Persona created</span>
          </div>
        ) : (
          <>
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Persona name (e.g. Carlos Ruiz)"
              autoFocus
              className="w-full px-4 py-3 rounded-sm border border-border text-sm bg-white focus:outline-none focus:ring-1 focus:ring-terracotta mb-2"
            />
            {name && (
              <p className="text-xs text-muted mb-4 font-mono">{email}</p>
            )}
            {role === 'contractor' && (
              <p className="text-xs text-stone mb-4 leading-relaxed">
                The contractor account is created with KYC auto-bypassed.
                You can accept payments immediately in sandbox mode.
              </p>
            )}
            <Button fullWidth className="py-3.5" type="button"
              onClick={handleCreate}
              disabled={!name.trim() || loading}>{loading ? <Loader2 size={14} className="animate-spin" /> : null}
              Create persona</Button>
          </>
        )}
      </div>
    </div>
  );
}

export default function SandboxDashboard() {
  const navigate = useNavigate();
  const { enabled, enable, disable, personas, activePersonaId, removePersona, setActivePersona } = useSandboxStore();
  const [modal, setModal] = useState<CreatePersonaModal>({ open: false, role: 'contractor' });

  const handleActivate = (persona: SandboxPersona) => {
    setActivePersona(persona.id);
    if (persona.role === 'contractor' && persona.contractorId) {
      mergeLeoAuth({
        contractor_id: persona.contractorId,
        contractor_name: persona.name,
        stripe_onboarding_complete: true,
      });
      navigate('/dashboard');
    } else {
      sessionStorage.setItem('leo_homeowner_auth', JSON.stringify({ id: `sandbox-ho-${persona.id}`, email: persona.email }));
    }
  };

  return (
    <div className="min-h-dvh bg-cream">
      <header className="px-4 h-14 flex items-center justify-between border-b border-border sticky top-0 bg-cream/95 backdrop-blur-lg z-50">
        <Button type="button" onClick={() => navigate('/dashboard')} className="text-sm text-stone hover:text-ink">← Back</Button>
        <h1 className="font-display text-base font-semibold text-ink">Sandbox</h1>
        <div className="w-16" />
      </header>

      <div className="px-4 py-6 max-w-lg mx-auto space-y-6">
        {/* Mode toggle */}
        <div className="bg-amber-50 border border-amber-200 rounded-sm px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-amber-800">Sandbox Mode</p>
              <p className="text-xs text-amber-700 mt-0.5">
                {enabled ? 'Active — using Stripe test keys' : 'Disabled'}
              </p>
            </div>
            <Button
              type="button"
              onClick={() => {
                if (enabled) { disable(); } else { enable(); track('sandbox.enabled'); }
              }}
              className={`relative w-12 h-6 rounded-full transition-colors ${enabled ? 'bg-amber-500' : 'bg-stone/30'}`}
            >
              <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${enabled ? 'translate-x-7' : 'translate-x-1'}`} />
            </Button>
          </div>
        </div>

        {/* Test card info */}
        {enabled && (
          <div className="bg-white rounded-sm border border-border px-4 py-4">
            <p className="text-xs font-semibold text-stone uppercase tracking-wide mb-2">Stripe test card</p>
            <code className="text-sm font-mono text-ink">4242 4242 4242 4242</code>
            <p className="text-xs text-muted mt-1">Date: any future · CVC: any number</p>
          </div>
        )}

        {/* Personas */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-ink">Test personas</h2>
            <div className="flex gap-2">
              <Button
                type="button"
                onClick={() => setModal({ open: true, role: 'contractor' })}
                className="flex items-center gap-1 text-xs text-stone hover:text-ink border border-border rounded-sm px-2.5 py-1.5"
              >
                <Plus size={11} /> Contractor
              </Button>
              <Button
                type="button"
                onClick={() => setModal({ open: true, role: 'homeowner' })}
                className="flex items-center gap-1 text-xs text-stone hover:text-ink border border-border rounded-sm px-2.5 py-1.5"
              >
                <Plus size={11} /> Homeowner
              </Button>
            </div>
          </div>

          {personas.length === 0 ? (
            <p className="text-sm text-muted text-center py-8">
              Create test personas to simulate the full flow.
            </p>
          ) : (
            <div className="space-y-2">
              {personas.map((persona) => (
                <PersonaCard
                  key={persona.id}
                  persona={persona}
                  isActive={persona.id === activePersonaId}
                  onDelete={removePersona}
                  onActivate={handleActivate}
                />
              ))}
            </div>
          )}
        </div>

        {/* Quick links */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-stone uppercase tracking-wide">Quick links</p>
          {[
            { label: 'Contractor dashboard', path: '/dashboard' },
            { label: 'My projects (homeowner)', path: '/my-quotes' },
          ].map(({ label, path }) => (
            <Button
              key={path}
              type="button"
              onClick={() => navigate(path)}
              className="w-full flex items-center justify-between px-4 py-3 rounded-sm border border-border bg-white text-sm text-ink hover:border-stone/50 transition-colors"
            >
              {label}
              <ArrowRight size={14} className="text-stone" />
            </Button>
          ))}
        </div>
      </div>

      {modal.open && (
        <CreatePersonaSheet role={modal.role} onClose={() => setModal({ open: false, role: 'contractor' })} />
      )}
    </div>
  );
}
