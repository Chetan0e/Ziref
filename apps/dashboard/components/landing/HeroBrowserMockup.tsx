'use client';

import React, { useState } from 'react';
import {
  CheckCircle2,
  ExternalLink,
  RotateCcw,
  Copy,
  Check,
  ChevronRight,
} from 'lucide-react';

const buildLog = [
  { time: '10:31:02', text: 'Preparing build environment',   type: 'info' },
  { time: '10:31:05', text: 'Detected Vite + React project', type: 'info' },
  { time: '10:31:07', text: 'Installing dependencies (pnpm)', type: 'info' },
  { time: '10:31:21', text: 'Running pnpm build',            type: 'info' },
  { time: '10:31:38', text: 'Build completed successfully',   type: 'success' },
  { time: '10:31:39', text: 'Uploading build artifact',      type: 'info' },
  { time: '10:31:42', text: 'Deployment ready',              type: 'success' },
];

export function HeroBrowserMockup() {
  const [copied, setCopied] = useState(false);
  const [rolledBack, setRolledBack] = useState(false);

  const handleCopy = () => {
    navigator.clipboard?.writeText('https://my-store.ziref.app');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRollback = () => {
    setRolledBack(true);
    setTimeout(() => setRolledBack(false), 3000);
  };

  return (
    <div
      className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden"
      style={{ boxShadow: 'var(--shadow-lg)' }}
      aria-label="Ziref dashboard preview"
    >
      {/* Window chrome bar */}
      <div className="flex items-center gap-1.5 px-4 h-10 border-b border-[var(--border)] bg-[var(--surface-muted)]">
        <div className="w-3 h-3 rounded-full bg-[#FF5F57] opacity-80" />
        <div className="w-3 h-3 rounded-full bg-[#FFBD2E] opacity-80" />
        <div className="w-3 h-3 rounded-full bg-[#28C840] opacity-80" />
        <div className="flex-1 mx-4">
          <div className="max-w-[280px] mx-auto flex items-center gap-1.5 px-3 h-6 rounded bg-[var(--background)] border border-[var(--border)] font-mono text-[11px] text-[var(--text-tertiary)]">
            <span className="text-emerald-500 text-[10px]">●</span>
            <span>app.ziref.dev / my-store</span>
          </div>
        </div>
      </div>

      {/* Dashboard layout */}
      <div className="flex h-[420px] overflow-hidden">
        {/* Left sidebar */}
        <div className="w-48 shrink-0 border-r border-[var(--border)] bg-[var(--surface-muted)] p-3 flex flex-col gap-0.5 hidden sm:flex">
          <div className="px-2 py-1.5 text-[11px] font-mono text-[var(--text-tertiary)] uppercase tracking-wider mb-1">
            Projects
          </div>
          {['my-store', 'admin-panel', 'api-gateway'].map((proj, i) => (
            <button
              key={proj}
              className={`flex items-center gap-2 px-2.5 py-1.5 rounded text-[12px] text-left transition-colors w-full ${
                i === 0
                  ? 'bg-[var(--accent-subtle)] text-[var(--accent-text)] font-medium'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--border)]'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  i === 0 ? 'bg-emerald-500' : 'bg-[var(--border-strong)]'
                }`}
              />
              {proj}
            </button>
          ))}

          <div className="mt-4 px-2 py-1.5 text-[11px] font-mono text-[var(--text-tertiary)] uppercase tracking-wider mb-1">
            Navigation
          </div>
          {['Deployments', 'Appify', 'Settings', 'Domains'].map((item) => (
            <button
              key={item}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded text-[12px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-left transition-colors w-full"
            >
              {item}
            </button>
          ))}
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Content header */}
          <div className="px-5 py-4 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-semibold text-[var(--text-primary)]">my-store</span>
              <ChevronRight className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
              <span className="text-[13px] text-[var(--text-secondary)]">Deployments</span>
            </div>
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity">
              Deploy
            </button>
          </div>

          {/* Deployment row */}
          <div className="px-5 py-4 flex-1 overflow-auto">
            {/* Current deployment */}
            <div className="border border-[var(--border)] rounded-lg overflow-hidden mb-3">
              <div className="px-4 py-3 bg-[var(--surface-muted)] border-b border-[var(--border)] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[13px] font-semibold text-[var(--text-primary)]">Production</span>
                  <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900">
                    Live
                  </span>
                </div>
                <span className="font-mono text-[11px] text-[var(--text-tertiary)]">#1842</span>
              </div>

              <div className="px-4 py-3 grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: 'Framework',   value: 'React + Vite', mono: true },
                  { label: 'Build time',  value: '41s',          mono: true },
                  { label: 'Output',      value: 'dist/',        mono: true },
                  { label: 'Environment', value: 'Production',   mono: false },
                ].map(({ label, value, mono }) => (
                  <div key={label}>
                    <div className="text-[11px] text-[var(--text-tertiary)] mb-0.5">{label}</div>
                    <div className={`text-[12px] font-medium text-[var(--text-primary)] ${mono ? 'font-mono' : ''}`}>
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              <div className="px-4 py-3 border-t border-[var(--border)] flex items-center justify-between">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 font-mono text-[11px] text-[var(--accent-text)] hover:underline"
                >
                  {copied ? <Check className="w-3 h-3" /> : <ExternalLink className="w-3 h-3" />}
                  https://my-store.ziref.app
                  {copied && <span className="font-sans text-emerald-600 ml-1">Copied</span>}
                </button>
                <button
                  onClick={handleRollback}
                  className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  {rolledBack ? 'Restored v1.3.1' : 'Rollback'}
                </button>
              </div>
            </div>

            {/* Previous deployment */}
            <div className="flex items-center justify-between px-4 py-3 rounded-lg border border-[var(--border)] text-[12px] opacity-60">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[var(--border-strong)]" />
                <span className="text-[var(--text-secondary)] font-mono">#1841</span>
                <span className="text-[var(--text-tertiary)]">Previous</span>
              </div>
              <span className="font-mono text-[var(--text-tertiary)]">Deactivated 22m ago</span>
            </div>
          </div>
        </div>

        {/* Right panel — build log */}
        <div className="w-56 shrink-0 border-l border-[var(--border)] bg-[#0D1117] hidden lg:flex flex-col overflow-hidden">
          <div className="px-3 py-2.5 border-b border-[#30363D] flex items-center justify-between">
            <span className="font-mono text-[11px] text-[#8B949E]">Build #1842</span>
            <span className="flex items-center gap-1 font-mono text-[10px] text-emerald-400">
              <CheckCircle2 className="w-3 h-3" />
              Done
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {buildLog.map((entry, i) => (
              <div key={i} className="flex gap-2">
                <span className="font-mono text-[10px] text-[#484F58] shrink-0 mt-0.5">
                  {entry.time}
                </span>
                <span
                  className={`font-mono text-[10px] leading-relaxed ${
                    entry.type === 'success'
                      ? 'text-emerald-400'
                      : 'text-[#8B949E]'
                  }`}
                >
                  {entry.text}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
