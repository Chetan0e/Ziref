'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useTheme } from '@/lib/theme';
import {
  Search,
  LayoutDashboard,
  FolderGit2,
  PlusCircle,
  Zap,
  Smartphone,
  Globe,
  Settings,
  Sun,
  Moon,
  LogOut,
  X
} from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const { logout } = useAuth();
  const { toggleTheme, resolvedTheme } = useTheme();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const actions = [
    {
      id: 'overview',
      label: 'Go to Overview',
      category: 'Navigation',
      icon: LayoutDashboard,
      perform: () => router.push('/dashboard'),
    },
    {
      id: 'projects',
      label: 'Browse Projects',
      category: 'Navigation',
      icon: FolderGit2,
      perform: () => router.push('/dashboard/projects'),
    },
    {
      id: 'new-project',
      label: 'Create New Project',
      category: 'Actions',
      icon: PlusCircle,
      perform: () => router.push('/dashboard/projects/new'),
    },
    {
      id: 'deployments',
      label: 'View Deployments',
      category: 'Navigation',
      icon: Zap,
      perform: () => router.push('/dashboard/deployments'),
    },
    {
      id: 'appify',
      label: 'Open Appify Mobile Studio',
      category: 'Navigation',
      icon: Smartphone,
      perform: () => router.push('/dashboard/appify'),
    },
    {
      id: 'domains',
      label: 'Custom Domains',
      category: 'Navigation',
      icon: Globe,
      perform: () => router.push('/dashboard/domains'),
    },
    {
      id: 'settings',
      label: 'Workspace Settings',
      category: 'Navigation',
      icon: Settings,
      perform: () => router.push('/dashboard/settings'),
    },
    {
      id: 'theme',
      label: `Switch to ${resolvedTheme === 'dark' ? 'Light' : 'Dark'} Mode`,
      category: 'Preferences',
      icon: resolvedTheme === 'dark' ? Sun : Moon,
      perform: () => toggleTheme(),
    },
    {
      id: 'logout',
      label: 'Sign out of Ziref',
      category: 'Account',
      icon: LogOut,
      perform: () => logout(),
    },
  ];

  const filtered = actions.filter((a) =>
    a.label.toLowerCase().includes(query.toLowerCase()) ||
    a.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + (filtered.length || 1)) % (filtered.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].perform();
        onClose();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/60 backdrop-blur-sm animate-fade-in-up">
      <div
        className="w-full max-w-xl rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search header */}
        <div className="flex items-center px-4 py-3 border-b border-[var(--border)]">
          <Search className="w-4 h-4 text-[var(--text-tertiary)] mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search..."
            className="w-full bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="p-6 text-center text-xs text-[var(--text-tertiary)]">
              No matching commands found
            </div>
          ) : (
            filtered.map((action, idx) => {
              const Icon = action.icon;
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={action.id}
                  onClick={() => {
                    action.perform();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-[var(--accent)] text-white'
                      : 'text-[var(--text-primary)] hover:bg-[var(--surface-muted)]'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isSelected ? 'text-white' : 'text-[var(--text-tertiary)]'}`} />
                    <span className="font-medium">{action.label}</span>
                  </div>
                  <span className={`text-[10px] uppercase font-mono tracking-wider ${isSelected ? 'text-blue-100' : 'text-[var(--text-tertiary)]'}`}>
                    {action.category}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-[var(--border)] bg-[var(--surface-muted)] flex items-center justify-between text-[11px] text-[var(--text-tertiary)]">
          <div className="flex items-center gap-3">
            <span>Use <kbd className="px-1 py-0.5 rounded border border-[var(--border)] bg-[var(--surface)] text-[10px] font-mono">↑</kbd> <kbd className="px-1 py-0.5 rounded border border-[var(--border)] bg-[var(--surface)] text-[10px] font-mono">↓</kbd> to navigate</span>
            <span><kbd className="px-1 py-0.5 rounded border border-[var(--border)] bg-[var(--surface)] text-[10px] font-mono">Enter</kbd> to select</span>
          </div>
          <span><kbd className="px-1 py-0.5 rounded border border-[var(--border)] bg-[var(--surface)] text-[10px] font-mono">Esc</kbd> to close</span>
        </div>
      </div>
    </div>
  );
}
