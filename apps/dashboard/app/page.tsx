'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { ArrowRight, LayoutDashboard, FolderGit2, Zap, Settings, LogOut, ChevronDown, User as UserIcon } from 'lucide-react';
import { ZirefLogo } from '@/components/ui/ZirefLogo';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { useAuth } from '@/lib/auth';
import { HeroBrowserMockup } from '@/components/landing/HeroBrowserMockup';
import { ArchitecturePipeline } from '@/components/landing/ArchitecturePipeline';
import { FrameworkMatrix } from '@/components/landing/FrameworkMatrix';
import { AppifyMobileSimulator } from '@/components/landing/AppifyMobileSimulator';
import { SecuritySection } from '@/components/landing/SecuritySection';
import { LandingFaq } from '@/components/landing/LandingFaq';

// ─── Anonymous Nav links ───────────────────────────────────────────────────
const anonymousNavLinks = [
  { label: 'Product',    href: '#how-it-works' },
  { label: 'Developers', href: '#frameworks'   },
  { label: 'Pricing',    href: '#pricing'      },
  { label: 'Security',   href: '#security'     },
  { label: 'Docs',       href: '#faq'          },
];

// ─── Authenticated Nav links ───────────────────────────────────────────────
const authenticatedNavLinks = [
  { label: 'Dashboard',   href: '/dashboard'             },
  { label: 'Projects',    href: '/dashboard/projects'    },
  { label: 'Deployments', href: '/dashboard/deployments' },
];

const footerLinks = {
  Product: [
    'Deployments',
    'Appify',
    'Domains',
    'Changelog',
    'Pricing',
  ],
  Developers: [
    'Documentation',
    'API Reference',
    'CLI',
    'SDK',
    'GitHub',
  ],
  Company: [
    'About',
    'Security',
    'Contact',
    'Status',
  ],
  Resources: [
    'Guides',
    'Examples',
    'Blog',
  ],
};

