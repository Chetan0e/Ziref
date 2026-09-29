'use client';

import React, { useEffect, useState, useRef } from 'react';
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
  Image as ImageIcon,
  UploadCloud,
  X,
  Trash2,
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
  const [appLogo, setAppLogo] = useState<string | null>(null);
  const [logoFileName, setLogoFileName] = useState<string>('');
  const [simulatorView, setSimulatorView] = useState<'app' | 'home'>('app');
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleLogoFile = (file: File) => {
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

  const handleRemoveLogo = () => {
    setAppLogo(null);
    setLogoFileName('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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
        icon_base64: appLogo || undefined,
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
    selectedProject && (selectedProject.active_deployment_id || selectedProject.status === 'DEPLOYED' || selectedProject.active_url)
      ? selectedProject.active_url || (selectedProject.slug ? api.getPreviewUrl(selectedProject.slug) : null)
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
                        onClick={handleRemoveLogo}
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
                      onClick={() => fileInputRef.current?.click()}
                      onDragOver={(e) => { e.preventDefault(); }}
                      onDrop={(e) => {
                        e.preventDefault();
                        if (e.dataTransfer.files?.[0]) {
                          handleLogoFile(e.dataTransfer.files[0]);
                        }
                      }}
                      className="flex-1 w-full p-3.5 border-2 border-dashed border-[var(--border)] hover:border-purple-500/60 rounded-xl cursor-pointer bg-[var(--surface)] hover:bg-[var(--surface-hover)] transition-all flex flex-col items-center justify-center text-center group"
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/png,image/jpeg,image/webp,image/svg+xml"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files?.[0]) {
                            handleLogoFile(e.target.files[0]);
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
                    {/* Warning if target URL is localhost */}
                    {mobileBuild.apk_url_is_localhost && (
                      <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-600 dark:text-amber-400 flex items-start gap-2.5">
                        <Shield className="w-4 h-4 shrink-0 mt-0.5 text-amber-500" />
                        <div>
                          <div className="font-semibold">Localhost Target Warning</div>
                          <div className="text-[11px] opacity-90 mt-0.5 leading-relaxed">
                            This APK embeds a local development URL ({mobileBuild.apk_target_url || 'localhost'}). On a physical Android device, &quot;localhost&quot; refers to the phone itself. To connect from your mobile device, ensure your phone is connected to the same Wi-Fi network and deploy with your computer&apos;s local IP address or a public domain.
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="flex flex-wrap items-center gap-3">
                      <a
                        href={api.getMobileApkDownloadUrl(mobileBuild.id)}
                        download={mobileBuild.apk_filename || undefined}
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 transition-colors shadow-sm"
                      >
                        <Download className="w-4 h-4" />
                        <span>Download {mobileBuild.apk_filename || 'Android APK (.apk)'}</span>
                      </a>
                      <a
                        href={api.getMobileSourceDownloadUrl(mobileBuild.id)}
                        download
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] text-[var(--text-primary)] text-xs font-semibold hover:bg-[var(--surface-hover)] transition-colors shadow-sm"
                      >
                        <Download className="w-4 h-4" />
                        <span>Download Project Source (.zip)</span>
                      </a>
                    </div>

                    {/* Artifact Details & ADB Command */}
                    <div className="p-4 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)] space-y-3 font-mono text-xs">
                      {mobileBuild.apk_package_name && (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pb-3 border-b border-[var(--border)] text-[11px]">
                          <div>
                            <span className="text-[var(--text-muted)] block text-[10px] uppercase font-sans">Package</span>
                            <span className="text-[var(--text-primary)] font-mono">{mobileBuild.apk_package_name}</span>
                          </div>
                          <div>
                            <span className="text-[var(--text-muted)] block text-[10px] uppercase font-sans">Version</span>
                            <span className="text-[var(--text-primary)] font-mono">v{mobileBuild.apk_version_name || '1.0.0'} ({mobileBuild.apk_version_code || 1})</span>
                          </div>
                          <div>
                            <span className="text-[var(--text-muted)] block text-[10px] uppercase font-sans">File Size</span>
                            <span className="text-[var(--text-primary)] font-mono">
                              {mobileBuild.apk_size_bytes ? `${(mobileBuild.apk_size_bytes / 1024).toFixed(1)} KB` : '—'}
                            </span>
                          </div>
                        </div>
                      )}

                      {mobileBuild.apk_sha256 && (
                        <div className="pb-2 border-b border-[var(--border)]">
                          <span className="text-[var(--text-muted)] block text-[10px] uppercase font-sans mb-1">SHA-256 Checksum</span>
                          <span className="text-[10px] text-[var(--text-secondary)] font-mono break-all block bg-black/30 p-1.5 rounded select-all">
                            {mobileBuild.apk_sha256}
                          </span>
                        </div>
                      )}

                      <div className="flex items-center justify-between">
                        <span className="text-[var(--text-muted)] text-[11px]">Install on Device via ADB:</span>
                        <button
                          onClick={() =>
                            copyToClipboard(`adb install ${mobileBuild.apk_filename || `app-debug-${mobileBuild.id}.apk`}`, 'adb')
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
                        adb install {mobileBuild.apk_filename || `app-debug-${mobileBuild.id}.apk`}
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
            <div className="flex items-center justify-between w-[300px] mb-2 px-1">
              <span className="text-xs text-[var(--text-secondary)] font-medium">
                Native Phone Preview
              </span>
              <div className="inline-flex rounded-lg bg-[var(--surface-muted)] p-0.5 border border-[var(--border)] text-[10px]">
                <button
                  type="button"
                  onClick={() => setSimulatorView('app')}
                  className={`px-2 py-0.5 rounded-md font-medium transition-colors ${
                    simulatorView === 'app'
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  App View
                </button>
                <button
                  type="button"
                  onClick={() => setSimulatorView('home')}
                  className={`px-2 py-0.5 rounded-md font-medium transition-colors ${
                    simulatorView === 'home'
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  Home Screen
                </button>
              </div>
            </div>

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

              {/* In-Phone Screen Content */}
              <div className="flex-1 w-full mt-2 bg-zinc-950 overflow-hidden relative">
                {simulatorView === 'home' ? (
                  <div className="w-full h-full bg-gradient-to-b from-indigo-950/60 via-zinc-950 to-zinc-950 p-6 flex flex-col justify-between select-none">
                    {/* Clock & Widget */}
                    <div className="text-center pt-8">
                      <div className="text-4xl font-light text-white tracking-tight">09:41</div>
                      <div className="text-xs text-zinc-400 mt-1">Monday, September 28</div>
                    </div>

                    {/* App Grid with Custom App Icon */}
                    <div className="grid grid-cols-4 gap-4 pb-12">
                      {/* User's Mobile App */}
                      <div className="flex flex-col items-center gap-1.5 group cursor-pointer" onClick={() => setSimulatorView('app')}>
                        <div className="w-12 h-12 rounded-2xl bg-zinc-800 border border-white/10 overflow-hidden shadow-lg flex items-center justify-center relative ring-2 ring-purple-500/50">
                          {appLogo ? (
                            <img src={appLogo} alt="App Icon" className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-white font-bold text-base">
                              {appName ? appName[0].toUpperCase() : 'Z'}
                            </div>
                          )}
                        </div>
                        <span className="text-[10px] text-zinc-200 text-center font-medium truncate max-w-[56px]">
                          {appName || 'App'}
                        </span>
                      </div>

                      {/* Mock System Apps */}
                      <div className="flex flex-col items-center gap-1.5 opacity-60">
                        <div className="w-12 h-12 rounded-2xl bg-emerald-600 flex items-center justify-center text-white text-xs font-semibold shadow">
                          📞
                        </div>
                        <span className="text-[10px] text-zinc-400">Phone</span>
                      </div>

                      <div className="flex flex-col items-center gap-1.5 opacity-60">
                        <div className="w-12 h-12 rounded-2xl bg-sky-600 flex items-center justify-center text-white text-xs font-semibold shadow">
                          💬
                        </div>
                        <span className="text-[10px] text-zinc-400">Messages</span>
                      </div>

                      <div className="flex flex-col items-center gap-1.5 opacity-60">
                        <div className="w-12 h-12 rounded-2xl bg-amber-600 flex items-center justify-center text-white text-xs font-semibold shadow">
                          ⚙️
                        </div>
                        <span className="text-[10px] text-zinc-400">Settings</span>
                      </div>
                    </div>
                  </div>
                ) : previewUrl ? (
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
