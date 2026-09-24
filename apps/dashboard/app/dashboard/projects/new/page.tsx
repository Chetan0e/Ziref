'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { AnalysisResult } from '@ziref/types';
import {
  UploadCloud,
  FileArchive,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  Settings,
  Sparkles,
  GitBranch,
  FolderGit2
} from 'lucide-react';

export default function NewProjectPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [creationMode, setCreationMode] = useState<'upload' | 'git' | 'demo'>('upload');

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
        setError('Only .zip archive files are supported.');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!name) {
        setName(selected.name.replace(/\.zip$/i, ''));
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
        setBuildCommand(uploadRes.analysis.buildCommand || 'npm run build');
        setOutputDirectory(uploadRes.analysis.outputDirectory || 'dist');
      }

      setUploadProgress(null);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze project archive.');
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
    setUploadProgress('Cloning and analyzing Git repository...');

    try {
      const res = await api.importGitProject(projName, gitUrl.trim(), gitBranch.trim() || 'main', slug.trim() || undefined);
      router.push(`/dashboard/projects/${res.project_id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to import Git repository.');
      setIsUploading(false);
    }
  };

  const handleStartDeployment = async () => {
    if (!projectId || !uploadId) return;

    setIsUploading(true);
    setUploadProgress('Queueing build worker...');

    try {
      await api.triggerBuild(projectId, uploadId, buildCommand, outputDirectory);
      router.push(`/dashboard/projects/${projectId}`);
    } catch (err: any) {
      setError(err.message || 'Failed to start build.');
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Create New Project</h1>
        <p className="text-xs text-zinc-400 mt-1">Deploy web applications to production and mobile in minutes</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-rose-950/50 border border-rose-900 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Method Selector Tabs */}
      {!analysis && (
        <div className="flex p-1 bg-zinc-900 rounded-xl border border-zinc-800">
          <button
            onClick={() => setCreationMode('upload')}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-colors ${
              creationMode === 'upload' ? 'bg-zinc-800 text-white shadow' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <UploadCloud className="w-4 h-4" /> Upload ZIP
          </button>
          <button
            onClick={() => setCreationMode('git')}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-colors ${
              creationMode === 'git' ? 'bg-zinc-800 text-white shadow' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <FolderGit2 className="w-4 h-4" /> Git Repository
          </button>
          <button
            onClick={() => setCreationMode('demo')}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-colors ${
              creationMode === 'demo' ? 'bg-zinc-800 text-amber-400 shadow' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Sparkles className="w-4 h-4" /> 1-Click React Demo
          </button>
        </div>
      )}

      {/* 1-Click Demo Option */}
      {!analysis && creationMode === 'demo' && (
        <div className="p-6 rounded-xl border border-amber-900/60 bg-amber-950/20 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Bundled React 18 + Vite Sample App</h3>
              <p className="text-xs text-zinc-400">Instantly deploy a production-grade TypeScript React app with hot reloading and counter widget.</p>
            </div>
          </div>
          <button
            onClick={async () => {
              setIsUploading(true);
              setUploadProgress('Setting up demo project...');
              try {
                const res = await api.createDemoProject();
                router.push(`/dashboard/projects/${res.project_id}`);
              } catch (e: any) {
                setError(e.message);
                setIsUploading(false);
              }
            }}
            disabled={isUploading}
            className="w-full px-5 py-2.5 rounded-lg bg-amber-500 text-black text-xs font-bold hover:bg-amber-400 transition-colors shadow-lg flex items-center justify-center gap-2"
          >
            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            <span>Deploy Sample Project Now</span>
          </button>
        </div>
      )}

      {/* Git Repository Import Option */}
      {!analysis && creationMode === 'git' && (
        <form onSubmit={handleGitImport} className="space-y-6 bg-zinc-950 border border-zinc-800 rounded-xl p-6 shadow-xl">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">Git Repository URL</label>
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
                placeholder="https://github.com/vitejs/vite or public repo URL"
                className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 font-mono focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Project Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. my-vite-app"
                  className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Branch</label>
                <div className="flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg">
                  <GitBranch className="w-4 h-4 text-zinc-500 shrink-0" />
                  <input
                    type="text"
                    value={gitBranch}
                    onChange={(e) => setGitBranch(e.target.value)}
                    placeholder="main"
                    className="w-full bg-transparent text-xs text-white placeholder-zinc-500 focus:outline-none font-mono"
                  />
                </div>
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={isUploading || !gitUrl}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors disabled:opacity-50"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{uploadProgress || 'Cloning repository...'}</span>
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

      {/* ZIP Upload Option */}
      {!analysis && creationMode === 'upload' && (
        <div className="space-y-6 bg-zinc-950 border border-zinc-800 rounded-xl p-6 shadow-xl">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">Project Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. my-awesome-app"
                className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">Custom Slug (Optional)</label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="e.g. my-awesome-app"
                className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-sky-500 font-mono"
              />
            </div>
          </div>

          {/* Drag & Drop Upload Box */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Project Source Archive (.ZIP)</label>
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                dragActive ? 'border-sky-500 bg-sky-950/20' : 'border-zinc-800 hover:border-zinc-700 bg-zinc-900/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                onChange={handleFileChange}
                className="hidden"
              />
              <UploadCloud className="w-10 h-10 text-zinc-500 mx-auto mb-3" />
              {file ? (
                <div className="flex items-center justify-center gap-2 text-sky-400 font-medium text-xs">
                  <FileArchive className="w-4 h-4" />
                  <span>{file.name}</span>
                  <span className="text-zinc-500">({(file.size / (1024 * 1024)).toFixed(2)} MB)</span>
                </div>
              ) : (
                <>
                  <p className="text-xs text-zinc-300 font-medium">Click to upload or drag & drop project ZIP</p>
                  <p className="text-[11px] text-zinc-500 mt-1">Supports Vite, React, Next.js, Vue, Angular, Node.js, and static HTML (up to 50MB)</p>
                </>
              )}
            </div>
          </div>

          <button
            onClick={handleUploadAndAnalyze}
            disabled={isUploading || !file || !name}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors disabled:opacity-50"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{uploadProgress || 'Processing...'}</span>
              </>
            ) : (
              <>
                <span>Analyze Project</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      )}

      {/* Step 2: Analyzer Review & Build Launch (For ZIP Upload Flow) */}
      {analysis && (
        <div className="space-y-6 bg-zinc-950 border border-zinc-800 rounded-xl p-6 shadow-xl">
          <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
            <CheckCircle2 className="w-5 h-5" />
            <span>Project Detected Successfully</span>
          </div>

          {/* Analysis Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
            <div className="p-3 bg-zinc-900 rounded-lg border border-zinc-800">
              <span className="text-zinc-500 text-[10px] block">FRAMEWORK</span>
              <span className="font-bold text-white capitalize">{analysis.framework}</span>
            </div>
            <div className="p-3 bg-zinc-900 rounded-lg border border-zinc-800">
              <span className="text-zinc-500 text-[10px] block">LANGUAGE</span>
              <span className="font-bold text-white capitalize">{analysis.language}</span>
            </div>
            <div className="p-3 bg-zinc-900 rounded-lg border border-zinc-800">
              <span className="text-zinc-500 text-[10px] block">PACKAGE MANAGER</span>
              <span className="font-bold text-white uppercase">{analysis.packageManager}</span>
            </div>
            <div className="p-3 bg-zinc-900 rounded-lg border border-zinc-800">
              <span className="text-zinc-500 text-[10px] block">RUNTIME</span>
              <span className="font-bold text-sky-400 capitalize">{analysis.runtime}</span>
            </div>
          </div>

          {/* Overrides Configuration */}
          <div className="space-y-3 pt-4 border-t border-zinc-800">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-300">
              <Settings className="w-4 h-4 text-zinc-500" />
              <span>Build Configuration</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Build Command</label>
                <input
                  type="text"
                  value={buildCommand}
                  onChange={(e) => setBuildCommand(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Output Directory</label>
                <input
                  type="text"
                  value={outputDirectory}
                  onChange={(e) => setOutputDirectory(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-white font-mono"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 flex items-center justify-between gap-4">
            <button
              onClick={() => setAnalysis(null)}
              className="px-4 py-2 rounded-lg border border-zinc-800 text-zinc-400 hover:text-white text-xs"
            >
              Back
            </button>
            <button
              onClick={handleStartDeployment}
              disabled={isUploading}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-sky-500 text-black font-semibold text-xs hover:bg-sky-400 transition-colors shadow-lg"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Starting Sandbox Build...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Deploy Project</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
