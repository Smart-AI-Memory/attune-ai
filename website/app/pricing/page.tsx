import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { HARNESS_PACKAGE_URL, HARNESS_RELEASE_NOTICE } from '@/lib/harness-release';
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
                  href="https://github.com/Smart-AI-Memory/attune-harness"
                  className="px-6 py-3 rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >Read the source</a>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-harness/blob/main/LICENSE"
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
              {HARNESS_RELEASE_NOTICE}
            </p>
            <p className="text-[var(--text-secondary)] mb-6">
              Use Python 3.10 or later in a fresh, isolated environment.
              Retain existing environments and saved work; installation does not migrate them.
              The Quick Start explains candidate validation and installation of
              the published package. Add Redis or Voyage only when your workflow needs them;
              their services, credentials and paid-call permissions are separate.
            </p>
            <p className="text-[var(--text-secondary)] mb-6">
              Installing the Python package does not install an agent plugin or skill.
              Check the selected version and run the local example before connecting your agent.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link className="btn btn-primary" href="/harness/help/get-started/">Read the Harness Quick Start</Link>
              <a className="btn btn-outline" href={HARNESS_PACKAGE_URL}>Published package and installation guide</a>
            </div>
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
