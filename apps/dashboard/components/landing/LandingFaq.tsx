'use client';

import React, { useState } from 'react';
import { Plus, Minus } from 'lucide-react';

interface FaqItem {
  question: string;
  answer: string;
}

const faqs: FaqItem[] = [
  {
    question: 'What frameworks does Ziref support?',
    answer:
      'Ziref supports React + Vite, Next.js, Vue 3, Angular, Astro, SvelteKit, and static HTML/CSS/JS. Detection is automatic — Ziref inspects package.json, lockfiles, and framework manifests to determine the correct build command and output directory without any manual configuration.',
  },
  {
    question: 'How does deployment work?',
    answer:
      'Your project archive runs in an ephemeral Docker sandbox with non-root user privileges, cgroup resource limits, and a hard execution timeout. Once the build completes, the artifact is captured and traffic switches atomically via an in-memory pointer update — zero downtime, rollback in under 20ms.',
  },
  {
    question: 'Can I use my own domain?',
    answer:
      'Yes. Custom domains can be connected to any deployment. Ziref provisions and renews TLS certificates automatically. Your deployment is also immediately available at a ziref.app subdomain.',
  },
  {
    question: 'How does the Android build work?',
    answer:
      'Once your web project is deployed, Ziref\'s Appify engine generates a complete Kotlin Android project — WebViewClient, pull-to-refresh, adaptive icons, permission declarations — and compiles an installable debug APK targeting Android 14 (API 34). You can download the APK directly or export the full Android Studio project.',
  },
  {
    question: 'How are projects isolated from each other?',
    answer:
      'Every build runs in a freshly created Docker container with no access to host filesystems, other user builds, or the Docker daemon. Containers are destroyed immediately after the build artifact is collected. Environment variables and secrets are encrypted at rest using Fernet symmetric encryption and decrypted only in memory at build time.',
  },
];

export function LandingFaq() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggle = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section id="faq" className="py-24 border-t border-[var(--border)]">
      <div className="max-w-layout mx-auto px-6 lg:px-10">
        {/* Section label */}
        <div className="mb-12">
          <p className="font-mono text-[13px] text-[var(--text-tertiary)] tracking-wider uppercase mb-3">
            FAQ
          </p>
          <h2
            className="text-4xl font-bold text-[var(--text-primary)]"
            style={{ letterSpacing: '-0.025em', lineHeight: 1.15 }}
          >
            Common questions
          </h2>
        </div>

        {/* Accordion rows */}
        <div role="list" aria-label="Frequently asked questions">
          {faqs.map((faq, index) => {
            const isOpen = openIndex === index;
            const panelId = `faq-panel-${index}`;
            const triggerId = `faq-trigger-${index}`;
            return (
              <div
                key={index}
                role="listitem"
                className="border-b border-[var(--border)] last:border-b-0"
              >
                <button
                  id={triggerId}
                  aria-expanded={isOpen}
                  aria-controls={panelId}
                  onClick={() => toggle(index)}
                  className="w-full py-5 text-left flex items-center justify-between gap-8 group"
                >
                  <span
                    className="text-[15px] font-medium text-[var(--text-primary)] group-hover:text-[var(--accent)] transition-colors duration-150"
                    style={{ lineHeight: 1.5 }}
                  >
                    {faq.question}
                  </span>
                  <span
                    className="shrink-0 w-5 h-5 flex items-center justify-center text-[var(--text-tertiary)] group-hover:text-[var(--accent)] transition-colors duration-150"
                    aria-hidden="true"
                  >
                    {isOpen
                      ? <Minus className="w-4 h-4" />
                      : <Plus className="w-4 h-4" />
                    }
                  </span>
                </button>

                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={triggerId}
                  hidden={!isOpen}
                  className={`overflow-hidden transition-all duration-200 ${
                    isOpen ? 'max-h-96 pb-5' : 'max-h-0'
                  }`}
                >
                  <p
                    className="text-[15px] text-[var(--text-secondary)] leading-relaxed max-w-prose-wide"
                    style={{ lineHeight: 1.65 }}
                  >
                    {faq.answer}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
