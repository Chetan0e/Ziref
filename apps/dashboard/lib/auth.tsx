'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { api, ApiError } from './api';
import { User } from '@ziref/types';

export type AuthState = 'AUTH_INITIALIZING' | 'AUTHENTICATED' | 'UNAUTHENTICATED';

interface AuthContextType {
  authState: AuthState;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string, redirectTo?: string) => Promise<void>;
  register: (email: string, password: string, name: string, redirectTo?: string) => Promise<void>;
  logout: (redirectTo?: string) => Promise<void>;
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authState, setAuthState] = useState<AuthState>('AUTH_INITIALIZING');
  const [user, setUser] = useState<User | null>(null);

  // Authoritative user resolution
  const resolveUser = useCallback(async (): Promise<User | null> => {
    const token = api.getToken();
    if (!token) {
      setUser(null);
      setAuthState('UNAUTHENTICATED');
      return null;
    }

    try {
      const currentUser = await api.getMe();
      setUser(currentUser);
      setAuthState('AUTHENTICATED');
      return currentUser;
    } catch (err: any) {
      // If 401 or invalid token, reset session
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        api.clearToken();
        setUser(null);
        setAuthState('UNAUTHENTICATED');
      } else {
        // In case of transient network error, keep authenticated if token exists, or retry
        setUser(null);
        setAuthState('UNAUTHENTICATED');
      }
      return null;
    }
  }, []);

  // Hydrate on mount
  useEffect(() => {
    resolveUser();

    // Listen to token changes across tabs or window events
    const handleAuthChange = () => {
      resolveUser();
    };

    const handleUnauthorized = () => {
      api.clearToken();
      setUser(null);
      setAuthState('UNAUTHENTICATED');
    };

    window.addEventListener('storage', handleAuthChange);
    window.addEventListener('ziref:auth-change', handleAuthChange);
    window.addEventListener('ziref:auth-unauthorized', handleUnauthorized as EventListener);

    return () => {
      window.removeEventListener('storage', handleAuthChange);
      window.removeEventListener('ziref:auth-change', handleAuthChange);
      window.removeEventListener('ziref:auth-unauthorized', handleUnauthorized as EventListener);
    };
  }, [resolveUser]);

  const login = async (email: string, password: string, redirectTo?: string) => {
    const data = await api.login(email, password);
    setUser(data.user);
    setAuthState('AUTHENTICATED');
    if (redirectTo) {
      router.push(redirectTo);
    } else {
      router.push('/dashboard');
    }
  };

  const register = async (email: string, password: string, name: string, redirectTo?: string) => {
    const data = await api.register(email, password, name);
    setUser(data.user);
    setAuthState('AUTHENTICATED');
    if (redirectTo) {
      router.push(redirectTo);
    } else {
      router.push('/dashboard');
    }
  };

  const logout = async (redirectTo: string = '/login') => {
    await api.logout();
    setUser(null);
    setAuthState('UNAUTHENTICATED');
    router.push(redirectTo);
  };

  const refreshUser = async () => {
    return resolveUser();
  };

  const value: AuthContextType = {
    authState,
    user,
    isAuthenticated: authState === 'AUTHENTICATED',
    isLoading: authState === 'AUTH_INITIALIZING',
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

/**
 * Route protection wrapper for authenticated pages.
 * Handles initialization, redirects unauthenticated users with return destination,
 * and renders a clean skeleton during initialization to avoid UI flashes.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { authState } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (authState === 'UNAUTHENTICATED') {
      const returnUrl = encodeURIComponent(pathname);
      router.replace(`/login?redirect=${returnUrl}`);
    }
  }, [authState, router, pathname]);

  if (authState === 'AUTH_INITIALIZING') {
    return (
      <div className="min-h-screen bg-[var(--background)] flex flex-col items-center justify-center text-[var(--text-secondary)] font-mono text-xs">
        <div className="w-6 h-6 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin mb-3"></div>
        <span>Validating developer session...</span>
      </div>
    );
  }

  if (authState === 'UNAUTHENTICATED') {
    return null;
  }

  return <>{children}</>;
}
