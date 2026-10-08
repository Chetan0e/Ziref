'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, ApiError } from '@/lib/api';
import { AnalysisResult } from '@ziref/types';
import { useToast } from '@/lib/toast';
import {
  UploadCloud,
  FileArchive,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Settings,
  GitBranch,
  FolderGit2,
  Terminal,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react';

export default function NewProjectPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addToast } = useToast();

  const [creationMode, setCreationMode] = useState<'upload' | 'git'>('upload');

  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // Git state
  const [gitUrl, setGitUrl] = useState('');
  const [gitBranch, setGitBranch] = useState('main');

  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Editable overrides
  const [buildCommand, setBuildCommand] = useState('');
  const [outputDirectory, setOutputDirectory] = useState('');

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.zip')) {
        setFile(droppedFile);
        if (!name) {
          setName(droppedFile.name.replace(/\.zip$/i, ''));
        }
      } else {
        setError('Only .zip source archive files are supported.');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.name.endsWith('.zip')) {
        setFile(selected);
        if (!name) {
          setName(selected.name.replace(/\.zip$/i, ''));
        }
      } else {
        setError('Only .zip source archive files are supported.');
      }
    }
  };

  const handleUploadAndAnalyze = async () => {
    if (!name.trim()) {
      setError('Please provide a project name.');
      return;
    }
    if (!file) {
      setError('Please select a project ZIP file to upload.');
      return;
    }

    setError(null);
    setIsUploading(true);
    setUploadProgress('Creating project workspace...');

    try {
      // 1. Create Project
      const project = await api.createProject(name.trim(), slug.trim() || undefined);
      setProjectId(project.id);

      // 2. Upload and automatically analyze
      setUploadProgress('Uploading and analyzing project structure...');
      const uploadRes = await api.uploadZip(project.id, file);

      setUploadId(uploadRes.id);
      if (uploadRes.analysis) {
        setAnalysis(uploadRes.analysis);
        setBuildCommand(uploadRes.analysis.buildCommand || '');
        setOutputDirectory(uploadRes.analysis.outputDirectory || '.');
      }

      setUploadProgress(null);
      addToast({
        title: 'Project analyzed',
        description: `Identified ${uploadRes.analysis?.framework || 'detected'} project structure.`,
        type: 'success',
      });
    } catch (err: any) {
      const msg = err.message || 'Failed to analyze project archive.';
      setError(msg);
      addToast({
        title: 'Upload failed',
        description: msg,
        type: 'error',
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleGitImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gitUrl.trim()) {
      setError('Please provide a valid Git repository URL.');
      return;
    }

    const projName = name.trim() || gitUrl.split('/').pop()?.replace('.git', '') || 'git-project';
    setError(null);
    setIsUploading(true);
    setUploadProgress('Cloning repository and inspecting build manifest...');

    try {
      const res = await api.importGitProject(projName, gitUrl.trim(), gitBranch.trim() || undefined, slug.trim() || undefined);
      addToast({
        title: 'Git import initialized',
        description: 'Cloning repository and initiating pipeline.',
        type: 'success',
      });
      router.push(`/dashboard/projects/${res.project_id}`);
    } catch (err: any) {
      const msg = err.message || 'Failed to import Git repository.';
      setError(msg);
      addToast({
        title: 'Git import failed',
        description: msg,
        type: 'error',
      });
      setIsUploading(false);
    }
  };

  const handleStartDeployment = async () => {
    if (!projectId || !uploadId) return;

    setIsUploading(true);
    setUploadProgress('Queueing isolated sandbox worker...');

    try {
      await api.triggerBuild(projectId, uploadId, buildCommand, outputDirectory);
      addToast({
        title: 'Build scheduled',
        description: 'Build job queued on isolated worker.',
        type: 'success',
      });
      router.push(`/dashboard/projects/${projectId}`);
    } catch (err: any) {
      const msg = err.message || 'Failed to start build.';
      setError(msg);
      addToast({
        title: 'Build trigger failed',
        description: msg,
        type: 'error',
      });
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Top Breadcrumb & Heading */}
      <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
        <div>
          <Link
            href="/dashboard/projects"
            className="inline-flex items-center gap-1 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-1 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Projects
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Create New Project
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Deploy web applications and compile mobile packages in isolated environments
          </p>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold block mb-0.5">Deployment Configuration Error</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Creation Mode Tabs */}
      {!analysis && (
        <div className="flex p-1 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)]">
          <button
            onClick={() => {
              setCreationMode('upload');
              setError(null);
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-colors ${
              creationMode === 'upload'
                ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-sm border border-[var(--border)]'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <UploadCloud className="w-4 h-4 text-sky-500" />
            <span>Upload ZIP Archive</span>
          </button>
          <button
            onClick={() => {
              setCreationMode('git');
              setError(null);
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-colors ${
              creationMode === 'git'
                ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-sm border border-[var(--border)]'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <FolderGit2 className="w-4 h-4 text-purple-500" />
            <span>Git Repository</span>
          </button>
        </div>
      )}

      {/* Method 1: Git Repository Import */}
      {!analysis && creationMode === 'git' && (
        <form
          onSubmit={handleGitImport}
          className="space-y-6 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-sm"
        >
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                Git Repository URL
              </label>
              <input
                type="url"
                required
                value={gitUrl}
                onChange={(e) => {
                  setGitUrl(e.target.value);
                  if (!name) {
                    const extracted = e.target.value.split('/').pop()?.replace('.git', '');
                    if (extracted) setName(extracted);
                  }
                }}
                placeholder="https://github.com/org/repo or public git url"
                className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] font-mono focus:outline-none focus:border-sky-500 transition-colors"
              />
              <p className="text-[11px] text-[var(--text-muted)] mt-1">
                Supports public HTTPS repository links.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                  Project Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. my-app"
                  className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-sky-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                  Branch
                </label>
                <div className="flex items-center gap-2 px-3 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg">
                  <GitBranch className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
                  <input
                    type="text"
                    value={gitBranch}
                    onChange={(e) => setGitBranch(e.target.value)}
                    placeholder="main"
                    className="w-full bg-transparent text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none font-mono"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                Custom Slug (Optional)
              </label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="e.g. my-app"
                className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-sky-500 font-mono transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isUploading || !gitUrl}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors disabled:opacity-50 shadow-sm"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{uploadProgress || 'Cloning and deploying...'}</span>
              </>
            ) : (
              <>
                <span>Clone & Deploy Repository</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      )}

      {/* Method 2: ZIP Upload */}
      {!analysis && creationMode === 'upload' && (
        <div className="space-y-6 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                Project Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. ecommerce-frontend"
                className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-sky-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                Custom Subdomain / Slug (Optional)
              </label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="e.g. ecommerce-store"
                className="w-full px-3.5 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-sky-500 font-mono transition-colors"
              />
            </div>
          </div>

          {/* Drag & Drop Upload Zone */}
          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
              Source Code Archive (.ZIP)
            </label>
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                dragActive
                  ? 'border-sky-500 bg-sky-500/10'
                  : 'border-[var(--border)] hover:border-zinc-500 bg-[var(--surface-muted)]'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                onChange={handleFileChange}
                className="hidden"
              />
              <UploadCloud className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3" />
              {file ? (
                <div className="flex items-center justify-center gap-2 text-sky-500 font-medium text-xs">
                  <FileArchive className="w-4 h-4" />
                  <span>{file.name}</span>
                  <span className="text-[var(--text-muted)] font-mono">
                    ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                </div>
              ) : (
                <>
                  <p className="text-xs text-[var(--text-primary)] font-medium">
                    Click to select or drag & drop your project ZIP file
                  </p>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-1">
                    Supports Vite, React, Next.js, Vue, Angular, Node.js, and static HTML (max 50MB)
                  </p>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-xs text-[var(--text-secondary)]">
            <Info className="w-4 h-4 text-sky-500 shrink-0" />
            <span>
              Ziref automatically inspects your <code>package.json</code> or index files, detects framework and dependencies, and provisions the optimal build runtime.
            </span>
          </div>

          <button
            onClick={handleUploadAndAnalyze}
            disabled={isUploading || !file || !name}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors disabled:opacity-50 shadow-sm"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{uploadProgress || 'Processing...'}</span>
              </>
            ) : (
              <>
                <span>Upload & Analyze Project</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      )}

      {/* Step 2: Analyzer Review & Build Launch (For ZIP Upload Flow) */}
      {analysis && (
        <div className="space-y-6 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 text-emerald-500 font-semibold text-sm">
            <CheckCircle2 className="w-5 h-5" />
            <span>Stack Analyzed & Verified</span>
          </div>

          {/* Analysis Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
            <div className="p-3 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)]">
              <span className="text-[var(--text-muted)] text-[10px] block">FRAMEWORK</span>
              <span className="font-bold text-[var(--text-primary)] capitalize">
                {analysis.framework}
              </span>
            </div>
            <div className="p-3 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)]">
              <span className="text-[var(--text-muted)] text-[10px] block">LANGUAGE</span>
              <span className="font-bold text-[var(--text-primary)] capitalize">
                {analysis.language}
              </span>
            </div>
            <div className="p-3 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)]">
              <span className="text-[var(--text-muted)] text-[10px] block">PACKAGE MANAGER</span>
              <span className="font-bold text-[var(--text-primary)] uppercase">
                {analysis.packageManager}
              </span>
            </div>
            <div className="p-3 bg-[var(--surface-muted)] rounded-lg border border-[var(--border)]">
              <span className="text-[var(--text-muted)] text-[10px] block">RUNTIME</span>
              <span className="font-bold text-sky-500 capitalize">{analysis.runtime}</span>
            </div>
          </div>

          {/* Overrides Configuration */}
          <div className="space-y-3 pt-4 border-t border-[var(--border)]">
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
              <Settings className="w-4 h-4 text-sky-500" />
              <span>Build & Output Configuration</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Build Command (Optional for static apps)
                </label>
                <input
                  type="text"
                  value={buildCommand}
                  placeholder="None (Static application)"
                  onChange={(e) => setBuildCommand(e.target.value)}
                  className="w-full px-3 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] font-mono focus:outline-none focus:border-sky-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Output Directory
                </label>
                <input
                  type="text"
                  value={outputDirectory}
                  placeholder="."
                  onChange={(e) => setOutputDirectory(e.target.value)}
                  className="w-full px-3 py-2 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-xs text-[var(--text-primary)] font-mono focus:outline-none focus:border-sky-500 transition-colors"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 flex items-center justify-between gap-4">
            <button
              onClick={() => setAnalysis(null)}
              className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs transition-colors"
            >
              Back
            </button>
            <button
              onClick={handleStartDeployment}
              disabled={isUploading}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors shadow-sm disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Queueing Sandbox Build...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Deploy to Production</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
