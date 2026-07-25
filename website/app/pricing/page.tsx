import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';
import { CAPABILITIES, PILLARS, getPricingSummary } from '@/lib/features';

export const metadata: Metadata = genMeta({
  title: 'Pricing — Free & Open Source',
  description:
    'Attune-AI is the spec-driven development platform — AI workflows, ' +
    'project memory, retrieval grounding, and verification — released ' +
    'under the Apache License 2.0.',
  url: 'https://smartaimemory.com/pricing',
});

// Literal Tailwind class strings per pillar color. Built as full
// literals (not `bg-[var(--${color})]`) so the JIT scanner can see
// and generate them — dynamically-constructed class names are not
// emitted.
const PILLAR_COLOR: Record<string, { bg: string; text: string }> = {
  primary: { bg: 'bg-[var(--primary)]/10', text: 'text-[var(--primary)]' },
  secondary: { bg: 'bg-[var(--secondary)]/10', text: 'text-[var(--secondary)]' },
  accent: { bg: 'bg-[var(--accent)]/10', text: 'text-[var(--accent)]' },
};

const includedItems = [
  `${CAPABILITIES.workflows} AI workflows`,
  `MCP server with ${CAPABILITIES.mcpTools} registered tools`,
  `${CAPABILITIES.skills} auto-triggering Claude Code skills`,
  'Spec-driven workflow with an approval gate (/spec)',
  'Retrieval grounding — attune-rag is built in',
  'Local-first project memory and lessons corpus',
  'Verification: fact-check generated content before it ships',
  'Full source code access',
  'Community support on GitHub',
  'Commercial use rights (Apache 2.0)',
];

export default function PricingPage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Pricing', url: 'https://smartaimemory.com/pricing' },
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
              <span className="inline-block text-xs font-bold tracking-[0.2em] uppercase mb-4 opacity-80">
                Pricing
              </span>
              <h1 className="text-5xl font-bold mb-6">
                The whole platform, free &amp; open source
              </h1>
              <p className="text-xl opacity-90 mb-8">
                Apache License 2.0 — full source, commercial use included.
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

        {/* What's in the platform */}
        <section className="py-24 px-6">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
                What You Get
              </span>
              <h2 className="text-4xl font-extrabold">
                What&apos;s included
              </h2>
              <p className="text-[var(--text-secondary)] mt-4 max-w-2xl mx-auto">
                Every pillar, every workflow, every tool —{' '}
                {getPricingSummary().toLowerCase()}.
              </p>
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

        {/* Pillars — memory leads (DEC-3), all free */}
        <section className="py-24 px-6 bg-[var(--surface-container-low)]">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
                The Platform
              </span>
              <h2 className="text-4xl font-extrabold">
                Memory first, zero cost
              </h2>
              <p className="text-[var(--text-secondary)] mt-4 max-w-2xl mx-auto">
                Project memory and every capability around it — all real,
                shipped, and included in the free, open source release.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
              {PILLARS.map((p) => {
                const c = PILLAR_COLOR[p.color];
                return (
                  <div
                    key={p.id}
                    className="group bg-[var(--surface)] rounded-2xl p-8 hover:bg-[var(--background)] transition-all duration-300 hover:scale-[1.02]"
                  >
                    <div className={`w-14 h-14 rounded-xl ${c.bg} flex items-center justify-center mb-6`}>
                      <span className="text-2xl" aria-hidden="true">{p.icon}</span>
                    </div>
                    <span className={`text-xs font-bold uppercase tracking-[0.12em] ${c.text}`}>
                      {p.tag}
                    </span>
                    <h3 className="text-lg font-bold mt-1 mb-3">{p.title}</h3>
                    <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                      {p.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Why open source */}
        <section className="py-24 px-6">
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-16">
              <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
                Our Philosophy
              </span>
              <h2 className="text-4xl font-extrabold">
                Why the platform is free
              </h2>
            </div>

            <div className="space-y-8">
              <div className="p-8 rounded-2xl bg-[var(--surface)] border-l-4 border-[var(--primary)]">
                <h3 className="text-xl font-bold mb-3">
                  Reliability shouldn&apos;t be a premium tier
                </h3>
                <p className="text-[var(--text-secondary)] leading-relaxed">
                  Specifying, grounding, remembering, and verifying are how
                  teams turn requirements into software they can trust. Those
                  aren&apos;t add-ons to charge for — they&apos;re the whole
                  point. Apache 2.0 keeps the reliability loop open to everyone.
                </p>
              </div>

              <div className="p-8 rounded-2xl bg-[var(--surface)] border-l-4 border-[var(--secondary)]">
                <h3 className="text-xl font-bold mb-3">Built for teams</h3>
                <p className="text-[var(--text-secondary)] leading-relaxed">
                  The best developer tools are built by communities, not locked
                  behind seats. Memory is local-first with an optional Redis
                  semantic tier, so a team can adopt the platform on its own
                  terms. Your feedback and contributions are what make it better.
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
                Ready to ship reliable software?
              </h2>
              <p className="text-xl mb-8 opacity-90">
                Free and open source forever. Install from PyPI, run /spec on
                your next feature, and let the platform keep the work grounded,
                remembered, and verified.
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
