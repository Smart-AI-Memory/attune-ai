import type { Metadata } from 'next';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import FixWorkspaceEmbed from '@/components/FixWorkspaceEmbed';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';

export const metadata: Metadata = genMeta({
  title: 'Interactive Fix Approval Workspace',
  description:
    'Try Attune AI’s hashed, one-time Fix approval contract in a safe browser-only sandbox. Edit, approve, and prove replay rejection without executing a workflow.',
  url: 'https://smartaimemory.com/fix-workspace',
});

export default function FixWorkspacePage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Fix workspace', url: 'https://smartaimemory.com/fix-workspace' },
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
        <section className="py-16 border-b border-[var(--border)] bg-[var(--surface-container-low)]">
          <div className="container">
            <div className="max-w-4xl mx-auto text-center">
              <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
                Live security interaction
              </span>
              <h1 className="text-4xl md:text-6xl font-bold mb-5">
                Don&apos;t trust the button. Bind the approval.
              </h1>
              <p className="text-xl text-[var(--text-secondary)] max-w-3xl mx-auto">
                This public sandbox lets you inspect the exact authority
                Attune creates for Fix, change it, approve it once, and
                deliberately attack it with a replay.
              </p>
            </div>
          </div>
        </section>

        <section className="py-8 md:py-12">
          <div className="container">
            <div className="max-w-7xl mx-auto overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--background)] shadow-xl">
              <FixWorkspaceEmbed />
            </div>
          </div>
        </section>

        <section className="py-16 bg-[var(--surface-container-low)]">
          <div className="container">
            <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-6">
              {[
                ['1', 'Edit the contract', 'The rendered hash and action nonce are invalidated immediately.'],
                ['2', 'Authorize once', 'Only the exact canonical command crosses the approval boundary.'],
                ['3', 'Attack the replay', 'The consumed nonce makes the identical second response fail closed.'],
              ].map(([number, title, body]) => (
                <div key={number} className="glass-panel rounded-xl p-7">
                  <span className="text-sm font-bold text-[var(--primary)]">{number}</span>
                  <h2 className="text-xl font-bold mt-2 mb-3">{title}</h2>
                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
