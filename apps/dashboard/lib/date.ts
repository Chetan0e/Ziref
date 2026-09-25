/**
 * Shared Date & Time formatting utilities for Ziref
 * Handles null, undefined, invalid dates, timezone conversion, ISO strings, timestamps.
 * Guarantees that "Invalid Date" will NEVER be displayed to the user.
 */

export function parseSafeDate(input: string | number | Date | null | undefined): Date | null {
  if (!input) return null;
  if (input instanceof Date) {
    return isNaN(input.getTime()) ? null : input;
  }

  if (typeof input === 'number') {
    // If timestamp in seconds, convert to milliseconds
    const ms = input < 10000000000 ? input * 1000 : input;
    const d = new Date(ms);
    return isNaN(d.getTime()) ? null : d;
  }

  if (typeof input === 'string') {
    let clean = input.trim();
    if (!clean) return null;

    // Handle malformed ISO strings such as "...+00:00Z"
    if (clean.endsWith('+00:00Z')) {
      clean = clean.replace('+00:00Z', 'Z');
    } else if (clean.match(/\+\d{2}:\d{2}Z$/)) {
      clean = clean.replace(/Z$/, '');
    }

    const d = new Date(clean);
    if (!isNaN(d.getTime())) {
      return d;
    }

    // Try parsing as number if string is numeric timestamp
    const num = Number(clean);
    if (!isNaN(num) && num > 0) {
      const ms = num < 10000000000 ? num * 1000 : num;
      const dNum = new Date(ms);
      if (!isNaN(dNum.getTime())) return dNum;
    }
  }

  return null;
}

/**
 * Formats a date nicely. Never returns "Invalid Date".
 */
export function formatDate(
  input: string | number | Date | null | undefined,
  format: 'date' | 'datetime' | 'relative' | 'time' = 'date',
  fallback: string = '—'
): string {
  const date = parseSafeDate(input);
  if (!date) return fallback;

  if (format === 'relative') {
    return formatRelativeTime(date, fallback);
  }

  try {
    if (format === 'time') {
      return new Intl.DateTimeFormat('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      }).format(date);
    }

    if (format === 'datetime') {
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      }).format(date);
    }

    // Default 'date'
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  } catch (_) {
    return fallback;
  }
}

/**
 * Returns human-readable relative time (e.g. "just now", "2 minutes ago", "yesterday")
 */
export function formatRelativeTime(
  input: string | number | Date | null | undefined,
  fallback: string = '—'
): string {
  const date = parseSafeDate(input);
  if (!date) return fallback;

  const now = Date.now();
  const diffMs = now - date.getTime();

  // Future date check
  if (diffMs < -2000) {
    return formatDate(date, 'date', fallback);
  }

  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 45) return 'just now';
  if (diffSec < 90) return '1 minute ago';

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} minutes ago`;

  const diffHours = Math.floor(diffMin / 60);
  if (diffHours === 1) return '1 hour ago';
  if (diffHours < 24) return `${diffHours} hours ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;

  return formatDate(date, 'date', fallback);
}

/**
 * Formats a duration in seconds to "41s" or "2m 15s"
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || isNaN(seconds) || seconds < 0) return '—';
  const sec = Math.round(seconds);
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}
