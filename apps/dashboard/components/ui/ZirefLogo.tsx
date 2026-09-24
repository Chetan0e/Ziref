import React from 'react';

interface ZirefLogoProps {
  size?: number;
  className?: string;
  showText?: boolean;
  textSize?: string;
}

export function ZirefLogo({
  size = 32,
  className = '',
  showText = false,
  textSize = 'text-xl',
}: ZirefLogoProps) {
  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        className="shrink-0"
      >
        {/* Clean geometric Z mark — angular, precise, no gradient soup */}
        <rect width="32" height="32" rx="7" fill="#1D4ED8" />
        {/* Z stroke — top bar */}
        <path
          d="M8 9.5H24L24 11.5H8V9.5Z"
          fill="white"
        />
        {/* Z stroke — diagonal */}
        <path
          d="M22.5 11.5L9.5 20.5H8L21 11.5H22.5Z"
          fill="white"
          fillOpacity="0.6"
        />
        <path
          d="M24 11L9 21.5L8 20.5L23 10L24 11Z"
          fill="white"
        />
        {/* Z stroke — bottom bar */}
        <path
          d="M8 20.5H24V22.5H8V20.5Z"
          fill="white"
        />
      </svg>

      {showText && (
        <span
          className={`font-semibold tracking-tight text-[var(--text-primary)] ${textSize}`}
          style={{ letterSpacing: '-0.02em' }}
        >
          Ziref
        </span>
      )}
    </div>
  );
}
