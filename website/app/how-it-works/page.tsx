import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';
import { RELIABILITY_LOOP, PILLARS } from '@/lib/features';

export const metadata: Metadata = genMeta({
  title: 'Attune AI reference',
  description:
    'Retained reference for Attune AI’s memory and workflow model. Attune Harness is the current project focus.',
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
              <h1 className="text-5xl font-bold mb-4">How Attune AI works</h1>
              <p className="text-xl opacity-90">
                Reference for the earlier project’s memory and workflow model.
                Attune Harness is the current focus; these materials remain
                available for existing users.
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
                  Five stages describe a way to organize development. Choose
                  checks appropriate to the change and inspect their results.
                  This practice does not enforce every step in every workflow
                  or guarantee correct output.
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
                  Project memory can support the loop alongside four
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

        {/* Forms, live — the communication pillar made touchable:
            two real widget-pipeline renders you can fill in (the
            capture GIF at /images/attune-forms-retro-demo.gif stays
            published for blog embeds). Iframe heights fit each full
            form so nothing is cut short. */}
        <section className="py-20 bg-[var(--surface-container-low)]">
          <div className="container">
            <div className="max-w-5xl mx-auto">
              <div className="text-center mb-12">
                <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
                  Try a form
                </span>
                <h2 className="text-3xl font-bold mb-4">
                  The agent asks with structure — go ahead, answer it
                </h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  Both of these are live renders from the production
                  form pipeline, not mockups. Left: scope an audit — a
                  recommended decision card with tradeoffs,
                  multi-select, a dropdown, a bounded number, free
                  text. Right: a session retro triaged one tap per
                  item. Submit either empty and validation catches you.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-6 items-start">
                <div className="bg-[var(--background)] rounded-xl border border-[var(--border)] overflow-hidden">
                  <iframe
                    src="/forms-demo/audit.html"
                    title="Live attune-forms demo: scope a security audit"
                    className="w-full bg-[#faf9f5]"
                    style={{ height: 1050 }}
                    loading="lazy"
                  />
                  <p className="text-xs text-[var(--text-secondary)] px-4 py-3 border-t border-[var(--border)]">
                    Live embed — filling it here goes nowhere; in a
                    session, answers come back validated.
                  </p>
                </div>
                <div className="bg-[var(--background)] rounded-xl border border-[var(--border)] overflow-hidden">
                  <iframe
                    src="/forms-demo/retro.html"
                    title="Live attune-forms demo: rule a session retro, one tap per item"
                    className="w-full bg-[#faf9f5]"
                    style={{ height: 1310 }}
                    loading="lazy"
                  />
                  <p className="text-xs text-[var(--text-secondary)] px-4 py-3 border-t border-[var(--border)]">
                    The session retro as a triage form — real items from
                    the session that built this demo, ruled one tap each.
                  </p>
                </div>
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
                  Cross-model review, with you deciding.
                </h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  The earlier <code className="text-base">/roundtable</code>{' '}
                  integration provides a shared board for discussion with
                  configured model seats. Check each seat&apos;s availability,
                  authentication and permissions before use. The advice
                  informs your decision; you choose what to adopt.
                </p>
              </div>

              <div className="grid md:grid-cols-3 gap-6">
                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4" aria-hidden="true">&#x1f5e3;&#xfe0f;</div>
                  <h3 className="text-xl font-bold mb-3">Deliberate</h3>
                  <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                    Participants can post positions and critiques to a
                    Redis-backed board. Check which reviewers actually
                    participated and which source material they saw.
                    Re-verify handoff context against the current project
                    before continuing work.
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
                    For actions you approve, capture the executed result
                    and relevant check evidence. A decision to act is
                    separate from evidence that the action succeeded.
                  </p>
                </div>
              </div>

              <p className="text-center text-[var(--text-secondary)] mt-10 max-w-2xl mx-auto">
                For a second opinion,{' '}
                <code className="text-base">/cross-review</code> requests
                an advisory review of a real diff. Check the reviewer&apos;s
                identity, the files included and any omissions. Findings
                need assessment and appropriate verification before adoption.
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
                  Draft the specification, agree the work and inspect the checks.
                </h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  Use specifications and independent checks to make a change
                  reviewable. Keep their tested scope and limits visible.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4">&#x1f4dd;</div>
                  <h3 className="text-xl font-bold mb-3">Before implementation</h3>
                  <ul className="space-y-3 text-[var(--text-secondary)]">
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Write requirements, design and tasks; agree to the plan
                        and scope before implementation
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Use structured questions to resolve unclear requirements
                        and record the decisions
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Compare the result with the agreed specification and
                        keep changes in scope visible for review
                      </span>
                    </li>
                  </ul>
                </div>

                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4">&#x2705;</div>
                  <h3 className="text-xl font-bold mb-3">Before accepting a change</h3>
                  <ul className="space-y-3 text-[var(--text-secondary)]">
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Check generated claims against the relevant project
                        sources
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Choose checks for imports, CLI flags, links, counts and
                        other properties the change depends on
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Inspect what passed, what failed and what remains
                        unchecked. Passing checks do not guarantee a correct
                        change
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
                Explore Attune Harness
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Work from a concrete goal, check the result, and retain
                the context needed for the next step.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/docs#harness-docs"
                  className="btn btn-primary text-lg px-8 py-4"
                >
                  Harness docs
                </Link>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-harness"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline text-lg px-8 py-4"
                >
                  Harness on GitHub
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
