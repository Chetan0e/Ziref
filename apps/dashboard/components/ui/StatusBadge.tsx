import React from 'react';
import { getStatusPresentation } from '@/lib/status';

interface StatusBadgeProps {
  status: string | null | undefined;
  showIcon?: boolean;
  className?: string;
}

export function StatusBadge({ status, showIcon = true, className = '' }: StatusBadgeProps) {
  const presentation = getStatusPresentation(status);
  const Icon = presentation.icon;

  return (
    <span
      title={presentation.description}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors ${presentation.badgeClass} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${presentation.dotClass}`} />
      <span className="truncate">{presentation.label}</span>
    </span>
  );
}
