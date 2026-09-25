'use client';

import React, { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import { ZirefLogo } from '@/components/ui/ZirefLogo';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get('redirect') || '/dashboard';
  const { login, isAuthenticated, isLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(redirectTo);
    }
  }, [isAuthenticated, redirectTo, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await login(email.trim(), password, redirectTo);
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify your credentials.');
      setSubmitting(false);
    }
  };

  if (isLoading || isAuthenticated) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-6 h-6 animate-spin text-[var(--accent)]" />
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto my-auto bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-8 shadow-xl">
      <h1 className="text-2xl font-bold tracking-tight mb-1 text-[var(--text-primary)]">
        Sign in to Ziref
      </h1>
      <p className="text-xs md:text-sm text-[var(--text-secondary)] mb-6">
        Access your developer workspaces and deployed projects
      </p>

      {error && (
        <div className="flex items-center gap-2 p-3 mb-6 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5">
            Email Address
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="developer@domain.com"
            className="w-full px-3.5 py-2.5 bg-[var(--surface-muted)] border border-[var(--border)] rounded-xl text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-blue-600/20 transition-all"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5">
            Password
          </label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
            className="w-full px-3.5 py-2.5 bg-[var(--surface-muted)] border border-[var(--border)] rounded-xl text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-blue-600/20 transition-all"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full flex items-center justify-center gap-2 mt-4 px-4 py-2.5 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-semibold text-sm transition-all disabled:opacity-50"
        >
          {submitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <span>Sign in</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>

      <p className="text-center text-xs text-[var(--text-secondary)] mt-6">
        Don&apos;t have an account?{' '}
        <Link
          href={`/register${redirectTo !== '/dashboard' ? `?redirect=${encodeURIComponent(redirectTo)}` : ''}`}
          className="text-[var(--accent)] font-semibold hover:underline"
        >
          Create an account
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-[var(--background)] flex flex-col justify-between p-6 transition-colors">
      <div className="flex items-center justify-between max-w-md w-full mx-auto pt-4">
        <Link href="/" className="inline-flex items-center">
          <ZirefLogo size={30} showText={true} textSize="text-xl" />
        </Link>
        <ThemeToggle />
      </div>

      <Suspense fallback={
        <div className="flex items-center justify-center p-12">
          <Loader2 className="w-6 h-6 animate-spin text-[var(--accent)]" />
        </div>
      }>
        <LoginForm />
      </Suspense>

      <div className="text-center text-[11px] text-[var(--text-tertiary)] pb-2 font-mono">
        🔒 Encrypted session with isolated token exchange
      </div>
    </div>
  );
}
