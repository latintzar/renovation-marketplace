/**
 * ErrorBoundary — Catches React render errors and shows a friendly recovery screen.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <MyPage />
 *   </ErrorBoundary>
 */

import { Component, type ReactNode } from 'react';
import { Button } from '@scope/ui';

interface Props {
  children: ReactNode;
  /** Optional custom fallback UI */
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error?.message || 'Unknown error' };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    // Log to console in dev; in prod this would go to Sentry / PostHog
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary] Render error:', error, info.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, errorMessage: '' });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="min-h-dvh flex flex-col items-center justify-center bg-cream px-6 text-center">
          <div className="w-14 h-14 rounded-full bg-terracotta/10 flex items-center justify-center mb-5">
            <span className="text-2xl">⚠️</span>
          </div>
          <h1 className="font-display text-xl font-semibold text-ink mb-2">Something went wrong</h1>
          <p className="text-sm text-stone mb-6 max-w-xs leading-relaxed">
            An unexpected error occurred. Please try again or reload the page.
          </p>
          {import.meta.env.DEV && this.state.errorMessage && (
            <p className="text-[11px] text-muted mb-4 font-mono bg-border/30 rounded-sm px-3 py-2 max-w-sm break-all">
              {this.state.errorMessage}
            </p>
          )}
          <div className="flex gap-3">
            <Button size="lg" type="button"
              onClick={this.handleRetry}>Try again</Button>
            <Button
              type="button"
              onClick={() => window.location.reload()}
              className="px-5 py-2.5 rounded-sm border border-border text-stone text-sm font-medium hover:border-stone hover:text-ink transition-colors"
            >
              Reload
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
