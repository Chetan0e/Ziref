'use client';

import React, { useEffect, useState, useRef, use, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { api, ApiError } from '@/lib/api';
import { Project, Deployment, EnvVar, MobileApp, MobileBuild, Build } from '@ziref/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TerminalViewer } from '@/components/ui/TerminalViewer';
import { formatDate, formatRelativeTime } from '@/lib/date';
import { useToast } from '@/lib/toast';
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
  Check,
  ArrowLeft,
  ChevronRight,
  Shield,
  Clock,
  Radio,
  UploadCloud,
} from 'lucide-react';

type TabType =
  | 'overview'
  | 'deployments'
  | 'logs'
  | 'analytics'
  | 'runtime'
  | 'env'
  | 'domains'
  | 'webhooks'
  | 'appify'
  | 'settings';

export default function ProjectDetailPageWrapper({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense
      fallback={
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-center">
          <div className="w-8 h-8 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
          <p className="text-xs text-[var(--text-secondary)] font-mono">Loading project...</p>
        </div>
      }
    >
      <ProjectDetailContent params={params} />
    </Suspense>
  );
}

function ProjectDetailContent({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addToast } = useToast();

  const initialTab = (searchParams.get('tab') as TabType) || 'overview';
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);

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
  const [isDeletingProject, setIsDeletingProject] = useState(false);

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
  const [appLogo, setAppLogo] = useState<string | null>(null);
  const [logoFileName, setLogoFileName] = useState<string>('');
  const mobileLogoInputRef = useRef<HTMLInputElement>(null);
  const [isBuildingApp, setIsBuildingApp] = useState(false);
  const [mobileBuild, setMobileBuild] = useState<MobileBuild | null>(null);
  const [mobileLogs, setMobileLogs] = useState<any[]>([]);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  // Sync tab with URL search parameter if changed
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab') as TabType;
    if (tabFromUrl && tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams]);

  const fetchProjectData = async () => {
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);
      if (!appName) {
        setAppName(proj.name);
        setPackageId(`com.ziref.${proj.slug.replace(/[^a-z0-9]/gi, '').toLowerCase() || 'app'}`);
      }

      const targetId = proj.id || projectId;
      const [deps, envs, apps, doms, whs, builds] = await Promise.all([
        api.getDeployments(targetId),
        api.getEnvVars(targetId),
        api.getMobileApps(targetId),
        api.getDomains(targetId).catch(() => []),
        api.getWebhooks(targetId).catch(() => []),
        api.getBuilds(targetId).catch(() => []),
      ]);

      setDeployments(deps);
      setEnvVars(envs);
      setMobileApps(apps);
      setCustomDomains(doms);
      setWebhooks(whs);

      // Resolve the latest build: either newest build from builds API, or from deps[0].build_id
      const b = builds && builds.length > 0
        ? builds[0]
        : (deps.length > 0 && deps[0].build_id ? await api.getBuild(deps[0].build_id).catch(() => null) : null);

      if (b) {
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
    const interval = setInterval(fetchProjectData, 6000);
    return () => clearInterval(interval);
  }, [projectId]);

  // Handle log loading and live SSE streaming for build logs
  useEffect(() => {
    if (latestBuild?.id) {
      // Fetch initial log snapshot from server
      api.getBuildLogs(latestBuild.id).then((res) => {
        if (res && res.events && res.events.length > 0) {
          setLogs(res.events);
        }
      }).catch(() => {});

      // Connect SSE stream if currently active or if viewing logs tab
      const isBuildActive = ['BUILDING', 'QUEUED', 'PREPARING'].includes(latestBuild.status);
      if (isBuildActive || activeTab === 'logs') {
        setIsStreaming(true);
        const unsubscribe = api.streamBuildLogs(
          latestBuild.id,
          (evt) => {
            setLogs((prev) => {
              const exists = prev.some(p => p.timestamp === evt.timestamp && p.message === evt.message);
              if (exists) return prev;
              return [...prev, evt];
            });
          },
          () => {
            setIsStreaming(false);
          }
        );
        return () => unsubscribe();
      }
    }
  }, [activeTab, latestBuild?.id, latestBuild?.status]);

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
      addToast({
        title: 'Redeployment triggered',
        description: 'New build queued in worker pool.',
        type: 'info',
      });
      setActiveTab('logs');
      fetchProjectData();
    } catch (err: any) {
      addToast({
        title: 'Redeploy failed',
        description: err.message || 'Could not queue redeployment.',
        type: 'error',
      });
    } finally {
      setIsRebuilding(false);
    }
  };

  const handleRollback = async (deploymentId: string) => {
    if (!confirm('Rollback project live traffic to this deployment?')) return;
    try {
      await api.rollback(projectId, deploymentId);
      addToast({
        title: 'Rollback successful',
        description: `Traffic routed to deployment ${deploymentId.slice(-8)}.`,
        type: 'success',
      });
      fetchProjectData();
    } catch (err: any) {
      addToast({
        title: 'Rollback failed',
        description: err.message || 'Could not perform rollback.',
        type: 'error',
      });
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
      addToast({
        title: 'Environment variable added',
        description: `Saved ${newEnvKey.trim()}. Will apply on subsequent builds.`,
        type: 'success',
      });
    } catch (err: any) {
      addToast({
        title: 'Failed to add variable',
        description: err.message || 'Error saving variable.',
        type: 'error',
      });
    }
  };

  const handleDeleteEnv = async (key: string) => {
    try {
      await api.deleteEnvVar(projectId, key);
      const updated = await api.getEnvVars(projectId);
      setEnvVars(updated);
      addToast({
        title: 'Variable deleted',
        description: `Removed ${key}.`,
        type: 'success',
      });
    } catch (err: any) {
      addToast({
        title: 'Failed to delete variable',
        description: err.message || 'Error removing variable.',
        type: 'error',
      });
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
      addToast({
        title: 'Custom domain added',
        description: 'Configure your DNS CNAME record as indicated.',
        type: 'success',
      });
    } catch (err: any) {
      addToast({
        title: 'Failed to add domain',
        description: err.message || 'Could not register custom domain.',
        type: 'error',
      });
    } finally {
      setIsAddingDomain(false);
    }
  };

  const handleVerifyDomain = async (domainId: string) => {
    try {
      await api.verifyDomain(projectId, domainId);
      const doms = await api.getDomains(projectId);
      setCustomDomains(doms);
      addToast({
        title: 'Verification checked',
        description: 'Domain DNS status verified successfully.',
        type: 'success',
      });
    } catch (err: any) {
      addToast({
        title: 'Verification failed',
        description: err.message || 'DNS CNAME record not detected yet.',
        type: 'error',
      });
    }
  };

  const handleDeleteDomain = async (domainId: string) => {
    try {
      await api.deleteDomain(projectId, domainId);
      const doms = await api.getDomains(projectId);
      setCustomDomains(doms);
      addToast({
        title: 'Domain removed',
        description: 'Custom domain successfully unlinked.',
        type: 'success',
      });
    } catch (err: any) {
      addToast({
        title: 'Failed to remove domain',
        description: err.message || 'Error deleting domain.',
        type: 'error',
      });
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
      addToast({
        title: 'Webhook endpoint registered',
        description: 'Deployment events will now trigger signed POST notifications.',
        type: 'success',
      });
    } catch (err: any) {
      addToast({
        title: 'Failed to add webhook',
        description: err.message || 'Could not save webhook endpoint.',
        type: 'error',
      });
    } finally {
      setIsAddingWebhook(false);
    }
  };

  const handleDeleteWebhook = async (webhookId: string) => {
    try {
      await api.deleteWebhook(projectId, webhookId);
      const whs = await api.getWebhooks(projectId);
      setWebhooks(whs);
      addToast({
        title: 'Webhook deleted',
        description: 'Endpoint removed.',
        type: 'success',
      });
    } catch (err: any) {
      addToast({
        title: 'Failed to delete webhook',
        description: err.message || 'Error deleting webhook.',
        type: 'error',
      });
    }
  };

  const handleTestWebhook = async (webhookId: string) => {
    try {
      await api.testWebhook(projectId, webhookId);
      addToast({
        title: 'Test ping dispatched',
        description: 'Ping event delivered to your webhook endpoint.',
        type: 'success',
      });
    } catch (err: any) {
      addToast({
        title: 'Test failed',
        description: err.message || 'Endpoint did not return 2xx response.',
        type: 'error',
      });
    }
  };

  const handleMobileLogoFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      addToast({
        title: 'Invalid file format',
        description: 'Please upload an image file (PNG, JPG, WebP, SVG).',
        type: 'error',
      });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      addToast({
        title: 'File too large',
        description: 'Image size must be less than 5MB.',
        type: 'error',
      });
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setAppLogo(result);
      setLogoFileName(file.name);
      addToast({
        title: 'App Icon Loaded',
        description: `Successfully loaded '${file.name}' for mobile packaging.`,
        type: 'success',
      });
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveMobileLogo = () => {
    setAppLogo(null);
    setLogoFileName('');
    if (mobileLogoInputRef.current) {
      mobileLogoInputRef.current.value = '';
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
        permissions: appPermissions,
        icon_base64: appLogo || undefined,
      });

      const build = await api.triggerMobileBuild(app.id);
      setMobileBuild(build);
      addToast({
        title: 'Appify compilation started',
        description: 'Generating native Android wrapper APK.',
        type: 'info',
      });

      let pollInterval: any = null;
      let isDone = false;

      const finishBuild = (updated: MobileBuild) => {
        if (isDone) return;
        isDone = true;
        if (pollInterval) clearInterval(pollInterval);
        setIsBuildingApp(false);
        setMobileBuild(updated);
        if (updated.status === 'APP_READY') {
          addToast({
            title: 'APK Ready!',
            description: 'Your native Android package is ready for download.',
            type: 'success',
          });
        } else if (updated.status === 'APP_FAILED') {
          addToast({
            title: 'Compilation Failed',
            description: updated.error_message || 'Mobile app generation failed.',
            type: 'error',
          });
        }
      };

      const unsubscribe = api.streamMobileLogs(
        build.id,
        (evt) => {
          setMobileLogs((prev) => [...prev, evt]);
        },
        async () => {
          try {
            const updated = await api.getMobileBuild(build.id);
            finishBuild(updated);
          } catch (_) {}
        }
      );

      // Active safety poll to guarantee completion
      pollInterval = setInterval(async () => {
        try {
          const updated = await api.getMobileBuild(build.id);
          if (updated.status === 'APP_READY' || updated.status === 'APP_FAILED') {
            unsubscribe();
            finishBuild(updated);
          }
        } catch (_) {}
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Mobile build failed');
      setIsBuildingApp(false);
      addToast({
        title: 'Compilation failed',
        description: err.message || 'Mobile app generation failed.',
        type: 'error',
      });
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    addToast({
      title: 'Copied to clipboard',
      description: text,
      type: 'info',
    });
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  if (loading || !project) {
    return (
      <div className="py-20 flex flex-col items-center justify-center gap-3 text-center">
        <div className="w-8 h-8 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
        <p className="text-xs text-[var(--text-secondary)] font-mono">Loading project details...</p>
      </div>
    );
  }

  const previewUrl =
    (project.active_deployment_id || project.status === 'DEPLOYED' || project.active_url) &&
    project.slug
      ? project.active_url && !project.active_url.includes('localhost')
        ? project.active_url
        : api.getPreviewUrl(project.slug)
      : null;

  const tabs: { id: TabType; label: string; icon: any }[] = [
    { id: 'overview', label: 'Overview', icon: Globe },
    { id: 'deployments', label: 'Deployments', icon: Layers },
    { id: 'logs', label: 'Build Logs', icon: Terminal },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'runtime', label: 'Runtime Logs', icon: Activity },
    { id: 'env', label: 'Environment', icon: KeyRound },
    { id: 'domains', label: 'Domains', icon: Globe },
    { id: 'webhooks', label: 'Webhooks', icon: Webhook },
    { id: 'appify', label: 'Appify Mobile', icon: Smartphone },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
        <Link
          href="/dashboard/projects"
          className="hover:text-[var(--text-primary)] transition-colors inline-flex items-center gap-1"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Projects
        </Link>
        <span>/</span>
        <span className="text-[var(--text-primary)] font-medium">{project.name}</span>
      </div>

      {/* Project Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              {project.name}
            </h1>
            <StatusBadge status={project.status} />
          </div>
          <div className="flex items-center gap-3 text-xs text-[var(--text-secondary)] mt-1 font-mono">
            <span>slug: {project.slug}</span>
            <span>•</span>
            <span>framework: {project.framework || 'pending'}</span>
            <span>•</span>
            <span>updated: {formatRelativeTime(project.updated_at)}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRedeploy}
            disabled={isRebuilding}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] hover:border-zinc-500 text-xs font-semibold transition-colors disabled:opacity-50 shadow-sm"
            title="Rebuild latest upload"
          >
            {isRebuilding ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-500" />
            ) : (
              <Play className="w-3.5 h-3.5 text-sky-500" />
            )}
            <span>Redeploy</span>
          </button>

          {previewUrl && (
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black hover:bg-sky-400 text-xs font-semibold transition-colors shadow-sm"
            >
              <span>Visit Site</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-[var(--border)] overflow-x-auto pb-px">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                active
                  ? 'border-sky-500 text-sky-500 font-semibold'
                  : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border)]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.id === 'runtime' && runtimeLogs.length > 0 && (
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              )}
            </button>
          );
        })}
      </div>

      {/* AI Build Diagnosis Alert Banner (Shown if latest build failed) */}
      {diagnosis && (
        <div className="p-5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-xs space-y-2">
          <div className="flex items-center gap-2 text-amber-500 font-bold">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>AI Build Diagnosis: {diagnosis.summary}</span>
          </div>
          <p className="text-[var(--text-primary)]">{diagnosis.root_cause}</p>
          <div className="p-3 bg-black/40 border border-[var(--border)] rounded-lg text-emerald-400 font-mono text-[11px]">
            <span className="text-[var(--text-muted)] block mb-1">Recommended Fix:</span>
            {diagnosis.actionable_fix}
          </div>
        </div>
      )}

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
              <span className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Production URL
              </span>
              <div className="mt-2">
                {previewUrl ? (
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-mono text-sky-500 hover:underline break-all inline-flex items-center gap-1.5"
                  >
                    <span>{previewUrl}</span>
                    <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                ) : (
                  <span className="text-xs text-[var(--text-muted)] font-mono">No active deployment</span>
                )}
              </div>
            </div>

            <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
              <span className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Framework & Runtime
              </span>
              <div className="mt-2 text-xs text-[var(--text-primary)] font-mono">
                {project.framework || 'Detecting...'} ({project.language || 'js'})
              </div>
              <div className="text-[11px] text-[var(--text-muted)] mt-1 font-mono">
                {project.build_command || 'npm run build'}
              </div>
            </div>

            <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
              <span className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Total Deployments
              </span>
              <div className="mt-2 text-2xl font-bold text-[var(--text-primary)]">
                {deployments.length}
              </div>
              <div className="text-[11px] text-[var(--text-muted)] mt-1">Immutable atomic versions</div>
            </div>
          </div>

          {/* Interactive In-Dashboard Web Preview */}
          {previewUrl && (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-sm">
              <div className="px-4 py-2.5 bg-[var(--surface-muted)] border-b border-[var(--border)] flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5 mr-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
                  </div>
                  <span className="font-semibold text-[var(--text-primary)]">Live Web Preview</span>
                </div>

                <div className="flex items-center gap-1 bg-[var(--surface)] p-1 rounded-lg border border-[var(--border)]">
                  <button
                    onClick={() => setPreviewDevice('desktop')}
                    className={`p-1 rounded ${
                      previewDevice === 'desktop'
                        ? 'bg-sky-500/10 text-sky-500'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                    }`}
                    title="Desktop Preview"
                  >
                    <Monitor className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setPreviewDevice('tablet')}
                    className={`p-1 rounded ${
                      previewDevice === 'tablet'
                        ? 'bg-sky-500/10 text-sky-500'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                    }`}
                    title="Tablet Preview"
                  >
                    <Tablet className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setPreviewDevice('mobile')}
                    className={`p-1 rounded ${
                      previewDevice === 'mobile'
                        ? 'bg-sky-500/10 text-sky-500'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                    }`}
                    title="Mobile Preview"
                  >
                    <Smartphone className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPreviewKey((k) => k + 1)}
                    className="p-1.5 rounded hover:bg-[var(--surface-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                    title="Reload Preview"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded hover:bg-[var(--surface-hover)] text-[var(--text-secondary)] hover:text-sky-500 transition-colors"
                    title="Open In New Window"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>

              <div className="p-4 bg-[var(--surface-muted)] flex justify-center min-h-[460px]">
                <iframe
                  key={previewKey}
                  src={previewUrl}
                  title="App Live Preview"
                  className={`border border-[var(--border)] bg-black rounded-lg shadow-xl transition-all h-[440px] ${
                    previewDevice === 'desktop'
                      ? 'w-full'
                      : previewDevice === 'tablet'
                      ? 'w-[768px]'
                      : 'w-[375px]'
                  }`}
                />
              </div>
            </div>
          )}

          {/* Quick Terminal Preview */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-[var(--text-secondary)]">
                Latest Build Output
              </span>
              <button
                onClick={() => setActiveTab('logs')}
                className="text-xs text-sky-500 hover:underline"
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
            <span className="text-xs text-[var(--text-secondary)]">
              Deployment history with atomic one-click rollbacks
            </span>
            <button
              onClick={handleRedeploy}
              disabled={isRebuilding}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500 text-black text-xs font-semibold hover:bg-sky-400 transition-colors shadow-sm disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" /> Trigger Redeploy
            </button>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-sm">
            {deployments.length === 0 ? (
              <div className="py-12 text-center text-xs text-[var(--text-secondary)] font-mono">
                No deployments recorded yet.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)] font-medium">
                  <tr>
                    <th className="px-5 py-3">Deployment ID</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Public Hostname</th>
                    <th className="px-5 py-3">Deployed</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)] font-mono">
                  {deployments.map((d) => {
                    const isCurrent = d.id === project.active_deployment_id;
                    return (
                      <tr key={d.id} className="hover:bg-[var(--surface-hover)] transition-colors">
                        <td className="px-5 py-3.5">
                          <span className="text-[var(--text-primary)] font-medium">{d.id.slice(-8)}</span>
                          {isCurrent && (
                            <span className="ml-2 px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-500 text-[10px] font-sans font-semibold border border-sky-500/30">
                              ACTIVE
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-3.5">
                          <StatusBadge status={d.status} />
                        </td>
                        <td className="px-5 py-3.5">
                          {d.url ? (
                            <a
                              href={d.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sky-500 hover:underline inline-flex items-center gap-1"
                            >
                              <span>{d.subdomain || d.url}</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-[var(--text-muted)]">—</span>
                          )}
                        </td>
                        <td className="px-5 py-3.5 text-[var(--text-secondary)]">
                          {d.completed_at ? (
                            <span title={formatDate(d.completed_at)}>
                              {formatRelativeTime(d.completed_at)}
                            </span>
                          ) : (
                            <span className="text-amber-500">In Progress</span>
                          )}
                        </td>
                        <td className="px-5 py-3.5 text-right font-sans">
                          {!isCurrent && d.status === 'READY' && (
                            <button
                              onClick={() => handleRollback(d.id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs hover:border-zinc-500 transition-colors"
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
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Build Logs */}
      {activeTab === 'logs' && (
        <div className="space-y-4">
          <TerminalViewer
            logs={logs}
            title={`Build Terminal [ID: ${latestBuild?.id ? latestBuild.id.slice(-8) : 'active'}]`}
            isStreaming={isStreaming}
          />
        </div>
      )}

      {/* Tab 4: Traffic & Performance Analytics */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
              <span className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Total Requests
              </span>
              <div className="mt-2 text-2xl font-bold text-[var(--text-primary)]">
                {analytics?.total_requests || 0}
              </div>
              <span className="text-[11px] text-[var(--text-muted)]">Recorded hits</span>
            </div>

            <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
              <span className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Avg Latency
              </span>
              <div className="mt-2 text-2xl font-bold text-sky-500">{analytics?.avg_latency_ms || 0}ms</div>
              <span className="text-[11px] text-[var(--text-muted)]">P95: {analytics?.p95_latency_ms || 0}ms</span>
            </div>

            <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
              <span className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Unique Visitors
              </span>
              <div className="mt-2 text-2xl font-bold text-emerald-500">{analytics?.unique_visitors || 0}</div>
              <span className="text-[11px] text-[var(--text-muted)]">Unique client IPs</span>
            </div>

            <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
              <span className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Success Rate
              </span>
              <div className="mt-2 text-2xl font-bold text-[var(--text-primary)]">
                {analytics?.total_requests && analytics?.status_codes?.status_2xx !== undefined
                  ? Math.round((analytics.status_codes.status_2xx / analytics.total_requests) * 100)
                  : 100}
                %
              </div>
              <span className="text-[11px] text-[var(--text-muted)]">2xx HTTP responses</span>
            </div>
          </div>

          {/* Top Endpoints Table */}
          <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] space-y-3 shadow-sm">
            <h3 className="text-xs font-semibold text-[var(--text-primary)]">Top Requested Paths</h3>
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)]">
                <tr>
                  <th className="px-4 py-2">Path</th>
                  <th className="px-4 py-2">Requests</th>
                  <th className="px-4 py-2 text-right">Avg Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {analytics?.top_paths?.length ? (
                  analytics.top_paths.map((p: any, idx: number) => (
                    <tr key={idx} className="hover:bg-[var(--surface-hover)]">
                      <td className="px-4 py-2 text-[var(--text-primary)]">{p.path}</td>
                      <td className="px-4 py-2 text-[var(--text-secondary)]">{p.count}</td>
                      <td className="px-4 py-2 text-right text-sky-500">{p.avg_latency_ms}ms</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-center text-[var(--text-muted)] font-sans">
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
          <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] flex items-center justify-between shadow-sm">
            <div>
              <h3 className="text-xs font-semibold text-[var(--text-primary)]">Live HTTP Access Traffic</h3>
              <p className="text-[11px] text-[var(--text-secondary)]">
                Real-time incoming requests to your deployed application
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-500 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
              <span>Listening Live</span>
            </div>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden font-mono text-xs shadow-sm">
            <table className="w-full text-left">
              <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)]">
                <tr>
                  <th className="px-4 py-2.5">Time</th>
                  <th className="px-4 py-2.5">Method</th>
                  <th className="px-4 py-2.5">Path</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Latency</th>
                  <th className="px-4 py-2.5">Client IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {runtimeLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-[var(--text-muted)] font-sans">
                      No HTTP traffic recorded yet. Visit your live site to generate requests.
                    </td>
                  </tr>
                ) : (
                  runtimeLogs.map((req, idx) => (
                    <tr key={idx} className="hover:bg-[var(--surface-hover)]">
                      <td className="px-4 py-2.5 text-[var(--text-muted)] text-[11px]">
                        {req.timestamp ? req.timestamp.slice(11, 19) : '-'}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            req.method === 'GET'
                              ? 'bg-sky-500/10 text-sky-500 border border-sky-500/20'
                              : req.method === 'POST'
                              ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                              : 'bg-[var(--surface-muted)] text-[var(--text-secondary)]'
                          }`}
                        >
                          {req.method}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-[var(--text-primary)] font-semibold">{req.path}</td>
                      <td className="px-4 py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            req.status_code >= 200 && req.status_code < 300
                              ? 'text-emerald-500'
                              : req.status_code >= 400
                              ? 'text-rose-500'
                              : 'text-[var(--text-secondary)]'
                          }`}
                        >
                          {req.status_code}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-[var(--text-secondary)]">{req.duration_ms}ms</td>
                      <td className="px-4 py-2.5 text-[var(--text-muted)] text-[11px]">{req.client_ip}</td>
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
          <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
              Add Environment Variable
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mb-4">
              Securely injected into isolated sandbox builds and runtime containers
            </p>
            <form onSubmit={handleAddEnv} className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={newEnvKey}
                onChange={(e) => setNewEnvKey(e.target.value)}
                placeholder="VARIABLE_NAME"
                className="px-3 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] font-mono uppercase focus:outline-none focus:border-sky-500 sm:w-1/3"
              />
              <input
                type="text"
                value={newEnvVal}
                onChange={(e) => setNewEnvVal(e.target.value)}
                placeholder="Value..."
                className="px-3 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] font-mono focus:outline-none focus:border-sky-500 flex-1"
              />
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors flex items-center justify-center gap-1.5 shadow-sm"
              >
                <Plus className="w-4 h-4" /> Save
              </button>
            </form>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)]">
                <tr>
                  <th className="px-5 py-3">Key</th>
                  <th className="px-5 py-3">Value</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {envVars.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-6 text-center text-[var(--text-muted)] font-sans">
                      No environment variables configured.
                    </td>
                  </tr>
                ) : (
                  envVars.map((ev) => (
                    <tr key={ev.id} className="hover:bg-[var(--surface-hover)]">
                      <td className="px-5 py-3 font-semibold text-[var(--text-primary)]">{ev.key}</td>
                      <td className="px-5 py-3 text-[var(--text-secondary)]">{ev.value}</td>
                      <td className="px-5 py-3 text-right font-sans">
                        <button
                          onClick={() => handleDeleteEnv(ev.key)}
                          className="text-[var(--text-muted)] hover:text-rose-500 transition-colors p-1"
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
          <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Add Custom Domain</h3>
            <p className="text-xs text-[var(--text-secondary)] mb-4">
              Map your own apex or subdomain (e.g. <code>app.mycompany.com</code>) directly to this project
            </p>
            <form onSubmit={handleAddDomain} className="flex gap-3">
              <input
                type="text"
                required
                value={newDomainInput}
                onChange={(e) => setNewDomainInput(e.target.value)}
                placeholder="app.mycompany.com"
                className="px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] font-mono flex-1 focus:outline-none focus:border-sky-500"
              />
              <button
                type="submit"
                disabled={isAddingDomain}
                className="px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                <Plus className="w-4 h-4" /> Add Domain
              </button>
            </form>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)]">
                <tr>
                  <th className="px-5 py-3">Domain</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3">DNS Target</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {customDomains.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-6 text-center text-[var(--text-muted)] font-sans">
                      No custom domains configured.
                    </td>
                  </tr>
                ) : (
                  customDomains.map((d) => (
                    <tr key={d.id} className="hover:bg-[var(--surface-hover)]">
                      <td className="px-5 py-3 font-semibold text-[var(--text-primary)]">{d.domain}</td>
                      <td className="px-5 py-3 text-[var(--text-secondary)]">CNAME</td>
                      <td className="px-5 py-3 text-sky-500">{d.cname_target}</td>
                      <td className="px-5 py-3 font-sans">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            d.status === 'VERIFIED'
                              ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                              : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                          }`}
                        >
                          {d.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-sans space-x-2">
                        {d.status !== 'VERIFIED' && (
                          <button
                            onClick={() => handleVerifyDomain(d.id)}
                            className="px-2 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-primary)] hover:border-zinc-500 text-xs"
                          >
                            Verify DNS
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteDomain(d.id)}
                          className="text-[var(--text-muted)] hover:text-rose-500 p-1"
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
          <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
              Add Outgoing Webhook
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mb-4">
              Receive signed HTTP POST notifications on deployment transitions (Slack, Discord, or custom backend)
            </p>
            <form onSubmit={handleAddWebhook} className="flex gap-3">
              <input
                type="url"
                required
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                placeholder="https://hooks.slack.com/services/... or https://api.mycompany.com/webhook"
                className="px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] font-mono flex-1 focus:outline-none focus:border-sky-500"
              />
              <button
                type="submit"
                disabled={isAddingWebhook}
                className="px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                <Plus className="w-4 h-4" /> Add Webhook
              </button>
            </form>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)] text-[var(--text-secondary)]">
                <tr>
                  <th className="px-5 py-3">Endpoint URL</th>
                  <th className="px-5 py-3">Events</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {webhooks.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-6 text-center text-[var(--text-muted)] font-sans">
                      No webhook endpoints configured.
                    </td>
                  </tr>
                ) : (
                  webhooks.map((wh) => (
                    <tr key={wh.id} className="hover:bg-[var(--surface-hover)]">
                      <td className="px-5 py-3 text-[var(--text-primary)] font-medium break-all">
                        {wh.url}
                      </td>
                      <td className="px-5 py-3 text-[var(--text-secondary)] font-sans">
                        <span className="px-2 py-0.5 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[10px]">
                          {wh.events?.join(', ') || 'All Events'}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-sans space-x-2">
                        <button
                          onClick={() => handleTestWebhook(wh.id)}
                          className="px-2.5 py-1 rounded bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs inline-flex items-center gap-1"
                        >
                          <Send className="w-3 h-3" /> Test
                        </button>
                        <button
                          onClick={() => handleDeleteWebhook(wh.id)}
                          className="text-[var(--text-muted)] hover:text-rose-500 p-1"
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
            <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <Smartphone className="w-5 h-5 text-purple-500" />
                <h2 className="text-base font-semibold text-[var(--text-primary)]">
                  Compile Native Android Application
                </h2>
              </div>
              <p className="text-xs text-[var(--text-secondary)] mb-6">
                Transform this deployed web application into a complete native Android APK with custom splash, offline shell, and native device capabilities.
              </p>

              <form onSubmit={handleCreateAndBuildApp} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                      App Name
                    </label>
                    <input
                      type="text"
                      required
                      value={appName}
                      onChange={(e) => setAppName(e.target.value)}
                      placeholder="My Application"
                      className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] focus:outline-none focus:border-purple-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                      Package Identifier
                    </label>
                    <input
                      type="text"
                      required
                      value={packageId}
                      onChange={(e) => setPackageId(e.target.value)}
                      placeholder="com.company.app"
                      className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] font-mono focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>

                {/* App Logo / Launcher Icon Upload Section */}
                <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)]/50 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-primary)]">
                        App Logo & Launcher Icon
                      </label>
                      <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                        Upload custom icon for the Android home screen, launcher, and system app drawer
                      </p>
                    </div>
                    {appLogo && (
                      <button
                        type="button"
                        onClick={handleRemoveMobileLogo}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-rose-500 hover:text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 rounded-md transition-colors"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Remove Icon</span>
                      </button>
                    )}
                  </div>

                  <div className="flex flex-col sm:flex-row items-center gap-4">
                    {/* Live Icon Previews */}
                    <div className="flex items-center gap-3 shrink-0">
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-14 h-14 rounded-2xl bg-zinc-800 border border-[var(--border)] overflow-hidden flex items-center justify-center shadow-md relative">
                          {appLogo ? (
                            <img src={appLogo} alt="App Icon" className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-white font-bold text-lg select-none">
                              {appName ? appName[0].toUpperCase() : 'Z'}
                            </div>
                          )}
                        </div>
                        <span className="text-[10px] text-[var(--text-muted)] font-mono">Squircle</span>
                      </div>

                      <div className="flex flex-col items-center gap-1">
                        <div className="w-14 h-14 rounded-full bg-zinc-800 border border-[var(--border)] overflow-hidden flex items-center justify-center shadow-md relative">
                          {appLogo ? (
                            <img src={appLogo} alt="App Round Icon" className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-white font-bold text-lg select-none">
                              {appName ? appName[0].toUpperCase() : 'Z'}
                            </div>
                          )}
                        </div>
                        <span className="text-[10px] text-[var(--text-muted)] font-mono">Round</span>
                      </div>
                    </div>

                    {/* Upload Dropzone */}
                    <div
                      onClick={() => mobileLogoInputRef.current?.click()}
                      onDragOver={(e) => { e.preventDefault(); }}
                      onDrop={(e) => {
                        e.preventDefault();
                        if (e.dataTransfer.files?.[0]) {
                          handleMobileLogoFile(e.dataTransfer.files[0]);
                        }
                      }}
                      className="flex-1 w-full p-3.5 border-2 border-dashed border-[var(--border)] hover:border-purple-500/60 rounded-xl cursor-pointer bg-[var(--surface)] hover:bg-[var(--surface-hover)] transition-all flex flex-col items-center justify-center text-center group"
                    >
                      <input
                        ref={mobileLogoInputRef}
                        type="file"
                        accept="image/png,image/jpeg,image/webp,image/svg+xml"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files?.[0]) {
                            handleMobileLogoFile(e.target.files[0]);
                          }
                        }}
                      />
                      <UploadCloud className="w-5 h-5 text-[var(--text-muted)] group-hover:text-purple-400 transition-colors mb-1" />
                      <div className="text-xs text-[var(--text-primary)] font-medium">
                        {logoFileName ? (
                          <span className="text-purple-400 font-semibold">{logoFileName}</span>
                        ) : (
                          <>
                            <span className="text-purple-400 underline decoration-purple-400/40">Click to upload logo</span> or drag and drop
                          </>
                        )}
                      </div>
                      <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                        PNG, JPG, WebP, SVG • 512×512px square recommended
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                      Theme
                    </label>
                    <select
                      value={appTheme}
                      onChange={(e) => setAppTheme(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] focus:outline-none focus:border-purple-500"
                    >
                      <option value="system">System Default</option>
                      <option value="dark">Dark Theme</option>
                      <option value="light">Light Theme</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                      Screen Orientation
                    </label>
                    <select
                      value={appOrientation}
                      onChange={(e) => setAppOrientation(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] focus:outline-none focus:border-purple-500"
                    >
                      <option value="portrait">Portrait</option>
                      <option value="landscape">Landscape</option>
                      <option value="sensor">Sensor Auto</option>
                    </select>
                  </div>
                </div>

                {/* Android Device Permissions */}
                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-2">
                    Android Permissions
                  </label>
                  <div className="grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
                    <label className="flex items-center gap-2 p-2.5 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={appPermissions.includes('camera')}
                        onChange={(e) => {
                          setAppPermissions((prev) =>
                            e.target.checked ? [...prev, 'camera'] : prev.filter((x) => x !== 'camera')
                          );
                        }}
                        className="rounded"
                      />
                      <span>Camera Access</span>
                    </label>

                    <label className="flex items-center gap-2 p-2.5 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={appPermissions.includes('location')}
                        onChange={(e) => {
                          setAppPermissions((prev) =>
                            e.target.checked ? [...prev, 'location'] : prev.filter((x) => x !== 'location')
                          );
                        }}
                        className="rounded"
                      />
                      <span>GPS / Location</span>
                    </label>

                    <label className="flex items-center gap-2 p-2.5 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={appPermissions.includes('notifications')}
                        onChange={(e) => {
                          setAppPermissions((prev) =>
                            e.target.checked
                              ? [...prev, 'notifications']
                              : prev.filter((x) => x !== 'notifications')
                          );
                        }}
                        className="rounded"
                      />
                      <span>Push Notifications</span>
                    </label>

                    <label className="flex items-center gap-2 p-2.5 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={appPermissions.includes('audio')}
                        onChange={(e) => {
                          setAppPermissions((prev) =>
                            e.target.checked ? [...prev, 'audio'] : prev.filter((x) => x !== 'audio')
                          );
                        }}
                        className="rounded"
                      />
                      <span>Microphone Audio</span>
                    </label>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isBuildingApp}
                  className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg bg-purple-600 text-white font-semibold text-xs hover:bg-purple-500 transition-colors disabled:opacity-50 shadow-sm"
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
              <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] space-y-6 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-[var(--text-secondary)]">Mobile Build:</span>
                    <StatusBadge status={mobileBuild.status} />
                  </div>
                </div>

                {mobileBuild.status === 'APP_READY' && (
                  <div className="space-y-4 pt-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <a
                        href={api.getMobileApkDownloadUrl(mobileBuild.id)}
                        download
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 transition-colors shadow-sm"
                      >
                        <Download className="w-4 h-4" />
                        Download Android APK (.apk)
                      </a>
                      <a
                        href={api.getMobileSourceDownloadUrl(mobileBuild.id)}
                        download
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] text-[var(--text-primary)] text-xs font-semibold hover:bg-[var(--surface-hover)] transition-colors shadow-sm"
                      >
                        <Download className="w-4 h-4" />
                        Download Project Source (.zip)
                      </a>
                    </div>

                    <div className="p-4 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)] space-y-3 font-mono text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-[var(--text-muted)] text-[11px]">Install on Device via ADB:</span>
                        <button
                          onClick={() =>
                            copyToClipboard(`adb install app-debug-${mobileBuild.id}.apk`, 'adb')
                          }
                          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center gap-1 text-[11px]"
                        >
                          {copiedCmd === 'adb' ? (
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                          {copiedCmd === 'adb' ? 'Copied' : 'Copy'}
                        </button>
                      </div>
                      <div className="p-2 bg-black/60 rounded border border-[var(--border)] text-sky-400 select-all">
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
            <span className="text-xs text-[var(--text-secondary)] mb-3 font-medium">
              Interactive Native Phone Mockup
            </span>
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
                  <iframe src={previewUrl} title="Phone Simulator" className="w-full h-full border-none" />
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
          <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] space-y-4 shadow-sm">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Project Configuration</h3>
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                Project Name
              </label>
              <input
                type="text"
                defaultValue={project.name}
                className="w-full max-w-md px-3 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)]"
              />
            </div>
          </div>

          <div className="p-6 rounded-xl border border-rose-500/20 bg-rose-500/5 space-y-3">
            <h3 className="text-sm font-semibold text-rose-500">Danger Zone</h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Permanently delete this project, all deployments, artifacts, and logs. This cannot be undone.
            </p>
            <button
              onClick={async () => {
                const targetId = project?.id || projectId;
                if (confirm(`Permanently delete project '${project.name}'?`)) {
                  setIsDeletingProject(true);
                  try {
                    await api.deleteProject(targetId);
                    addToast({
                      title: 'Project deleted',
                      description: `Project ${project.name} has been removed.`,
                      type: 'success',
                    });
                    router.push('/dashboard/projects');
                  } catch (e: any) {
                    addToast({
                      title: 'Delete failed',
                      description: e.message || 'Failed to delete project.',
                      type: 'error',
                    });
                  } finally {
                    setIsDeletingProject(false);
                  }
                }
              }}
              disabled={isDeletingProject}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 text-white font-semibold text-xs hover:bg-rose-500 transition-colors shadow-sm disabled:opacity-50"
            >
              {isDeletingProject && (
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              )}
              <span>{isDeletingProject ? 'Deleting Project...' : 'Delete Project'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
