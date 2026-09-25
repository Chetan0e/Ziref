'use client';

import React, { useEffect, useState } from 'react';
import { Moon, Sun, Laptop } from 'lucide-react';
import { useTheme } from '@/lib/theme';

export function ThemeToggle({ className = '', showSystem = false }: { className?: string; showSystem?: boolean }) {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className={`w-8 h-8 rounded-full border border-[var(--border)] bg-[var(--surface)] opacity-50 ${className}`} />
    );
  }

  if (showSystem) {
    return (
      <div className={`inline-flex items-center p-0.5 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] ${className}`}>
        <button
          onClick={() => setTheme('light')}
          title="Light mode"
          className={`p-1.5 rounded-md transition-colors ${
            theme === 'light'
              ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-sm'
              : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Sun className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => setTheme('dark')}
          title="Dark mode"
          className={`p-1.5 rounded-md transition-colors ${
            theme === 'dark'
              ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-sm'
              : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Moon className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => setTheme('system')}
          title="System preference"
          className={`p-1.5 rounded-md transition-colors ${
            theme === 'system'
              ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-sm'
              : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Laptop className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  const isDark = resolvedTheme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={`inline-flex items-center justify-center w-8 h-8 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] transition-all ${className}`}
    >
      {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
    </button>
  );
}
