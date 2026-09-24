'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Project } from '@ziref/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { PlusCircle, Search, ExternalLink, Trash2, FolderGit2 } from 'lucide-react';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchProjects = () => {
    api.getProjects()
      .then(data => {
        setProjects(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete project '${name}'? This will permanently remove all builds and deployments.`)) {
      return;
    }
    try {
      await api.deleteProject(id);
      fetchProjects();
    } catch (err: any) {
      alert(err.message || 'Failed to delete project');
    }
  };

  const filtered = projects.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.slug.toLowerCase().includes(search.toLowerCase()) ||
    (p.framework && p.framework.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
          <p className="text-xs text-zinc-400 mt-1">Manage and inspect your deployed applications</p>
        </div>
        <Link
          href="/dashboard/projects/new"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors"
        >
          <PlusCircle className="w-4 h-4" />
          New Project
        </Link>
      </div>

      {/* Search Input */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-3" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search projects by name, slug, or framework..."
          className="w-full pl-9 pr-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-sky-500"
        />
      </div>

      {/* Projects Grid / Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-zinc-500 text-xs font-mono">Loading projects...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-zinc-400 text-xs">
            {search ? 'No projects match your search.' : 'No projects created yet.'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-zinc-400 font-medium">
                <tr>
                  <th className="px-5 py-3">Project</th>
                  <th className="px-5 py-3">Framework</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">URL</th>
                  <th className="px-5 py-3">Last Updated</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {filtered.map((p) => (
                  <tr key={p.id} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="px-5 py-3.5">
                      <Link href={`/dashboard/projects/${p.id}`} className="font-semibold text-white hover:text-sky-400">
                        {p.name}
                      </Link>
                      <div className="text-[11px] text-zinc-500 font-mono mt-0.5">{p.slug}</div>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-zinc-400">
                      {p.framework || 'unknown'}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={p.status} />
                    </td>
                    <td className="px-5 py-3.5">
                      {p.active_url ? (
                        <a
                          href={p.active_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sky-400 hover:underline flex items-center gap-1 font-mono text-[11px]"
                        >
                          {p.slug} <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-zinc-500">
                      {p.updated_at ? new Date(p.updated_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-2">
                      <Link
                        href={`/dashboard/projects/${p.id}`}
                        className="inline-block px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white text-xs"
                      >
                        Open
                      </Link>
                      <button
                        onClick={() => handleDelete(p.id, p.name)}
                        className="inline-block px-2 py-1 rounded hover:bg-rose-950/50 text-zinc-500 hover:text-rose-400 transition-colors"
                        title="Delete project"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
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
