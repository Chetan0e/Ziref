'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Project, MobileApp, MobileBuild } from '@ziref/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TerminalViewer } from '@/components/ui/TerminalViewer';
import { formatDate, formatRelativeTime } from '@/lib/date';
import { useToast } from '@/lib/toast';
import {
  Smartphone,
  Download,
  Loader2,
  Copy,
  Check,
  RefreshCw,
  FolderGit2,
  ExternalLink,
  Settings,
  Sparkles,
  Info,
  ChevronRight,
  Shield,
  Layers,
} from 'lucide-react';

export default function AppifyStudioPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  const [appName, setAppName] = useState('');
  const [packageId, setPackageId] = useState('com.ziref.app');
  const [appTheme, setAppTheme] = useState('system');
  const [appOrientation, setAppOrientation] = useState('portrait');
  const [appPermissions, setAppPermissions] = useState<string[]>([]);

  const [isBuildingApp, setIsBuildingApp] = useState(false);
  const [mobileBuild, setMobileBuild] = useState<MobileBuild | null>(null);
  const [mobileLogs, setMobileLogs] = useState<any[]>([]);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  const [loadingProjects, setLoadingProjects] = useState(true);
  const { addToast } = useToast();

  const loadProjects = async () => {
    try {
      setLoadingProjects(true);
      const data = await api.getProjects();
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
        setSelectedProject(data[0]);
        setAppName(data[0].name);
        setPackageId(`com.ziref.${data[0].slug.replace(/[^a-z0-9]/gi, '').toLowerCase() || 'app'}`);
      }
    } catch (err: any) {
      addToast({
        title: 'Failed to load projects',
        description: err.message || 'Error fetching project list.',
        type: 'error',
      });
    } finally {
      setLoadingProjects(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleSelectProject = (projectId: string) => {
    setSelectedProjectId(projectId);
    const found = projects.find((p) => p.id === projectId);
    if (found) {
      setSelectedProject(found);
      setAppName(found.name);
      setPackageId(`com.ziref.${found.slug.replace(/[^a-z0-9]/gi, '').toLowerCase() || 'app'}`);
    }
  };

  const handleBuildApp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) {
      addToast({
        title: 'Project required',
        description: 'Please select a project to package into a mobile app.',
        type: 'error',
      });
      return;
    }

    setIsBuildingApp(true);
    setMobileLogs([]);
    try {
      const app = await api.createMobileApp(selectedProjectId, {
        app_name: appName,
        package_id: packageId,
        theme: appTheme,
        orientation: appOrientation,
        permissions: appPermissions,
      });

      const build = await api.triggerMobileBuild(app.id);
      setMobileBuild(build);
      addToast({
        title: 'Compilation initiated',
        description: 'Generating native Android APK in isolated worker.',
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
            description: 'Your native Android APK is ready for download.',
            type: 'success',
          });
        } else if (updated.status === 'APP_FAILED') {
          addToast({
            title: 'Compilation Failed',
            description: updated.error_message || 'Mobile APK build failed.',
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

      // Active safety poll to guarantee completion even if stream closes early
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
      setIsBuildingApp(false);
      addToast({
        title: 'Mobile build failed',
        description: err.message || 'Failed to trigger mobile build pipeline.',
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

  const previewUrl =
    (selectedProject?.active_deployment_id ||
      selectedProject?.status === 'DEPLOYED' ||
      selectedProject?.active_url) &&
    selectedProject?.slug
      ? selectedProject.active_url && !selectedProject.active_url.includes('localhost')
        ? selectedProject.active_url
        : api.getPreviewUrl(selectedProject.slug)
      : null;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
        <div>
          <div className="flex items-center gap-2">
            <Smartphone className="w-6 h-6 text-purple-500" />
            <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              Appify Mobile Studio
            </h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Package any deployed web application into an installable native Android APK
          </p>
        </div>
      </div>

      {loadingProjects ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-center">
          <div className="w-8 h-8 rounded-full border-2 border-purple-500 border-t-transparent animate-spin" />
          <p className="text-xs text-[var(--text-secondary)] font-mono">Loading projects...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="p-12 text-center max-w-md mx-auto space-y-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <Smartphone className="w-12 h-12 text-[var(--text-muted)] mx-auto" />
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">No projects found</h3>
          <p className="text-xs text-[var(--text-secondary)]">
            Deploy a project first so Appify can wrap its live URL into a native Android application package.
          </p>
          <Link
            href="/dashboard/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors"
          >
            Deploy Project
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Configuration Form Column */}
          <div className="lg:col-span-7 space-y-6">
            <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm space-y-6">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                  Select Target Project
                </label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => handleSelectProject(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] font-medium focus:outline-none focus:border-purple-500 transition-colors"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.slug}) — {p.status}
                    </option>
                  ))}
                </select>
              </div>

              <form onSubmit={handleBuildApp} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                      Android App Name
                    </label>
                    <input
                      type="text"
                      required
                      value={appName}
                      onChange={(e) => setAppName(e.target.value)}
                      placeholder="My Mobile App"
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

                {/* Device Permissions */}
                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-2">
                    Native Device Permissions
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
                  disabled={isBuildingApp || !selectedProjectId}
                  className="w-full flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg bg-purple-600 text-white font-semibold text-xs hover:bg-purple-500 transition-colors disabled:opacity-50 shadow-sm"
                >
                  {isBuildingApp ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Compiling Android APK in Sandbox...</span>
                    </>
                  ) : (
                    <>
                      <Smartphone className="w-4 h-4" />
                      <span>Build Native Android Package</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Build Result & Terminal */}
            {mobileBuild && (
              <div className="p-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] space-y-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-[var(--text-secondary)]">Build Status:</span>
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

                <TerminalViewer
                  logs={mobileLogs}
                  title="Android Gradle & APK Pipeline"
                  isStreaming={isBuildingApp}
                />
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
                    <span>Select a deployed project to view live mobile simulator</span>
                  </div>
                )}
              </div>

              {/* Home indicator bar */}
              <div className="w-24 h-1 bg-zinc-600 rounded-full mx-auto my-2 shrink-0"></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
