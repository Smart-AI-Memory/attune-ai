import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import GitHubStarsBadge from '@/components/GitHubStarsBadge';
import TestsBadge from '@/components/TestsBadge';
import { generateStructuredData } from '@/lib/metadata';
import { METRICS, RELIABILITY_LOOP } from '@/lib/features';

// What a coding agent re-learns every session — and what Attune
// persists. Shared by the problem and memory sections.
const WHAT_PERSISTS = [
  ['Architectural decisions', 'why the code is shaped the way it is'],
  ['Coding conventions', 'the patterns your reviewers actually enforce'],
  ['Discovered constraints', 'the limits that are not written down anywhere'],
  ['Lessons from failed approaches', 'so the same dead end is not explored twice'],
  ['Implementation details', 'the seams, gotchas, and load-bearing quirks'],
  ['Project-specific knowledge', 'domain terms, priorities, and context'],
] as const;

export default function Home() {
  const softwareSchema = generateStructuredData('product');

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(softwareSchema),
        }}
      />
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">

        {/* 1 — Hero */}
        <section className="relative overflow-hidden px-6 py-24 md:py-32" aria-label="Hero">
          <div className="max-w-4xl mx-auto text-center">
            {/* The literal version is required here: the
                test_homepage_badge_includes_package_version guard scans
                this file for vX.Y.Z and compares it to the package. */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--surface-container-high)] text-[var(--primary)] text-xs font-bold tracking-widest mb-8 uppercase">
              <span>v16.1.0</span>
              <span className="w-1 h-1 rounded-full bg-[var(--primary)]" aria-hidden="true"></span>
              <span className="opacity-80">Persistent memory for AI coding agents</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tighter mb-8 leading-[1.1]">
              Give your agent a <span className="text-gradient">memory</span>.
              Make it show <span className="text-gradient">receipts</span>.
            </h1>
            <p className="text-lg md:text-xl text-[var(--text-secondary)] mb-10 max-w-2xl mx-auto leading-relaxed">
              Your agent stops starting from zero &mdash; and its word stops
              being the evidence. Attune carries decisions, bugs, and lessons
              across sessions, and verifies every change with probes re-run
              independently of the agent that claims it finished.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/docs#quickstart"
                className="bg-[var(--primary)] !text-white px-8 py-3 rounded-lg font-bold hover:opacity-90 transition-opacity text-center no-underline"
              >
                Install Attune
              </Link>
              <a
                href="https://github.com/Smart-AI-Memory/attune-ai"
                target="_blank"
                rel="noopener noreferrer"
                className="bg-[var(--surface-container-highest)] text-[var(--foreground)] px-8 py-3 rounded-lg font-bold hover:bg-[var(--surface-variant)] transition-colors text-center border border-[var(--border)] no-underline"
              >
                View on GitHub
              </a>
            </div>
            <p className="text-sm text-[var(--text-muted)] mt-4">
              Or install it as a{' '}
              <a href="#get-started" className="font-bold text-[var(--primary)] hover:opacity-80 transition-opacity">
                Claude Code plugin
              </a>{' '}
              &mdash; no Python required.
            </p>
            <div className="flex flex-wrap gap-3 mt-8 justify-center items-center">
              <span className="text-sm text-[var(--text-muted)]">
                Free and open source &middot; Apache 2.0
              </span>
              <GitHubStarsBadge />
              <TestsBadge />
            </div>
          </div>
        </section>

        {/* 2 — Problem */}
        <section className="py-24 px-6 bg-[var(--surface-container-low)]" aria-label="The problem">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-4xl md:text-5xl font-extrabold mb-8 tracking-tight">
              Your AI is smart.<br className="hidden sm:block" />{' '}
              Your project has amnesia.
            </h2>
            <p className="text-lg text-[var(--text-secondary)] leading-relaxed mb-6">
              A coding agent spends hours learning your architecture, your
              constraints, your conventions, the decisions behind the code,
              and the approaches that already failed. Then the session ends
              &mdash; and most of that knowledge is gone. The next session,
              the next tool, the next model: each one starts rediscovering
              your project from zero.
            </p>
            <p className="text-xl md:text-2xl font-bold text-[var(--foreground)]">
              Attune makes that knowledge persistent.
            </p>
          </div>
        </section>

        {/* 3 — Reliability loop */}
        <section className="py-24 px-6 max-w-7xl mx-auto" aria-label="The reliability loop">
          <div className="text-center mb-16">
            <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">How it works</span>
            <h2 className="text-4xl md:text-5xl font-extrabold">One reliability loop</h2>
            <p className="text-[var(--text-secondary)] mt-4 max-w-2xl mx-auto">
              Every change moves through the same five stages &mdash; from a
              requirement you can point at to an implementation you can trust.
            </p>
          </div>
          <ol className="grid md:grid-cols-5 gap-6 md:gap-0 list-none">
            {RELIABILITY_LOOP.map((s, i) => (
              <li key={s.name} className="relative flex md:block items-start gap-4">
                <div className="flex md:flex-col items-center md:items-start gap-4 md:gap-0 md:px-5">
                  <div className="flex items-center w-auto md:w-full">
                    <span className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-[var(--primary)]/10 text-[var(--primary)] font-bold text-sm shrink-0">
                      {s.n}
                    </span>
                    {i < RELIABILITY_LOOP.length - 1 && (
                      <span className="hidden md:block flex-1 h-px bg-[var(--border)] ml-4" aria-hidden="true"></span>
                    )}
                  </div>
                  <div className="md:mt-4">
                    <h3 className="font-bold text-lg leading-tight">{s.name}</h3>
                    <p className="text-sm text-[var(--text-muted)] leading-snug mt-1.5">{s.description}</p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* 4 — Memory */}
        <section className="py-24 px-6 bg-[var(--surface-container-low)]" aria-label="Persistent project memory">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-16">
              <span className="text-xs font-bold text-[var(--secondary)] tracking-[0.2em] uppercase mb-4 block">Project memory</span>
              <h2 className="text-4xl md:text-5xl font-extrabold">
                Your agent stops starting from zero.
              </h2>
              <p className="text-[var(--text-secondary)] mt-4 max-w-2xl mx-auto">
                Findings from each session are stashed and recalled in the
                next &mdash; automatically, or on demand with{' '}
                <code className="bg-[var(--surface-container-high)] px-1.5 py-0.5 rounded text-sm">/recall</code>.
                What persists:
              </p>
            </div>
            <ul className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 list-none">
              {WHAT_PERSISTS.map(([title, detail]) => (
                <li key={title} className="bg-[var(--surface)] rounded-xl p-5 border border-[var(--border)]/40">
                  <div className="font-bold text-sm mb-1">{title}</div>
                  <p className="text-xs text-[var(--text-muted)] leading-snug">{detail}</p>
                </li>
              ))}
            </ul>
            <p className="text-sm text-[var(--text-muted)] text-center mt-10 max-w-2xl mx-auto">
              Local-first by default &mdash; memory lives on your machine, no
              cloud required. An optional Redis tier adds semantic recall with
              local Ollama embeddings.
            </p>
          </div>
        </section>

        {/* 5 — Multi-model */}
        <section className="py-24 px-6 max-w-6xl mx-auto" aria-label="One project brain, multiple agents">
          <div className="text-center mb-16">
            <span className="text-xs font-bold text-[var(--accent)] tracking-[0.2em] uppercase mb-4 block">Multi-agent</span>
            <h2 className="text-4xl md:text-5xl font-extrabold">One project brain. Multiple agents.</h2>
            <p className="text-[var(--text-secondary)] mt-4 max-w-2xl mx-auto">
              Attune is the persistent layer beneath your coding agents, not a
              feature of one of them. Claude Code, Codex, and Antigravity work
              against the same project memory, specs, lessons, and repository
              state &mdash; handing off work with git-verified packets and
              giving each other second opinions on real diffs.
            </p>
          </div>
          {/* Architecture diagram — responsive flex, no image dependency */}
          <figure aria-label="Architecture: coding agents share the Attune project brain, which grounds work in your repository">
            <div className="flex flex-col md:flex-row items-stretch md:items-center gap-4 md:gap-0">
              {/* Agents */}
              <div className="flex flex-row md:flex-col gap-3 md:w-52 shrink-0 justify-center">
                {['Claude Code', 'Codex', 'Antigravity'].map((agent) => (
                  <div key={agent} className="flex-1 md:flex-none bg-[var(--surface)] border border-[var(--border)]/60 rounded-xl px-4 py-3 text-center font-mono text-sm font-bold">
                    {agent}
                  </div>
                ))}
              </div>
              {/* Connector */}
              <div className="flex md:flex-1 items-center justify-center md:px-2" aria-hidden="true">
                <span className="hidden md:block w-full h-px bg-[var(--border)]"></span>
                <span className="md:hidden text-[var(--text-muted)] text-xl">&darr;</span>
                <span className="hidden md:inline text-[var(--text-muted)] text-xl">&rarr;</span>
              </div>
              {/* Brain */}
              <div className="bg-[var(--primary)]/5 border-2 border-[var(--primary)]/40 rounded-2xl px-6 py-6 text-center md:w-72 shrink-0">
                <div className="font-extrabold tracking-wide text-[var(--primary)]">ATTUNE PROJECT BRAIN</div>
                <div className="text-xs text-[var(--text-muted)] mt-2 leading-relaxed">
                  Memory &middot; Specs &middot; Lessons &middot; Grounding &middot; Verification
                </div>
              </div>
              {/* Connector */}
              <div className="flex md:flex-1 items-center justify-center md:px-2" aria-hidden="true">
                <span className="hidden md:block w-full h-px bg-[var(--border)]"></span>
                <span className="md:hidden text-[var(--text-muted)] text-xl">&darr;</span>
                <span className="hidden md:inline text-[var(--text-muted)] text-xl">&rarr;</span>
              </div>
              {/* Repository */}
              <div className="bg-[var(--surface)] border border-[var(--border)]/60 rounded-xl px-6 py-5 text-center font-mono text-sm font-bold md:w-52 shrink-0 self-center w-full md:self-auto">
                Your repository
              </div>
            </div>
            <figcaption className="text-xs text-[var(--text-muted)] text-center mt-6">
              Cross-model review and deliberation are advisory &mdash; you
              decide what gets adopted.
            </figcaption>
          </figure>
        </section>

        {/* 6 — Proof */}
        <section className="py-20 bg-[var(--surface-container-low)]" aria-label="Proof points">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-extrabold">Measured, not promised.</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <div>
                <div className="text-4xl font-extrabold text-[var(--primary)]">{METRICS.testsFloor}</div>
                <div className="text-sm text-[var(--text-muted)] mt-1">automated tests</div>
              </div>
              <div>
                <div className="text-4xl font-extrabold text-[var(--primary)]">{METRICS.coverageFloorPct}%</div>
                <div className="text-sm text-[var(--text-muted)] mt-1">coverage floor, CI-enforced</div>
              </div>
              <div>
                <div className="text-4xl font-extrabold text-[var(--primary)]">{METRICS.ragFaithfulness}</div>
                <div className="text-sm text-[var(--text-muted)] mt-1">mean RAG faithfulness, CI-gated</div>
              </div>
              <div>
                <div className="text-4xl font-extrabold text-[var(--primary)]">100%</div>
                <div className="text-sm text-[var(--text-muted)] mt-1">open source &middot; Apache 2.0</div>
              </div>
            </div>
            <div className="text-center mt-10">
              <Link href="/benchmarks" className="text-sm font-bold text-[var(--primary)] hover:opacity-80 transition-opacity">
                See methodology &rarr;
              </Link>
            </div>
          </div>
        </section>

        {/* 7 — Open source */}
        <section className="py-24 px-6 max-w-3xl mx-auto text-center" aria-label="Open source">
          <h2 className="text-4xl md:text-5xl font-extrabold mb-6">Inspect everything.</h2>
          <p className="text-lg text-[var(--text-secondary)] leading-relaxed mb-8">
            Attune is open source under the Apache License 2.0. Every
            workflow, every memory operation, every verification step is code
            you can read, modify, evaluate, and use &mdash; commercially
            included. No black box between your agent and your repository.
          </p>
          <a
            href="https://github.com/Smart-AI-Memory/attune-ai"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-[var(--surface-container-highest)] text-[var(--foreground)] px-8 py-3 rounded-lg font-bold hover:bg-[var(--surface-variant)] transition-colors border border-[var(--border)] no-underline"
          >
            View the source on GitHub
          </a>
        </section>

        {/* 8 — Get started */}
        <section id="get-started" className="py-24 px-6 bg-[var(--surface-container-low)]" aria-label="Get started">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-4xl md:text-5xl font-extrabold">Get started</h2>
            </div>
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              {/* Marketplace-first, matching the README's own ordering:
                  the plugin works standalone — no Python required. */}
              <div className="bg-[var(--surface)] rounded-2xl p-7 border-2 border-[var(--primary)]/40">
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="font-bold text-lg">In Claude Code</h3>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--primary)] bg-[var(--primary)]/10 px-2 py-0.5 rounded-full">
                    Works standalone
                  </span>
                </div>
                <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-xs p-4 mb-4 overflow-x-auto">
                  <div><span className="text-white/50">$ </span>claude plugin marketplace add Smart-AI-Memory/attune-ai</div>
                  <div><span className="text-white/50">$ </span>claude plugin install attune-ai@attune-ai</div>
                </div>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  No Python environment required. Runs on your existing Claude
                  subscription &mdash; then type{' '}
                  <code className="bg-[var(--surface-container-high)] px-1.5 py-0.5 rounded text-xs">/spec</code>{' '}
                  or{' '}
                  <code className="bg-[var(--surface-container-high)] px-1.5 py-0.5 rounded text-xs">/coach</code>{' '}
                  to start.
                </p>
              </div>
              <div className="bg-[var(--surface)] rounded-2xl p-7 border border-[var(--border)]/40">
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="font-bold text-lg">Python package</h3>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] bg-[var(--surface-container-high)] px-2 py-0.5 rounded-full">
                    Adds CLI + MCP
                  </span>
                </div>
                <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-xs p-4 mb-4 overflow-x-auto">
                  <div><span className="text-white/50">$ </span>pip install attune-ai</div>
                </div>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Unlocks the CLI, the MCP server, and multi-agent workflows.
                  With <code className="bg-[var(--surface-container-high)] px-1.5 py-0.5 rounded text-xs">ANTHROPIC_API_KEY</code>{' '}
                  set, large modules fall back to the Anthropic API &mdash; API
                  usage bills API credits, separate from a Claude subscription.
                </p>
              </div>
            </div>
            <p className="text-sm text-[var(--text-muted)] text-center max-w-2xl mx-auto">
              Project memory, retrieval, and the help system are local-first
              &mdash; no API key, no cloud required.
            </p>
            <p className="text-center mt-6">
              <Link href="/docs#quickstart" className="text-sm font-bold text-[var(--primary)] hover:opacity-80 transition-opacity">
                Full installation guide &rarr;
              </Link>
            </p>
          </div>
        </section>

        {/* 9 — Final CTA */}
        <section className="max-w-7xl mx-auto px-6 py-24" aria-label="Call to action">
          <div className="hero-gradient rounded-3xl p-12 md:p-16 text-white relative overflow-hidden text-center">
            <div className="relative z-10 max-w-2xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-extrabold mb-4">
                Your coding agent shouldn&apos;t forget yesterday.
              </h2>
              <p className="text-white/80 text-lg mb-8">
                Give it a persistent project memory.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/docs#quickstart"
                  className="bg-white text-[var(--primary)] px-8 py-3 rounded-lg font-bold hover:bg-[var(--surface-container-low)] transition-colors text-center"
                >
                  Install Attune
                </Link>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-ghost-white border-2 border-white/60 px-8 py-3 rounded-lg font-bold hover:bg-white/15 transition-colors text-center"
                >
                  View on GitHub
                </a>
              </div>
            </div>
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl" aria-hidden="true"></div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
