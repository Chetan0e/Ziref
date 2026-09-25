'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info';

export interface ToastOptions {
  title?: string;
  description?: string;
  message?: string;
  type?: ToastType;
}

interface ToastItem {
  id: string;
  title?: string;
  description?: string;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  toast: (messageOrOptions: string | ToastOptions, type?: ToastType) => void;
  addToast: (messageOrOptions: string | ToastOptions, type?: ToastType) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback(
    (messageOrOptions: string | ToastOptions, fallbackType: ToastType = 'info') => {
      const id = Math.random().toString(36).slice(2, 9);

      let title: string | undefined;
      let description: string | undefined;
      let message: string;
      let type: ToastType = fallbackType;

      if (typeof messageOrOptions === 'string') {
        message = messageOrOptions;
      } else {
        title = messageOrOptions.title;
        description = messageOrOptions.description;
        message = messageOrOptions.message || title || description || '';
        type = messageOrOptions.type || fallbackType;
      }

      setToasts((prev) => [...prev, { id, title, description, message, type }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4500);
    },
    []
  );

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const value: ToastContextType = {
    toast: addToast,
    addToast,
    success: (msg: string) => addToast(msg, 'success'),
    error: (msg: string) => addToast(msg, 'error'),
    info: (msg: string) => addToast(msg, 'info'),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 pointer-events-none max-w-sm w-full">
        {toasts.map((t) => {
          const isSuccess = t.type === 'success';
          const isError = t.type === 'error';

          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex items-start justify-between p-3.5 rounded-xl border shadow-xl text-xs font-medium transition-all ${
                isSuccess
                  ? 'bg-emerald-50 text-emerald-950 border-emerald-300 dark:bg-emerald-950/90 dark:text-emerald-100 dark:border-emerald-800'
                  : isError
                  ? 'bg-rose-50 text-rose-950 border-rose-300 dark:bg-rose-950/90 dark:text-rose-100 dark:border-rose-900'
                  : 'bg-[var(--surface)] text-[var(--text-primary)] border-[var(--border)]'
              }`}
            >
              <div className="flex items-start gap-2.5 mr-2">
                {isSuccess && <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />}
                {isError && <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />}
                {!isSuccess && !isError && <Info className="w-4 h-4 text-sky-500 shrink-0 mt-0.5" />}
                <div>
                  {t.title && <div className="font-semibold text-xs">{t.title}</div>}
                  <div className={`${t.title ? 'text-[11px] opacity-80 mt-0.5' : 'text-xs'}`}>
                    {t.description || t.message}
                  </div>
                </div>
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="p-1 rounded opacity-70 hover:opacity-100 transition-opacity"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
