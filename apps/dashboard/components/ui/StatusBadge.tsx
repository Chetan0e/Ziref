import React from 'react';

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  let color = 'bg-zinc-800 text-zinc-300 border-zinc-700';

  if (['READY', 'DEPLOYED', 'BUILT', 'APP_READY'].includes(status)) {
    color = 'bg-emerald-950/60 text-emerald-400 border-emerald-800';
  } else if (['BUILDING', 'DEPLOYING', 'QUEUED', 'PREPARING', 'APP_BUILDING', 'APP_CONFIGURING', 'ANALYZING'].includes(status)) {
    color = 'bg-amber-950/60 text-amber-400 border-amber-800 animate-pulse';
  } else if (['FAILED', 'BUILD_FAILED', 'DEPLOY_FAILED', 'APP_FAILED'].includes(status)) {
    color = 'bg-rose-950/60 text-rose-400 border-rose-800';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${color}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      {status}
    </span>
  );
}
