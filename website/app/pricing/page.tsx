import { HARNESS_SOURCE_ROOT, HARNESS_RELEASE_NOTICE, HARNESS_PREPARATION_NOTICE, HARNESS_GET_STARTED, HARNESS_INSTALL_COMMAND } from '@/lib/harness-release';
import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';

export const metadata: Metadata = genMeta({
  title: 'Open Source — Attune Harness',
  description:
    'Attune Harness is released under the Apache License 2.0. Find the source, recommended installation and setup requirements.',
  url: 'https://smartaimemory.com/pricing',
});

export default function PricingPage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Open source', url: 'https://smartaimemory.com/pricing' },
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
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <p className="text-sm font-bold uppercase tracking-wider mb-4">Open source</p>
              <h1 className="text-5xl font-bold mb-6">Attune Harness, open source</h1>
              <p className="text-xl opacity-90 mb-8">
                Attune Harness is released under the Apache License 2.0.
                Read the source, try the package and inspect the evidence it keeps.
              </p>
              <div className="flex flex-wrap gap-4 justify-center">
                <a
                  href={HARNESS_SOURCE_ROOT.replace(`/blob/`, `/tree/`)}
                  className="px-6 py-3 rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >Read the source</a>
                <a
                  href={`${HARNESS_SOURCE_ROOT}/LICENSE`}
                  className="px-6 py-3 rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >Read the license</a>
              </div>
            </div>
          </div>
        </section>

        <section id="harness-install" className="py-20">
          <div className="container max-w-3xl">
            <h2 className="text-4xl font-bold mb-4">Start with Harness</h2>
            <p className="text-xl text-[var(--text-secondary)] mb-6">
              Use Python 3.12 or later. Install the published base package in its own managed environment:
            </p>
            <pre className="bg-[#263c30] text-white/90 rounded-xl font-mono text-sm p-4 overflow-x-auto"><code>{HARNESS_INSTALL_COMMAND}</code></pre>
            <p className="text-[var(--text-secondary)] mt-6">
              Add Redis or Voyage when the chosen workflow needs them. Redis needs a
              running service; Voyage retrieval needs an API key and spending permission. Integration requirements are covered in
              the{' '}
              <a className="underline" href={HARNESS_GET_STARTED}>released installation guide</a>.
            </p>
            <p className="text-[var(--text-secondary)] mt-4 mb-6">
              Installing the Python package does not install an agent plugin
              or skill. Follow the Quick Start to create an environment,
              confirm the version and run a small local example before
              connecting your agent.
            </p>
            <p className="text-[var(--text-secondary)] mb-6">{HARNESS_RELEASE_NOTICE} {HARNESS_PREPARATION_NOTICE}</p>
            <Link className="btn btn-primary" href={HARNESS_GET_STARTED}>Get started with Harness</Link>
          </div>
        </section>

        <section className="py-16 bg-[var(--surface-container-low)]">
          <div className="container max-w-5xl">
            <h2 className="text-3xl font-bold mb-6">Find a way to work together</h2>
            <div className="flex flex-wrap gap-4">
              <Link className="btn btn-primary" href="/#collaborate">Collaborate</Link>
              <Link className="btn btn-outline" href="/#pilot">Discuss a pilot</Link>
              <Link className="btn btn-outline" href="/#sponsor">Sponsor open-source milestones</Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
