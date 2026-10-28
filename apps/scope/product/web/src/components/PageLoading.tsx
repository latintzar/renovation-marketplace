/**
 * PageLoading — Full-page cream loading screen with a terracotta spinner.
 *
 * Replaces the copy-pasted "flex items-center justify-center h-dvh bg-cream"
 * + spinner pattern across Canvas, QuoteSent, FirstQuote, JobInbox, MyQuotes etc.
 *
 * Usage:
 *   if (loading) return <PageLoading />;
 *   if (loading) return <PageLoading label="Loading project…" />;
 */

interface PageLoadingProps {
  /** Optional caption shown below the spinner */
  label?: string;
}

export function PageLoading({ label }: PageLoadingProps = {}) {
  return (
    <div className="flex items-center justify-center h-dvh bg-cream">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-terracotta/30 border-t-terracotta rounded-full animate-spin mx-auto" />
        {label && <p className="text-sm text-muted mt-3">{label}</p>}
      </div>
    </div>
  );
}
