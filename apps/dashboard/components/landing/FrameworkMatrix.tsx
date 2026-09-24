'use client';

import React, { useState } from 'react';

interface FrameworkInfo {
  id: string;
  name: string;
  category: string;
  detectRule: string;
  buildCommand: string;
  outputDir: string;
  packageManager: string;
  runtime: string;
  description: string;
}

const frameworks: FrameworkInfo[] = [
  {
    id: 'vite-react',
    name: 'React + Vite',
    category: 'Single Page App',
    detectRule: 'package.json → "vite" + "react"',
    buildCommand: 'pnpm build',
    outputDir: 'dist/',
    packageManager: 'pnpm / npm / yarn',
    runtime: 'Static',
    description:
      'Auto-detects Vite config and compiles fast client bundles with native ES modules. No manual build command needed.',
  },
  {
    id: 'nextjs',
    name: 'Next.js',
    category: 'Fullstack / SSG',
    detectRule: 'package.json → "next" or next.config.js',
    buildCommand: 'next build',
    outputDir: '.next / out/',
    packageManager: 'pnpm / npm',
    runtime: 'Node / Static',
    description:
      'Zero-config detection for App Router and Pages Router. Static export and server optimization supported.',
  },
  {
    id: 'vue',
    name: 'Vue 3',
    category: 'Reactive SPA',
    detectRule: 'package.json → "vue" + vite config',
    buildCommand: 'vite build',
    outputDir: 'dist/',
    packageManager: 'pnpm / npm',
    runtime: 'Static',
    description:
      'Compiles modern Vue 3 single-file components into high-performance static assets.',
  },
  {
    id: 'angular',
    name: 'Angular',
    category: 'Enterprise SPA',
    detectRule: 'angular.json manifest present',
    buildCommand: 'ng build --configuration production',
    outputDir: 'dist/<project>',
    packageManager: 'npm',
    runtime: 'Static',
    description:
      'Parses angular.json to locate exact output paths, polyfills, and AoT compilation flags.',
  },
  {
    id: 'astro',
    name: 'Astro',
    category: 'Content Sites',
    detectRule: 'astro.config.mjs or "astro" in package.json',
    buildCommand: 'astro build',
    outputDir: 'dist/',
    packageManager: 'pnpm / npm / bun',
    runtime: 'Static',
    description:
      'Ultra-fast static delivery with partial hydration and zero unused client JavaScript.',
  },
  {
    id: 'svelte',
    name: 'SvelteKit',
    category: 'Compiler Framework',
    detectRule: 'svelte.config.js or "@sveltejs/kit"',
    buildCommand: 'vite build',
    outputDir: 'build/',
    packageManager: 'pnpm / npm',
    runtime: 'Static / Node',
    description:
      'Compiles components into surgical vanilla JS. Minimal runtime, maximum performance.',
  },
  {
    id: 'static',
    name: 'Static HTML',
    category: 'Pure Web',
    detectRule: 'index.html in root or subfolder',
    buildCommand: '— (no build step)',
    outputDir: './',
    packageManager: 'none required',
    runtime: 'Static',
    description:
      'Instant edge deployment with no compile delay. Gzip-compressed and served directly.',
  },
];

const dataRows = [
  { key: 'Detection',      field: 'detectRule'     },
  { key: 'Build command',  field: 'buildCommand'   },
  { key: 'Output',         field: 'outputDir'      },
  { key: 'Package manager',field: 'packageManager' },
  { key: 'Runtime',        field: 'runtime'        },
] as const;

export function FrameworkMatrix() {
  const [selectedId, setSelectedId] = useState<string>('vite-react');
  const selected = frameworks.find((f) => f.id === selectedId) ?? frameworks[0];

  return (
    <section id="frameworks" className="py-24 border-t border-[var(--border)]">
      <div className="max-w-layout mx-auto px-6 lg:px-10">
        {/* Header */}
        <div className="mb-10">
          <p className="font-mono text-[13px] text-[var(--text-tertiary)] tracking-wider uppercase mb-3">
            Framework Support
          </p>
          <div className="grid lg:grid-cols-2 gap-6 items-end">
            <h2
              className="text-4xl lg:text-5xl font-bold text-[var(--text-primary)]"
              style={{ letterSpacing: '-0.03em', lineHeight: 1.1 }}
            >
              Zero config.
              <br />Every framework.
            </h2>
            <p className="text-[16px] text-[var(--text-secondary)]" style={{ lineHeight: 1.65 }}>
              Ziref's analyzer inspects dependency manifests and lockfiles to infer commands, output paths, and runtime environments — automatically.
            </p>
          </div>
        </div>

        {/* Tab bar — underline style */}
        <div
          className="flex items-center gap-0 border-b border-[var(--border)] mb-8 overflow-x-auto"
          role="tablist"
          aria-label="Framework selector"
        >
          {frameworks.map((fw) => (
            <button
              key={fw.id}
              role="tab"
              aria-selected={selectedId === fw.id}
              aria-controls={`framework-panel-${fw.id}`}
              onClick={() => setSelectedId(fw.id)}
              className={`px-4 py-2.5 text-[13px] font-medium whitespace-nowrap transition-all duration-150 border-b-2 -mb-px ${
                selectedId === fw.id
                  ? 'border-[var(--accent)] text-[var(--accent-text)]'
                  : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]'
              }`}
            >
              {fw.name}
            </button>
          ))}
        </div>

        {/* Detail panel */}
        <div
          id={`framework-panel-${selected.id}`}
          role="tabpanel"
          className="grid lg:grid-cols-3 gap-8"
        >
          {/* Description + category */}
          <div className="lg:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <span className="font-mono text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider px-2 py-0.5 rounded border border-[var(--border)]">
                {selected.category}
              </span>
              <span className="flex items-center gap-1 font-mono text-[11px] text-emerald-600 dark:text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                Auto
              </span>
            </div>
            <h3
              className="text-[20px] font-semibold text-[var(--text-primary)] mb-3"
              style={{ letterSpacing: '-0.02em' }}
            >
              {selected.name}
            </h3>
            <p className="text-[14px] text-[var(--text-secondary)]" style={{ lineHeight: 1.6 }}>
              {selected.description}
            </p>
          </div>

          {/* Data table */}
          <div className="lg:col-span-2">
            <div className="border border-[var(--border)] rounded-lg overflow-hidden">
              {dataRows.map(({ key, field }, i) => (
                <div
                  key={key}
                  className={`flex items-start gap-4 px-5 py-3.5 ${
                    i < dataRows.length - 1 ? 'border-b border-[var(--border)]' : ''
                  } ${i % 2 === 0 ? 'bg-[var(--surface)]' : 'bg-[var(--surface-muted)]'}`}
                >
                  <span className="text-[12px] text-[var(--text-tertiary)] shrink-0 w-36">
                    {key}
                  </span>
                  <span className="font-mono text-[12px] text-[var(--text-primary)] font-medium">
                    {selected[field]}
                  </span>
                </div>
              ))}
            </div>

            {/* Bottom note */}
            <div className="mt-4 flex items-center gap-2 font-mono text-[11px] text-[var(--text-tertiary)]">
              <span>Detection accuracy</span>
              <span className="text-emerald-500 font-semibold">100% deterministic</span>
              <span className="mx-1">·</span>
              <span>Speed</span>
              <span className="font-semibold text-[var(--text-secondary)]">&lt; 45ms</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
