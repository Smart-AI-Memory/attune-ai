import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';

export const metadata: Metadata = genMeta({
  title: 'Free & Open Source',
  description:
    'Attune AI is fully open source under Apache 2.0. Help content generation, progressive depth, and staleness detection — free for everyone.',
  url: 'https://smartaimemory.com/pricing',
});

const includedItems = [
  'Help content generation from source code',
  'Progressive depth templates (concept / task / reference)',
  'Staleness detection and auto-regeneration',
  'Claude Code plugin with 14 skills',
  'Standalone reader (attune-help)',
  'Full source code access',
  'Community support on GitHub',
  'Commercial use rights (Apache 2.0)',
];

export default function PricingPage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Open Source', url: 'https://smartaimemory.com/pricing' },
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
        {/* Hero Section */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-5xl font-bold mb-6">
                Free &amp; Open Source
              </h1>
              <p className="text-xl opacity-90 mb-8">
                Apache License 2.0 — free for everyone. No hidden fees,
                no usage limits, no license keys.
              </p>
              <a
                href="https://github.com/Smart-AI-Memory/attune-ai"
                target="_blank"
                rel="noopener noreferrer"
                className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors inline-block"
              >
                View on GitHub
              </a>
            </div>
          </div>
        </section>

        {/* Everything Included */}
        <section className="py-24 px-6">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
                What You Get
              </span>
              <h2 className="text-4xl font-extrabold">
                Everything Included
              </h2>
            </div>

            <div className="grid md:grid-cols-2 gap-6 mb-16">
              {includedItems.map((item) => (
                <div
                  key={item}
                  className="flex items-start gap-4 p-6 rounded-2xl bg-[var(--surface)] hover:bg-[var(--surface-container-low)] transition-all"
                >
                  <span className="text-[var(--primary)] text-lg mt-0.5">&#10003;</span>
                  <span className="font-medium text-sm">{item}</span>
                </div>
              ))}
            </div>

            {/* Install */}
            <div className="text-center">
              <p className="text-[var(--text-secondary)] mb-6">
                Get started in seconds:
              </p>
              <div className="inline-flex items-center bg-[var(--foreground)] text-[var(--background)] px-6 py-3 rounded-lg font-mono text-sm">
                <span className="opacity-50 mr-2">$</span>
                <span>pip install attune-ai</span>
              </div>
            </div>
          </div>
        </section>

        {/* Open Source Benefits */}
        <section className="py-24 px-6 bg-[var(--surface-container-low)]">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
                Open Source
              </span>
              <h2 className="text-4xl font-extrabold">
                Why It&apos;s Free
              </h2>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
              <div className="group bg-[var(--surface)] rounded-2xl p-8 hover:bg-[var(--background)] transition-all duration-300 hover:scale-[1.02]">
                <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--primary)] transition-colors">
                  <span className="text-2xl group-hover:brightness-0 group-hover:invert transition-all">&#127881;</span>
                </div>
                <h3 className="text-lg font-bold mb-3">No Cost, Ever</h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Personal projects, startups, or enterprises.
                  No fees, no limits.
                </p>
              </div>

              <div className="group bg-[var(--surface)] rounded-2xl p-8 hover:bg-[var(--background)] transition-all duration-300 hover:scale-[1.02]">
                <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--primary)] transition-colors">
                  <span className="text-2xl group-hover:brightness-0 group-hover:invert transition-all">&#128275;</span>
                </div>
                <h3 className="text-lg font-bold mb-3">Commercial Friendly</h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Build and sell commercial products. Apache 2.0
                  includes patent protection.
                </p>
              </div>

              <div className="group bg-[var(--surface)] rounded-2xl p-8 hover:bg-[var(--background)] transition-all duration-300 hover:scale-[1.02]">
                <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--primary)] transition-colors">
                  <span className="text-2xl group-hover:brightness-0 group-hover:invert transition-all">&#128736;&#65039;</span>
                </div>
                <h3 className="text-lg font-bold mb-3">Fork &amp; Modify</h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Customize for your needs. Create private forks
                  or contribute back.
                </p>
              </div>

              <div className="group bg-[var(--surface)] rounded-2xl p-8 hover:bg-[var(--background)] transition-all duration-300 hover:scale-[1.02]">
                <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--primary)] transition-colors">
                  <span className="text-2xl group-hover:brightness-0 group-hover:invert transition-all">&#129309;</span>
                </div>
                <h3 className="text-lg font-bold mb-3">Community Driven</h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Contribute features, fix bugs, or star the repo.
                  We welcome everyone.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Why Open Source */}
        <section className="py-24 px-6">
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-16">
              <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
                Our Philosophy
              </span>
              <h2 className="text-4xl font-extrabold">
                Why We Went Open Source
              </h2>
            </div>

            <div className="space-y-8">
              <div className="p-8 rounded-2xl bg-[var(--surface)] border-l-4 border-[var(--primary)]">
                <h3 className="text-xl font-bold mb-3">
                  Adoption Over Revenue
                </h3>
                <p className="text-[var(--text-secondary)] leading-relaxed">
                  Developers want proven, open source tools — especially
                  in the AI space. Going Apache 2.0 lets us focus on
                  building the best help content generation framework
                  and growing a community of contributors.
                </p>
              </div>

              <div className="p-8 rounded-2xl bg-[var(--surface)] border-l-4 border-[var(--secondary)]">
                <h3 className="text-xl font-bold mb-3">Community First</h3>
                <p className="text-[var(--text-secondary)] leading-relaxed">
                  The best developer tools are built by communities,
                  not companies. Your feedback, contributions, and
                  support are what will make this project successful.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-4xl font-bold mb-6">
                Ready to Get Started?
              </h2>
              <p className="text-xl mb-8 opacity-90">
                Free and open source forever. Generate help content
                from your codebase today.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >
                  Star on GitHub
                </a>
                <Link
                  href="/docs"
                  className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >
                  View Documentation
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
