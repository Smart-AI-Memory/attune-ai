import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta } from '@/lib/metadata';

export const metadata: Metadata = {
  ...genMeta({
    title: 'Attune Author reference',
    description: 'Historical Attune Author reference. Attune AI is deprecated; use the current Attune Harness Quick Start for new work.',
    url: 'https://smartaimemory.com/attune-author/',
  }),
  robots: { index: false, follow: true },
};

// Retain the Author section from website main 6695106f8 without rewriting it.
export default function AttuneAuthorReference() {
  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        <header className="container max-w-5xl pt-12">
          <p className="text-sm font-bold uppercase tracking-wider mb-4">Earlier project reference</p>
          <h1 className="text-4xl font-bold mb-4">Attune Author reference</h1>
          <p className="text-[var(--text-secondary)] mb-6">
            The original authoring reference is retained below.{' '}
            <Link className="underline" href="/docs/">Return to documentation</Link> for Harness guidance and other project references.
          </p>
          <p className="text-[var(--text-secondary)] mb-6">
            Attune AI is deprecated. For new work, use Attune Harness. The{' '}
            <Link className="underline" href="/harness/help/get-started/">current Harness Quick Start</Link>{' '}
            covers 1.5.1 preparation, candidate validation and available published
            packages. Confirm release availability there before choosing an artifact.
          </p>
          <p className="text-[var(--text-secondary)] mb-6">
            The original instructions below, including the Attune AI installation
            command, are historical. Keep existing environments and saved work
            intact; deprecation does not establish migration parity. The standalone
            attune-help reader is a separate project.
          </p>
        </header>
        <section id="attune-author" className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-4">
                Attune Author
              </h2>
              <p className="text-center text-[var(--text-secondary)] mb-8 max-w-2xl mx-auto">
                Consolidated into attune-ai as of July 2026. The
                standalone package is archived on PyPI &mdash; released
                versions stay installable, but no further releases are
                planned.
              </p>

              <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6 max-w-2xl mx-auto">
                <p className="text-sm text-[var(--text-secondary)] mb-4">
                  Its authoring capabilities now ship with the attune-ai
                  platform: the{" "}
                  <code className="text-xs bg-[var(--surface-container-high)] px-1 rounded">
                    author-feature
                  </code>{" "}
                  skill writes a single code-verified master per feature
                  and projects it to the .help template kinds and docs
                  pages, and{" "}
                  <code className="text-xs bg-[var(--surface-container-high)] px-1 rounded">
                    /coach maintain
                  </code>{" "}
                  keeps generated templates in sync with your source.
                  attune-help remains the standalone reader.
                </p>
                <div className="bg-[#263c30] text-white/90 rounded-xl font-mono text-xs p-4 leading-relaxed">
                  <div className="text-white/50"># Authoring now ships with attune-ai</div>
                  <div>pip install attune-ai</div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
