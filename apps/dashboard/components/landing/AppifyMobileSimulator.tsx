'use client';

import React, { useState } from 'react';
import { Wifi, WifiOff, RotateCw } from 'lucide-react';

const features = [
  {
    title: 'Native Android package',
    desc: 'Kotlin project with WebViewClient, AdaptiveIcon, and full AndroidManifest.xml — generated automatically.',
  },
  {
    title: 'App icon & splash screen',
    desc: 'Adaptive mipmap vector icons generated from your brand. Configurable splash screen included.',
  },
  {
    title: 'Pull-to-refresh',
    desc: 'SwipeRefreshLayout wired to reload your live URL with hardware acceleration enabled.',
  },
  {
    title: 'Offline fallback',
    desc: 'Native offline detection with a graceful fallback screen and cached content access.',
  },
  {
    title: 'Downloadable APK',
    desc: 'Receive an installable debug .apk, or export the full Android Studio Gradle workspace.',
  },
];

export function AppifyMobileSimulator() {
  const [isOffline, setIsOffline] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  return (
    <section id="appify" className="py-24 border-t border-[var(--border)]">
      <div className="max-w-layout mx-auto px-6 lg:px-10">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left — copy */}
          <div>
            <p className="font-mono text-[13px] text-[var(--text-tertiary)] tracking-wider uppercase mb-3">
              Appify — Web to Mobile
            </p>
            <h2
              className="text-4xl lg:text-5xl font-bold text-[var(--text-primary)] mb-5"
              style={{ letterSpacing: '-0.03em', lineHeight: 1.1 }}
            >
              Your web app,
              <br />packaged for mobile.
            </h2>
            <p className="text-[16px] text-[var(--text-secondary)] mb-8" style={{ lineHeight: 1.65 }}>
              One click. Ziref wraps your deployed web app into a native Android application — no Android development experience required.
            </p>

            <div className="space-y-5 mb-10">
              {features.map(({ title, desc }) => (
                <div key={title} className="flex gap-4">
                  <div className="mt-1 w-4 h-4 shrink-0 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                  </div>
                  <div>
                    <div className="text-[14px] font-semibold text-[var(--text-primary)] mb-0.5">
                      {title}
                    </div>
                    <div className="text-[13px] text-[var(--text-secondary)]" style={{ lineHeight: 1.6 }}>
                      {desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>


          </div>

          {/* Right — phone */}
          <div className="flex flex-col items-center">
            {/* Sim controls */}
            <div className="flex items-center gap-2 mb-4 text-[12px] font-mono text-[var(--text-tertiary)]">
              <button
                onClick={() => setIsOffline(!isOffline)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded border transition-colors ${
                  isOffline
                    ? 'border-amber-300 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400'
                    : 'border-[var(--border)] hover:border-[var(--border-strong)]'
                }`}
              >
                {isOffline
                  ? <WifiOff className="w-3 h-3" />
                  : <Wifi className="w-3 h-3" />
                }
                {isOffline ? 'Offline' : 'Online'}
              </button>
              <button
                onClick={handleRefresh}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[var(--border)] hover:border-[var(--border-strong)] transition-colors"
              >
                <RotateCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>

            {/* Phone frame */}
            <div className="relative w-[260px] rounded-[40px] border-[7px] border-slate-900 dark:border-zinc-700 bg-slate-900 shadow-float overflow-hidden select-none">
              {/* Notch */}
              <div className="h-7 bg-black flex items-center justify-center">
                <div className="w-16 h-4 bg-slate-900 rounded-b-xl flex items-center justify-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-slate-800" />
                  <div className="w-7 h-1 bg-slate-800 rounded-full" />
                </div>
              </div>

              {/* Screen */}
              <div className="h-[480px] bg-white dark:bg-zinc-950 flex flex-col overflow-hidden">
                {/* Status bar */}
                <div className="flex items-center justify-between px-5 py-1.5 bg-[#1D4ED8] text-white text-[10px] font-mono">
                  <span>18:30</span>
                  <div className="flex items-center gap-1">
                    {isOffline
                      ? <WifiOff className="w-2.5 h-2.5 text-amber-300" />
                      : <Wifi className="w-2.5 h-2.5" />
                    }
                    <span>100%</span>
                  </div>
                </div>

                {/* App bar */}
                <div className="flex items-center gap-2 px-3 py-2.5 bg-[#1D4ED8] text-white border-b border-blue-600">
                  <div className="w-6 h-6 rounded bg-white/20 flex items-center justify-center font-bold text-[11px]">
                    Z
                  </div>
                  <span className="text-[12px] font-semibold">Shop Analytics</span>
                </div>

                {/* Content area */}
                {isOffline ? (
                  <div className="flex-1 flex flex-col items-center justify-center p-5 text-center bg-white dark:bg-zinc-950">
                    <WifiOff className="w-8 h-8 text-amber-400 mb-3" />
                    <p className="text-[12px] font-semibold text-[var(--text-primary)] mb-1">You're offline</p>
                    <p className="text-[11px] text-[var(--text-tertiary)] mb-4">Cached data is available.</p>
                    <button
                      onClick={() => setIsOffline(false)}
                      className="px-3 py-1.5 rounded bg-[#1D4ED8] text-white text-[11px] font-semibold"
                    >
                      Retry
                    </button>
                  </div>
                ) : (
                  <div className="flex-1 p-3 space-y-2.5 overflow-y-auto bg-slate-50 dark:bg-zinc-900">
                    {isRefreshing && (
                      <div className="text-center text-[10px] font-mono text-[#1D4ED8] animate-pulse py-0.5">
                        Refreshing…
                      </div>
                    )}

                    {/* Revenue card */}
                    <div className="p-3 rounded-lg bg-white dark:bg-zinc-800 border border-slate-100 dark:border-zinc-700">
                      <div className="text-[10px] text-[var(--text-tertiary)] mb-0.5">Today's Revenue</div>
                      <div className="text-[18px] font-bold text-[var(--text-primary)] font-mono">$14,892</div>
                      <div className="text-[10px] text-emerald-600 font-medium mt-0.5">+18.4% vs yesterday</div>
                    </div>

                    {/* Two stat cards */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-800 border border-slate-100 dark:border-zinc-700">
                        <div className="text-[10px] text-[var(--text-tertiary)] mb-0.5">Orders</div>
                        <div className="text-[14px] font-bold text-[var(--text-primary)] font-mono">128</div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-800 border border-slate-100 dark:border-zinc-700">
                        <div className="text-[10px] text-[var(--text-tertiary)] mb-0.5">Conversion</div>
                        <div className="text-[14px] font-bold text-emerald-600 font-mono">3.8%</div>
                      </div>
                    </div>

                    {/* Sessions row */}
                    <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-800 border border-slate-100 dark:border-zinc-700">
                      <div className="text-[10px] text-[var(--text-tertiary)] mb-0.5">Active sessions</div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-slate-100 dark:bg-zinc-700 rounded-full overflow-hidden">
                          <div className="h-full bg-[#1D4ED8] rounded-full" style={{ width: '62%' }} />
                        </div>
                        <span className="text-[10px] font-mono font-semibold text-[var(--text-primary)]">62%</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Android nav bar */}
                <div className="h-7 bg-white dark:bg-zinc-950 flex items-center justify-center border-t border-slate-100 dark:border-zinc-800">
                  <div className="w-20 h-1 bg-slate-300 dark:bg-zinc-600 rounded-full" />
                </div>
              </div>
            </div>

            {/* Caption */}
            <div className="mt-4 font-mono text-[11px] text-[var(--text-tertiary)] text-center">
              Generated Android APK · 8.4 MB · API 34
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
