import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';
import { RELIABILITY_LOOP, PILLARS } from '@/lib/features';

export const metadata: Metadata = genMeta({
  title: 'How It Works',
  description:
    'How Attune AI gives your coding agent a memory and makes it show receipts: specify, ground, build, remember, verify — and a multi-model round table you chair.',
  url: 'https://smartaimemory.com/how-it-works',
});

// Literal Tailwind class strings per pillar color so the JIT
// scanner emits them (dynamic `bg-[var(--${color})]` is not emitted).
const PILLAR_COLOR: Record<string, { bg: string; text: string }> = {
  primary: { bg: 'bg-[var(--primary)]/10', text: 'text-[var(--primary)]' },
  secondary: { bg: 'bg-[var(--secondary)]/10', text: 'text-[var(--secondary)]' },
  accent: { bg: 'bg-[var(--accent)]/10', text: 'text-[var(--accent)]' },
};

export default function HowItWorksPage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'How It Works', url: 'https://smartaimemory.com/how-it-works' },
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
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-5xl font-bold mb-4">How It Works</h1>
              <p className="text-xl opacity-90">
                The loop that gives your agent a memory and makes it show
                receipts — every session, every change.
              </p>
            </div>
          </div>
        </section>

        {/* The reliability loop */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-5xl mx-auto">
              <div className="text-center mb-16">
                <h2 className="text-3xl font-bold mb-4">The reliability loop</h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  Five stages keep the work honest from idea to merge.
                  Nothing gets generated without a spec, grounded without
                  your code, or shipped without verification.
                </p>
              </div>

              <div className="relative">
                {/* Vertical timeline line (desktop only) */}
                <div className="hidden md:block absolute left-1/2 top-0 bottom-0 w-px bg-[var(--border)] -translate-x-1/2" />

                <div className="space-y-12 md:space-y-20">
                  {RELIABILITY_LOOP.map((stage, index) => {
                    const isLeft = index % 2 === 0;
                    return (
                      <div key={stage.name} className="relative">
                        {/* Timeline dot (desktop only) */}
                        <div className="hidden md:flex absolute left-1/2 top-8 -translate-x-1/2 -translate-y-1/2 z-10 w-12 h-12 rounded-full bg-[var(--primary)] text-white items-center justify-center font-bold text-sm shadow-lg">
                          {stage.n}
                        </div>

                        {/* Card */}
                        <div
                          className={`md:w-[calc(50%-2.5rem)] ${
                            isLeft ? 'md:mr-auto' : 'md:ml-auto'
                          }`}
                        >
                          <div className="glass-panel rounded-xl p-8">
                            <div className="flex items-center gap-3 mb-3">
                              <div className="md:hidden w-10 h-10 rounded-full bg-[var(--primary)] text-white flex items-center justify-center font-bold text-sm shrink-0">
                                {stage.n}
                              </div>
                              <h3 className="text-2xl font-bold">{stage.name}</h3>
                            </div>
                            <p className="text-[var(--text-secondary)] leading-relaxed">
                              {stage.description}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Pillars underneath — memory leads (DEC-3) */}
        <section className="py-20 bg-[var(--surface-container-low)]">
          <div className="container">
            <div className="max-w-5xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-3xl font-bold mb-4">What&apos;s working underneath</h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  Memory powers every stage of the loop — with four
                  supporting capabilities, each real and shipped.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                {PILLARS.map((p) => {
                  const c = PILLAR_COLOR[p.color];
                  return (
                    <div
                      key={p.id}
                      className="bg-[var(--background)] rounded-xl p-8 border border-[var(--border)]"
                    >
                      <div className={`w-14 h-14 rounded-xl ${c.bg} flex items-center justify-center mb-5`}>
                        <span className="text-3xl" aria-hidden="true">{p.icon}</span>
                      </div>
                      <span className={`text-xs font-bold uppercase tracking-[0.12em] ${c.text}`}>
                        {p.tag}
                      </span>
                      <h3 className="text-xl font-bold mt-1 mb-3">{p.title}</h3>
                      <p className="text-[var(--text-secondary)] leading-relaxed text-sm mb-4">
                        {p.description}
                      </p>
                      <ul className="space-y-1.5">
                        {p.points.map((pt) => (
                          <li key={pt} className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
                            <span className={`${c.text} mt-0.5`} aria-hidden="true">&#10003;</span>
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* Round table — the receipts culture across models (DEC-14a:
            the multi-LLM fold stands, but the roundtable gets marquee
            treatment here as the vivid case of receipts + chairing) */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-5xl mx-auto">
              <div className="text-center mb-12">
                <span className="text-xs font-bold text-[var(--accent)] tracking-[0.2em] uppercase mb-4 block">
                  The round table
                </span>
                <h2 className="text-3xl font-bold mb-4">
                  Three models. One project brain. You chair.
                </h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  The final QA check before you ship:{' '}
                  <code className="text-base">/roundtable</code> convenes
                  Claude Code, OpenAI Codex, and Google Antigravity —
                  three agents sharing one project memory — to deliberate
                  the question on a shared board. Every seat is advisory.
                  Nothing is adopted until you promote it.
                </p>
              </div>

              <div className="grid md:grid-cols-3 gap-6">
                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4" aria-hidden="true">&#x1f5e3;&#xfe0f;</div>
                  <h3 className="text-xl font-bold mb-3">Deliberate</h3>
                  <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                    Each model posts positions and critiques to a shared,
                    Redis-backed board — three different frontier models
                    reasoning about the same question, not one model
                    agreeing with itself. Work crosses seats as
                    git-verified handoff packets, re-verified against the
                    actual tree on resume.
                  </p>
                </div>
                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4" aria-hidden="true">&#x1fa91;</div>
                  <h3 className="text-xl font-bold mb-3">You decide</h3>
                  <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                    The seats advise; only the chair promotes. You rule on
                    what gets adopted, and the ruling is recorded — a
                    decision that outlives the session.
                  </p>
                </div>
                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4" aria-hidden="true">&#x1f9fe;</div>
                  <h3 className="text-xl font-bold mb-3">Receipts, still</h3>
                  <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                    A claim without a receipt doesn&apos;t ship — even
                    between AIs. Promoted actions get an executed receipt
                    posted back to the board, closing the loop between a
                    ruling and its execution.
                  </p>
                </div>
              </div>

              <p className="text-center text-[var(--text-secondary)] mt-10 max-w-2xl mx-auto">
                For a lighter touch,{' '}
                <code className="text-base">/cross-review</code> gets one
                advisory second opinion on a real diff from a different
                model than the one that wrote it. It earns its keep: one
                release exists because a cross-provider receipt probe
                caught a protocol bug the primary client silently
                tolerated.
              </p>
            </div>
          </div>
        </section>

        {/* You stay in control */}
        <section className="py-20 bg-[var(--surface-container-low)]">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-3xl font-bold mb-4">
                  The Agent Drafts. You Approve. The Platform Verifies.
                </h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  Reliability isn&apos;t a vibe — it&apos;s a gate at each end of
                  the work.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4">&#x1f4dd;</div>
                  <h3 className="text-xl font-bold mb-3">The spec gate</h3>
                  <ul className="space-y-3 text-[var(--text-secondary)]">
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Requirements, design, and tasks are written and
                        approved before a line of code
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Socratic discovery scopes the work with you, not
                        around you
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        The spec is the contract the build is measured
                        against &mdash; and the ladder the agent executes
                        between your approvals
                      </span>
                    </li>
                  </ul>
                </div>

                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4">&#x2705;</div>
                  <h3 className="text-xl font-bold mb-3">The verification gate</h3>
                  <ul className="space-y-3 text-[var(--text-secondary)]">
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Generated claims are fact-checked against your real
                        source
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Imports import, CLI flags are real, links resolve,
                        counts match
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Hallucinations are caught before the change reaches
                        main
                      </span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl font-bold mb-4">
                Ready to give your agent a memory?
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Install from PyPI and run <code className="text-base">/spec</code>{' '}
                on your next feature.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/docs#quickstart"
                  className="btn btn-primary text-lg px-8 py-4"
                >
                  Get Started
                </Link>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline text-lg px-8 py-4"
                >
                  Star on GitHub
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
