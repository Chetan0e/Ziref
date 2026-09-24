'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Shield, Cpu, Lock, Zap } from 'lucide-react';

// ─── Pipeline nodes ────────────────────────────────────────────────────────────
const NODES = [
  {
    id: 'platform',
    label: 'Ziref Platform',
    tag: null,
    color: '#3B82F6',
    glow: 'rgba(59,130,246,0.35)',
    bg: 'rgba(59,130,246,0.08)',
    specs: null,
  },
  {
    id: 'gateway',
    label: 'API Gateway',
    tag: 'auth · rate-limit · log',
    color: '#8B5CF6',
    glow: 'rgba(139,92,246,0.35)',
    bg: 'rgba(139,92,246,0.08)',
    specs: null,
  },
  {
    id: 'worker',
    label: 'Build Worker',
    tag: 'detect · queue · run',
    color: '#06B6D4',
    glow: 'rgba(6,182,212,0.35)',
    bg: 'rgba(6,182,212,0.08)',
    specs: null,
  },
  {
    id: 'sandbox',
    label: 'Ephemeral Sandbox',
    tag: null,
    color: '#10B981',
    glow: 'rgba(16,185,129,0.35)',
    bg: 'rgba(16,185,129,0.08)',
    specs: [
      ['user', 'UID 10001'],
      ['cpu', '1.0 core'],
      ['memory', '1024 MB'],
      ['pids', '128 max'],
      ['fs', 'read-only'],
      ['net', 'bridge isolated'],
      ['timeout', '300s hard'],
    ],
  },
  {
    id: 'capture',
    label: 'Artifact Capture',
    tag: 'sha256 · destroy · store',
    color: '#F59E0B',
    glow: 'rgba(245,158,11,0.35)',
    bg: 'rgba(245,158,11,0.08)',
    specs: null,
  },
] as const;

// ─── Security feature cards ────────────────────────────────────────────────────
const CARDS = [
  {
    icon: Shield,
    title: 'Zip Slip & bomb defense',
    desc: 'Path traversal validation on every extracted file. Uncompressed ratio capped at 100× to prevent decompression DOS.',
    color: '#3B82F6',
  },
  {
    icon: Cpu,
    title: 'Hardened cgroup quotas',
    desc: 'Non-root UID 10001. Memory: 1024 MB. CPU: 1.0 core. PIDs: 128. Zero host socket exposure. Container destroyed post-build.',
    color: '#8B5CF6',
  },
  {
    icon: Lock,
    title: 'Encryption at rest',
    desc: 'Environment variables encrypted with Fernet symmetric keys. Values masked in UI, decrypted strictly in memory at build time.',
    color: '#10B981',
  },
  {
    icon: Zap,
    title: 'Ephemeral environments',
    desc: 'Every build container is created fresh and destroyed immediately after artifact capture. No cross-tenant access is possible.',
    color: '#F59E0B',
  },
];

// ─── Animated connector ────────────────────────────────────────────────────────
function Connector({ active, fromColor, toColor }: { active: boolean; fromColor: string; toColor: string }) {
  return (
    <div className="flex flex-col items-center" style={{ height: 28 }}>
      <div
        style={{
          width: 2,
          flex: 1,
          background: active
            ? `linear-gradient(to bottom, ${fromColor}, ${toColor})`
            : 'rgba(255,255,255,0.06)',
          transition: 'background 0.5s ease',
          borderRadius: 1,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {active && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '100%',
              background: `linear-gradient(to bottom, transparent, ${toColor}80, transparent)`,
              animation: 'flowDown 0.8s linear infinite',
            }}
          />
        )}
      </div>
      {/* Arrowhead */}
      <svg width="8" height="5" viewBox="0 0 8 5" fill="none" style={{ display: 'block', flexShrink: 0 }}>
        <path
          d="M4 5L0.5 0.5H7.5L4 5Z"
          fill={active ? toColor : 'rgba(255,255,255,0.1)'}
          style={{ transition: 'fill 0.4s ease' }}
        />
      </svg>
    </div>
  );
}

