'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Moon, Sun, ArrowRight } from 'lucide-react';
import { ZirefLogo } from '@/components/ui/ZirefLogo';
import { HeroBrowserMockup } from '@/components/landing/HeroBrowserMockup';
import { ArchitecturePipeline } from '@/components/landing/ArchitecturePipeline';
import { FrameworkMatrix } from '@/components/landing/FrameworkMatrix';
import { AppifyMobileSimulator } from '@/components/landing/AppifyMobileSimulator';
import { SecuritySection } from '@/components/landing/SecuritySection';
import { LandingFaq } from '@/components/landing/LandingFaq';

// ─── Nav link type ───────────────────────────────────────────────────────────
const navLinks = [
  { label: 'Product',    href: '#how-it-works' },
  { label: 'Developers', href: '#frameworks'   },
  { label: 'Pricing',    href: '#'             },
  { label: 'Security',   href: '#security'     },
  { label: 'Docs',       href: '#'             },
  { label: 'Resources',  href: '#'             },
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
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Sync isDark with the actual class on mount
  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'));
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('ziref-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('ziref-theme', 'light');
    }
  };

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
          className="hidden lg:flex items-center gap-0"
        >
          {navLinks.map(({ label, href }) => (
            <a
              key={label}
              href={href}
              className="px-3.5 py-1.5 text-[13px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 rounded"
            >
              {label}
            </a>
          ))}
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-3">
          <button
              onClick={toggleTheme}
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              className="hidden sm:flex items-center justify-center w-8 h-8 rounded-full text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)] transition-colors"
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
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
          {navLinks.map(({ label, href }) => (
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
        </div>
      )}
    </header>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function LandingPage() {
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
            From Code to Product
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
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--accent)] text-white text-[14px] font-semibold hover:bg-[var(--accent-hover)] transition-colors"
            >
              Start building
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[var(--border-strong)] text-[14px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent)] transition-colors"
            >
              See how it works
            </a>
          </div>

          {/* Trust line */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 font-mono text-[12px] text-[var(--text-tertiary)] mb-14">
            <span>Automatic detection</span>
            <span>·</span>
            <span>Sandboxed builds</span>
            <span>·</span>
            <span>Zero-downtime deploys</span>
            <span>·</span>
            <span>Android APK in one click</span>
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
        className="py-24 border-t border-[#1E1E20]"
        style={{ backgroundColor: '#0C0C0D' }}
      >
        <div className="max-w-layout mx-auto px-6 lg:px-10">
          <div className="max-w-[600px]">
            <p className="font-mono text-[12px] text-zinc-500 tracking-wider uppercase mb-5">
              Get started
            </p>
            <h2
              className="text-[46px] lg:text-[56px] font-bold text-white mb-5"
              style={{ letterSpacing: '-0.04em', lineHeight: 1.0 }}
            >
              Your code is ready.
              <br />Ship it.
            </h2>
            <p className="text-[16px] text-zinc-400 mb-10" style={{ lineHeight: 1.65 }}>
              Build once. Deploy anywhere. Zero infrastructure to manage.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1D4ED8] text-white text-[14px] font-semibold hover:bg-[#1E40AF] transition-colors"
              >
                Start with Ziref
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="#"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-zinc-700 text-[14px] font-medium text-zinc-300 hover:border-zinc-500 hover:text-white transition-colors"
              >
                Read the docs
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer
        className="border-t border-[#1E1E20] py-14"
        style={{ backgroundColor: '#0C0C0D' }}
      >
        <div className="max-w-layout mx-auto px-6 lg:px-10">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-8 mb-12">
            {/* Brand column */}
            <div className="col-span-2 sm:col-span-3 lg:col-span-1">
              <Link href="/" className="inline-flex mb-5">
                <ZirefLogo size={24} showText={true} textSize="text-[14px]" />
              </Link>
              <p className="text-[13px] text-zinc-500 leading-relaxed max-w-[200px]">
                Developer infrastructure. From code to product.
              </p>
              <div className="flex items-center gap-1.5 mt-4 font-mono text-[11px] text-emerald-500">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                All systems operational
              </div>
            </div>

            {/* Link columns */}
            {Object.entries(footerLinks).map(([group, links]) => (
              <div key={group}>
                <div className="text-[12px] font-semibold text-zinc-300 mb-4">{group}</div>
                <ul className="space-y-2.5">
                  {links.map((link) => (
                    <li key={link}>
                      <a
                        href="#"
                        className="text-[13px] text-zinc-500 hover:text-zinc-200 transition-colors"
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
          <div className="pt-8 border-t border-[#1E1E20] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <span className="text-[12px] text-zinc-600">
              © 2026 Ziref. All rights reserved.
            </span>
            <div className="flex items-center gap-5 text-[12px] text-zinc-600">
              {['Privacy', 'Terms', 'Security', 'Status'].map((item) => (
                <a key={item} href="#" className="hover:text-zinc-400 transition-colors">
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
