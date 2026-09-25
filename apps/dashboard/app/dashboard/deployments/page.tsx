'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Project, Deployment } from '@ziref/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatDate, formatRelativeTime } from '@/lib/date';
import { useToast } from '@/lib/toast';
import {
  Layers,
  Search,
  ExternalLink,
  RefreshCw,
  RotateCcw,
  Filter,
  Globe,
  ArrowRight,
  FolderGit2,
  Clock,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react';

interface EnrichedDeployment extends Deployment {
  projectName?: string;
  projectSlug?: string;
}

export default function DeploymentsPage() {
  const [deployments, setDeployments] = useState<EnrichedDeployment[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { addToast } = useToast();

  const fetchAllDeployments = async () => {
    try {
      setLoading(true);
      const projs = await api.getProjects();
      setProjects(projs);

      const allDeps: EnrichedDeployment[] = [];
      await Promise.all(
        projs.map(async (p) => {
          try {
            const deps = await api.getDeployments(p.id);
            deps.forEach((d) => {
              allDeps.push({
                ...d,
                projectName: p.name,
                projectSlug: p.slug,
              });
            });
          } catch (_) {}
        })
      );

      // Sort newest first
      allDeps.sort((a, b) => {
        const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return timeB - timeA;
      });

      setDeployments(allDeps);
    } catch (err: any) {
      addToast({
        title: 'Failed to load deployments',
        description: err.message || 'Error communicating with backend.',
        type: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllDeployments();
  }, []);

  const handleRollback = async (projectId: string, deploymentId: string) => {
    if (!confirm(`Rollback project to deployment ${deploymentId.slice(-8)}?`)) return;
    setActionLoading(deploymentId);
    try {
      await api.rollback(projectId, deploymentId);
      addToast({
        title: 'Rollback initiated',
        description: `Traffic successfully routed to deployment ${deploymentId.slice(-8)}.`,
        type: 'success',
      });
      fetchAllDeployments();
    } catch (err: any) {
      addToast({
        title: 'Rollback failed',
        description: err.message || 'Could not complete rollback.',
        type: 'error',
      });
    } finally {
      setActionLoading(null);
    }
  };

  const filteredDeployments = useMemo(() => {
    return deployments.filter((d) => {
      const matchesProject =
        selectedProjectId === 'all' || d.project_id === selectedProjectId;

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'ready' && d.status === 'READY') ||
        (statusFilter === 'building' && (d.status === 'QUEUED' || d.status === 'DEPLOYING')) ||
        (statusFilter === 'failed' && d.status === 'FAILED');

      const matchesSearch =
        d.id.toLowerCase().includes(search.toLowerCase()) ||
        (d.projectName && d.projectName.toLowerCase().includes(search.toLowerCase())) ||
        (d.subdomain && d.subdomain.toLowerCase().includes(search.toLowerCase()));

      return matchesProject && matchesStatus && matchesSearch;
    });
  }, [deployments, selectedProjectId, statusFilter, search]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Deployments
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Global timeline of all builds, atomic releases, and instant rollback history
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchAllDeployments}
            disabled={loading}
            className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-zinc-500 transition-colors shadow-sm"
            title="Refresh deployments"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <Link
            href="/dashboard/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors shadow-sm"
          >
            New Deployment
          </Link>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex flex-1 items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by ID, project, or domain..."
              className="w-full pl-9 pr-4 py-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-sky-500 transition-colors"
            />
          </div>

          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="px-3 py-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] focus:outline-none focus:border-sky-500 transition-colors"
          >
            <option value="all">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
          <span className="text-[11px] text-[var(--text-muted)] flex items-center gap-1 px-1">
            <Filter className="w-3 h-3" /> Status:
          </span>
          {[
            { id: 'all', label: 'All' },
            { id: 'ready', label: 'Ready' },
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

      {/* Deployments List Table */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3 text-center">
            <div className="w-8 h-8 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
            <p className="text-xs text-[var(--text-secondary)] font-mono">Loading deployments...</p>
          </div>
        ) : filteredDeployments.length === 0 ? (
          <div className="py-16 px-6 text-center max-w-md mx-auto space-y-4">
            <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-500 flex items-center justify-center mx-auto">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                {search || statusFilter !== 'all' || selectedProjectId !== 'all'
                  ? 'No matching deployments'
                  : 'No deployments found'}
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {search || statusFilter !== 'all' || selectedProjectId !== 'all'
                  ? 'Try changing the filters or search keywords.'
                  : 'Create your first project to start deploying applications with atomic rollbacks.'}
              </p>
            </div>
            {!(search || statusFilter !== 'all' || selectedProjectId !== 'all') && (
              <Link
                href="/dashboard/projects/new"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors shadow-sm"
              >
                Create Project
              </Link>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)] font-medium">
                <tr>
                  <th className="px-5 py-3">Deployment</th>
                  <th className="px-5 py-3">Project</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Domain / URL</th>
                  <th className="px-5 py-3">Created</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {filteredDeployments.map((d) => (
                  <tr key={d.id} className="hover:bg-[var(--surface-hover)] transition-colors">
                    <td className="px-5 py-4 font-mono">
                      <span className="text-[var(--text-primary)] font-semibold">
                        {d.id.slice(-8)}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <Link
                        href={`/dashboard/projects/${d.project_id}`}
                        className="font-medium text-[var(--text-primary)] hover:text-sky-500 transition-colors inline-flex items-center gap-1"
                      >
                        <span>{d.projectName || d.project_id}</span>
                        <ChevronRight className="w-3 h-3 text-[var(--text-muted)]" />
                      </Link>
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={d.status} />
                    </td>
                    <td className="px-5 py-4 font-mono text-[11px]">
                      {d.url ? (
                        <a
                          href={d.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sky-500 hover:underline inline-flex items-center gap-1 max-w-[200px] truncate"
                        >
                          <span>{d.subdomain || d.url}</span>
                          <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      ) : (
                        <span className="text-[var(--text-muted)]">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-[var(--text-secondary)] font-mono text-[11px]">
                      <span title={formatDate(d.created_at)}>
                        {formatRelativeTime(d.created_at)}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right space-x-2 whitespace-nowrap">
                      <Link
                        href={`/dashboard/projects/${d.project_id}?tab=deployments`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-primary)] hover:border-sky-500 text-xs transition-colors"
                      >
                        Inspect
                      </Link>
                      {d.status === 'READY' && (
                        <button
                          onClick={() => handleRollback(d.project_id, d.id)}
                          disabled={actionLoading === d.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs hover:border-zinc-500 transition-colors disabled:opacity-50"
                          title="Rollback traffic to this release"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Rollback</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
