'use client';

import React, { useState, useEffect, useRef } from 'react';

// ─── Pipeline step definitions ───────────────────────────────────────────────
const steps = [
  {
    id: 1,
    label: 'Source',
    meta: 'my-store.zip · 1.2 MB · SHA-256 verified',
    detail: {
      title: 'Project ingested',
      lines: [
        '  source    zip-upload',
        '  filename  my-store.zip',
        '  size      1,234,891 bytes',
        '  sha256    4a71b3c...882e',
        '  zip_slip  PASSED',
      ],
    },
  },
  {
    id: 2,
    label: 'Analyze',
    meta: 'Framework detected < 45ms · Zero configuration',
    detail: {
      title: 'Detection output',
      lines: [
        '  framework  vite + react',
        '  manager    pnpm',
        '  command    pnpm build',
        '  output     dist/',
        '  runtime    static',
      ],
    },
  },
  {
    id: 3,
    label: 'Sandbox',
    meta: 'Ephemeral container · non-root · cgroup enforced',
    detail: {
      title: 'Container limits',
      lines: [
        '  cpu        1.0 core',
        '  memory     1024 MB',
        '  pids       128 max',
        '  network    bridge isolated',
        '  timeout    300s',
      ],
    },
  },
  {
    id: 4,
    label: 'Build',
    meta: 'pnpm build · dist/ · 41s elapsed',
    detail: {
      title: 'Build output',
      lines: [
        '  10:31:07  installing dependencies',
        '  10:31:21  running pnpm build',
        '  10:31:38  ✓ build completed',
        '  10:31:39  uploading artifact',
        '  10:31:42  ✓ deployment ready',
      ],
    },
  },
  {
    id: 5,
    label: 'Deploy',
    meta: 'Atomic pointer switch · zero downtime',
    detail: {
      title: 'Deployment record',
      lines: [
        '  url        my-store.ziref.app',
        '  build      #1842',
        '  cutover    12ms',
        '  rollback   < 20ms',
        '  status     ● live',
      ],
    },
  },
];

const fullLog = [
  { t: '10:31:02', text: 'Preparing build environment',    ok: false },
  { t: '10:31:05', text: 'Detected Vite + React project',  ok: false },
  { t: '10:31:07', text: 'Installing dependencies (pnpm)', ok: false },
  { t: '10:31:21', text: 'Running pnpm build',             ok: false },
  { t: '10:31:38', text: 'Build completed successfully',   ok: true  },
  { t: '10:31:39', text: 'Uploading build artifact',       ok: false },
  { t: '10:31:42', text: 'Deployment ready',               ok: true  },
];

