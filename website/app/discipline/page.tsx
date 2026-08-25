import fs from 'fs';
import path from 'path';
import type { Metadata } from 'next';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateStructuredData } from '@/lib/metadata';

// Single-source: the master markdown lives in attune-ai-dev/ (the
// canonical home is attune-ai.dev/discipline, built from the same
// file). This page renders it at build time — never copy the text.
// Vercel includes outside-root files (sourceFilesOutsideRootDirectory)
// so the ../ read works in CI builds too.
const MASTER = path.join(
  process.cwd(),
  '..',
  'attune-ai-dev',
  'discipline',
  'COLLABORATION_DISCIPLINE.md'
);

export const metadata: Metadata = {
  title: 'The Discipline of Agent Collaboration — Attune AI',
  description:
    'An answer to vibe coding, from someone shipping real work this ' +
    'way: seven earned disciplines for human-AI collaboration — ' +
    'contract, pacing, artifacts, memory, multi-agent coordination, ' +
    'verification, and context budgeting.',
  // The canonical home stays attune-ai.dev — this mirror must not
  // compete with it in search indexes.
  alternates: { canonical: 'https://attune-ai.dev/discipline/' },
};

export default function DisciplinePage() {
  const content = fs.readFileSync(MASTER, 'utf8');
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Discipline', url: 'https://smartaimemory.com/discipline' },
    ],
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        <article className="py-16 px-6">
          <div className="max-w-3xl mx-auto">
            <p className="text-xs text-[var(--text-muted)] mb-8">
              Draft v5 &middot; also at{' '}
              <a
                href="https://attune-ai.dev/discipline/"
                className="text-[var(--primary)] hover:opacity-80 transition-opacity"
              >
                attune-ai.dev/discipline
              </a>
            </p>
            <div className="prose prose-lg max-w-none prose-headings:font-bold prose-a:text-[var(--primary)] prose-a:no-underline hover:prose-a:underline prose-code:bg-[var(--border)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-[var(--border)] prose-pre:border prose-pre:border-[var(--border)]">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </div>
            <p className="mt-12 pt-8 border-t border-[var(--border)]/40">
              <Link
                href="/"
                className="text-sm font-bold text-[var(--primary)] hover:opacity-80 transition-opacity"
              >
                &larr; Back to Attune AI
              </Link>
            </p>
          </div>
        </article>
      </main>
      <Footer />
    </>
  );
}
