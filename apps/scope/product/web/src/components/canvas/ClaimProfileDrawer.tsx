/**
 * ClaimProfileDrawer — Sticky bottom bar shown on unclaimed profile canvases.
 * Initiates Google OAuth to claim the contractor profile.
 */

import { useState } from 'react';
import { Star } from 'lucide-react';
import { signInWithGoogleForClaim } from '../../lib/supabase';
import { Button } from '@scope/ui';

export function ClaimProfileDrawer({ canvasToken }: { canvasToken: string }) {
  const [claiming, setClaiming] = useState(false);
  const [error, setError] = useState('');

  const handleClaim = async () => {
    setClaiming(true);
    setError('');
    const result = await signInWithGoogleForClaim(canvasToken);
    if (result.error) {
      setError(result.error);
      setClaiming(false);
    }
  };

  return (
    <div className="shrink-0 border-t border-border bg-cream/95 backdrop-blur-sm px-4 pt-4 pb-safe">
      <div className="max-w-lg mx-auto">
        <div className="flex items-start gap-2.5 mb-3">
          <span className="w-8 h-8 rounded-full bg-terracotta/10 flex items-center justify-center shrink-0 mt-0.5">
            <Star size={14} className="text-terracotta" fill="currentColor" />
          </span>
          <div>
            <p className="text-sm font-semibold text-ink leading-tight">This profile was created for you</p>
            <p className="text-xs text-stone leading-relaxed mt-0.5">
              Claim it to make a quote and get paid through Leo.
            </p>
          </div>
        </div>

        <Button fullWidth className="gap-2.5 py-3.5 active:scale-[0.98] duration-150 disabled:opacity-60" type="button"
          onClick={handleClaim}
          disabled={claiming}>{claiming ? (
            <>
              <div className="w-4 h-4 border-2 border-cream/30 border-t-cream rounded-full animate-spin" />
              <span>Opening Google…</span>
            </>
          ) : (
            <>
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              Claim with Google
            </>
          )}</Button>

        {error && <p className="text-center text-xs text-red-500 mt-2">{error}</p>}
        <p className="text-center text-xs text-muted mt-2 pb-1">Free to use. No card required.</p>
      </div>
    </div>
  );
}