// ─── Navbar ──────────────────────────────────────────────────────────────────
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header
      role="banner"
      className={`sticky top-0 z-50 transition-all duration-200 ${
        scrolled
          ? 'bg-[var(--surface)]/95 backdrop-blur-sm border-b border-[var(--border)]'
          : 'bg-[var(--background)] border-b border-[var(--border)]'
      }`}
    >
      <div className="max-w-layout mx-auto px-6 lg:px-10 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" aria-label="Ziref home" className="flex items-center gap-0">
          <ZirefLogo size={26} showText={true} textSize="text-[15px]" />
        </Link>

        {/* Center nav — desktop */}
        <nav
          aria-label="Main navigation"
          className="hidden lg:flex items-center gap-1"
        >
          {isAuthenticated ? (
            authenticatedNavLinks.map(({ label, href }) => (
              <Link
                key={label}
                href={href}
                className="px-3.5 py-1.5 text-[13px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 rounded"
              >
                {label}
              </Link>
            ))
          ) : (
            anonymousNavLinks.map(({ label, href }) => (
              <a
                key={label}
                href={href}
                className="px-3.5 py-1.5 text-[13px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 rounded"
              >
                {label}
              </a>
            ))
          )}
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-3">
          <ThemeToggle />

          {isLoading ? (
            <div className="w-20 h-8 rounded-lg bg-[var(--surface-muted)] animate-pulse hidden sm:block" />
          ) : isAuthenticated ? (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-muted)] text-[13px] font-medium text-[var(--text-primary)] transition-colors"
              >
                <div className="w-5 h-5 rounded-full bg-[var(--accent)] text-white flex items-center justify-center text-[10px] font-bold">
                  {user?.name?.slice(0, 1).toUpperCase() || 'U'}
                </div>
                <span className="hidden sm:inline max-w-[120px] truncate">{user?.name || 'Workspace'}</span>
                <ChevronDown className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl py-1 text-xs z-50 animate-fade-in-up">
                  <div className="px-3 py-2 border-b border-[var(--border)]">
                    <div className="font-semibold text-[var(--text-primary)] truncate">{user?.name}</div>
                    <div className="text-[11px] text-[var(--text-tertiary)] truncate">{user?.email}</div>
                  </div>
                  <div className="py-1">
                    <Link
                      href="/dashboard"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)] transition-colors"
                    >
                      <LayoutDashboard className="w-4 h-4 text-[var(--text-tertiary)]" />
                      <span>Workspace Dashboard</span>
                    </Link>
                    <Link
                      href="/dashboard/projects"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)] transition-colors"
                    >
                      <FolderGit2 className="w-4 h-4 text-[var(--text-tertiary)]" />
                      <span>Projects</span>
                    </Link>
                    <Link
                      href="/dashboard/deployments"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)] transition-colors"
                    >
                      <Zap className="w-4 h-4 text-[var(--text-tertiary)]" />
                      <span>Deployments</span>
                    </Link>
                    <Link
                      href="/dashboard/settings"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)] transition-colors"
                    >
                      <Settings className="w-4 h-4 text-[var(--text-tertiary)]" />
                      <span>Settings</span>
                    </Link>
                  </div>
                  <div className="pt-1 border-t border-[var(--border)]">
                    <button
                      onClick={() => {
                        setDropdownOpen(false);
                        logout();
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors text-left"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Sign out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden sm:inline-block text-[13px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors px-2"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-[13px] font-semibold hover:bg-[var(--accent-hover)] transition-colors"
              >
                Get started
              </Link>
            </>
          )}

          {/* Mobile menu toggle */}
          <button
            className="lg:hidden flex flex-col gap-1 w-6 h-5 justify-center"
            aria-expanded={mobileOpen}
            aria-label="Toggle menu"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            <span className={`h-px w-full bg-[var(--text-primary)] transition-all ${mobileOpen ? 'rotate-45 translate-y-[5px]' : ''}`} />
            <span className={`h-px w-full bg-[var(--text-primary)] transition-all ${mobileOpen ? 'opacity-0' : ''}`} />
            <span className={`h-px w-full bg-[var(--text-primary)] transition-all ${mobileOpen ? '-rotate-45 -translate-y-[5px]' : ''}`} />
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="lg:hidden border-t border-[var(--border)] bg-[var(--surface)] px-6 py-4 space-y-1">
          {isAuthenticated ? (
            <>
              {authenticatedNavLinks.map(({ label, href }) => (
                <Link
                  key={label}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className="block px-2 py-2 text-[14px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                >
                  {label}
                </Link>
              ))}
              <div className="pt-3 border-t border-[var(--border)] flex items-center justify-between">
                <span className="text-xs text-[var(--text-secondary)]">{user?.name}</span>
                <button
                  onClick={() => {
                    setMobileOpen(false);
                    logout();
                  }}
                  className="text-xs text-rose-500 font-medium"
                >
                  Sign out
                </button>
              </div>
            </>
          ) : (
            <>
              {anonymousNavLinks.map(({ label, href }) => (
                <a
                  key={label}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className="block px-2 py-2 text-[14px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                >
                  {label}
                </a>
              ))}
              <div className="pt-3 border-t border-[var(--border)] flex items-center gap-3">
                <Link
                  href="/login"
                  className="text-[13px] font-medium text-[var(--text-secondary)]"
                >
                  Log in
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-[13px] font-semibold"
                >
                  Get started
                </Link>
              </div>
            </>
          )}
        </div>
      )}
    </header>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div
      style={{
        backgroundColor: 'var(--background)',
        color: 'var(--text-primary)',
      }}
      className="min-h-screen"
    >
      <Navbar />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="pt-16 pb-20 lg:pt-20 lg:pb-28">
        <div className="max-w-layout mx-auto px-6 lg:px-10">
          {/* Eyebrow */}
          <p className="font-mono text-[12px] text-[var(--text-tertiary)] tracking-wider uppercase mb-5">
            Developer Infrastructure Platform
          </p>

          {/* Headline */}
          <h1
            className="text-[52px] sm:text-[62px] lg:text-[68px] font-bold text-[var(--text-primary)] mb-6 max-w-[760px]"
            style={{ letterSpacing: '-0.04em', lineHeight: 1.0 }}
          >
            Ship your project.
            <br />
            Not your{' '}
            <span style={{ color: 'var(--accent)' }}>infrastructure.</span>
          </h1>

          {/* Subtitle */}
          <p
            className="text-[17px] text-[var(--text-secondary)] mb-8 max-w-[500px]"
            style={{ lineHeight: 1.65 }}
          >
            Upload your project. Ziref detects the stack, builds it in an isolated environment, deploys it instantly, and prepares it for mobile.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap items-center gap-3 mb-8">
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--accent)] text-white text-[14px] font-semibold hover:bg-[var(--accent-hover)] transition-colors shadow-sm"
              >
                Go to Dashboard
                <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <Link
                href="/register"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--accent)] text-white text-[14px] font-semibold hover:bg-[var(--accent-hover)] transition-colors shadow-sm"
              >
                Start building
                <ArrowRight className="w-4 h-4" />
              </Link>
            )}
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[var(--border-strong)] text-[14px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent)] transition-colors"
            >
              See how it works
            </a>
          </div>

          {/* Trust line */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 font-mono text-[12px] text-[var(--text-tertiary)] mb-14">
            <span>Deterministic detection</span>
            <span>·</span>
            <span>Sandboxed builds</span>
            <span>·</span>
            <span>Zero-downtime deploys</span>
            <span>·</span>
            <span>Android APK packaging</span>
          </div>

          {/* Hero visual */}
          <HeroBrowserMockup />
        </div>
      </section>

      {/* ── Pipeline ─────────────────────────────────────────────────────── */}
      <ArchitecturePipeline />

      {/* ── Framework Matrix ─────────────────────────────────────────────── */}
      <FrameworkMatrix />

      {/* ── Appify ───────────────────────────────────────────────────────── */}
      <AppifyMobileSimulator />

      {/* ── Security ─────────────────────────────────────────────────────── */}
      <SecuritySection />

      {/* ── FAQ ──────────────────────────────────────────────────────────── */}
      <LandingFaq />

      {/* ── Final CTA ────────────────────────────────────────────────────── */}
      <section
        className="py-24 border-t border-[var(--border)] bg-[var(--surface-muted)]"
      >
        <div className="max-w-layout mx-auto px-6 lg:px-10">
          <div className="max-w-[600px]">
            <p className="font-mono text-[12px] text-[var(--text-tertiary)] tracking-wider uppercase mb-5">
              Production Infrastructure
            </p>
            <h2
              className="text-[46px] lg:text-[56px] font-bold text-[var(--text-primary)] mb-5"
              style={{ letterSpacing: '-0.04em', lineHeight: 1.0 }}
            >
              Your code is ready.
              <br />Ship it.
            </h2>
            <p className="text-[16px] text-[var(--text-secondary)] mb-10" style={{ lineHeight: 1.65 }}>
              Build once. Deploy anywhere. Zero infrastructure to manage.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href={isAuthenticated ? "/dashboard" : "/register"}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--accent)] text-white text-[14px] font-semibold hover:bg-[var(--accent-hover)] transition-colors"
              >
                {isAuthenticated ? "Enter Dashboard" : "Start with Ziref"}
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="#faq"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[var(--border-strong)] text-[14px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
              >
                Read architecture guide
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer
        className="border-t border-[var(--border)] py-14 bg-[var(--surface)]"
      >
        <div className="max-w-layout mx-auto px-6 lg:px-10">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-8 mb-12">
            {/* Brand column */}
            <div className="col-span-2 sm:col-span-3 lg:col-span-1">
              <Link href="/" className="inline-flex mb-5">
                <ZirefLogo size={24} showText={true} textSize="text-[14px]" />
              </Link>
              <p className="text-[13px] text-[var(--text-secondary)] leading-relaxed max-w-[200px]">
                Developer infrastructure. From code to product.
              </p>
              <div className="flex items-center gap-1.5 mt-4 font-mono text-[11px] text-emerald-600 dark:text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                All systems operational
              </div>
            </div>

            {/* Link columns */}
            {Object.entries(footerLinks).map(([group, links]) => (
              <div key={group}>
                <div className="text-[12px] font-semibold text-[var(--text-primary)] mb-4">{group}</div>
                <ul className="space-y-2.5">
                  {links.map((link) => (
                    <li key={link}>
                      <a
                        href="#"
                        className="text-[13px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                      >
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Bottom bar */}
          <div className="pt-8 border-t border-[var(--border)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <span className="text-[12px] text-[var(--text-tertiary)]">
              © 2026 Ziref. All rights reserved.
            </span>
            <div className="flex items-center gap-5 text-[12px] text-[var(--text-tertiary)]">
              {['Privacy', 'Terms', 'Security', 'Status'].map((item) => (
                <a key={item} href="#" className="hover:text-[var(--text-secondary)] transition-colors">
                  {item}
                </a>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
