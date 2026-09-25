'use client';

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth, ProtectedRoute } from '@/lib/auth';
import { useTheme } from '@/lib/theme';
import { ZirefLogo } from '@/components/ui/ZirefLogo';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { CommandPalette } from '@/components/ui/CommandPalette';
import {
  LayoutDashboard,
  FolderGit2,
  Zap,
  Smartphone,
  Globe,
  Settings,
  PlusCircle,
  LogOut,
  Search,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  Menu,
  X,
  HelpCircle
} from 'lucide-react';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <DashboardShell>{children}</DashboardShell>
    </ProtectedRoute>
  );
}

function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { resolvedTheme } = useTheme();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);

  // Global Ctrl/Cmd + K shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Close account menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(e.target as Node)) {
        setAccountMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Generate breadcrumb items
  const pathParts = pathname.split('/').filter(Boolean);
  // Example: ['dashboard', 'projects', '123']
  const breadcrumbs = [
    { label: 'Ziref', href: '/dashboard' },
  ];

  if (pathParts.length > 1) {
    if (pathParts[1] === 'projects') {
      breadcrumbs.push({ label: 'Projects', href: '/dashboard/projects' });
      if (pathParts[2] && pathParts[2] !== 'new') {
        breadcrumbs.push({ label: 'Project Workspace', href: `/dashboard/projects/${pathParts[2]}` });
      } else if (pathParts[2] === 'new') {
        breadcrumbs.push({ label: 'New Project', href: '/dashboard/projects/new' });
      }
    } else if (pathParts[1] === 'deployments') {
      breadcrumbs.push({ label: 'Deployments', href: '/dashboard/deployments' });
    } else if (pathParts[1] === 'appify') {
      breadcrumbs.push({ label: 'Appify Mobile', href: '/dashboard/appify' });
    } else if (pathParts[1] === 'domains') {
      breadcrumbs.push({ label: 'Custom Domains', href: '/dashboard/domains' });
    } else if (pathParts[1] === 'settings') {
      breadcrumbs.push({ label: 'Settings', href: '/dashboard/settings' });
    }
  } else {
    breadcrumbs.push({ label: 'Overview', href: '/dashboard' });
  }

  const primaryNav = [
    { label: 'Overview', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Projects', href: '/dashboard/projects', icon: FolderGit2 },
    { label: 'Deployments', href: '/dashboard/deployments', icon: Zap },
  ];

  const buildShipNav = [
    { label: 'Appify', href: '/dashboard/appify', icon: Smartphone },
    { label: 'Domains', href: '/dashboard/domains', icon: Globe },
  ];

  const workspaceNav = [
    { label: 'Settings', href: '/dashboard/settings', icon: Settings },
  ];


  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--text-primary)] flex flex-col transition-colors">
      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />

      {/* ─── Top Bar ────────────────────────────────────────────────────────── */}
      <header className="h-14 border-b border-[var(--border)] bg-[var(--surface)] px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40">
        {/* Left: Mobile trigger & Breadcrumbs */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="md:hidden p-1.5 rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            aria-label="Open sidebar"
          >
            <Menu className="w-4 h-4" />
          </button>

          <Link href="/dashboard" className="flex items-center gap-2 mr-2">
            <ZirefLogo size={24} showText={false} />
          </Link>

          {/* Breadcrumb path */}
          <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs font-medium text-[var(--text-secondary)]">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={crumb.href + idx}>
                {idx > 0 && <ChevronRight className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />}
                <Link
                  href={crumb.href}
                  className={`hover:text-[var(--text-primary)] transition-colors truncate max-w-[140px] sm:max-w-none ${
                    idx === breadcrumbs.length - 1 ? 'text-[var(--text-primary)] font-semibold' : ''
                  }`}
                >
                  {crumb.label}
                </Link>
              </React.Fragment>
            ))}
          </nav>
        </div>

        {/* Right: Search, Theme, Help, User */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Command palette button */}
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] hover:border-[var(--border-strong)] text-xs text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Search or jump to...</span>
            <kbd className="ml-2 px-1.5 py-0.5 rounded border border-[var(--border)] bg-[var(--surface)] text-[10px] font-mono">
              ⌘K
            </kbd>
          </button>

          {/* Home Link */}
          <Link
            href="/"
            title="View marketing page"
            className="hidden lg:flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)] transition-colors"
          >
            Home <ExternalLink className="w-3 h-3 text-[var(--text-tertiary)]" />
          </Link>

          <div className="h-4 w-px bg-[var(--border)] hidden sm:block" />

          {/* Theme Toggle */}
          <ThemeToggle />

          {/* Help link */}
          <a
            href="/#faq"
            title="Documentation & Guides"
            className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)] transition-colors hidden sm:inline-flex"
          >
            <HelpCircle className="w-4 h-4" />
          </a>

          {/* User Account Menu */}
          <div className="relative" ref={accountMenuRef}>
            <button
              onClick={() => setAccountMenuOpen(!accountMenuOpen)}
              className="flex items-center gap-2 p-1 pl-1.5 pr-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-muted)] transition-colors"
            >
              <div className="w-6 h-6 rounded-full bg-[var(--accent)] text-white flex items-center justify-center text-[11px] font-bold">
                {user?.name?.slice(0, 1).toUpperCase() || 'U'}
              </div>
              <span className="text-xs font-medium hidden sm:inline max-w-[100px] truncate">
                {user?.name || 'Account'}
              </span>
              <ChevronDown className="w-3 h-3 text-[var(--text-tertiary)]" />
            </button>

            {accountMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl py-1 text-xs z-50 animate-fade-in-up">
                <div className="px-3 py-2.5 border-b border-[var(--border)]">
                  <p className="font-semibold text-[var(--text-primary)] truncate">{user?.name}</p>
                  <p className="text-[11px] text-[var(--text-tertiary)] truncate">{user?.email}</p>
                </div>

                <div className="py-1">
                  <Link
                    href="/dashboard/settings"
                    onClick={() => setAccountMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)]"
                  >
                    <Settings className="w-4 h-4 text-[var(--text-tertiary)]" />
                    <span>Workspace Settings</span>
                  </Link>
                  <Link
                    href="/dashboard/projects/new"
                    onClick={() => setAccountMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)]"
                  >
                    <PlusCircle className="w-4 h-4 text-[var(--text-tertiary)]" />
                    <span>New Project</span>
                  </Link>
                  <a
                    href="/#faq"
                    onClick={() => setAccountMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)]"
                  >
                    <HelpCircle className="w-4 h-4 text-[var(--text-tertiary)]" />
                    <span>Documentation</span>
                  </a>
                </div>

                <div className="pt-1 border-t border-[var(--border)]">
                  <button
                    onClick={() => {
                      setAccountMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 text-left"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ─── Main Workspace & Sidebar ───────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Mobile Sidebar Overlay */}
        {mobileMenuOpen && (
          <div
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          >
            <div
              className="w-64 max-w-[80vw] h-full bg-[var(--surface)] border-r border-[var(--border)] p-4 flex flex-col justify-between"
              onClick={(e) => e.stopPropagation()}
            >
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-[var(--border)] mb-4">
                  <ZirefLogo size={24} showText={true} />
                  <button onClick={() => setMobileMenuOpen(false)} className="p-1 rounded text-[var(--text-tertiary)]">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <SidebarNav
                  pathname={pathname}
                  primaryNav={primaryNav}
                  buildShipNav={buildShipNav}
                  workspaceNav={workspaceNav}
                />
              </div>
            </div>
          </div>
        )}

        {/* Desktop Sidebar */}
        <aside className="w-56 border-r border-[var(--border)] bg-[var(--surface)] p-3 hidden md:flex flex-col shrink-0">
          <div className="space-y-4">
            <SidebarNav
              pathname={pathname}
              primaryNav={primaryNav}
              buildShipNav={buildShipNav}
              workspaceNav={workspaceNav}
            />
          </div>
        </aside>

        {/* Main Workspace Area */}
        <main className="flex-1 p-5 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

interface SidebarNavProps {
  pathname: string;
  primaryNav: { label: string; href: string; icon: React.ComponentType<{ className?: string }> }[];
  buildShipNav: { label: string; href: string; icon: React.ComponentType<{ className?: string }> }[];
  workspaceNav: { label: string; href: string; icon: React.ComponentType<{ className?: string }> }[];
}

function SidebarNav({ pathname, primaryNav, buildShipNav, workspaceNav }: SidebarNavProps) {
  const isItemActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname.startsWith(href);
  };

  return (
    <div className="space-y-4">
      {/* Primary section */}
      <div>
        <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)] px-2.5 mb-1">
          Platform
        </div>
        <div className="space-y-0.5">
          {primaryNav.map((item) => {
            const active = isItemActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  active
                    ? 'bg-[var(--accent)] text-white font-semibold shadow-xs'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)]'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-white' : 'text-[var(--text-tertiary)]'}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Build & Ship section */}
      <div>
        <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)] px-2.5 mb-1">
          Build & Ship
        </div>
        <div className="space-y-0.5">
          {buildShipNav.map((item) => {
            const active = isItemActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  active
                    ? 'bg-[var(--accent)] text-white font-semibold shadow-xs'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)]'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-white' : 'text-[var(--text-tertiary)]'}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Workspace section */}
      <div>
        <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)] px-2.5 mb-1">
          Workspace
        </div>
        <div className="space-y-0.5">
          {workspaceNav.map((item) => {
            const active = isItemActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  active
                    ? 'bg-[var(--accent)] text-white font-semibold shadow-xs'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-muted)]'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-white' : 'text-[var(--text-tertiary)]'}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}


