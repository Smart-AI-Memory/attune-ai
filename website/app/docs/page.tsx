import { HARNESS_INSTALL_COMMAND, HARNESS_PUBLISHED, HARNESS_RELEASE_NOTICE, HARNESS_RELEASE_SLUG, HARNESS_SOURCE_ROOT, HARNESS_VERSION } from '@/lib/harness-release';
import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';
import { HARNESS_FAQ_ITEMS } from '@/lib/harness-faq';

export const metadata: Metadata = genMeta({
  title: 'Documentation',
  description:
    'Attune Harness documentation for scoped engineering work, setup, checked results and retained context.',
  url: 'https://smartaimemory.com/docs',
});

export default function DocsPage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Docs', url: 'https://smartaimemory.com/docs' },
    ],
  });

  const faqSchema = generateStructuredData('faq', {
    questions: [...HARNESS_FAQ_ITEMS],
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-5xl font-bold mb-6">Attune Harness documentation</h1>
              <p className="text-xl opacity-90 mb-8">
                Start with Attune Harness. Find guidance for useful work,
                execution permissions, checkable results and retained context.
              </p>
              <nav className="flex flex-wrap justify-center gap-3">
                <a href="#harness-docs" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">Harness</a>
                <Link href="/harness/help/get-started/" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  Harness Quick Start
                </Link>
                <a href="#faq" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  FAQ
                </a>
              </nav>
            </div>
          </div>
        </section>

        <section id="harness-docs" className="py-20">
          <div className="container max-w-5xl">
            <h2 className="text-4xl font-bold mb-4">Start with Attune Harness</h2>
            <p className="text-xl text-[var(--text-secondary)] mb-6"><Link className="underline" href="/harness/help/">Open the Harness Help Center.</Link> {HARNESS_RELEASE_NOTICE} Full Windows parity remains deferred.</p>
            <p className="text-xl text-[var(--text-secondary)] mb-6">Define a useful next step, build or repair within scope, check the result, and return with the context intact. Choose a workflow from the guide; command syntax is available when you need it.</p>
            <div className="flex flex-wrap gap-4 mb-6">
              <Link className="btn btn-primary" href="/harness/help/goals/">What do you want to accomplish?</Link>
              <Link className="btn btn-outline" href={`/harness/help/${HARNESS_RELEASE_SLUG}/`}>{HARNESS_PUBLISHED ? `Install Harness ${HARNESS_VERSION}` : `Prepare for Harness ${HARNESS_VERSION}`}</Link>
              <a className="btn btn-outline" href={`${HARNESS_SOURCE_ROOT}/docs/cli-guide.md`}>Read the Harness guide</a>
              <a className="btn btn-outline" href={`${HARNESS_SOURCE_ROOT}/docs/release-readiness-${HARNESS_VERSION}.md`}>Check the {HARNESS_VERSION} qualification limits</a>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">Claude Code and Codex have documented setup paths. Native planning and building remain experimental; Antigravity integration is unverified here. Intent acceptance is separate from paid execution permission.</p>
            <p className="text-sm text-[var(--text-secondary)] mt-4">Bringing existing work? <a className="underline" href={`${HARNESS_SOURCE_ROOT}/docs/migration.md`}>Review the migration boundaries</a> before changing an existing setup.</p>
          </div>
        </section>

        {/* Retain the current quick-start anchor for existing links. */}
        <section id="quickstart" className="py-20 bg-[var(--surface-container-low)]">
          <div className="container max-w-5xl">
            <h2 className="text-4xl font-bold mb-4">Harness {HARNESS_VERSION} quick start</h2>
            <p className="text-xl text-[var(--text-secondary)] mb-6">
              {HARNESS_RELEASE_NOTICE}
            </p>
            <p className="text-[var(--text-secondary)] mb-6">
              Follow the current guide for installation, a version check and a
              first local result. Continue with the setup for your agent.
            </p>
            {HARNESS_PUBLISHED ? (
              <pre className="overflow-x-auto rounded-lg bg-[var(--surface-container-high)] p-4 mb-6"><code>{HARNESS_INSTALL_COMMAND}</code></pre>
            ) : null}
            <div className="flex flex-wrap gap-4 mb-6">
              <Link className="btn btn-primary" href="/harness/help/get-started/">Open the current quick start</Link>
              <Link className="btn btn-outline" href={`/harness/help/${HARNESS_RELEASE_SLUG}/`}>Review Harness {HARNESS_VERSION}</Link>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">
              For the older setup, <Link className="underline" href="/harness/archive/1-4-0/#quickstart">read the archived Harness 1.4.0 quick start</Link>.
            </p>
          </div>
        </section>

        {/* Standalone reader reference; retain the earlier link target. */}
        <section id="attune-help" className="py-8">
          <div className="container max-w-5xl">
            <h2 className="!text-xl font-bold mb-3">Standalone help reader</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Attune Help reads existing <code>.help/</code> templates.
              If you need the reader independently, see the{' '}
              <a className="underline" href="https://pypi.org/project/attune-help/">standalone package reference</a>.
            </p>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-12">
                Attune Harness FAQ
              </h2>

              <div className="space-y-6 mb-8">
                {HARNESS_FAQ_ITEMS.map((item) => (
                  <div key={item.question} className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                    <h3 className="!text-xl font-bold mb-2">{item.question}</h3>
                    <p className="text-sm text-[var(--text-secondary)]">{item.answer}</p>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-4 mb-12">
                <Link href="/harness/help/goals/" className="btn btn-primary">Browse all goals</Link>
                <Link href={`/harness/help/${HARNESS_RELEASE_SLUG}/`} className="btn btn-outline">Read the {HARNESS_VERSION} guide</Link>
                <a href={`${HARNESS_SOURCE_ROOT}/docs/migration.md`} className="btn btn-outline">Check migration boundaries</a>
                <a href="/faq" className="btn btn-outline">Harness FAQ</a>
              </div>
              <div id="attune-ai-reference-questions" className="border border-[var(--border)] rounded-lg p-6 scroll-mt-24">
                <h3 className="!text-xl font-bold mb-3">Historical references</h3>
                <p className="text-sm text-[var(--text-secondary)]">
                  For an earlier installation, <Link className="underline" href="/faq/#attune-ai-reference-questions">open the historical project references</Link>.
                </p>
                <p id="attune-author" className="text-sm text-[var(--text-secondary)] mt-4 scroll-mt-24">
                  <Link className="underline" href="/attune-author/#attune-author">Attune Author reference</Link>.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-4xl font-bold mb-6">Choose a Harness workflow</h2>
              <p className="text-xl mb-8 opacity-90">
                Start with a concrete goal and a result you can assess.
                The guide explains the available workflows and their limits.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="https://github.com/Smart-AI-Memory/attune-harness"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >
                  Harness on GitHub
                </a>
                <a
                  href="#harness-docs"
                  className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >
                  Harness guide
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