// ─── Pipeline node card ────────────────────────────────────────────────────────
function PipelineNode({ node, isActive, index, totalActive }: {
  node: typeof NODES[number];
  isActive: boolean;
  index: number;
  totalActive: number;
}) {
  const isPast = index < totalActive;

  return (
    <div
      style={{
        borderRadius: 10,
        border: `1px solid ${isActive ? node.color : isPast ? `${node.color}50` : 'rgba(255,255,255,0.06)'}`,
        background: isActive ? node.bg : isPast ? `${node.bg.slice(0, -5)}0.04)` : 'rgba(255,255,255,0.02)',
        boxShadow: isActive ? `0 0 24px ${node.glow}, 0 0 48px ${node.glow.replace('0.35', '0.12')}` : 'none',
        padding: '10px 16px',
        transition: 'all 0.4s ease',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Shimmer sweep on active */}
      {isActive && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `linear-gradient(105deg, transparent 40%, ${node.color}18 50%, transparent 60%)`,
            animation: 'shimmer 1.6s ease-in-out infinite',
          }}
        />
      )}

      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 12,
          fontWeight: 600,
          color: isActive ? node.color : isPast ? `${node.color}90` : 'rgba(255,255,255,0.3)',
          transition: 'color 0.4s ease',
          marginBottom: node.tag || node.specs ? 3 : 0,
          position: 'relative',
        }}
      >
        {node.label}
        {isActive && (
          <span
            style={{
              marginLeft: 8,
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: '0.08em',
              color: node.color,
              backgroundColor: `${node.color}20`,
              border: `1px solid ${node.color}40`,
              borderRadius: 4,
              padding: '1px 5px',
              verticalAlign: 'middle',
            }}
          >
            ACTIVE
          </span>
        )}
      </div>

      {node.tag && (
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: isActive ? `${node.color}CC` : 'rgba(255,255,255,0.18)',
            transition: 'color 0.4s ease',
            position: 'relative',
          }}
        >
          {node.tag}
        </div>
      )}

      {node.specs && (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 2, position: 'relative' }}>
          {node.specs.map(([k, v], si) => (
            <div
              key={k}
              style={{
                display: 'flex',
                gap: 8,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                opacity: isActive ? 1 : 0.3,
                transition: `opacity 0.3s ease ${si * 40}ms`,
              }}
            >
              <span style={{ color: 'rgba(255,255,255,0.3)', width: 52, flexShrink: 0 }}>{k}:</span>
              <span style={{ color: isActive ? '#6EE7B7' : 'rgba(255,255,255,0.2)' }}>{v}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main exported section ─────────────────────────────────────────────────────
export function SecuritySection() {
  const [activeNode, setActiveNode] = useState(-1);
  const [visible, setVisible] = useState(false);
  const [buildCount, setBuildCount] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);

  // Intersection observer — trigger once
  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.15 }
    );
    if (sectionRef.current) obs.observe(sectionRef.current);
    return () => obs.disconnect();
  }, []);

  // Pipeline animation loop — start after visibility
  useEffect(() => {
    if (!visible) return;
    // Small delay before starting
    const startDelay = setTimeout(() => {
      setActiveNode(0);
    }, 400);
    return () => clearTimeout(startDelay);
  }, [visible]);

  useEffect(() => {
    if (activeNode < 0) return;
    const timer = setTimeout(() => {
      if (activeNode < NODES.length - 1) {
        setActiveNode((n) => n + 1);
      } else {
        // Restart the loop
        setTimeout(() => {
          setBuildCount((c) => c + 1);
          setActiveNode(0);
        }, 1200);
      }
    }, 1300);
    return () => clearTimeout(timer);
  }, [activeNode]);

  return (
    <>
      {/* Keyframes injected once */}
      <style>{`
        @keyframes flowDown {
          0%   { transform: translateY(-100%); }
          100% { transform: translateY(100%);  }
        }
        @keyframes shimmer {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(100%);  }
        }
        @keyframes secFadeUp {
          from { opacity: 0; transform: translateY(18px); }
          to   { opacity: 1; transform: translateY(0);    }
        }
        @keyframes secSlideIn {
          from { opacity: 0; transform: translateX(-16px); }
          to   { opacity: 1; transform: translateX(0);     }
        }
        @keyframes pulseDot {
          0%, 100% { transform: scale(1);   opacity: 1; }
          50%       { transform: scale(1.6); opacity: 0.6; }
        }
        @keyframes counterUp {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <section
        ref={sectionRef}
        id="security"
        className="py-24 border-t border-[var(--border)] relative overflow-hidden"
      >
        {/* Subtle radial glow in background */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(ellipse 60% 50% at 75% 50%, rgba(59,130,246,0.045) 0%, transparent 70%)',
            pointerEvents: 'none',
          }}
        />

        <div className="max-w-layout mx-auto px-6 lg:px-10 relative">
          {/* ── Header ─────────────────────────────────────────────────── */}
          <div className="grid lg:grid-cols-2 gap-10 mb-16">
            <div
              style={
                visible
                  ? { animation: 'secFadeUp 0.6s ease forwards' }
                  : { opacity: 0 }
              }
            >
              <p className="font-mono text-[13px] text-[var(--text-tertiary)] tracking-wider uppercase mb-3">
                Security
              </p>
              <h2
                className="text-4xl lg:text-5xl font-bold text-[var(--text-primary)]"
                style={{ letterSpacing: '-0.03em', lineHeight: 1.1 }}
              >
                Secure by default.
                <br />Isolated by design.
              </h2>
            </div>
            <div
              className="flex items-end"
              style={
                visible
                  ? { animation: 'secFadeUp 0.6s ease 0.15s both' }
                  : { opacity: 0 }
              }
            >
              <p className="text-[16px] text-[var(--text-secondary)]" style={{ lineHeight: 1.65 }}>
                Uploaded code is inherently untrusted. Ziref ensures that no user archive
                can compromise the host, access neighboring sandboxes, or leak runtime credentials.
              </p>
            </div>
          </div>

          {/* ── Main grid: cards (left) + pipeline (right) ──────────────── */}
          <div className="grid lg:grid-cols-2 gap-12 items-start">

            {/* Left — Security feature cards */}
            <div className="space-y-3">
              {CARDS.map(({ icon: Icon, title, desc, color }, i) => (
                <div
                  key={title}
                  style={
                    visible
                      ? { animation: `secSlideIn 0.5s ease ${0.1 + i * 0.1}s both` }
                      : { opacity: 0 }
                  }
                >
                  <div
                    className="group flex gap-4 p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] cursor-default"
                    style={{ transition: 'border-color 0.25s, box-shadow 0.25s' }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLDivElement).style.borderColor = `${color}60`;
                      (e.currentTarget as HTMLDivElement).style.boxShadow = `0 0 0 1px ${color}20, 0 4px 16px ${color}12`;
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLDivElement).style.borderColor = '';
                      (e.currentTarget as HTMLDivElement).style.boxShadow = '';
                    }}
                  >
                    {/* Icon badge */}
                    <div
                      className="w-9 h-9 shrink-0 rounded-lg flex items-center justify-center"
                      style={{
                        backgroundColor: `${color}16`,
                        border: `1px solid ${color}28`,
                        transition: 'background 0.25s',
                      }}
                    >
                      <Icon className="w-4 h-4" style={{ color }} />
                    </div>

                    <div>
                      <div className="text-[14px] font-semibold text-[var(--text-primary)] mb-1">
                        {title}
                      </div>
                      <div
                        className="text-[13px] text-[var(--text-secondary)]"
                        style={{ lineHeight: 1.65 }}
                      >
                        {desc}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Right — Animated pipeline terminal */}
            <div
              style={
                visible
                  ? { animation: 'secFadeUp 0.7s ease 0.2s both' }
                  : { opacity: 0 }
              }
            >
              <div
                style={{
                  borderRadius: 14,
                  border: '1px solid rgba(255,255,255,0.08)',
                  backgroundColor: '#0A0A0E',
                  overflow: 'hidden',
                  boxShadow: '0 24px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04)',
                }}
              >
                {/* Terminal title bar */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '10px 16px',
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    background: 'rgba(255,255,255,0.02)',
                  }}
                >
                  {/* Traffic lights */}
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#FF5F57' }} />
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#FFBD2E' }} />
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#28C840' }} />

                  <span
                    style={{
                      marginLeft: 8,
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 11,
                      color: 'rgba(255,255,255,0.25)',
                    }}
                  >
                    sandbox-architecture
                  </span>

                  {/* Live badge */}
                  <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5 }}>
                    <div
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: '#10B981',
                        animation: 'pulseDot 1.8s ease-in-out infinite',
                      }}
                    />
                    <span
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 10,
                        fontWeight: 600,
                        color: '#10B981',
                        letterSpacing: '0.06em',
                      }}
                    >
                      LIVE
                    </span>
                  </div>
                </div>

                {/* Build counter strip */}
                <div
                  style={{
                    padding: '6px 16px',
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    background: 'rgba(255,255,255,0.01)',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 10,
                      color: 'rgba(255,255,255,0.2)',
                    }}
                  >
                    run #{1842 + buildCount}
                  </span>
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 10,
                      color: activeNode === NODES.length - 1 ? '#10B981' : '#F59E0B',
                      transition: 'color 0.3s ease',
                    }}
                  >
                    {activeNode === NODES.length - 1 ? '✓ complete' : '⟳ running…'}
                  </span>
                  {/* Progress bar */}
                  <div
                    style={{
                      marginLeft: 'auto',
                      width: 80,
                      height: 2,
                      borderRadius: 1,
                      background: 'rgba(255,255,255,0.06)',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        borderRadius: 1,
                        background: 'linear-gradient(to right, #3B82F6, #10B981)',
                        width: `${activeNode < 0 ? 0 : ((activeNode + 1) / NODES.length) * 100}%`,
                        transition: 'width 0.5s ease',
                      }}
                    />
                  </div>
                </div>

                {/* Pipeline nodes */}
                <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  {NODES.map((node, i) => (
                    <React.Fragment key={node.id}>
                      <div style={{ width: '100%', maxWidth: 320 }}>
                        <PipelineNode
                          node={node}
                          isActive={activeNode === i}
                          index={i}
                          totalActive={activeNode}
                        />
                      </div>
                      {i < NODES.length - 1 && (
                        <Connector
                          active={activeNode > i}
                          fromColor={node.color}
                          toColor={NODES[i + 1].color}
                        />
                      )}
                    </React.Fragment>
                  ))}
                </div>

                {/* Footer stats bar */}
                <div
                  style={{
                    padding: '10px 16px',
                    borderTop: '1px solid rgba(255,255,255,0.04)',
                    display: 'flex',
                    gap: 20,
                    background: 'rgba(255,255,255,0.01)',
                  }}
                >
                  {[
                    { label: 'containers destroyed', value: `${1842 + buildCount}` },
                    { label: 'host exposure', value: 'zero' },
                    { label: 'cross-tenant access', value: 'impossible' },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <div
                        style={{
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 10,
                          fontWeight: 700,
                          color: 'rgba(255,255,255,0.5)',
                        }}
                      >
                        {value}
                      </div>
                      <div
                        style={{
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 9,
                          color: 'rgba(255,255,255,0.18)',
                          marginTop: 1,
                        }}
                      >
                        {label}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
