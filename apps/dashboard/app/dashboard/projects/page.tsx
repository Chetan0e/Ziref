'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { api, ApiError } from '@/lib/api';
import { Project } from '@ziref/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatDate, formatRelativeTime } from '@/lib/date';
import { useToast } from '@/lib/toast';
import {
  PlusCircle,
  Search,
  ExternalLink,
  Trash2,
  FolderGit2,
  Layers,
  Smartphone,
  RefreshCw,
  ArrowRight,
  Filter,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  ChevronRight,
} from 'lucide-react';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const { addToast } = useToast();

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await api.getProjects();
      setProjects(data);
    } catch (err: any) {
      console.error(err);
      addToast({
        title: 'Failed to load projects',
        description: err.message || 'Could not connect to the API server.',
        type: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete project '${name}'? This will permanently remove all associated builds, deployments, and mobile artifacts.`)) {
      return;
    }
    setActionInProgress(id);
    try {
      await api.deleteProject(id);
      addToast({
        title: 'Project deleted',
        description: `Project '${name}' has been successfully removed.`,
        type: 'success',
      });
      setProjects(prev => prev.filter(p => p.id !== id && p.slug !== id));
    } catch (err: any) {
      addToast({
        title: 'Failed to delete project',
        description: err.message || 'An error occurred while deleting the project.',
        type: 'error',
      });
    } finally {
      setActionInProgress(null);
    }
  };

  const filtered = useMemo(() => {
    return projects.filter(p => {
      const matchesSearch =
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.slug.toLowerCase().includes(search.toLowerCase()) ||
        (p.framework && p.framework.toLowerCase().includes(search.toLowerCase()));

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'live' && p.status === 'DEPLOYED') ||
        (statusFilter === 'building' &&
          (p.status === 'BUILDING' ||
            p.status === 'BUILD_QUEUED' ||
            p.status === 'DEPLOYING' ||
            p.status === 'DEPLOY_QUEUED')) ||
        (statusFilter === 'failed' &&
          (p.status === 'BUILD_FAILED' || p.status === 'DEPLOY_FAILED'));

      return matchesSearch && matchesStatus;
    });
  }, [projects, search, statusFilter]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">Projects</h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Manage, deploy, and inspect your web applications and mobile apps
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchProjects}
            disabled={loading}
            className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-zinc-500 transition-colors"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <Link
            href="/dashboard/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            New Project
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects by name, slug, or framework..."
            className="w-full pl-9 pr-4 py-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <span className="text-[11px] text-[var(--text-muted)] flex items-center gap-1 px-1">
            <Filter className="w-3 h-3" /> Filter:
          </span>
          {[
            { id: 'all', label: 'All' },
            { id: 'live', label: 'Live' },
            { id: 'building', label: 'In Progress' },
            { id: 'failed', label: 'Failed' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                statusFilter === tab.id
                  ? 'bg-sky-500/10 text-sky-500 border border-sky-500/30'
                  : 'bg-[var(--surface)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Projects Table / Empty State */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3 text-center">
            <div className="w-8 h-8 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
            <p className="text-xs text-[var(--text-secondary)] font-mono">Loading projects...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 px-6 text-center max-w-md mx-auto space-y-4">
            <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-500 flex items-center justify-center mx-auto">
              <FolderGit2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                {search || statusFilter !== 'all' ? 'No matching projects' : 'No projects deployed yet'}
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {search || statusFilter !== 'all'
                  ? 'Try adjusting your search criteria or resetting the filters.'
                  : 'Upload your source code archive (.zip) or import a Git repository to deploy in seconds.'}
              </p>
            </div>
            {search || statusFilter !== 'all' ? (
              <button
                onClick={() => {
                  setSearch('');
                  setStatusFilter('all');
                }}
                className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--text-primary)] hover:bg-[var(--surface-hover)] transition-colors"
              >
                Clear Filters
              </button>
            ) : (
              <Link
                href="/dashboard/projects/new"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors shadow-sm"
              >
                <PlusCircle className="w-4 h-4" />
                Create First Project
              </Link>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)] font-medium">
                <tr>
                  <th className="px-5 py-3">Project</th>
                  <th className="px-5 py-3">Framework</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Live URL</th>
                  <th className="px-5 py-3">Updated</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {filtered.map((p) => {
                  const previewUrl =
                    (p.active_deployment_id || p.status === 'DEPLOYED' || p.active_url) && p.slug
                      ? p.active_url && !p.active_url.includes('localhost')
                        ? p.active_url
                        : api.getPreviewUrl(p.slug)
                      : null;

                  return (
                    <tr
                      key={p.id}
                      className="hover:bg-[var(--surface-hover)] transition-colors group"
                    >
                      <td className="px-5 py-4">
                        <Link
                          href={`/dashboard/projects/${p.id}`}
                          className="font-semibold text-[var(--text-primary)] hover:text-sky-500 transition-colors flex items-center gap-1.5"
                        >
                          <span>{p.name}</span>
                          <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-sky-500" />
                        </Link>
                        <div className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
                          {p.slug}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-secondary)] capitalize">
                          {p.framework || 'pending'}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <StatusBadge status={p.status} />
                      </td>
                      <td className="px-5 py-4">
                        {previewUrl ? (
                          <a
                            href={previewUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sky-500 hover:underline inline-flex items-center gap-1 font-mono text-[11px] max-w-[200px] truncate"
                          >
                            <span>{p.slug}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-[var(--text-muted)] font-mono">—</span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-[var(--text-secondary)] font-mono text-[11px]">
                        <span title={formatDate(p.updated_at)}>
                          {formatRelativeTime(p.updated_at)}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right space-x-1.5 whitespace-nowrap">
                        <Link
                          href={`/dashboard/projects/${p.id}?tab=appify`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs transition-colors"
                          title="Generate Android App"
                        >
                          <Smartphone className="w-3 h-3 text-purple-400" />
                          <span className="hidden md:inline">Appify</span>
                        </Link>
                        <Link
                          href={`/dashboard/projects/${p.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-primary)] hover:border-sky-500 text-xs font-medium transition-colors"
                        >
                          View
                        </Link>
                        <button
                          onClick={() => handleDelete(p.id, p.name)}
                          disabled={actionInProgress === p.id}
                          className="inline-flex items-center justify-center w-7 h-7 rounded text-[var(--text-muted)] hover:text-rose-500 hover:bg-rose-500/10 transition-colors disabled:opacity-50"
                          title="Delete project"
                        >
                          {actionInProgress === p.id ? (
                            <div className="w-3.5 h-3.5 border-2 border-rose-500 border-t-transparent rounded-full animate-spin" />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
