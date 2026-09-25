import React from 'react';
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Radio,
  FileCode,
  Package,
  Layers,
  Smartphone,
  Check
} from 'lucide-react';

export type StatusCategory = 'queued' | 'running' | 'success' | 'failed' | 'neutral';

export interface StatusPresentation {
  key: string;
  label: string;
  category: StatusCategory;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  badgeClass: string;
  dotClass: string;
  textClass: string;
  availableActions: ('view' | 'logs' | 'retry' | 'rollback' | 'deploy' | 'appify')[];
}

const statusMap: Record<string, StatusPresentation> = {
  // --- Project & Build states ---
  CREATED: {
    key: 'CREATED',
    label: 'Created',
    category: 'neutral',
    description: 'Project initialized, awaiting source upload',
    icon: FileCode,
    badgeClass: 'bg-zinc-100 text-zinc-700 border-zinc-200 dark:bg-zinc-800/80 dark:text-zinc-300 dark:border-zinc-700',
    dotClass: 'bg-zinc-400',
    textClass: 'text-zinc-600 dark:text-zinc-400',
    availableActions: ['deploy', 'view'],
  },
  UPLOADING: {
    key: 'UPLOADING',
    label: 'Uploading',
    category: 'running',
    description: 'Source archive is uploading',
    icon: Loader2,
    badgeClass: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
    dotClass: 'bg-blue-500 animate-pulse',
    textClass: 'text-blue-600 dark:text-blue-400',
    availableActions: ['view'],
  },
  UPLOADED: {
    key: 'UPLOADED',
    label: 'Uploaded',
    category: 'neutral',
    description: 'Source archive uploaded successfully',
    icon: Package,
    badgeClass: 'bg-zinc-100 text-zinc-700 border-zinc-200 dark:bg-zinc-800/80 dark:text-zinc-300 dark:border-zinc-700',
    dotClass: 'bg-zinc-400',
    textClass: 'text-zinc-600 dark:text-zinc-400',
    availableActions: ['deploy', 'view'],
  },
  ANALYZING: {
    key: 'ANALYZING',
    label: 'Analyzing',
    category: 'running',
    description: 'Detecting framework, language, and dependencies',
    icon: Loader2,
    badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800',
    dotClass: 'bg-indigo-500 animate-pulse',
    textClass: 'text-indigo-600 dark:text-indigo-400',
    availableActions: ['view'],
  },
  ANALYZED: {
    key: 'ANALYZED',
    label: 'Analyzed',
    category: 'neutral',
    description: 'Framework identified and ready for build',
    icon: CheckCircle2,
    badgeClass: 'bg-zinc-100 text-zinc-700 border-zinc-200 dark:bg-zinc-800/80 dark:text-zinc-300 dark:border-zinc-700',
    dotClass: 'bg-zinc-400',
    textClass: 'text-zinc-600 dark:text-zinc-400',
    availableActions: ['deploy', 'view'],
  },
  BUILD_QUEUED: {
    key: 'BUILD_QUEUED',
    label: 'Queued',
    category: 'queued',
    description: 'Waiting for available build sandbox worker',
    icon: Clock,
    badgeClass: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800',
    dotClass: 'bg-amber-500 animate-pulse',
    textClass: 'text-amber-600 dark:text-amber-400',
    availableActions: ['logs', 'view'],
  },
  QUEUED: {
    key: 'QUEUED',
    label: 'Queued',
    category: 'queued',
    description: 'Build job waiting in dispatch queue',
    icon: Clock,
    badgeClass: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800',
    dotClass: 'bg-amber-500 animate-pulse',
    textClass: 'text-amber-600 dark:text-amber-400',
    availableActions: ['logs', 'view'],
  },
  PREPARING: {
    key: 'PREPARING',
    label: 'Preparing',
    category: 'running',
    description: 'Allocating container filesystem and sandbox environment',
    icon: Loader2,
    badgeClass: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800',
    dotClass: 'bg-sky-500 animate-pulse',
    textClass: 'text-sky-600 dark:text-sky-400',
    availableActions: ['logs', 'view'],
  },
  BUILDING: {
    key: 'BUILDING',
    label: 'Building',
    category: 'running',
    description: 'Installing packages and compiling production assets',
    icon: Loader2,
    badgeClass: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
    dotClass: 'bg-blue-500 animate-pulse',
    textClass: 'text-blue-600 dark:text-blue-400',
    availableActions: ['logs', 'view'],
  },
  BUILT: {
    key: 'BUILT',
    label: 'Built',
    category: 'neutral',
    description: 'Artifact generated and verified successfully',
    icon: CheckCircle2,
    badgeClass: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800',
    dotClass: 'bg-sky-500',
    textClass: 'text-sky-600 dark:text-sky-400',
    availableActions: ['logs', 'deploy', 'view'],
  },
  BUILD_FAILED: {
    key: 'BUILD_FAILED',
    label: 'Build failed',
    category: 'failed',
    description: 'Build command exited with an error code',
    icon: XCircle,
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-900',
    dotClass: 'bg-rose-500',
    textClass: 'text-rose-600 dark:text-rose-400',
    availableActions: ['logs', 'retry', 'view'],
  },
  FAILED: {
    key: 'FAILED',
    label: 'Failed',
    category: 'failed',
    description: 'Task failed during execution',
    icon: XCircle,
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-900',
    dotClass: 'bg-rose-500',
    textClass: 'text-rose-600 dark:text-rose-400',
    availableActions: ['logs', 'retry', 'view'],
  },
  CANCELLED: {
    key: 'CANCELLED',
    label: 'Cancelled',
    category: 'neutral',
    description: 'Job was cancelled by user',
    icon: AlertTriangle,
    badgeClass: 'bg-zinc-100 text-zinc-700 border-zinc-200 dark:bg-zinc-800/80 dark:text-zinc-300 dark:border-zinc-700',
    dotClass: 'bg-zinc-400',
    textClass: 'text-zinc-600 dark:text-zinc-400',
    availableActions: ['retry', 'view'],
  },

  // --- Deployment states ---
  DEPLOY_QUEUED: {
    key: 'DEPLOY_QUEUED',
    label: 'Deploy queued',
    category: 'queued',
    description: 'Waiting for edge router propagation',
    icon: Clock,
    badgeClass: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800',
    dotClass: 'bg-amber-500 animate-pulse',
    textClass: 'text-amber-600 dark:text-amber-400',
    availableActions: ['logs', 'view'],
  },
  DEPLOYING: {
    key: 'DEPLOYING',
    label: 'Deploying',
    category: 'running',
    description: 'Extracting assets and configuring edge proxy routes',
    icon: Loader2,
    badgeClass: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800',
    dotClass: 'bg-purple-500 animate-pulse',
    textClass: 'text-purple-600 dark:text-purple-400',
    availableActions: ['logs', 'view'],
  },
  DEPLOYED: {
    key: 'DEPLOYED',
    label: 'Live',
    category: 'success',
    description: 'Application is active and serving traffic',
    icon: Radio,
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800',
    dotClass: 'bg-emerald-500',
    textClass: 'text-emerald-600 dark:text-emerald-400',
    availableActions: ['view', 'appify', 'logs'],
  },
  READY: {
    key: 'READY',
    label: 'Live',
    category: 'success',
    description: 'Deployment is healthy and reachable',
    icon: CheckCircle2,
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800',
    dotClass: 'bg-emerald-500',
    textClass: 'text-emerald-600 dark:text-emerald-400',
    availableActions: ['view', 'appify', 'logs', 'rollback'],
  },
  DEPLOY_FAILED: {
    key: 'DEPLOY_FAILED',
    label: 'Deployment failed',
    category: 'failed',
    description: 'Failed to mount or route deployment assets',
    icon: XCircle,
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-900',
    dotClass: 'bg-rose-500',
    textClass: 'text-rose-600 dark:text-rose-400',
    availableActions: ['logs', 'retry', 'view'],
  },

  // --- Mobile (Appify) states ---
  APP_CREATED: {
    key: 'APP_CREATED',
    label: 'App configured',
    category: 'neutral',
    description: 'Mobile wrapper configured',
    icon: Smartphone,
    badgeClass: 'bg-zinc-100 text-zinc-700 border-zinc-200 dark:bg-zinc-800/80 dark:text-zinc-300 dark:border-zinc-700',
    dotClass: 'bg-zinc-400',
    textClass: 'text-zinc-600 dark:text-zinc-400',
    availableActions: ['view'],
  },
  APP_QUEUED: {
    key: 'APP_QUEUED',
    label: 'App queued',
    category: 'queued',
    description: 'Waiting for mobile builder worker',
    icon: Clock,
    badgeClass: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800',
    dotClass: 'bg-amber-500 animate-pulse',
    textClass: 'text-amber-600 dark:text-amber-400',
    availableActions: ['view'],
  },
  APP_CONFIGURING: {
    key: 'APP_CONFIGURING',
    label: 'Configuring native app',
    category: 'running',
    description: 'Generating Android manifest and native scaffolding',
    icon: Loader2,
    badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800',
    dotClass: 'bg-indigo-500 animate-pulse',
    textClass: 'text-indigo-600 dark:text-indigo-400',
    availableActions: ['view'],
  },
  APP_BUILDING: {
    key: 'APP_BUILDING',
    label: 'Packaging APK',
    category: 'running',
    description: 'Compiling Android APK artifact',
    icon: Loader2,
    badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800',
    dotClass: 'bg-indigo-500 animate-pulse',
    textClass: 'text-indigo-600 dark:text-indigo-400',
    availableActions: ['view'],
  },
  APP_READY: {
    key: 'APP_READY',
    label: 'APK ready',
    category: 'success',
    description: 'Android APK package ready for download',
    icon: CheckCircle2,
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800',
    dotClass: 'bg-emerald-500',
    textClass: 'text-emerald-600 dark:text-emerald-400',
    availableActions: ['view'],
  },
  APP_FAILED: {
    key: 'APP_FAILED',
    label: 'APK build failed',
    category: 'failed',
    description: 'Native bundling encountered an error',
    icon: XCircle,
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-900',
    dotClass: 'bg-rose-500',
    textClass: 'text-rose-600 dark:text-rose-400',
    availableActions: ['retry', 'view'],
  },
};

/**
 * Returns formatted status presentation details for any backend status string.
 */
export function getStatusPresentation(rawStatus: string | null | undefined): StatusPresentation {
  if (!rawStatus) {
    return {
      key: 'UNKNOWN',
      label: 'Unknown',
      category: 'neutral',
      description: 'Status unavailable',
      icon: Clock,
      badgeClass: 'bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700',
      dotClass: 'bg-zinc-400',
      textClass: 'text-zinc-500',
      availableActions: ['view'],
    };
  }

  const normalized = rawStatus.toUpperCase().trim();
  if (statusMap[normalized]) {
    return statusMap[normalized];
  }

  // Graceful fallback for unexpected status values
  const readable = normalized.replace(/_/g, ' ').toLowerCase();
  const label = readable.charAt(0).toUpperCase() + readable.slice(1);

  return {
    key: normalized,
    label,
    category: 'neutral',
    description: `Status: ${label}`,
    icon: Clock,
    badgeClass: 'bg-zinc-100 text-zinc-700 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700',
    dotClass: 'bg-zinc-400',
    textClass: 'text-zinc-600 dark:text-zinc-400',
    availableActions: ['view'],
  };
}
