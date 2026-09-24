'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Project } from '@ziref/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { useRouter } from 'next/navigation';
import {
  FolderGit2,
  Zap,
  Smartphone,
  PlusCircle,
  ExternalLink,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Loader2
} from 'lucide-react';

export default function DashboardOverviewPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState(false);

  useEffect(() => {
    api.getProjects()
      .then(data => {
        setProjects(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleInstantDemo = async () => {
    setDemoLoading(true);
    try {
      const res = await api.createDemoProject();
      router.push(`/dashboard/projects/${res.project_id}`);
    } catch (err: any) {
      alert(err.message || 'Failed to initialize demo');
      setDemoLoading(false);
    }
  };

  const deployedCount = projects.filter(p => p.status === 'DEPLOYED' || p.active_deployment_id).length;
  const buildingCount = projects.filter(p => ['BUILDING', 'BUILD_QUEUED', 'DEPLOYING'].includes(p.status)).length;

  return (
    <div className="space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System Overview</h1>
          <p className="text-xs text-zinc-400 mt-1">Real-time status of your projects, builds, and deployed applications</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleInstantDemo}
            disabled={demoLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-zinc-900 border border-zinc-700 hover:border-sky-500 text-sky-400 hover:text-white font-medium text-xs transition-all shadow-md disabled:opacity-50"
          >
            {demoLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-amber-400" />}
            <span>1-Click Demo (React + Vite)</span>
          </button>
          <Link
            href="/dashboard/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors shadow-lg"
          >
            <PlusCircle className="w-4 h-4" />
            New Project
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Projects</span>
            <FolderGit2 className="w-4 h-4 text-zinc-500" />
          </div>
          <div className="text-2xl font-bold text-white">{loading ? '-' : projects.length}</div>
          <div className="text-[11px] text-zinc-500 mt-1">Managed workspaces</div>
        </div>

        <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Active Deployments</span>
            <Zap className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{loading ? '-' : deployedCount}</div>
          <div className="text-[11px] text-zinc-500 mt-1">Serving production traffic</div>
        </div>

        <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Current Builds</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">{loading ? '-' : buildingCount}</div>
          <div className="text-[11px] text-zinc-500 mt-1">Active worker jobs</div>
        </div>

        <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Storage Engine</span>
            <CheckCircle2 className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-sky-400">Local Object</div>
          <div className="text-[11px] text-zinc-500 mt-1">Persistent volume mounted</div>
        </div>
      </div>

      {/* Recent Projects Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden">
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Recent Projects</h2>
            <p className="text-xs text-zinc-400 mt-0.5">Quick access to your deployments and build pipelines</p>
          </div>
          <Link
            href="/dashboard/projects"
            className="text-xs text-sky-400 hover:underline flex items-center gap-1"
          >
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {loading ? (
          <div className="p-8 text-center text-zinc-500 text-xs font-mono">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto mb-3 text-zinc-500">
              <FolderGit2 className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-medium text-white mb-1">No projects deployed yet</h3>
            <p className="text-xs text-zinc-400 max-w-sm mx-auto mb-4">
              Get started by uploading your first project ZIP. Ziref will automatically analyze and build it.
            </p>
            <Link
              href="/dashboard/projects/new"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors"
            >
              <PlusCircle className="w-4 h-4" />
              Create First Project
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-zinc-400 font-medium">
                <tr>
                  <th className="px-5 py-3">Project Name</th>
                  <th className="px-5 py-3">Framework</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Production URL</th>
                  <th className="px-5 py-3">Created</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {projects.slice(0, 5).map((project) => (
                  <tr key={project.id} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-white">
                      <Link href={`/dashboard/projects/${project.id}`} className="hover:text-sky-400">
                        {project.name}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 text-zinc-400 font-mono">
                      {project.framework || 'pending'}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={project.status} />
                    </td>
                    <td className="px-5 py-3.5">
                      {project.active_url ? (
                        <a
                          href={project.active_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sky-400 hover:underline flex items-center gap-1"
                        >
                          {project.slug} <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-zinc-500">
                      {project.created_at ? new Date(project.created_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        href={`/dashboard/projects/${project.id}`}
                        className="text-xs text-zinc-400 hover:text-white px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition-colors"
                      >
                        Manage
                      </Link>
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
