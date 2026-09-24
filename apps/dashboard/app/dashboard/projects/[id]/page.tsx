'use client';

import React, { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Project, Deployment, EnvVar, MobileApp, MobileBuild, Build } from '@ziref/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TerminalViewer } from '@/components/ui/TerminalViewer';
import {
  ExternalLink,
  Terminal,
  Layers,
  KeyRound,
  Smartphone,
  Settings,
  RefreshCw,
  RotateCcw,
  Plus,
  Trash2,
  Download,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Globe,
  Activity,
  Monitor,
  Tablet,
  BarChart3,
  Webhook,
  Play,
  XCircle,
  AlertTriangle,
  Send,
  Copy,
  Check
} from 'lucide-react';

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<'overview' | 'deployments' | 'logs' | 'analytics' | 'runtime' | 'env' | 'domains' | 'webhooks' | 'appify' | 'settings'>('overview');
  const [project, setProject] = useState<Project | null>(null);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [envVars, setEnvVars] = useState<EnvVar[]>([]);
  const [customDomains, setCustomDomains] = useState<any[]>([]);
  const [runtimeLogs, setRuntimeLogs] = useState<any[]>([]);
  const [mobileApps, setMobileApps] = useState<MobileApp[]>([]);
  const [latestBuild, setLatestBuild] = useState<Build | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Diagnostics & Rebuild State
  const [diagnosis, setDiagnosis] = useState<any | null>(null);
  const [isRebuilding, setIsRebuilding] = useState(false);

  // Analytics State
  const [analytics, setAnalytics] = useState<any | null>(null);

  // Webhooks State
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [newWebhookUrl, setNewWebhookUrl] = useState('');
  const [isAddingWebhook, setIsAddingWebhook] = useState(false);

  // Web Preview State
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');
  const [previewKey, setPreviewKey] = useState(1);

  // New Env Var State
  const [newEnvKey, setNewEnvKey] = useState('');
  const [newEnvVal, setNewEnvVal] = useState('');
  const [newEnvSecret, setNewEnvSecret] = useState(true);

  // Custom Domain State
  const [newDomainInput, setNewDomainInput] = useState('');
  const [isAddingDomain, setIsAddingDomain] = useState(false);

  // Appify State
  const [appName, setAppName] = useState('');
  const [packageId, setPackageId] = useState('com.ziref.app');
  const [appTheme, setAppTheme] = useState('system');
  const [appOrientation, setAppOrientation] = useState('portrait');
  const [appPermissions, setAppPermissions] = useState<string[]>([]);
  const [isBuildingApp, setIsBuildingApp] = useState(false);
  const [mobileBuild, setMobileBuild] = useState<MobileBuild | null>(null);
  const [mobileLogs, setMobileLogs] = useState<any[]>([]);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  const fetchProjectData = async () => {
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);
      if (!appName) {
        setAppName(proj.name);
        setPackageId(`com.ziref.${proj.slug.replace(/[^a-z0-9]/gi, '').toLowerCase() || 'app'}`);
      }

      const [deps, envs, apps, doms, whs] = await Promise.all([
        api.getDeployments(projectId),
        api.getEnvVars(projectId),
        api.getMobileApps(projectId),
        api.getDomains(projectId).catch(() => []),
        api.getWebhooks(projectId).catch(() => []),
      ]);

      setDeployments(deps);
      setEnvVars(envs);
      setMobileApps(apps);
      setCustomDomains(doms);
      setWebhooks(whs);

      if (deps.length > 0 && deps[0].build_id) {
        const b = await api.getBuild(deps[0].build_id);
        setLatestBuild(b);
        if (b.status === 'FAILED') {
          api.getBuildDiagnosis(b.id).then(setDiagnosis).catch(() => {});
        } else {
          setDiagnosis(null);
        }
      }

      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch project');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjectData();
    const interval = setInterval(fetchProjectData, 5000);
    return () => clearInterval(interval);
  }, [projectId]);

  // Handle SSE streaming for build logs
  useEffect(() => {
    if (activeTab === 'logs' && latestBuild?.id) {
      setIsStreaming(true);
      const unsubscribe = api.streamBuildLogs(
        latestBuild.id,
        (evt) => {
          setLogs((prev) => [...prev, evt]);
        },
        () => {
          setIsStreaming(false);
        }
      );
      return () => unsubscribe();
    }
  }, [activeTab, latestBuild?.id]);

  // Handle Analytics loading
  useEffect(() => {
    if (activeTab === 'analytics') {
      api.getProjectAnalytics(projectId).then(setAnalytics).catch(() => {});
    }
  }, [activeTab, projectId]);

  // Handle SSE streaming for runtime HTTP traffic logs
  useEffect(() => {
    if (activeTab === 'runtime') {
      api.getRuntimeLogs(projectId).then(setRuntimeLogs).catch(() => {});
      const unsubscribe = api.streamRuntimeLogs(projectId, (evt) => {
        setRuntimeLogs((prev) => [evt, ...prev.slice(0, 99)]);
      });
      return () => unsubscribe();
    }
  }, [activeTab, projectId]);

  const handleRedeploy = async () => {
    setIsRebuilding(true);
    try {
      await api.redeployProject(projectId);
      setActiveTab('logs');
      fetchProjectData();
    } catch (err: any) {
      alert(err.message || 'Redeploy failed');
    } finally {
      setIsRebuilding(false);
    }
  };

  const handleRollback = async (deploymentId: string) => {
    if (!confirm('Rollback project traffic to this deployment?')) return;
    try {
      await api.rollback(projectId, deploymentId);
      fetchProjectData();
    } catch (err: any) {
      alert(err.message || 'Rollback failed');
    }
  };

  const handleAddEnv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEnvKey.trim() || !newEnvVal.trim()) return;
    try {
      await api.createEnvVar(projectId, newEnvKey.trim(), newEnvVal.trim(), newEnvSecret);
      setNewEnvKey('');
      setNewEnvVal('');
      const updated = await api.getEnvVars(projectId);
      setEnvVars(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to add environment variable');
    }
  };

  const handleDeleteEnv = async (key: string) => {
    try {
      await api.deleteEnvVar(projectId, key);
      const updated = await api.getEnvVars(projectId);
      setEnvVars(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to delete');
    }
  };

  const handleAddDomain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDomainInput.trim()) return;
    setIsAddingDomain(true);
    try {
      await api.addDomain(projectId, newDomainInput.trim());
      setNewDomainInput('');
      const doms = await api.getDomains(projectId);
      setCustomDomains(doms);
    } catch (err: any) {
      alert(err.message || 'Failed to add domain');
    } finally {
      setIsAddingDomain(false);
    }
  };

  const handleVerifyDomain = async (domainId: string) => {
    try {
      await api.verifyDomain(projectId, domainId);
      const doms = await api.getDomains(projectId);
      setCustomDomains(doms);
    } catch (err: any) {
      alert(err.message || 'Verification failed');
    }
  };

  const handleDeleteDomain = async (domainId: string) => {
    try {
      await api.deleteDomain(projectId, domainId);
      const doms = await api.getDomains(projectId);
      setCustomDomains(doms);
    } catch (err: any) {
      alert(err.message || 'Failed to delete domain');
    }
  };

  const handleAddWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWebhookUrl.trim()) return;
    setIsAddingWebhook(true);
    try {
      await api.createWebhook(projectId, newWebhookUrl.trim());
      setNewWebhookUrl('');
      const whs = await api.getWebhooks(projectId);
      setWebhooks(whs);
    } catch (err: any) {
      alert(err.message || 'Failed to add webhook');
    } finally {
      setIsAddingWebhook(false);
    }
  };

  const handleDeleteWebhook = async (webhookId: string) => {
    try {
      await api.deleteWebhook(projectId, webhookId);
      const whs = await api.getWebhooks(projectId);
      setWebhooks(whs);
    } catch (err: any) {
      alert(err.message || 'Failed to delete webhook');
    }
  };

  const handleTestWebhook = async (webhookId: string) => {
    try {
      await api.testWebhook(projectId, webhookId);
      alert('Test webhook ping sent successfully!');
    } catch (err: any) {
      alert(err.message || 'Failed to test webhook');
    }
  };

  const handleCreateAndBuildApp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsBuildingApp(true);
    setError(null);
    try {
      const app = await api.createMobileApp(projectId, {
        app_name: appName,
        package_id: packageId,
        theme: appTheme,
        orientation: appOrientation,
      });

      const build = await api.triggerMobileBuild(app.id);
      setMobileBuild(build);

      api.streamMobileLogs(
        build.id,
        (evt) => {
          setMobileLogs((prev) => [...prev, evt]);
        },
        () => {
          setIsBuildingApp(false);
          api.getMobileBuild(build.id).then(setMobileBuild);
        }
      );
    } catch (err: any) {
      setError(err.message || 'Mobile build failed');
      setIsBuildingApp(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  if (loading || !project) {
    return (
      <div className="p-12 text-center text-zinc-500 font-mono text-xs">
        Loading project details...
      </div>
    );
  }

  const previewUrl = project.active_url ? (
    project.active_url.includes('localhost:8080')
      ? `http://localhost:8080/sites/${project.slug}/`
      : project.active_url
  ) : null;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Globe },
    { id: 'deployments', label: 'Deployments', icon: Layers },
    { id: 'logs', label: 'Build Logs', icon: Terminal },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'runtime', label: 'Runtime Logs', icon: Activity },
    { id: 'env', label: 'Environment', icon: KeyRound },
    { id: 'domains', label: 'Domains', icon: Globe },
    { id: 'webhooks', label: 'Webhooks', icon: Webhook },
    { id: 'appify', label: 'Appify (Android)', icon: Smartphone },
    { id: 'settings', label: 'Settings', icon: Settings },
  ] as const;

  return (
    <div className="space-y-6">
      {/* Project Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white">{project.name}</h1>
            <StatusBadge status={project.status} />
          </div>
          <div className="flex items-center gap-3 text-xs text-zinc-400 mt-1 font-mono">
            <span>slug: {project.slug}</span>
            <span>•</span>
            <span>framework: {project.framework || 'pending'}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRedeploy}
            disabled={isRebuilding}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-300 hover:text-white hover:border-zinc-500 text-xs font-semibold transition-colors disabled:opacity-50"
            title="Rebuild latest upload"
          >
            {isRebuilding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            <span>Redeploy</span>
          </button>

          {previewUrl && (
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black hover:bg-sky-400 text-xs font-semibold transition-colors shadow-md"
            >
              Visit Live Site <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-zinc-800 overflow-x-auto pb-px">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                active
                  ? 'border-sky-500 text-white'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
              {tab.id === 'runtime' && runtimeLogs.length > 0 && (
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              )}
            </button>
          );
        })}
      </div>

      {/* AI Build Diagnosis Alert Banner (Shown if latest build failed) */}
      {diagnosis && (
        <div className="p-5 rounded-xl border border-amber-900/60 bg-amber-950/20 text-xs space-y-2">
          <div className="flex items-center gap-2 text-amber-400 font-bold">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>AI Build Failure Diagnosis: {diagnosis.summary}</span>
          </div>
          <p className="text-zinc-300">{diagnosis.root_cause}</p>
          <div className="p-3 bg-black/50 border border-zinc-800 rounded-lg text-emerald-400 font-mono text-[11px]">
            <span className="text-zinc-500 block mb-1">Recommended Fix:</span>
            {diagnosis.actionable_fix}
          </div>
        </div>
      )}

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Production URL</span>
              <div className="mt-2">
                {previewUrl ? (
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-mono text-sky-400 hover:underline break-all"
                  >
                    {previewUrl}
                  </a>
                ) : (
                  <span className="text-xs text-zinc-500 font-mono">Build pending...</span>
                )}
              </div>
            </div>

            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Framework Configuration</span>
              <div className="mt-2 text-xs text-white font-mono">
                {project.framework || 'Detecting...'} ({project.language || 'js'})
              </div>
              <div className="text-[11px] text-zinc-500 mt-1 font-mono">{project.build_command || 'npm run build'}</div>
            </div>

            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Total Deployments</span>
              <div className="mt-2 text-2xl font-bold text-white">{deployments.length}</div>
              <div className="text-[11px] text-zinc-500 mt-1">Immutable atomic versions</div>
            </div>
          </div>

          {/* Interactive In-Dashboard Web Preview */}
          {previewUrl && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden shadow-2xl">
              <div className="px-4 py-2.5 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5 mr-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
                  </div>
                  <span className="font-semibold text-zinc-300">Live Web Preview</span>
                </div>

                <div className="flex items-center gap-1 bg-zinc-950 p-1 rounded border border-zinc-800">
                  <button
                    onClick={() => setPreviewDevice('desktop')}
                    className={`p-1 rounded ${previewDevice === 'desktop' ? 'bg-zinc-800 text-sky-400' : 'text-zinc-500 hover:text-zinc-300'}`}
                    title="Desktop Preview"
                  >
                    <Monitor className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setPreviewDevice('tablet')}
                    className={`p-1 rounded ${previewDevice === 'tablet' ? 'bg-zinc-800 text-sky-400' : 'text-zinc-500 hover:text-zinc-300'}`}
                    title="Tablet Preview"
                  >
                    <Tablet className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setPreviewDevice('mobile')}
                    className={`p-1 rounded ${previewDevice === 'mobile' ? 'bg-zinc-800 text-sky-400' : 'text-zinc-500 hover:text-zinc-300'}`}
                    title="Mobile Preview"
                  >
                    <Smartphone className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPreviewKey(k => k + 1)}
                    className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white"
                    title="Reload Preview"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-sky-400"
                    title="Open In New Window"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>

              <div className="p-4 bg-zinc-900/30 flex justify-center min-h-[460px]">
                <iframe
                  key={previewKey}
                  src={previewUrl}
                  title="App Live Preview"
                  className={`border border-zinc-800 bg-black rounded-lg shadow-2xl transition-all h-[440px] ${
                    previewDevice === 'desktop' ? 'w-full' :
                    previewDevice === 'tablet' ? 'w-[768px]' : 'w-[375px]'
                  }`}
                />
              </div>
            </div>
          )}

          {/* Quick Terminal Preview */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-zinc-400">Latest Build Terminal Output</span>
              <button
                onClick={() => setActiveTab('logs')}
                className="text-xs text-sky-400 hover:underline"
              >
                Expand Logs
              </button>
            </div>
            <TerminalViewer logs={logs.slice(-25)} title="Latest Build Output" isStreaming={isStreaming} />
          </div>
        </div>
      )}

      {/* Tab 2: Deployments */}
      {activeTab === 'deployments' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400">Deployment history with atomic rollbacks</span>
            <button
              onClick={handleRedeploy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500 text-black text-xs font-semibold hover:bg-sky-400"
            >
              <Play className="w-3.5 h-3.5" /> Trigger Redeploy
            </button>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-5 py-3">Deployment ID</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Public Hostname</th>
                  <th className="px-5 py-3">Deployed At</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 font-mono">
                {deployments.map((d) => {
                  const isCurrent = d.id === project.active_deployment_id;
                  return (
                    <tr key={d.id} className="hover:bg-zinc-900/30">
                      <td className="px-5 py-3.5">
                        <span className="text-zinc-300 font-medium">{d.id.slice(-8)}</span>
                        {isCurrent && (
                          <span className="ml-2 px-1.5 py-0.5 rounded bg-sky-950 text-sky-400 text-[10px] font-sans font-semibold border border-sky-800">
                            ACTIVE
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3.5">
                        <StatusBadge status={d.status} />
                      </td>
                      <td className="px-5 py-3.5">
                        <a href={d.url} target="_blank" rel="noopener noreferrer" className="text-sky-400 hover:underline">
                          {d.subdomain}
                        </a>
                      </td>
                      <td className="px-5 py-3.5 text-zinc-500">
                        {d.completed_at ? new Date(d.completed_at).toLocaleString() : 'in progress'}
                      </td>
                      <td className="px-5 py-3.5 text-right font-sans">
                        {!isCurrent && d.status === 'READY' && (
                          <button
                            onClick={() => handleRollback(d.id)}
                            className="flex items-center gap-1 ml-auto px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white text-xs hover:border-zinc-700 transition-colors"
                          >
                            <RotateCcw className="w-3 h-3" /> Rollback
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Build Logs */}
      {activeTab === 'logs' && (
        <div className="space-y-4">
          <TerminalViewer logs={logs} title={`Build Terminal [ID: ${latestBuild?.id || 'live'}]`} isStreaming={isStreaming} />
        </div>
      )}

      {/* Tab 4: Traffic & Performance Analytics */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Total Requests</span>
              <div className="mt-2 text-2xl font-bold text-white">{analytics?.total_requests || 0}</div>
              <span className="text-[11px] text-zinc-500">Recorded hits</span>
            </div>

            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Avg Latency</span>
              <div className="mt-2 text-2xl font-bold text-sky-400">{analytics?.avg_latency_ms || 0}ms</div>
              <span className="text-[11px] text-zinc-500">P95: {analytics?.p95_latency_ms || 0}ms</span>
            </div>

            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Unique Visitors</span>
              <div className="mt-2 text-2xl font-bold text-emerald-400">{analytics?.unique_visitors || 0}</div>
              <span className="text-[11px] text-zinc-500">Unique client IPs</span>
            </div>

            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Success Rate</span>
              <div className="mt-2 text-2xl font-bold text-white">
                {analytics?.total_requests ? Math.round((analytics.status_codes.status_2xx / analytics.total_requests) * 100) : 100}%
              </div>
              <span className="text-[11px] text-zinc-500">2xx HTTP responses</span>
            </div>
          </div>

          {/* Top Endpoints Table */}
          <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950 space-y-3">
            <h3 className="text-xs font-semibold text-white">Top Requested Paths</h3>
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-4 py-2">Path</th>
                  <th className="px-4 py-2">Requests</th>
                  <th className="px-4 py-2 text-right">Avg Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {analytics?.top_paths?.length ? (
                  analytics.top_paths.map((p: any, idx: number) => (
                    <tr key={idx} className="hover:bg-zinc-900/30">
                      <td className="px-4 py-2 text-white">{p.path}</td>
                      <td className="px-4 py-2 text-zinc-400">{p.count}</td>
                      <td className="px-4 py-2 text-right text-sky-400">{p.avg_latency_ms}ms</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-center text-zinc-500 font-sans">
                      No traffic data recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 5: Runtime Traffic Logs */}
      {activeTab === 'runtime' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-950 flex items-center justify-between">
            <div>
              <h3 className="text-xs font-semibold text-white">Live HTTP Access Traffic</h3>
              <p className="text-[11px] text-zinc-400">Real-time incoming requests to your deployed application</p>
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              <span>Live Listening</span>
            </div>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden font-mono text-xs">
            <table className="w-full text-left">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-4 py-2.5">Time</th>
                  <th className="px-4 py-2.5">Method</th>
                  <th className="px-4 py-2.5">Path</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Latency</th>
                  <th className="px-4 py-2.5">Client IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {runtimeLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-zinc-500 font-sans">
                      No HTTP traffic recorded yet. Visit your live site to trigger requests.
                    </td>
                  </tr>
                ) : (
                  runtimeLogs.map((req, idx) => (
                    <tr key={idx} className="hover:bg-zinc-900/40">
                      <td className="px-4 py-2.5 text-zinc-500 text-[11px]">
                        {req.timestamp ? req.timestamp.slice(11, 19) : '-'}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          req.method === 'GET' ? 'bg-sky-950 text-sky-400 border border-sky-800' :
                          req.method === 'POST' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                          'bg-zinc-800 text-zinc-300'
                        }`}>
                          {req.method}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-white font-semibold">{req.path}</td>
                      <td className="px-4 py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] ${
                          req.status_code >= 200 && req.status_code < 300 ? 'text-emerald-400' :
                          req.status_code >= 400 ? 'text-rose-400' : 'text-zinc-400'
                        }`}>
                          {req.status_code}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-zinc-400">{req.duration_ms}ms</td>
                      <td className="px-4 py-2.5 text-zinc-500 text-[11px]">{req.client_ip}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 6: Environment Variables */}
      {activeTab === 'env' && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
            <h3 className="text-sm font-semibold text-white mb-1">Add Environment Variable</h3>
            <p className="text-xs text-zinc-400 mb-4">Injected securely into the isolated sandbox during build time</p>
            <form onSubmit={handleAddEnv} className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={newEnvKey}
                onChange={(e) => setNewEnvKey(e.target.value)}
                placeholder="VARIABLE_NAME"
                className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 font-mono uppercase focus:outline-none focus:border-sky-500 sm:w-1/3"
              />
              <input
                type="text"
                value={newEnvVal}
                onChange={(e) => setNewEnvVal(e.target.value)}
                placeholder="Value..."
                className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 font-mono focus:outline-none focus:border-sky-500 flex-1"
              />
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors flex items-center justify-center gap-1.5"
              >
                <Plus className="w-4 h-4" /> Save
              </button>
            </form>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-5 py-3">Key</th>
                  <th className="px-5 py-3">Value</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {envVars.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-6 text-center text-zinc-500 font-sans">
                      No environment variables defined yet.
                    </td>
                  </tr>
                ) : (
                  envVars.map((ev) => (
                    <tr key={ev.id} className="hover:bg-zinc-900/30">
                      <td className="px-5 py-3 font-semibold text-white">{ev.key}</td>
                      <td className="px-5 py-3 text-zinc-400">{ev.value}</td>
                      <td className="px-5 py-3 text-right font-sans">
                        <button
                          onClick={() => handleDeleteEnv(ev.key)}
                          className="text-zinc-500 hover:text-rose-400 transition-colors p-1"
                          title="Delete Variable"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 7: Custom Domains */}
      {activeTab === 'domains' && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
            <h3 className="text-sm font-semibold text-white mb-1">Add Custom Domain</h3>
            <p className="text-xs text-zinc-400 mb-4">Map your domain (e.g. <code>app.mycompany.com</code>) directly to this project</p>
            <form onSubmit={handleAddDomain} className="flex gap-3">
              <input
                type="text"
                required
                value={newDomainInput}
                onChange={(e) => setNewDomainInput(e.target.value)}
                placeholder="app.mycompany.com"
                className="px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 font-mono flex-1 focus:outline-none focus:border-sky-500"
              />
              <button
                type="submit"
                disabled={isAddingDomain}
                className="px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" /> Add Domain
              </button>
            </form>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-5 py-3">Domain</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3">DNS Target</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {customDomains.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-6 text-center text-zinc-500 font-sans">
                      No custom domains configured.
                    </td>
                  </tr>
                ) : (
                  customDomains.map((d) => (
                    <tr key={d.id} className="hover:bg-zinc-900/30">
                      <td className="px-5 py-3 font-semibold text-white">{d.domain}</td>
                      <td className="px-5 py-3 text-zinc-400">CNAME</td>
                      <td className="px-5 py-3 text-sky-400">{d.cname_target}</td>
                      <td className="px-5 py-3 font-sans">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          d.status === 'VERIFIED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                          'bg-amber-950 text-amber-400 border border-amber-800'
                        }`}>
                          {d.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-sans space-x-2">
                        {d.status !== 'VERIFIED' && (
                          <button
                            onClick={() => handleVerifyDomain(d.id)}
                            className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white text-xs"
                          >
                            Verify DNS
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteDomain(d.id)}
                          className="text-zinc-500 hover:text-rose-400 p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 8: Outgoing Webhooks */}
      {activeTab === 'webhooks' && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950">
            <h3 className="text-sm font-semibold text-white mb-1">Add Outgoing Webhook</h3>
            <p className="text-xs text-zinc-400 mb-4">Receive signed HTTP POST notifications on deployment transitions (Slack, Discord, or API)</p>
            <form onSubmit={handleAddWebhook} className="flex gap-3">
              <input
                type="url"
                required
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                placeholder="https://hooks.slack.com/services/... or https://api.mycompany.com/webhook"
                className="px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 font-mono flex-1 focus:outline-none focus:border-sky-500"
              />
              <button
                type="submit"
                disabled={isAddingWebhook}
                className="px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" /> Add Webhook
              </button>
            </form>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-5 py-3">Endpoint URL</th>
                  <th className="px-5 py-3">Events</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {webhooks.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-6 text-center text-zinc-500 font-sans">
                      No webhook endpoints configured.
                    </td>
                  </tr>
                ) : (
                  webhooks.map((wh) => (
                    <tr key={wh.id} className="hover:bg-zinc-900/30">
                      <td className="px-5 py-3 text-white font-medium break-all">{wh.url}</td>
                      <td className="px-5 py-3 text-zinc-400 font-sans">
                        <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px]">
                          {wh.events?.join(', ') || 'All Events'}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-sans space-x-2">
                        <button
                          onClick={() => handleTestWebhook(wh.id)}
                          className="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white text-xs inline-flex items-center gap-1"
                        >
                          <Send className="w-3 h-3" /> Test
                        </button>
                        <button
                          onClick={() => handleDeleteWebhook(wh.id)}
                          className="text-zinc-500 hover:text-rose-400 p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 9: Appify Engine (Android) with Mobile Bezel Simulator */}
      {activeTab === 'appify' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 space-y-6">
            <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-950 shadow-xl">
              <div className="flex items-center gap-2 mb-2">
                <Smartphone className="w-5 h-5 text-purple-400" />
                <h2 className="text-base font-semibold text-white">Generate Android Application</h2>
              </div>
              <p className="text-xs text-zinc-400 mb-6">
                Transform this deployed website into a complete native Android application (APK) with an optimized WebView shell.
              </p>

              <form onSubmit={handleCreateAndBuildApp} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">App Name</label>
                    <input
                      type="text"
                      required
                      value={appName}
                      onChange={(e) => setAppName(e.target.value)}
                      placeholder="My Application"
                      className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">Package Identifier</label>
                    <input
                      type="text"
                      required
                      value={packageId}
                      onChange={(e) => setPackageId(e.target.value)}
                      placeholder="com.example.myapp"
                      className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">Theme</label>
                    <select
                      value={appTheme}
                      onChange={(e) => setAppTheme(e.target.value)}
                      className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white"
                    >
                      <option value="system">System Default</option>
                      <option value="dark">Dark Theme</option>
                      <option value="light">Light Theme</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">Screen Orientation</label>
                    <select
                      value={appOrientation}
                      onChange={(e) => setAppOrientation(e.target.value)}
                      className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white"
                    >
                      <option value="portrait">Portrait</option>
                      <option value="landscape">Landscape</option>
                      <option value="sensor">Sensor Auto</option>
                    </select>
                  </div>
                </div>

                {/* Android Device Permissions */}
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-2">Android Permissions</label>
                  <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400">
                    <label className="flex items-center gap-2 p-2 bg-zinc-900 rounded border border-zinc-800 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={appPermissions.includes('camera')}
                        onChange={(e) => {
                          setAppPermissions(prev => e.target.checked ? [...prev, 'camera'] : prev.filter(x => x !== 'camera'));
                        }}
                        className="rounded bg-zinc-800"
                      />
                      <span>Camera Access</span>
                    </label>

                    <label className="flex items-center gap-2 p-2 bg-zinc-900 rounded border border-zinc-800 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={appPermissions.includes('location')}
                        onChange={(e) => {
                          setAppPermissions(prev => e.target.checked ? [...prev, 'location'] : prev.filter(x => x !== 'location'));
                        }}
                        className="rounded bg-zinc-800"
                      />
                      <span>GPS / Location</span>
                    </label>

                    <label className="flex items-center gap-2 p-2 bg-zinc-900 rounded border border-zinc-800 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={appPermissions.includes('notifications')}
                        onChange={(e) => {
                          setAppPermissions(prev => e.target.checked ? [...prev, 'notifications'] : prev.filter(x => x !== 'notifications'));
                        }}
                        className="rounded bg-zinc-800"
                      />
                      <span>Push Notifications</span>
                    </label>

                    <label className="flex items-center gap-2 p-2 bg-zinc-900 rounded border border-zinc-800 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={appPermissions.includes('audio')}
                        onChange={(e) => {
                          setAppPermissions(prev => e.target.checked ? [...prev, 'audio'] : prev.filter(x => x !== 'audio'));
                        }}
                        className="rounded bg-zinc-800"
                      />
                      <span>Microphone Audio</span>
                    </label>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isBuildingApp}
                  className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg bg-purple-600 text-white font-semibold text-xs hover:bg-purple-500 transition-colors disabled:opacity-50"
                >
                  {isBuildingApp ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Compiling Android App...</span>
                    </>
                  ) : (
                    <>
                      <Smartphone className="w-4 h-4" />
                      <span>Build Android APK</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Mobile Build Artifacts & Status */}
            {mobileBuild && (
              <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-950 space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-zinc-400">Mobile Build Status:</span>
                    <StatusBadge status={mobileBuild.status} />
                  </div>
                </div>

                {mobileBuild.status === 'APP_READY' && (
                  <div className="space-y-4 pt-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <a
                        href={`http://localhost:8000/api/v1/mobile-builds/${mobileBuild.id}/download/apk`}
                        download
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 transition-colors shadow-lg"
                      >
                        <Download className="w-4 h-4" />
                        Download APK (.apk)
                      </a>
                      <a
                        href={`http://localhost:8000/api/v1/mobile-builds/${mobileBuild.id}/download/source`}
                        download
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-200 text-xs font-semibold hover:text-white hover:bg-zinc-800 transition-colors shadow-lg"
                      >
                        <Download className="w-4 h-4" />
                        Download Android Studio Project (.zip)
                      </a>
                    </div>

                    <div className="p-4 bg-zinc-900/60 rounded-xl border border-zinc-800 space-y-3 font-mono text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-400 text-[11px]">Install on Device via ADB:</span>
                        <button
                          onClick={() => copyToClipboard(`adb install app-debug-${mobileBuild.id}.apk`, 'adb')}
                          className="text-zinc-400 hover:text-white flex items-center gap-1 text-[11px]"
                        >
                          {copiedCmd === 'adb' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {copiedCmd === 'adb' ? 'Copied' : 'Copy'}
                        </button>
                      </div>
                      <div className="p-2 bg-black rounded border border-zinc-800 text-sky-400 select-all">
                        adb install app-debug-{mobileBuild.id}.apk
                      </div>
                    </div>
                  </div>
                )}

                <TerminalViewer logs={mobileLogs} title="Android Compilation Pipeline" isStreaming={isBuildingApp} />
              </div>
            )}
          </div>

          {/* Interactive Native Phone Mockup Simulator */}
          <div className="lg:col-span-5 flex flex-col items-center">
            <span className="text-xs text-zinc-400 mb-3 font-medium">Interactive Native Phone Mockup</span>
            <div className="w-[300px] h-[600px] bg-black border-4 border-zinc-700 rounded-[44px] shadow-2xl overflow-hidden relative flex flex-col">
              {/* Dynamic Island / Speaker notch */}
              <div className="w-28 h-5 bg-zinc-900 rounded-full mx-auto mt-2.5 z-20 flex items-center justify-center">
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-950 mr-2"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-sky-950"></span>
              </div>

              {/* Status bar */}
              <div className="px-6 pt-1 flex items-center justify-between text-[10px] text-zinc-400 select-none z-10">
                <span>9:41</span>
                <div className="flex items-center gap-1">
                  <span>5G</span>
                  <span>100%</span>
                </div>
              </div>

              {/* In-Phone WebView Frame */}
              <div className="flex-1 w-full mt-2 bg-zinc-950 overflow-hidden">
                {previewUrl ? (
                  <iframe
                    src={previewUrl}
                    title="Phone Simulator"
                    className="w-full h-full border-none"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center text-zinc-500 text-xs">
                    <Smartphone className="w-8 h-8 mb-2 text-zinc-600" />
                    <span>Deploy application to see live mobile preview</span>
                  </div>
                )}
              </div>

              {/* Home indicator bar */}
              <div className="w-24 h-1 bg-zinc-600 rounded-full mx-auto my-2 shrink-0"></div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 10: Settings */}
      {activeTab === 'settings' && (
        <div className="space-y-6">
          <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-950 space-y-4">
            <h3 className="text-sm font-semibold text-white">General Settings</h3>
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1">Project Name</label>
              <input
                type="text"
                defaultValue={project.name}
                className="w-full max-w-md px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white"
              />
            </div>
          </div>

          <div className="p-6 rounded-xl border border-rose-950/40 bg-zinc-950 space-y-3">
            <h3 className="text-sm font-semibold text-rose-400">Danger Zone</h3>
            <p className="text-xs text-zinc-400">Permanently delete this project, all deployments, artifacts, and logs.</p>
            <button
              onClick={async () => {
                if (confirm(`Permanently delete project '${project.name}'?`)) {
                  await api.deleteProject(projectId);
                  router.push('/dashboard/projects');
                }
              }}
              className="px-4 py-2 rounded-lg bg-rose-600 text-white font-semibold text-xs hover:bg-rose-500 transition-colors"
            >
              Delete Project
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
