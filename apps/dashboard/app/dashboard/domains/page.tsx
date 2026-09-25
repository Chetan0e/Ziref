'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Project } from '@ziref/types';
import { useToast } from '@/lib/toast';
import {
  Globe,
  Plus,
  RefreshCw,
  ExternalLink,
  Trash2,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ShieldCheck,
  ChevronRight,
  ArrowRight,
} from 'lucide-react';

interface EnrichedDomain {
  id: string;
  project_id: string;
  projectName?: string;
  projectSlug?: string;
  domain: string;
  cname_target: string;
  status: string;
  created_at?: string;
}

export default function DomainsPage() {
  const [domains, setDomains] = useState<EnrichedDomain[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [newDomain, setNewDomain] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { addToast } = useToast();

  const fetchDomains = async () => {
    try {
      setLoading(true);
      const projs = await api.getProjects();
      setProjects(projs);
      if (projs.length > 0 && !selectedProjectId) {
        setSelectedProjectId(projs[0].id);
      }

      const allDoms: EnrichedDomain[] = [];
      await Promise.all(
        projs.map(async (p) => {
          try {
            const doms = await api.getDomains(p.id);
            doms.forEach((d: any) => {
              allDoms.push({
                ...d,
                projectName: p.name,
                projectSlug: p.slug,
              });
            });
          } catch (_) {}
        })
      );

      setDomains(allDoms);
    } catch (err: any) {
      addToast({
        title: 'Failed to load domains',
        description: err.message || 'Error communicating with server.',
        type: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDomains();
  }, []);

  const handleAddDomain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || !newDomain.trim()) return;

    setIsAdding(true);
    try {
      await api.addDomain(selectedProjectId, newDomain.trim().toLowerCase());
      addToast({
        title: 'Custom domain added',
        description: `Linked ${newDomain.trim().toLowerCase()} to project.`,
        type: 'success',
      });
      setNewDomain('');
      fetchDomains();
    } catch (err: any) {
      addToast({
        title: 'Failed to add domain',
        description: err.message || 'Domain could not be added.',
        type: 'error',
      });
    } finally {
      setIsAdding(false);
    }
  };

  const handleVerify = async (projectId: string, domainId: string) => {
    setActionLoading(domainId);
    try {
      await api.verifyDomain(projectId, domainId);
      addToast({
        title: 'Verification complete',
        description: 'Domain DNS confirmed and SSL provisioned.',
        type: 'success',
      });
      fetchDomains();
    } catch (err: any) {
      addToast({
        title: 'Verification failed',
        description: err.message || 'DNS CNAME record not pointing yet.',
        type: 'error',
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (projectId: string, domainId: string, domainName: string) => {
    if (!confirm(`Are you sure you want to remove domain ${domainName}?`)) return;
    setActionLoading(domainId);
    try {
      await api.deleteDomain(projectId, domainId);
      addToast({
        title: 'Domain removed',
        description: `${domainName} has been unlinked.`,
        type: 'success',
      });
      setDomains((prev) => prev.filter((d) => d.id !== domainId));
    } catch (err: any) {
      addToast({
        title: 'Failed to delete domain',
        description: err.message || 'Error unlinking domain.',
        type: 'error',
      });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Custom Domains
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Connect custom domains and hostnames with automatic SSL certificate management
          </p>
        </div>
        <button
          onClick={fetchDomains}
          disabled={loading}
          className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-zinc-500 transition-colors shadow-sm self-start sm:self-auto"
          title="Refresh domains"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Add Domain Card */}
      <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Globe className="w-5 h-5 text-sky-500" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            Connect New Domain
          </h2>
        </div>

        {projects.length === 0 ? (
          <p className="text-xs text-[var(--text-secondary)]">
            You need to create a project before adding a custom domain.
          </p>
        ) : (
          <form onSubmit={handleAddDomain} className="grid grid-cols-1 sm:grid-cols-12 gap-3">
            <div className="sm:col-span-4">
              <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                Target Project
              </label>
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="w-full px-3 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] focus:outline-none focus:border-sky-500"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.slug})
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-6">
              <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                Custom Domain (Apex or Subdomain)
              </label>
              <input
                type="text"
                required
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder="app.mycompany.com"
                className="w-full px-3 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] font-mono placeholder-[var(--text-muted)] focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="sm:col-span-2 flex items-end">
              <button
                type="submit"
                disabled={isAdding || !newDomain.trim()}
                className="w-full flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors disabled:opacity-50 shadow-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Add Domain</span>
              </button>
            </div>
          </form>
        )}
      </div>

      {/* DNS Configuration Guide Box */}
      <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <span>DNS Configuration Instructions</span>
        </div>
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
          To verify your domain and route edge traffic, create a <strong>CNAME</strong> record at your DNS provider (Cloudflare, Namecheap, Route53, GoDaddy, etc.) pointing your hostname to the target below:
        </p>
        <div className="p-3 bg-[var(--surface)] border border-[var(--border)] rounded-lg font-mono text-xs text-[var(--text-primary)] flex items-center justify-between">
          <div>
            <span className="text-[var(--text-muted)] mr-4">Type: CNAME</span>
            <span className="text-[var(--text-muted)] mr-4">Target:</span>
            <span className="text-sky-500 font-bold">sites.ziref.dev</span>
          </div>
        </div>
      </div>

      {/* Domains Table */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3 text-center">
            <div className="w-8 h-8 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
            <p className="text-xs text-[var(--text-secondary)] font-mono">Loading custom domains...</p>
          </div>
        ) : domains.length === 0 ? (
          <div className="py-16 px-6 text-center max-w-md mx-auto space-y-4">
            <Globe className="w-12 h-12 text-[var(--text-muted)] mx-auto" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              No custom domains linked yet
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Add your domain above to map your custom brand URL directly to any deployed project.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)]">
                <tr>
                  <th className="px-5 py-3 font-sans font-medium">Domain</th>
                  <th className="px-5 py-3 font-sans font-medium">Project</th>
                  <th className="px-5 py-3 font-sans font-medium">Record</th>
                  <th className="px-5 py-3 font-sans font-medium">Target</th>
                  <th className="px-5 py-3 font-sans font-medium">Status</th>
                  <th className="px-5 py-3 text-right font-sans font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {domains.map((d) => (
                  <tr key={d.id} className="hover:bg-[var(--surface-hover)] transition-colors">
                    <td className="px-5 py-4 font-semibold text-[var(--text-primary)]">
                      <a
                        href={`https://${d.domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-sky-500 hover:underline inline-flex items-center gap-1"
                      >
                        <span>{d.domain}</span>
                        <ExternalLink className="w-3 h-3 text-[var(--text-muted)]" />
                      </a>
                    </td>
                    <td className="px-5 py-4 font-sans">
                      <Link
                        href={`/dashboard/projects/${d.project_id}`}
                        className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:underline"
                      >
                        {d.projectName || d.project_id}
                      </Link>
                    </td>
                    <td className="px-5 py-4 text-[var(--text-secondary)]">CNAME</td>
                    <td className="px-5 py-4 text-sky-500">{d.cname_target || 'sites.ziref.dev'}</td>
                    <td className="px-5 py-4 font-sans">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${
                          d.status === 'VERIFIED'
                            ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                        }`}
                      >
                        {d.status === 'VERIFIED' ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <AlertCircle className="w-3 h-3" />
                        )}
                        <span>{d.status}</span>
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right font-sans space-x-2 whitespace-nowrap">
                      {d.status !== 'VERIFIED' && (
                        <button
                          onClick={() => handleVerify(d.project_id, d.id)}
                          disabled={actionLoading === d.id}
                          className="px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-primary)] hover:border-zinc-500 text-xs transition-colors disabled:opacity-50"
                        >
                          Verify DNS
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(d.project_id, d.id, d.domain)}
                        disabled={actionLoading === d.id}
                        className="text-[var(--text-muted)] hover:text-rose-500 p-1 transition-colors disabled:opacity-50"
                        title="Remove domain"
                      >
                        <Trash2 className="w-4 h-4" />
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
