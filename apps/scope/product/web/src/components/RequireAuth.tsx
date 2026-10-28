/**
 * RequireAuth — Route-level auth guard
 * ======================================
 *
 * Wrap any route that needs authentication:
 *
 *   <Route path="/dashboard" element={
 *     <RequireAuth role="contractor"><Dashboard /></RequireAuth>
 *   } />
 *
 * Behaviour
 * ---------
 * - While auth is loading: shows a minimal spinner.
 * - No session: redirects to "/" (Login).
 * - Wrong role: redirects to the correct home for that role.
 * - Correct role (or no role constraint): renders children.
 */

import { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth, type UserRole } from '../context/AuthContext';

interface Props {
  children: ReactNode;
  /** If provided, the user must have this role or be redirected. */
  role?: UserRole;
}

const ROLE_HOME: Record<NonNullable<UserRole>, string> = {
  contractor: '/dashboard',
  homeowner: '/my-projects',
};

export function RequireAuth({ children, role }: Props) {
  const { user, role: userRole, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-cream">
        <div className="w-6 h-6 border-2 border-stone/30 border-t-terra rounded-full animate-spin" />
      </div>
    );
  }

  // No session at all → Login
  if (!user) {
    return <Navigate to="/" replace />;
  }

  // Role mismatch → redirect to the right home
  if (role && userRole && userRole !== role) {
    return <Navigate to={ROLE_HOME[userRole]} replace />;
  }

  return <>{children}</>;
}
