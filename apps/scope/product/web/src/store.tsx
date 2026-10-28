/**
 * @internal Dev-only fixture store — used exclusively by ComponentLibrary.tsx.
 * Do NOT import from production pages. Real auth lives in context/AuthContext.tsx.
 */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { JOBS, USERS, type User, type Job, type UserRole } from './data';

interface AppState {
  user: User | null;
  jobs: Job[];
  setRole: (role: UserRole) => void;
  ensureRole: (role: UserRole) => void;
  logout: () => void;
  getJob: (id: string) => Job | undefined;
  counterparty: (job: Job) => string;
  updateJob: (id: string, patch: Partial<Job>) => void;
}

const Ctx = createContext<AppState | null>(null);

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [jobs, setJobs] = useState<Job[]>(JOBS);

  const setRole = useCallback((role: UserRole) => {
    setUser(role === 'homeowner' ? USERS.peter : USERS.james);
  }, []);

  /** Set role only if no user is set yet — used by onboard pages for auto-routing from landing pages */
  const ensureRole = useCallback((role: UserRole) => {
    setUser((prev) => {
      if (prev) return prev;
      return role === 'homeowner' ? USERS.peter : USERS.james;
    });
  }, []);

  const logout = useCallback(() => setUser(null), []);

  const getJob = useCallback((id: string) => jobs.find((j) => j.id === id), [jobs]);

  const counterparty = useCallback(
    (job: Job) => {
      if (!user) return '';
      return user.role === 'homeowner' ? job.tradesperson.name : job.homeowner.name;
    },
    [user],
  );

  const updateJob = useCallback((id: string, patch: Partial<Job>) => {
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, ...patch } : j)));
  }, []);

  return (
    <Ctx.Provider value={{ user, jobs, setRole, ensureRole, logout, getJob, counterparty, updateJob }}>
      {children}
    </Ctx.Provider>
  );
};

export const useApp = () => {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useApp must be inside AppProvider');
  return ctx;
};
