/**
 * SubmitProofSheet — Bottom drawer for submitting phase completion photos.
 * Contractor selects a milestone, uploads photos, adds an optional note,
 * then sends the proof to the homeowner for approval.
 */

import { useState, useEffect } from 'react';
import { Camera, Check, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch, API_BASE } from '../../lib/api';
import { track } from '../../lib/tracking';
import { isReel } from '../../reel/flag';
import type { Milestone as FullMilestone } from '../project/types';
import { Button, Sheet, Textarea } from '@scope/ui';

const reelAsset = (f: string) => `${import.meta.env.BASE_URL}reel/${f}`;

type Milestone = Pick<FullMilestone, 'title' | 'status'>;

interface SubmitProofSheetProps {
  open: boolean;
  onClose: () => void;
  quoteToken: string;
  contractorId: string;
  milestones: Milestone[];
}

export function SubmitProofSheet({ open, onClose, quoteToken, contractorId, milestones }: SubmitProofSheetProps) {
  const [selectedMilestone, setSelectedMilestone] = useState(0);
  const [photos, setPhotos] = useState<string[]>([]);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);

  const currentIndex = milestones.findIndex(
    (m) => !m.status || m.status === 'pending' || m.status === 'in_progress',
  );

  useEffect(() => {
    if (open && currentIndex >= 0) setSelectedMilestone(currentIndex);
  }, [open, currentIndex]);

  // Reel mode: auto-fill the proof (photos + note) and submit, so the viewer
  // sees the real contractor flow play out. No-op outside reel mode.
  useEffect(() => {
    if (!open || !isReel()) return;
    let cancelled = false;
    const timers: ReturnType<typeof setTimeout>[] = [];
    const at = (ms: number, fn: () => void) =>
      timers.push(setTimeout(() => { if (!cancelled) fn(); }, ms));
    setPhotos([]);
    setNote('');
    at(1100, () => setPhotos([reelAsset('/app/sample-attachment.png')]));
    at(2000, () => setPhotos([reelAsset('/app/sample-attachment.png'), reelAsset('/app/sample-attachment.png')]));
    at(3000, () => setNote('Phase 2 complete — waterproofed, tiled full-height and grouted.'));
    at(4600, async () => {
      try {
        await apiFetch(`${API_BASE}/v1/milestone/submit-proof`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ quote_token: quoteToken, milestone_index: 1, photos: [], note: '', contractor_auth_id: contractorId }),
        });
      } catch { /* intercepted no-op in reel */ }
      if (cancelled) return;
      toast.success('Proof submitted — awaiting homeowner approval');
      onClose();
    });
    return () => { cancelled = true; timers.forEach(clearTimeout); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    files.slice(0, 9 - photos.length).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        if (ev.target?.result) setPhotos((p) => [...p, ev.target!.result as string]);
      };
      reader.readAsDataURL(file);
    });
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const resp = await apiFetch(`${API_BASE}/v1/milestone/submit-proof`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quote_token: quoteToken, milestone_index: selectedMilestone, photos, note, contractor_auth_id: contractorId }),
      });
      if (!resp.ok) throw new Error('Failed to submit proof');
      track('milestone.proof_submitted', { token: quoteToken, milestone_index: selectedMilestone });
      toast.success('Proof submitted — awaiting homeowner approval');
      setPhotos([]);
      setNote('');
      onClose();
    } catch {
      toast.error('Failed to submit — please try again');
    }
    setLoading(false);
  };

  return (
    <Sheet open={open} onClose={onClose}>
<div className="flex-1 overflow-y-auto px-5 pb-6">
            <h2 className="text-lg font-semibold text-ink mb-4 font-display">Submit proof</h2>

            {milestones.length > 1 && (
              <div className="mb-4">
                <p className="text-xs text-stone mb-2">Phase</p>
                <div className="space-y-1.5">
                  {milestones.map((m, i) => (
                    <Button
                      key={i}
                      type="button"
                      onClick={() => setSelectedMilestone(i)}
                      className={`w-full text-left px-3 py-2.5 rounded-sm text-sm border transition-colors ${
                        selectedMilestone === i
                          ? 'border-terracotta bg-terracotta/5 text-ink font-medium'
                          : 'border-border text-stone hover:border-stone/50'
                      }`}
                    >
                      {i + 1}. {m.title}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            <div className="mb-4">
              <p className="text-xs text-stone mb-2">Photos of completed phase</p>
              <div className="grid grid-cols-3 gap-2">
                {photos.map((src, i) => (
                  <div key={i} className="relative aspect-square">
                    <img src={src} alt={`Photo ${i + 1}`} className="w-full h-full object-cover rounded-sm border border-border" />
                    <Button
                      type="button"
                      onClick={() => setPhotos((p) => p.filter((_, j) => j !== i))}
                      className="absolute -top-1 -right-1 w-5 h-5 bg-ink rounded-full text-cream text-xs flex items-center justify-center"
                    >
                      ×
                    </Button>
                  </div>
                ))}
                {photos.length < 9 && (
                  <label className="aspect-square flex flex-col items-center justify-center rounded-sm border-2 border-dashed border-border cursor-pointer hover:border-terracotta transition-colors">
                    <Camera size={20} className="text-stone mb-1" />
                    <span className="text-xs text-muted">Add</span>
                    <input type="file" accept="image/*" multiple capture="environment" className="hidden" onChange={handlePhotoChange} />
                  </label>
                )}
              </div>
            </div>

            <div className="mb-5">
              <p className="text-xs text-stone mb-2">Note (optional)</p>
              <Textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Describe what you've completed…"
                rows={3}
                className="w-full px-4 py-3 rounded-sm border border-border text-sm text-ink bg-white resize-none focus:outline-none focus:ring-1 focus:ring-terracotta"
              />
            </div>

            <Button fullWidth className="py-3.5" type="button"
              onClick={handleSubmit}
              disabled={loading}>{loading ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              {loading ? 'Sending…' : 'Send to homeowner'}</Button>
          </div>
        </Sheet>
  );
}
