'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, SystemStatus } from '@/lib/api';
import { Project, Deployment, DashboardMetrics } from '@ziref/types';
import { useAuth } from '@/lib/auth';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatDate, formatRelativeTime } from '@/lib/date';
import {
  FolderGit2,
  Zap,
  Clock,
  PlusCircle,
  ExternalLink,
  ArrowRight,
  Server,
  Activity,
  Layers,
  ArrowUpRight,
  CheckCircle2,
  RefreshCw,
  AlertTriangle
} from 'lucide-react';

interface ActivityItem {
  id: string;
  type: 'project' | 'deployment';
  title: string;
  subtitle: string;
  status: string;
  timestamp: string;
  link: string;
}

export default function DashboardOverviewPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [dashboardMetrics, setDashboardMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboardData = async () => {
    try {
      const [projs, sys, metrics] = await Promise.all([
        api.getProjects(),
        api.getSystemStatus().catch(() => null),
        api.getDashboardMetrics().catch(() => null),
      ]);
      setProjects(projs);
      setSystemStatus(sys);
      setDashboardMetrics(metrics);

      // Fetch deployments across all user projects
      if (projs.length > 0) {
        const depPromises = projs.map(p => api.getDeployments(p.id).catch(() => []));
        const depResults = await Promise.all(depPromises);
        const allDeps = depResults.flat().sort((a, b) => {
          const tA = new Date(a.created_at).getTime() || 0;
          const tB = new Date(b.created_at).getTime() || 0;
          return tB - tA;
        });
        setDeployments(allDeps);
      } else {
        setDeployments([]);
      }
    } catch (err) {
      console.error('Failed to load overview data', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  // Determine time of day greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const deployedCount = projects.filter(p => p.status === 'DEPLOYED' || p.active_deployment_id).length;
  const buildingCount = projects.filter(p => ['BUILDING', 'BUILD_QUEUED', 'DEPLOYING', 'PREPARING'].includes(p.status)).length;
  const firstName = user?.name ? user.name.split(' ')[0] : 'Developer';

  // Build real activity stream
  const activityStream: ActivityItem[] = [];

  deployments.slice(0, 10).forEach((d) => {
    const proj = projects.find(p => p.id === d.project_id);
    activityStream.push({
      id: `dep-${d.id}`,
      type: 'deployment',
      title: d.status === 'READY' ? 'Deployment live' : `Deployment ${d.status.toLowerCase()}`,
      subtitle: proj ? `${proj.name} (production)` : `Deployment #${d.id.slice(-6)}`,
      status: d.status,
      timestamp: d.created_at,
      link: proj ? `/dashboard/projects/${proj.id}` : '/dashboard/deployments',
    });
  });

  projects.slice(0, 4).forEach((p) => {
    activityStream.push({
      id: `proj-${p.id}`,
      type: 'project',
      title: 'Project workspace active',
      subtitle: `${p.name} · ${p.framework || 'detected structure'}`,
      status: p.status,
      timestamp: p.updated_at || p.created_at,
      link: `/dashboard/projects/${p.id}`,
    });
  });

  // Sort activities by timestamp
  activityStream.sort((a, b) => {
    const tA = new Date(a.timestamp).getTime() || 0;
    const tB = new Date(b.timestamp).getTime() || 0;
    return tB - tA;
  });

  return (
    <div className="space-y-6">
      {/* ─── Top Section ──────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[var(--border)]">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            {getGreeting()}, {firstName}.
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Your projects, build pipelines, and production deployments at a glance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] transition-all disabled:opacity-50"
            title="Refresh dashboard metrics"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>

          <Link
            href="/dashboard/projects/new"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[var(--accent)] text-white text-xs font-semibold hover:bg-[var(--accent-hover)] transition-colors shadow-xs"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Project</span>
          </Link>
        </div>
      </div>

      {/* ─── Operational Metrics ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Metric: Projects */}
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-xs">
          <div className="flex items-center justify-between text-[var(--text-secondary)] mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Projects</span>
            <FolderGit2 className="w-4 h-4 text-[var(--text-tertiary)]" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {loading ? '—' : (dashboardMetrics?.projects ?? projects.length)}
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-1">
            {(dashboardMetrics?.projects ?? projects.length) === 0 ? 'No workspaces yet' : (dashboardMetrics?.projects ?? projects.length) === 1 ? '1 active workspace' : `${dashboardMetrics?.projects ?? projects.length} active workspaces`}
          </div>
        </div>

        {/* Metric: Live Deployments */}
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-xs">
          <div className="flex items-center justify-between text-[var(--text-secondary)] mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Live Deployments</span>
            <Zap className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {loading ? '—' : (dashboardMetrics?.live_deployments ?? deployedCount)}
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-1">
            {(dashboardMetrics?.live_deployments ?? deployedCount) > 0 ? `${dashboardMetrics?.live_deployments ?? deployedCount} active production ${(dashboardMetrics?.live_deployments ?? deployedCount) === 1 ? 'site' : 'sites'}` : 'No live deployments'}
          </div>
        </div>

        {/* Metric: Active Builds */}
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-xs">
          <div className="flex items-center justify-between text-[var(--text-secondary)] mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Active Builds</span>
            <Clock className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {loading ? '—' : (dashboardMetrics?.active_builds ?? buildingCount)}
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-1">
            {(dashboardMetrics?.active_builds ?? buildingCount) > 0 ? `${dashboardMetrics?.active_builds ?? buildingCount} build ${(dashboardMetrics?.active_builds ?? buildingCount) === 1 ? 'job' : 'jobs'} in progress` : 'No active jobs in queue'}
          </div>
        </div>

        {/* Metric: Total Deployments */}
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-xs">
          <div className="flex items-center justify-between text-[var(--text-secondary)] mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Total Deployments</span>
            <Layers className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {loading ? '—' : (dashboardMetrics?.total_deployments ?? deployments.length)}
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-1">
            {(dashboardMetrics?.total_deployments ?? deployments.length) > 0 ? `${dashboardMetrics?.total_deployments ?? deployments.length} immutable ${(dashboardMetrics?.total_deployments ?? deployments.length) === 1 ? 'release' : 'releases'}` : 'No releases deployed yet'}
          </div>
        </div>
      </div>

      {/* ─── Two-Column Operations Layout ──────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Recent Projects (2 cols) */}
        <div className="lg:col-span-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-xs">
          <div className="p-4 sm:p-5 border-b border-[var(--border)] flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Managed Projects</h2>
              <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Quick access to deployments and repositories</p>
            </div>
            {projects.length > 0 && (
              <Link
                href="/dashboard/projects"
                className="text-xs font-medium text-[var(--accent)] hover:underline flex items-center gap-1"
              >
                View all ({projects.length}) <ArrowRight className="w-3 h-3" />
              </Link>
            )}
          </div>

          {loading ? (
            <div className="p-12 text-center text-xs font-mono text-[var(--text-tertiary)]">
              Loading workspaces...
            </div>
          ) : projects.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-12 h-12 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] flex items-center justify-center mx-auto mb-3 text-[var(--text-tertiary)]">
                <FolderGit2 className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">No projects yet</h3>
              <p className="text-xs text-[var(--text-secondary)] max-w-sm mx-auto mb-5 leading-relaxed">
                Upload your first project ZIP or import a Git repository to begin automated analysis and deployment.
              </p>
              <Link
                href="/dashboard/projects/new"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-xs font-semibold hover:bg-[var(--accent-hover)] transition-colors"
              >
                <PlusCircle className="w-4 h-4" />
                <span>Upload First Project</span>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)] font-medium">
                  <tr>
                    <th className="px-4 py-2.5">Project</th>
                    <th className="px-4 py-2.5">Framework</th>
                    <th className="px-4 py-2.5">Status</th>
                    <th className="px-4 py-2.5">Production URL</th>
                    <th className="px-4 py-2.5 text-right">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {projects.slice(0, 5).map((project) => (
                    <tr key={project.id} className="hover:bg-[var(--surface-muted)]/50 transition-colors">
                      <td className="px-4 py-3">
                        <Link
                          href={`/dashboard/projects/${project.id}`}
                          className="font-medium text-[var(--text-primary)] hover:text-[var(--accent)] transition-colors"
                        >
                          {project.name}
                        </Link>
                        <div className="text-[10px] text-[var(--text-tertiary)] font-mono">{project.slug}</div>
                      </td>
                      <td className="px-4 py-3 text-[var(--text-secondary)] font-mono text-[11px]">
                        {project.framework || 'auto-detect'}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={project.status} />
                      </td>
                      <td className="px-4 py-3">
                        {project.active_url ? (
                          <a
                            href={project.active_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[var(--accent)] hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
                          >
                            <span>{project.slug}</span>
                            <ArrowUpRight className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-[var(--text-tertiary)]">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-[var(--text-tertiary)] font-mono text-[11px]">
                        {formatRelativeTime(project.updated_at || project.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right: Real Activity Stream (1 col) */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-xs flex flex-col">
          <div className="p-4 sm:p-5 border-b border-[var(--border)] flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Recent Activity</h2>
              <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Live operational events</p>
            </div>
            <Activity className="w-4 h-4 text-[var(--text-tertiary)]" />
          </div>

          <div className="p-4 flex-1">
            {loading ? (
              <div className="p-6 text-center text-xs font-mono text-[var(--text-tertiary)]">
                Loading events...
              </div>
            ) : activityStream.length === 0 ? (
              <div className="p-8 text-center text-xs text-[var(--text-tertiary)]">
                No recent activity recorded yet.
              </div>
            ) : (
              <div className="space-y-4">
                {activityStream.slice(0, 6).map((item) => (
                  <Link
                    key={item.id}
                    href={item.link}
                    className="flex items-start gap-3 p-2 -mx-2 rounded-lg hover:bg-[var(--surface-muted)] transition-colors group"
                  >
                    <div className="mt-1 shrink-0">
                      <span className={`w-2 h-2 rounded-full block ${
                        item.status === 'READY' || item.status === 'DEPLOYED' ? 'bg-emerald-500' :
                        item.status === 'FAILED' || item.status === 'BUILD_FAILED' ? 'bg-rose-500' :
                        item.status === 'BUILDING' || item.status === 'DEPLOYING' ? 'bg-blue-500 animate-pulse' :
                        'bg-zinc-400'
                      }`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-xs font-medium text-[var(--text-primary)] truncate group-hover:text-[var(--accent)] transition-colors">
                          {item.title}
                        </span>
                        <span className="text-[10px] text-[var(--text-tertiary)] shrink-0 font-mono">
                          {formatRelativeTime(item.timestamp)}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--text-secondary)] truncate">
                        {item.subtitle}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
