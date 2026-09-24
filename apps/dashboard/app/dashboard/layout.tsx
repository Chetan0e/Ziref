'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { User } from '@ziref/types';
import {
  LayoutDashboard,
  FolderGit2,
  PlusCircle,
  LogOut,
  User as UserIcon,
  Layers,
  ExternalLink,
  Shield,
} from 'lucide-react';
import { ZirefLogo } from '@/components/ui/ZirefLogo';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMe()
      .then(u => {
        setUser(u);
        setLoading(false);
      })
      .catch(() => {
        // If not logged in, redirect to login
        router.push('/login');
      });
  }, [router]);

  const handleLogout = () => {
    api.logout();
    router.push('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center text-zinc-500 font-mono text-sm">
        Authenticating session...
      </div>
    );
  }

  const navItems = [
    { label: 'Overview', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Projects', href: '/dashboard/projects', icon: FolderGit2 },
    { label: 'New Project', href: '/dashboard/projects/new', icon: PlusCircle },
  ];

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Top Bar */}
      <header className="h-14 border-b border-zinc-800 bg-zinc-950/80 px-6 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="flex items-center gap-2">
            <ZirefLogo size={28} showText={true} textSize="text-base" />
          </Link>
          <span className="text-zinc-600 font-mono text-xs">/</span>
          <span className="text-xs text-zinc-400 font-mono bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
            Developer Workspace
          </span>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="text-xs text-zinc-400 hover:text-white flex items-center gap-1 transition-colors"
          >
            Home <ExternalLink className="w-3 h-3" />
          </Link>
          <div className="h-4 w-px bg-zinc-800" />
          <div className="flex items-center gap-2 text-xs text-zinc-300">
            <div className="w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] font-bold">
              {user?.name?.slice(0, 1) || 'U'}
            </div>
            <span className="font-medium hidden sm:inline">{user?.name}</span>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded hover:bg-zinc-900 text-zinc-400 hover:text-rose-400 transition-colors"
            title="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Layout Container */}
      <div className="flex-1 flex">
        {/* Sidebar */}
        <aside className="w-56 border-r border-zinc-800/80 bg-zinc-950 p-4 hidden md:flex flex-col justify-between shrink-0">
          <div className="space-y-1">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500 px-3 mb-2">
              Platform
            </div>
            {navItems.map((item) => {
              const active = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    active
                      ? 'bg-zinc-800 text-white font-semibold'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-900/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${active ? 'text-sky-400' : 'text-zinc-500'}`} />
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Quick status footer */}
          <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800/60 text-[11px] text-zinc-400">
            <div className="flex items-center gap-1.5 text-emerald-400 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-semibold">Worker Online</span>
            </div>
            <p className="text-[10px] text-zinc-500">Docker Sandbox Active</p>
          </div>
        </aside>

        {/* Content area */}
        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
