import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom';
import { NuqsAdapter } from 'nuqs/adapters/react-router/v7';
import { useState, useEffect } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import OnboardPro from './pages/OnboardPro';
import OnboardHomeowner from './pages/OnboardHomeowner';
import ImportPro from './pages/ImportPro';
import FirstQuote from './pages/FirstQuote';
import JobInbox from './pages/JobInbox';
import OpsMonitor from './pages/OpsMonitor';
import ComponentLibrary from './pages/ComponentLibrary';
import DesignSystem from './pages/DesignSystem';
import Canvas from './pages/Canvas';
import AuthCallback from './pages/AuthCallback';
import QuoteSent from './pages/QuoteSent';
import StripeKyc from './pages/StripeKyc';
import StripeReturn from './pages/StripeReturn';
import StripeRefresh from './pages/StripeRefresh';
import Settings from './pages/Settings';
import ProjectDetail from './pages/ProjectDetail';
import MyQuotes from './pages/MyQuotes';
import JobChat from './pages/JobChat';
import SandboxDashboard from './pages/SandboxDashboard';
import { SandboxBadge } from './context/SandboxContext';
import { AuthProvider } from './context/AuthContext';
import { RequireAuth } from './components/RequireAuth';
import { initTracking } from './lib/tracking';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Button } from '@scope/ui';
import { isReel } from './reel/flag';
import { CaptionStrip } from './reel/CaptionStrip';
import { ReelSwitcher } from './reel/ReelSwitcher';
import { setAppLanguage } from './i18n';

// Reel is narrated in English — force the UI language to match (the real
// product stays Spanish-first when the flag is off).
if (isReel()) setAppLanguage('en');

// ---------------------------------------------------------------------------
// GDPR Cookie Consent Banner
// ---------------------------------------------------------------------------

const CONSENT_KEY = 'leo_cookie_consent';

function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isReel()) return; // no cookie banner in a portfolio reel
    const stored = localStorage.getItem(CONSENT_KEY);
    if (!stored) setVisible(true);
    else if (stored === 'accepted') initTracking();
  }, []);

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, 'accepted');
    setVisible(false);
    initTracking();
  };

  const decline = () => {
    localStorage.setItem(CONSENT_KEY, 'declined');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-[9000] px-4 pb-safe-or-4 pb-4"
      role="dialog"
      aria-label="Cookie consent"
    >
      <div className="max-w-lg mx-auto bg-ink text-cream rounded-sm px-4 py-4 shadow-2xl border border-white/10">
        <p className="text-sm leading-relaxed mb-3">
          We use analytics cookies to improve your experience.{' '}
          <a
            href="/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="underline text-cream/70 hover:text-cream"
          >
            Privacy policy
          </a>
        </p>
        <div className="flex gap-2">
          <Button variant="terracotta" className="flex-1 active:scale-[0.98]" type="button"
            onClick={accept}>Accept</Button>
          <Button className="flex-1 bg-white/10 text-cream/70 active:scale-[0.98]" type="button"
            onClick={decline}>Decline</Button>
        </div>
      </div>
    </div>
  );
}

function LegacyProjectRedirect() {
  const { token } = useParams<{ token: string }>();
  return <Navigate to={`/project/${token}`} replace />;
}

function App() {
  return (
    <div className="min-h-dvh bg-cream text-ink font-sans">
      <ErrorBoundary>
      {/* basename derives from Vite `base` so the vendored portfolio build
          (base '/scope/app/') routes correctly without a code change. Default
          build (base '/app/') still resolves to '/app'. See must-fix #3. */}
      <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '') || '/'}>
        <NuqsAdapter>
          <AuthProvider>
            {/* Sandbox pill badge — shows on all pages when sandbox is active */}
            <SandboxBadge />
            {/* Reel caption strip — narrates each beat in portfolio reel mode */}
            <CaptionStrip />
            {/* Reel flow switcher — jump between the five flows */}
            <ReelSwitcher />
            {/* GDPR cookie consent — only initialises PostHog after user accepts */}
            <CookieConsent />

            <Routes>
              {/* Public routes — no auth required */}
              <Route path="/" element={<Login />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
              <Route path="/canvas/:token" element={<Canvas />} />
              <Route path="/quote/sent/:token" element={<QuoteSent />} />
              <Route path="/inbox/:token" element={<JobInbox />} />
              <Route path="/ops/:token" element={<OpsMonitor />} />
              <Route path="/onboard/pro" element={<OnboardPro />} />
              <Route path="/onboard/homeowner" element={<OnboardHomeowner />} />
              {/* Redirect legacy /quote/create to /quote/first */}
              <Route path="/quote/create" element={<Navigate to="/quote/first" replace />} />

              {/* Contractor-only routes */}
              <Route path="/dashboard" element={<RequireAuth role="contractor"><Dashboard /></RequireAuth>} />
              <Route path="/quote/first" element={<RequireAuth role="contractor"><FirstQuote /></RequireAuth>} />
              <Route path="/import/pro" element={<RequireAuth role="contractor"><ImportPro /></RequireAuth>} />
              <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
              <Route path="/stripe/kyc" element={<RequireAuth role="contractor"><StripeKyc /></RequireAuth>} />
              <Route path="/stripe/complete" element={<RequireAuth role="contractor"><StripeReturn /></RequireAuth>} />
              <Route path="/stripe/refresh" element={<RequireAuth role="contractor"><StripeRefresh /></RequireAuth>} />

              {/* Project tracking — canonical new route + legacy redirects */}
              <Route path="/project/:token" element={<ProjectDetail />} />
              {/* Legacy /my-project/:token redirects to canonical route */}
              <Route path="/my-project/:token" element={<LegacyProjectRedirect />} />
              {/* Homeowner dashboard */}
              <Route path="/my-projects" element={<RequireAuth role="homeowner"><MyQuotes /></RequireAuth>} />
              <Route path="/projects" element={<Navigate to="/my-projects" replace />} />
              <Route path="/my-quotes" element={<Navigate to="/my-projects" replace />} />
              <Route path="/job-chat/:token" element={<JobChat />} />

              {/* Sandbox testing — requires any auth */}
              <Route path="/sandbox" element={<RequireAuth><SandboxDashboard /></RequireAuth>} />

              {/* Design system — single visual reference page */}
              <Route path="/design" element={<DesignSystem />} />
              {/* Dev — legacy alias (kept for muscle memory) */}
              <Route path="/dev/library" element={<ComponentLibrary />} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AuthProvider>
        </NuqsAdapter>
      </BrowserRouter>
      </ErrorBoundary>
    </div>
  );
}

export default App;