export function ArchitecturePipeline() {
  const [activeStep, setActiveStep] = useState(1);
  const [selectedStep, setSelectedStep] = useState(1);
  const [isRunning, setIsRunning] = useState(true);
  const [visibleLogs, setVisibleLogs] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-cycle through steps
  useEffect(() => {
    if (!isRunning) return;
    intervalRef.current = setInterval(() => {
      setActiveStep((prev) => (prev >= steps.length ? 1 : prev + 1));
    }, 2200);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isRunning]);

  // Sync selected to active when running
  useEffect(() => {
    if (isRunning) setSelectedStep(activeStep);
  }, [activeStep, isRunning]);

  // Stream log entries
  useEffect(() => {
    if (visibleLogs >= fullLog.length) return;
    const t = setTimeout(() => setVisibleLogs((v) => v + 1), 420);
    return () => clearTimeout(t);
  }, [visibleLogs]);

  const handleStepClick = (id: number) => {
    setSelectedStep(id);
    if (isRunning) {
      setIsRunning(false);
    }
  };

  const handleRunSim = () => {
    setIsRunning(false);
    setVisibleLogs(0);
    setActiveStep(1);
    setSelectedStep(1);
    setTimeout(() => setIsRunning(true), 100);
    setTimeout(() => setVisibleLogs(1), 200);
  };

  const currentDetail = steps.find((s) => s.id === selectedStep)?.detail;
  const progressPct = ((activeStep - 1) / (steps.length - 1)) * 100;

  return (
    <section id="how-it-works" className="py-24 border-t border-[var(--border)]">
      <div className="max-w-layout mx-auto px-6 lg:px-10">
        {/* Two-column header */}
        <div className="grid lg:grid-cols-2 gap-10 mb-16">
          <div>
            <p className="font-mono text-[13px] text-[var(--text-tertiary)] tracking-wider uppercase mb-3">
              Build Pipeline
            </p>
            <h2
              className="text-4xl lg:text-5xl font-bold text-[var(--text-primary)] mb-5"
              style={{ letterSpacing: '-0.03em', lineHeight: 1.1 }}
            >
              From local code
              <br />to a live product.
            </h2>
            <p className="text-[16px] text-[var(--text-secondary)]" style={{ lineHeight: 1.65 }}>
              Upload a ZIP or trigger via CLI. Ziref detects your stack, builds in an isolated sandbox, and deploys with zero downtime — no configuration required.
            </p>
          </div>

          <div className="flex items-end lg:justify-end">
            <div className="space-y-2 text-[13px] text-[var(--text-secondary)] font-mono">
              <div className="flex items-center gap-2">
                <span className="text-emerald-500">✓</span>
                <span>Automatic framework detection</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-500">✓</span>
                <span>Ephemeral sandboxed builds</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-500">✓</span>
                <span>Atomic zero-downtime deploys</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-500">✓</span>
                <span>Instant rollback &lt; 20ms</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main interactive area */}
        <div className="grid lg:grid-cols-5 gap-8">
          {/* Pipeline steps — left 3 cols */}
          <div className="lg:col-span-3">
            {/* Progress bar */}
            <div className="mb-6 flex items-center justify-between">
              <span className="text-[12px] font-mono text-[var(--text-tertiary)]">
                {isRunning ? `Step ${activeStep} of ${steps.length}` : 'Paused'}
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsRunning(!isRunning)}
                  className="text-[12px] font-mono text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
                >
                  {isRunning ? '⏸ pause' : '▶ resume'}
                </button>
                <button
                  onClick={handleRunSim}
                  className="text-[12px] font-mono text-[var(--accent-text)] hover:underline"
                >
                  ↺ replay
                </button>
              </div>
            </div>

            {/* Progress track */}
            <div className="h-0.5 bg-[var(--border)] rounded-full mb-6 overflow-hidden">
              <div
                className="h-full bg-[var(--accent)] transition-all duration-700 ease-out"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            {/* Step rows */}
            <div className="space-y-1">
              {steps.map((step, i) => {
                const isActive = activeStep === step.id;
                const isComplete = activeStep > step.id;
                const isSelected = selectedStep === step.id;

                return (
                  <button
                    key={step.id}
                    onClick={() => handleStepClick(step.id)}
                    className={`w-full text-left px-4 py-3.5 rounded-lg border transition-all duration-200 ${
                      isSelected
                        ? 'border-[var(--accent)] bg-[var(--accent-subtle)] dark:bg-[var(--accent-subtle)]'
                        : isActive
                        ? 'border-[var(--border-strong)] bg-[var(--surface)]'
                        : 'border-transparent bg-transparent hover:bg-[var(--surface-muted)]'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      {/* Step number / status */}
                      <div
                        className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 font-mono text-[11px] font-semibold transition-all duration-300 ${
                          isComplete
                            ? 'bg-emerald-500 text-white'
                            : isActive
                            ? 'bg-[var(--accent)] text-white'
                            : 'bg-[var(--surface-muted)] text-[var(--text-tertiary)] border border-[var(--border)]'
                        }`}
                      >
                        {isComplete ? '✓' : step.id}
                      </div>

                      {/* Label + meta */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[13px] font-semibold ${
                              isSelected || isActive
                                ? 'text-[var(--text-primary)]'
                                : 'text-[var(--text-secondary)]'
                            }`}
                          >
                            {step.label}
                          </span>
                          {isActive && isRunning && (
                            <span className="flex gap-0.5">
                              <span className="w-1 h-1 rounded-full bg-[var(--accent)] animate-bounce" style={{ animationDelay: '0ms' }} />
                              <span className="w-1 h-1 rounded-full bg-[var(--accent)] animate-bounce" style={{ animationDelay: '150ms' }} />
                              <span className="w-1 h-1 rounded-full bg-[var(--accent)] animate-bounce" style={{ animationDelay: '300ms' }} />
                            </span>
                          )}
                        </div>
                        <div className="font-mono text-[11px] text-[var(--text-tertiary)] truncate mt-0.5">
                          {step.meta}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Detail panel + log — right 2 cols */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            {/* Detail data */}
            <div className="border border-[var(--border)] rounded-lg overflow-hidden bg-[var(--surface)]">
              <div className="px-4 py-2.5 border-b border-[var(--border)] bg-[var(--surface-muted)] flex items-center justify-between">
                <span className="font-mono text-[11px] text-[var(--text-tertiary)]">
                  {currentDetail?.title}
                </span>
                <span className="font-mono text-[10px] text-emerald-500">✓ validated</span>
              </div>
              <div className="p-4">
                <pre className="font-mono text-[12px] text-[var(--text-secondary)] leading-relaxed">
                  {currentDetail?.lines.join('\n')}
                </pre>
              </div>
            </div>

            {/* Build log */}
            <div className="border border-[var(--border)] rounded-lg overflow-hidden bg-[#0D1117] flex-1">
              <div className="px-4 py-2.5 border-b border-[#30363D] flex items-center justify-between">
                <span className="font-mono text-[11px] text-[#8B949E]">Build #1842</span>
                {visibleLogs >= fullLog.length && (
                  <span className="font-mono text-[10px] text-emerald-400">● done</span>
                )}
              </div>
              <div className="p-4 space-y-2">
                {fullLog.slice(0, visibleLogs).map((entry, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="font-mono text-[10px] text-[#484F58] shrink-0 mt-0.5 tabular-nums">
                      {entry.t}
                    </span>
                    <span
                      className={`font-mono text-[10px] leading-relaxed ${
                        entry.ok ? 'text-emerald-400' : 'text-[#8B949E]'
                      }`}
                    >
                      {entry.text}
                    </span>
                  </div>
                ))}
                {visibleLogs < fullLog.length && (
                  <div className="flex gap-3">
                    <span className="font-mono text-[10px] text-[#484F58] shrink-0">
                      {fullLog[visibleLogs]?.t}
                    </span>
                    <span className="font-mono text-[10px] text-[#484F58]">
                      _<span className="animate-cursor-blink">|</span>
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
