'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Terminal, Copy, Check, ArrowDown } from 'lucide-react';

interface LogEvent {
  timestamp?: string;
  stage?: string;
  level?: string;
  message: string;
}

interface TerminalViewerProps {
  logs: LogEvent[];
  title?: string;
  isStreaming?: boolean;
}

export function TerminalViewer({ logs, title = "Build Output", isStreaming = false }: TerminalViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleCopy = () => {
    const text = logs.map(l => `${l.timestamp ? `[${l.timestamp.slice(11, 19)}] ` : ''}${l.stage ? `[${l.stage}] ` : ''}${l.message}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-[#0c0c0e] font-mono text-xs overflow-hidden shadow-2xl">
      {/* Terminal Title Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-900/80 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-zinc-400" />
          <span className="font-semibold text-zinc-300">{title}</span>
          {isStreaming && (
            <span className="flex items-center gap-1.5 text-[11px] text-amber-400 px-2 py-0.5 rounded bg-amber-950/40 border border-amber-900/50">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
              Live Streaming
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2 py-1 rounded text-[11px] transition-colors ${
              autoScroll ? 'bg-zinc-800 text-zinc-200' : 'text-zinc-500 hover:text-zinc-300'
            }`}
            title="Toggle Auto Scroll"
          >
            Auto-scroll
          </button>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 rounded text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      {/* Terminal Content */}
      <div
        ref={containerRef}
        className="p-4 max-h-[480px] overflow-y-auto space-y-1 select-text scroll-smooth"
      >
        {logs.length === 0 ? (
          <div className="text-zinc-600 py-8 text-center">Waiting for build worker output...</div>
        ) : (
          logs.map((log, i) => {
            const isError = log.level === 'error' || log.message.toLowerCase().includes('error');
            const isWarning = log.level === 'warning';
            const isStage = log.message.startsWith('==>') || log.message.startsWith('✓');

            return (
              <div key={i} className="flex items-start gap-2.5 leading-relaxed group hover:bg-zinc-900/50 px-1 py-0.5 rounded">
                {log.timestamp && (
                  <span className="text-zinc-600 shrink-0 select-none text-[11px]">
                    {log.timestamp.slice(11, 19)}
                  </span>
                )}
                {log.stage && (
                  <span className="text-sky-500/80 font-medium shrink-0 text-[11px] uppercase">
                    [{log.stage}]
                  </span>
                )}
                <span className={`break-all ${
                  isError ? 'text-rose-400 font-semibold' :
                  isWarning ? 'text-amber-400' :
                  isStage ? 'text-sky-300 font-medium' :
                  'text-zinc-300'
                }`}>
                  {log.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
