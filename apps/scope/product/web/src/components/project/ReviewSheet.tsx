/**
 * ReviewSheet — Star rating drawer shown after project completion.
 * Calls POST /v1/projects/:token/review (JWT-authenticated via apiFetch).
 */

import { useState } from 'react';
import { Check, Loader2, Star } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE, apiFetch } from '../../lib/api';
import { Button, Sheet, Textarea } from '@scope/ui';

interface ReviewSheetProps {
  open: boolean;
  onClose: () => void;
  quoteToken: string;
}

export function ReviewSheet({ open, onClose, quoteToken }: ReviewSheetProps) {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [body, setBody] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!rating) return;
    setLoading(true);
    const resp = await apiFetch(`${API_BASE}/v1/projects/${quoteToken}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating, body }),
    });
    if (resp.ok) { setSubmitted(true); toast.success('Thanks for your review!'); }
    setLoading(false);
  };

  return (
    <Sheet open={open} onClose={onClose}>
<div className="px-6 pt-2 pb-8">
            {submitted ? (
              <div className="text-center py-8">
                <Check size={40} className="text-green mx-auto mb-4" />
                <p className="text-lg font-semibold text-ink">Thank you!</p>
                <p className="text-sm text-stone mt-1">Your review has been saved.</p>
                <Button variant="ghost" className="mt-6 text-stone underline" type="button" onClick={onClose}>Close</Button>
              </div>
            ) : (
              <>
                <h2 className="text-xl font-semibold text-ink mb-1 font-display">How was the work?</h2>
                <p className="text-sm text-stone mb-5">Your review helps other homeowners.</p>
                <div className="flex justify-center gap-2 mb-5">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Button
                      key={s}
                      type="button"
                      onClick={() => setRating(s)}
                      onMouseEnter={() => setHovered(s)}
                      onMouseLeave={() => setHovered(0)}
                      className="transition-transform active:scale-110"
                    >
                      <Star
                        size={36}
                        className="transition-colors"
                        fill={(hovered || rating) >= s ? 'var(--color-terracotta)' : 'transparent'}
                        stroke={(hovered || rating) >= s ? 'var(--color-terracotta)' : 'var(--color-muted)'}
                      />
                    </Button>
                  ))}
                </div>
                <Textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="Anything to highlight? (optional)"
                  rows={3}
                  className="w-full px-4 py-3 rounded-sm border border-border text-sm text-ink bg-white resize-none focus:outline-none focus:ring-1 focus:ring-terracotta mb-4"
                />
                <Button fullWidth className="py-3.5 disabled:opacity-40" type="button"
                  onClick={handleSubmit}
                  disabled={!rating || loading}>{loading && <Loader2 size={14} className="animate-spin" />}
                  Submit review</Button>
              </>
            )}
          </div>
        </Sheet>
  );
}
