'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { ArrowRight, AlertCircle, Loader2, Lock } from 'lucide-react';
import { ZirefLogo } from '@/components/ui/ZirefLogo';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api.login(email, password);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed. Check your email and password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-black flex flex-col justify-between p-6 text-slate-900 dark:text-white transition-colors">
      <div className="flex items-center justify-between max-w-md w-full mx-auto pt-4">
        <Link href="/" className="inline-flex items-center">
          <ZirefLogo size={30} showText={true} textSize="text-xl" />
        </Link>
        <ThemeToggle />
      </div>

      <div className="w-full max-w-md mx-auto my-auto bg-white dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 rounded-2xl p-8 shadow-xl shadow-slate-200/50 dark:shadow-black/60">
        <h1 className="text-2xl font-bold tracking-tight mb-1 text-slate-900 dark:text-white">
          Welcome back
        </h1>
        <p className="text-xs md:text-sm text-slate-500 dark:text-zinc-400 mb-6">
          Sign in to your Ziref developer workspace
        </p>

        {error && (
          <div className="flex items-center gap-2 p-3 mb-6 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alex@company.com"
              className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-zinc-500 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 transition-all"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-zinc-300">
                Password
              </label>
            </div>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-zinc-500 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 mt-3 px-4 py-2.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm shadow-md shadow-blue-600/20 transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>Sign in</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <p className="text-center text-xs text-slate-500 dark:text-zinc-400 mt-6">
          Don&apos;t have an account?{' '}
          <Link href="/register" className="text-blue-600 dark:text-blue-400 font-semibold hover:underline">
            Create an account
          </Link>
        </p>
      </div>

      <div className="text-center text-[11px] text-slate-400 pb-2">
        🔒 Encrypted session with isolated token exchange
      </div>
    </div>
  );
}
