import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import GitHubStarsBadge from '@/components/GitHubStarsBadge';
import TestsBadge from '@/components/TestsBadge';
import { generateStructuredData } from '@/lib/metadata';
import { installCommand } from '@/lib/install-command';

// Doc-toolchain code sample. attune-ai is the parent
// framework (headlined in the hero); the four packages
// below are the standalone documentation toolchain we
// built with it.
const codeExample = `# 1. attune-author — generate polished, source-grounded
#    templates from your codebase (CI or dev time)
from attune_author.generator import generate_feature_templates
generate_feature_templates(feature, help_dir=".help", project_root=".")

# 2. attune-rag — keyword + semantic retrieval keeps
#    answers grounded. Mean faithfulness ≥ 0.97, CI-gated.

# 3. attune-help — read them at runtime. 1 dependency,
#    no API key required. Embed anywhere.
from attune_help import HelpEngine
engine = HelpEngine(template_dir=".help/templates")
print(engine.lookup("security-audit"))

# 4. attune-gui — local dashboard tying it all together.
#    ${installCommand()} && attune-gui --open`;

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

        {/* Hero Section */}
        <section className="relative overflow-hidden px-6 py-24 md:py-32" aria-label="Hero">
          <div className="max-w-7xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <div className="z-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--surface-container-high)] text-[var(--primary)] text-xs font-bold tracking-widest mb-6 uppercase">
                  <span>v6.5.4</span>
                  <span className="w-1 h-1 rounded-full bg-[var(--primary)]"></span>
                  <span className="opacity-80">AI Workflow OS for Claude Code</span>
                </div>
                <h1 className="text-5xl md:text-7xl font-extrabold tracking-tighter mb-8 leading-[1.1]">
                  AI Workflows for{' '}
                  <span className="text-gradient">Claude Code</span>
                </h1>
                <p className="text-lg md:text-xl text-[var(--text-secondary)] mb-10 max-w-xl leading-relaxed">
                  15 workflows, 14 auto-triggering skills, MCP server with 41 tools.
                  Plus the documentation toolchain we built along the way &mdash;
                  now four standalone packages.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <a
                    href="https://pypi.org/project/attune-ai/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-[var(--primary)] !text-white px-8 py-3 rounded-lg font-bold hover:opacity-90 transition-opacity text-center no-underline"
                  >
                    attune-ai on PyPI
                  </a>
                  <a
                    href="https://github.com/Smart-AI-Memory/attune-ai"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-[var(--surface-container-highest)] text-[var(--foreground)] px-8 py-3 rounded-lg font-bold hover:bg-[var(--surface-variant)] transition-colors text-center border border-[var(--border)] no-underline"
                  >
                    Star on GitHub
                  </a>
                  <Link
                    href="/how-it-works"
                    className="bg-[var(--surface-container-highest)] text-[var(--foreground)] px-8 py-3 rounded-lg font-bold hover:bg-[var(--surface-variant)] transition-colors text-center border border-[var(--border)]"
                  >
                    See How It Works
                  </Link>
                </div>
                {/* Trust badges */}
                <div className="flex flex-wrap gap-3 mt-8">
                  <GitHubStarsBadge />
                  <TestsBadge />
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--surface-container-high)] text-xs font-medium">
                    Apache 2.0
                  </span>
                </div>
              </div>

              {/* Depth cards visual */}
              <div className="relative">
                <div className="relative z-10 rounded-2xl overflow-hidden bg-[var(--surface-container-low)] p-8 border border-[var(--border)]/40 shadow-2xl">
                  <div className="flex items-center gap-2 mb-6">
                    <div className="w-3 h-3 rounded-full bg-red-500/40"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500/40"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500/40"></div>
                    <span className="ml-auto text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Progressive Depth</span>
                  </div>

                  {/* Code icon connecting to depth cards */}
                  <div className="flex items-center justify-center mb-6">
                    <div className="w-12 h-12 rounded-lg bg-[var(--surface-container-high)] border border-[var(--border)]/30 flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <polyline points="16 18 22 12 16 6" />
                        <polyline points="8 6 2 12 8 18" />
                      </svg>
                    </div>
                  </div>

                  {/* Connection lines */}
                  <div className="flex justify-center mb-4">
                    <div className="w-px h-4 bg-[var(--border)]"></div>
                  </div>
                  <div className="flex justify-between px-8 mb-2">
                    <div className="flex-1 flex justify-center">
                      <div className="w-full h-px bg-[var(--border)]"></div>
                    </div>
                  </div>

                  {/* Three depth cards */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="rounded-lg p-4 bg-[var(--primary)]/10 border border-[var(--primary)]/20 flex flex-col items-center justify-center text-center min-h-[100px]">
                      <span className="text-xs font-bold text-[var(--primary)] tracking-wider uppercase mb-2">Concept</span>
                      <p className="text-[10px] text-[var(--text-secondary)] leading-tight">What is it?</p>
                    </div>
                    <div className="rounded-lg p-4 bg-[var(--secondary)]/10 border border-[var(--secondary)]/20 flex flex-col items-center justify-center text-center min-h-[100px]">
                      <span className="text-xs font-bold text-[var(--secondary)] tracking-wider uppercase mb-2">Task</span>
                      <p className="text-[10px] text-[var(--text-secondary)] leading-tight">How to do it?</p>
                    </div>
                    <div className="rounded-lg p-4 bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex flex-col items-center justify-center text-center min-h-[100px]">
                      <span className="text-xs font-bold text-[var(--accent)] tracking-wider uppercase mb-2">Reference</span>
                      <p className="text-[10px] text-[var(--text-secondary)] leading-tight">Full API detail</p>
                    </div>
                  </div>
                </div>
                {/* Background blur */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[140%] h-[140%] bg-gradient-to-tr from-[var(--surface-container-high)]/50 to-transparent rounded-full blur-3xl -z-10"></div>
              </div>
            </div>
          </div>
        </section>

        {/* Platform overview — one code sample, three packages */}
        <section className="py-24 bg-[var(--surface-container-low)]" aria-label="Platform overview">
          <div className="max-w-7xl mx-auto px-6">
            <div className="flex flex-col md:flex-row gap-16 items-start">
              <div className="md:w-2/5">
                <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-3 block">Sister Family</span>
                <h2 className="text-3xl font-extrabold mb-6">The Documentation Toolchain</h2>
                <p className="text-[var(--text-secondary)] mb-8 leading-relaxed">
                  We built attune-ai to make our own docs better. The
                  doc toolchain split off as four standalone packages
                  &mdash; an end-to-end author &rarr; reader loop. Use
                  the full stack, or drop in just the piece you need.
                </p>
                <ul className="space-y-5">
                  <li className="flex items-start gap-3">
                    <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[var(--accent)]/15 text-[var(--accent)] font-bold text-xs shrink-0 mt-0.5">1</span>
                    <div>
                      <div className="font-semibold text-sm"><code className="font-mono">attune-author</code></div>
                      <p className="text-xs text-[var(--text-secondary)] leading-relaxed mt-1">
                        Generates 11 kinds of source-grounded templates with
                        per-type LLM polish. Runs at dev time or in CI.
                      </p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[var(--accent)]/15 text-[var(--accent)] font-bold text-xs shrink-0 mt-0.5">2</span>
                    <div>
                      <div className="font-semibold text-sm"><code className="font-mono">attune-rag</code></div>
                      <p className="text-xs text-[var(--text-secondary)] leading-relaxed mt-1">
                        Keyword + semantic retrieval, mean faithfulness &ge; 0.97
                        (CI-gated) &mdash; answers stay grounded in your code.
                      </p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[var(--secondary)]/15 text-[var(--secondary)] font-bold text-xs shrink-0 mt-0.5">3</span>
                    <div>
                      <div className="font-semibold text-sm"><code className="font-mono">attune-help</code></div>
                      <p className="text-xs text-[var(--text-secondary)] leading-relaxed mt-1">
                        Reads the templates at runtime. 1 dependency, no API
                        key required. Embed in any Python tool.
                      </p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[var(--surface-container-high)] text-[var(--foreground)] font-bold text-xs shrink-0 mt-0.5">4</span>
                    <div>
                      <div className="font-semibold text-sm"><code className="font-mono">attune-gui</code></div>
                      <p className="text-xs text-[var(--text-secondary)] leading-relaxed mt-1">
                        Local dashboard. Browse templates, edit specs,
                        run commands &mdash; one pane for the whole stack.
                      </p>
                    </div>
                  </li>
                </ul>
                <div className="mt-8 pt-6 border-t border-[var(--border)]/40">
                  <p className="text-xs text-[var(--text-muted)]">
                    All four are open source &mdash; Apache 2.0.
                  </p>
                </div>
              </div>
              <div className="md:w-3/5 w-full">
                <div className="bg-[#213145] rounded-xl overflow-hidden shadow-2xl">
                  <div className="flex items-center px-4 py-2 bg-[#2a3b50] border-b border-white/5">
                    <span className="text-[10px] font-mono text-white/50 uppercase tracking-widest">author_reader_loop.py</span>
                    <div className="ml-auto flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-white/10"></div>
                      <div className="w-2.5 h-2.5 rounded-full bg-white/10"></div>
                    </div>
                  </div>
                  <div className="p-6 font-mono text-sm overflow-x-auto">
                    <pre className="text-white/90 leading-relaxed"><code>{codeExample}</code></pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Four Product Cards */}
        <section className="py-32 px-6 max-w-7xl mx-auto" aria-label="Products">
          <div className="text-center mb-20">
            <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">Core Capabilities</span>
            <h2 className="text-4xl md:text-5xl font-extrabold">Six Ways to Use It</h2>
            <p className="text-[var(--text-secondary)] mt-4 max-w-2xl mx-auto">
              The attune-ai framework, its Claude Code plugin, and the
              four-package documentation toolchain we built with it.
              Pick the piece that fits the job.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* attune-ai */}
            <div className="group bg-[var(--surface)] rounded-2xl p-7 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--primary)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all" aria-hidden="true">&#128736;&#65039;</span>
              </div>
              <h3 className="text-xl font-bold mb-3">attune-ai</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                Full framework. Workflows, staleness detection, MCP server, and 14 auto-triggering skills for Claude Code.
              </p>
            </div>

            {/* attune-help */}
            <div className="group bg-[var(--surface)] rounded-2xl p-7 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--secondary)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--secondary)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all" aria-hidden="true">&#128214;</span>
              </div>
              <h3 className="text-xl font-bold mb-3">attune-help</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                Lightweight reader. 1 dependency, 6 files. Embed progressive help in any CLI tool, notebook, or internal app.
              </p>
            </div>

            {/* attune-author */}
            <div className="group bg-[var(--surface)] rounded-2xl p-7 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--accent)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--accent)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all" aria-hidden="true">&#9999;&#65039;</span>
              </div>
              <h3 className="text-xl font-bold mb-3">attune-author</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                AI authoring companion. Generates 11 kinds of source-grounded templates with per-type polish prompts.
              </p>
            </div>

            {/* attune-rag */}
            <div className="group bg-[var(--surface)] rounded-2xl p-7 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--accent)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--accent)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all" aria-hidden="true">&#128269;</span>
              </div>
              <h3 className="text-xl font-bold mb-3">attune-rag</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                Keyword + semantic retrieval over your Markdown corpus. Mean faithfulness &ge; 0.97, CI-gated &mdash; answers stay grounded.
              </p>
            </div>

            {/* attune-gui */}
            <div className="group bg-[var(--surface)] rounded-2xl p-7 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-6 group-hover:bg-[var(--primary)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all" aria-hidden="true">&#128202;</span>
              </div>
              <h3 className="text-xl font-bold mb-3">attune-gui</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                Local dashboard. Browse templates, edit specs, run commands, and watch jobs &mdash; one pane for the whole stack.
              </p>
            </div>

            {/* Claude Code Plugin */}
            <div className="group bg-[var(--surface)] rounded-2xl p-7 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--surface-container-high)] flex items-center justify-center mb-6 group-hover:bg-[var(--foreground)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all" aria-hidden="true">&#9889;</span>
              </div>
              <h3 className="text-xl font-bold mb-3">Claude Code Plugin</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                Type <code className="bg-[var(--surface-container-high)] px-1.5 py-0.5 rounded text-xs">/coach</code> in Claude Code. Progressive help in your terminal &mdash; no setup required.
              </p>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="max-w-7xl mx-auto px-6 pb-24" aria-label="Call to action">
          <div className="grid lg:grid-cols-5 gap-8 items-center">
            <div className="lg:col-span-3 hero-gradient rounded-3xl p-12 text-white relative overflow-hidden">
              <div className="relative z-10">
                <h3 className="text-3xl font-extrabold mb-6">Ready to make your docs live?</h3>
                <p className="text-white/80 text-lg mb-8 max-w-lg">
                  Install from PyPI. Generate templates from your code. Ship help that never goes stale.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link
                    href="/docs"
                    className="bg-white text-[var(--primary)] px-8 py-3 rounded-lg font-bold hover:bg-[var(--surface-container-low)] transition-colors text-center"
                  >
                    Read the Docs
                  </Link>
                  <a
                    href="https://github.com/Smart-AI-Memory/attune-ai"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-ghost-white border-2 border-white/60 px-8 py-3 rounded-lg font-bold hover:bg-white/15 transition-colors text-center"
                  >
                    Star on GitHub
                  </a>
                </div>
              </div>
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
            </div>

            <div className="lg:col-span-2 space-y-6">
              <div className="p-6 border border-[var(--border)]/40 rounded-2xl bg-[var(--surface-container-low)]">
                <div className="flex items-center gap-4 mb-3">
                  <span className="text-[var(--primary)]">&#x1F504;</span>
                  <span className="font-bold">Auto-Freshness</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Source hashes detect code drift. Stale templates regenerate automatically &mdash; your docs stay in sync with your codebase.
                </p>
              </div>
              <div className="p-6 border border-[var(--border)]/40 rounded-2xl bg-[var(--surface-container-low)]">
                <div className="flex items-center gap-4 mb-3">
                  <span className="text-[var(--secondary)]">&#x270F;&#xFE0F;</span>
                  <span className="font-bold">Human-Enhanceable</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Edit generated templates freely, or write from scratch. The engine respects hand-written content and never overwrites your work.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
