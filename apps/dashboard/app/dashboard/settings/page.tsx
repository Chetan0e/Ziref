'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { useTheme } from '@/lib/theme';
import { api, SystemStatus } from '@/lib/api';
import { useToast } from '@/lib/toast';
import {
  User,
  Settings as SettingsIcon,
  Sun,
  Moon,
  Laptop,
  Cpu,
  ShieldCheck,
  Server,
  LogOut,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Key,
  Copy,
  Check,
} from 'lucide-react';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { addToast } = useToast();

  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  const fetchStatus = async () => {
    try {
      setLoadingStatus(true);
      const res = await api.getSystemStatus();
      setSystemStatus(res);
    } catch (_) {
      // Non-fatal if system status is unavailable
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleCopyToken = () => {
    const token = api.getToken();
    if (token) {
      navigator.clipboard.writeText(token);
      setCopiedToken(true);
      addToast({
        title: 'API Token Copied',
        description: 'Bearer token copied to clipboard.',
        type: 'info',
      });
      setTimeout(() => setCopiedToken(false), 2000);
    }
  };

  return (
    <div className="max-w-4xl space-y-8">
      {/* Top Header */}
      <div className="pb-6 border-b border-[var(--border)]">
        <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">Settings</h1>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Manage your account profile, visual appearance, and infrastructure connectivity
        </p>
      </div>

      {/* Account Profile Card */}
      <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-500 flex items-center justify-center font-bold text-lg">
              {user?.name ? user.name.slice(0, 2).toUpperCase() : 'ZR'}
            </div>
            <div>
              <h2 className="text-base font-semibold text-[var(--text-primary)]">
                {user?.name || 'Ziref Engineer'}
              </h2>
              <p className="text-xs text-[var(--text-secondary)] font-mono">{user?.email || '—'}</p>
            </div>
          </div>
          <button
            onClick={() => logout()}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 text-xs font-semibold transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-[var(--border)] text-xs">
          <div>
            <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">User ID</span>
            <span className="font-mono text-[var(--text-primary)] mt-0.5 block truncate">
              {user?.id || '—'}
            </span>
          </div>
          <div>
            <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Role</span>
            <span className="text-[var(--text-primary)] font-semibold mt-0.5 block capitalize">
              {user?.role || 'Administrator'}
            </span>
          </div>
          <div>
            <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Workspace</span>
            <span className="text-[var(--text-primary)] mt-0.5 block">Standard Workspace</span>
          </div>
        </div>
      </div>

      {/* Appearance & Theme Selector */}
      <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Sun className="w-5 h-5 text-amber-500" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Appearance & Theme</h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)]">
          Customize the interface appearance across the platform and marketing pages.
        </p>

        <div className="grid grid-cols-3 gap-3 pt-2">
          {[
            { id: 'system', label: 'System Default', icon: Laptop, desc: 'Sync with OS setting' },
            { id: 'dark', label: 'Dark Mode', icon: Moon, desc: 'Quiet, high-contrast dark' },
            { id: 'light', label: 'Light Mode', icon: Sun, desc: 'Clean, crisp daylight' },
          ].map((item) => {
            const Icon = item.icon;
            const isSelected = theme === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setTheme(item.id as any)}
                className={`flex flex-col items-start p-4 rounded-xl border text-left transition-all ${
                  isSelected
                    ? 'border-sky-500 bg-sky-500/5 ring-1 ring-sky-500/30'
                    : 'border-[var(--border)] bg-[var(--surface-muted)] hover:border-zinc-500'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <Icon
                    className={`w-5 h-5 ${
                      isSelected ? 'text-sky-500' : 'text-[var(--text-secondary)]'
                    }`}
                  />
                  {isSelected && <CheckCircle2 className="w-4 h-4 text-sky-500" />}
                </div>
                <span className="text-xs font-semibold text-[var(--text-primary)] block">
                  {item.label}
                </span>
                <span className="text-[11px] text-[var(--text-muted)] mt-0.5 block">
                  {item.desc}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Infrastructure Diagnostics */}
      <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-sky-500" />
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Infrastructure & Worker Engine
            </h2>
          </div>
          <button
            onClick={fetchStatus}
            disabled={loadingStatus}
            className="p-1.5 rounded hover:bg-[var(--surface-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            title="Refresh status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingStatus ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <p className="text-xs text-[var(--text-secondary)]">
          Real-time health report of background build workers, Docker isolation sandbox, and database connectivity.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 font-mono text-xs">
          <div className="p-3 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)]">
            <span className="text-[var(--text-muted)] text-[10px] block font-sans uppercase">
              Worker Status
            </span>
            <div className="flex items-center gap-1.5 mt-1 font-semibold">
              <span
                className={`w-2 h-2 rounded-full ${
                  systemStatus?.worker?.status === 'online' ? 'bg-emerald-500' : 'bg-amber-500'
                }`}
              />
              <span className="text-[var(--text-primary)] capitalize">
                {systemStatus?.worker?.status || 'Online'}
              </span>
            </div>
          </div>

          <div className="p-3 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)]">
            <span className="text-[var(--text-muted)] text-[10px] block font-sans uppercase">
              Sandbox Isolation
            </span>
            <span className="font-semibold text-sky-500 mt-1 block uppercase">
              {systemStatus?.worker?.sandbox_mode || 'Docker'}
            </span>
          </div>

          <div className="p-3 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)]">
            <span className="text-[var(--text-muted)] text-[10px] block font-sans uppercase">
              Total Projects
            </span>
            <span className="font-semibold text-[var(--text-primary)] mt-1 block">
              {systemStatus?.metrics?.total_projects !== undefined
                ? systemStatus.metrics.total_projects
                : '—'}
            </span>
          </div>

          <div className="p-3 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)]">
            <span className="text-[var(--text-muted)] text-[10px] block font-sans uppercase">
              Active Builds
            </span>
            <span className="font-semibold text-[var(--text-primary)] mt-1 block">
              {systemStatus?.metrics?.active_builds || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Developer API Token */}
      <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Key className="w-5 h-5 text-sky-500" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            Developer Session Token
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)]">
          Your active session bearer token used for authenticating with the Ziref REST API and CLI tool.
        </p>

        <div className="flex items-center gap-2">
          <div className="flex-1 p-2.5 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg font-mono text-xs text-[var(--text-secondary)] truncate select-all">
            {api.getToken() ? `${api.getToken()?.slice(0, 36)}...` : 'Not authenticated'}
          </div>
          <button
            onClick={handleCopyToken}
            className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] text-xs text-[var(--text-primary)] hover:border-zinc-500 transition-colors shrink-0"
          >
            {copiedToken ? (
              <Check className="w-3.5 h-3.5 text-emerald-500" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
            <span>{copiedToken ? 'Copied' : 'Copy Token'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
