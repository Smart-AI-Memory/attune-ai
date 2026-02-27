import fs from 'fs';
import path from 'path';
import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata, generateStructuredData } from '@/lib/metadata';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export const metadata: Metadata = generateSEOMetadata({
  title: 'Attune AI Changelog — Release History & Updates',
  description:
    'Full release history for Attune AI. See what changed in each version: new features, bug fixes, deprecations, and breaking changes.',
  url: 'https://smartaimemory.com/changelog',
  keywords: [
    'Attune AI changelog',
    'Attune AI releases',
    'AI framework updates',
    'Claude Code plugin updates',
  ],
});

function getChangelog(): string {
  const changelogPath = path.join(process.cwd(), '..', 'CHANGELOG.md');
  if (fs.existsSync(changelogPath)) {
    return fs.readFileSync(changelogPath, 'utf8');
  }
  return '# Changelog\n\nNo changelog available.';
}

export default function ChangelogPage() {
  const content = getChangelog();

  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Changelog', url: 'https://smartaimemory.com/changelog' },
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
        {/* Hero */}
        <section className="py-16 bg-gradient-to-b from-[var(--border)] to-transparent">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <h1 className="text-4xl sm:text-5xl font-bold mb-4">Changelog</h1>
              <p className="text-xl text-[var(--text-secondary)]">
                Release history for Attune AI. All notable changes, new features,
                and bug fixes.
              </p>
              <div className="mt-6 flex gap-4">
                <a
                  href="https://pypi.org/project/attune-ai/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                >
                  Install on PyPI
                </a>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline"
                >
                  GitHub
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* Content */}
        <section className="py-16">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <div className="prose prose-lg max-w-none prose-headings:font-bold prose-a:text-[var(--primary)] prose-a:no-underline hover:prose-a:underline prose-code:bg-[var(--border)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-[var(--border)] prose-pre:border prose-pre:border-[var(--border)]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 border-t border-[var(--border)]">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl font-bold mb-4">Stay Up to Date</h2>
              <p className="text-[var(--text-secondary)] mb-6">
                Watch the GitHub repository to get notified of new releases.
              </p>
              <div className="flex justify-center gap-4">
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline"
                >
                  Star on GitHub
                </a>
                <Link href="/blog" className="btn btn-primary">
                  Read the Blog
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
