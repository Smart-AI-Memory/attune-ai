import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';

export const metadata: Metadata = genMeta({
  title: 'Documentation',
  description:
    'Get started with Attune-AI — the spec-driven development platform. Install in one command, then turn requirements into reliable software with AI workflows, project memory, retrieval grounding, and verification.',
  url: 'https://smartaimemory.com/docs',
});

const faqItems = [
  {
    question: 'What is attune-ai?',
    answer:
      'A development platform built around project memory that turns requirements into reliable software. Memory leads; AI workflows, retrieval grounding, and verification support it in one reliability loop: specify with /spec, ground every change in your real code, build with a team of workflows, remember what worked across sessions, and verify the output before it ships.',
  },
  {
    question: 'How does it keep generated content from drifting?',
    answer:
      'Retrieval grounding (powered by attune-rag, a built-in dependency) keeps generated content anchored to your actual source — mean faithfulness is at least 0.97 and CI-gated, so drift fails the build. For docs specifically, templates carry source file hashes; when code changes, staleness detection flags the affected templates so they can be regenerated automatically.',
  },
  {
    question: 'Do I need attune-ai to read templates?',
    answer:
      'No. The standalone attune-help package (1 dependency) can read any .help/ directory without the full framework. Generate templates with attune-author or attune-ai, then ship them alongside attune-help for a minimal runtime with no Anthropic API key required.',
  },
  {
    question: 'Can I write templates by hand?',
    answer:
      'Yes. Hand-written templates are preserved during regeneration. Remove the auto-discovered tag from frontmatter and the maintenance system will skip the file.',
  },
  {
    question: 'How does staleness detection work?',
    answer:
      'Each template stores SHA-256 hashes of the source files it was generated from. The maintenance workflow re-hashes those files and compares. If the hash changed, the template is flagged stale and queued for regeneration.',
  },
  {
    question: 'Is it free? What do I need to run it?',
    answer:
      'Fully open source under Apache 2.0 — free for personal, commercial, and enterprise use, with no license keys and no usage limits. It works on a Claude subscription or an API key, so you can run it with whichever access you already have.',
  },
  {
    question: 'What Claude Code skills are included?',
    answer:
      '24 auto-invoking skills: security audit, smart test, code quality, bug prediction, doc generation, refactor planning, release prep, planning, spec-driven development, fix-test, workflow orchestration, RAG-grounded code generation, content verification, cross-session recall, memory and context, personal memory, image analysis, batch processing, capability catalog, discovery sweep, form-driven elicitation, the coach help system, the attune hub router, and single-source feature-page authoring.',
  },
  {
    question: 'Where do I install attune-help and attune-author from?',
    answer:
      'Both ship on PyPI: `pip install attune-help` (the reader, no API key required) and `pip install \'attune-author[plugin]\'` (the AI authoring companion). Their Claude Code plugin versions now live in the same Smart-AI-Memory/attune-ai marketplace as attune-ai itself: `claude plugin marketplace add Smart-AI-Memory/attune-ai`, then `claude plugin install attune-help@attune-ai` / `attune-author@attune-ai`. (The old Smart-AI-Memory/attune-docs marketplace is retired.)',
  },
];

const workflows = [
  { name: 'Security Audit', description: 'OWASP-focused vulnerability scan' },
  { name: 'Code Review', description: 'Multi-tier analysis with architecture feedback' },
  { name: 'Bug Prediction', description: 'Pattern-based risk scoring' },
  { name: 'Test Generation', description: 'Parametrized pytest generation' },
  { name: 'Deep Review', description: 'Multi-pass security, quality, and test gap analysis' },
  { name: 'Documentation', description: 'Docstring and API reference generation' },
  { name: 'Performance Audit', description: 'Profiling and optimization suggestions' },
  { name: 'Refactoring', description: 'Code smell detection and roadmap' },
  { name: 'Release Prep', description: 'Changelog, version bump, health checks' },
];

// The 24 plugin skills — keep in sync with plugin/skills/
// (test_skill_count asserts the directory count).
const skills = [
  'security-audit', 'smart-test', 'code-quality', 'bug-predict',
  'doc-gen', 'refactor-plan', 'release-prep', 'planning',
  'spec', 'fix-test', 'workflow-orchestration', 'rag-code-gen',
  'verify', 'recall', 'memory-and-context', 'personal-memory',
  'image-analysis', 'bulk', 'catalog', 'discovery-sweep',
  'elicit', 'coach', 'attune-hub', 'author-feature',
];

export default function DocsPage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Docs', url: 'https://smartaimemory.com/docs' },
    ],
  });

  const faqSchema = generateStructuredData('faq', {
    questions: faqItems,
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
              <h1 className="text-5xl font-bold mb-6">Documentation</h1>
              <p className="text-xl opacity-90 mb-8">
                Everything you need to turn requirements into reliable
                software — install in one command, then run the reliability
                loop: specify, ground, build, remember, verify.
              </p>
              <nav className="flex flex-wrap justify-center gap-3">
                <a href="#quickstart" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  Quick Start
                </a>
                <a href="#attune-ai" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  Framework
                </a>
                <a href="#attune-help" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  Reader
                </a>
                <a href="#attune-author" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  Authoring
                </a>
                <a href="#plugin" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  Plugin
                </a>
                <a href="#workflows" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  Workflows
                </a>
                <a href="#faq" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  FAQ
                </a>
              </nav>
            </div>
          </div>
        </section>

        {/* Quick Start */}
        <section id="quickstart" className="py-20">
          <div className="container">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-4">Quick Start</h2>
              <p className="text-center text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto">
                Install the platform, or pick the piece that fits the job.
                Works on a Claude subscription or an API key. Everything is
                open source under Apache 2.0.
              </p>

              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* attune-help */}
                <div className="bg-[var(--background)] border-2 border-[var(--primary)] rounded-lg p-6 flex flex-col relative">
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--primary)] text-white text-xs font-bold px-3 py-1 rounded-full">
                    Recommended
                  </div>
                  <div className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider mb-2">
                    Reader Only
                  </div>
                  <h3 className="text-lg font-bold mb-2">attune-help</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-5 flex-1">
                    Lightweight reader for .help/ templates. 1 dependency,
                    6 files. Embed in any Python tool. No AI key required.
                  </p>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-xs p-3">
                    <span className="text-white/50">$ </span>pip install attune-help
                  </div>
                </div>

                {/* attune-ai */}
                <div className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-6 flex flex-col">
                  <div className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider mb-2">
                    Full Platform
                  </div>
                  <h3 className="text-lg font-bold mb-2">attune-ai</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-5 flex-1">
                    The whole platform: spec engine, AI workflows, project
                    memory, retrieval grounding, and verification.
                    20 workflows, 24 skills, 47 MCP tools.
                  </p>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-xs p-3">
                    <span className="text-white/50">$ </span>pip install attune-ai
                  </div>
                </div>

                {/* attune-author */}
                <div className="bg-[var(--background)] border-2 border-[var(--primary)] rounded-lg p-6 flex flex-col relative">
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--primary)] text-white text-xs font-bold px-3 py-1 rounded-full">
                    Recommended
                  </div>
                  <div className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider mb-2">
                    AI Authoring
                  </div>
                  <h3 className="text-lg font-bold mb-2">attune-author</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-5 flex-1">
                    Generate 15 kinds of source-grounded templates with
                    per-type polish prompts. Pairs with attune-help.
                  </p>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-xs p-3 break-all">
                    <span className="text-white/50">$ </span>pip install &apos;attune-author[plugin]&apos;
                  </div>
                </div>

                {/* Claude Code Plugin */}
                <div className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-6 flex flex-col">
                  <div className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider mb-2">
                    Claude Code
                  </div>
                  <h3 className="text-lg font-bold mb-2">Plugin</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-5 flex-1">
                    Install from the marketplace. Type /coach for
                    progressive help right in your terminal.
                  </p>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-xs p-3 break-all">
                    <span className="text-white/50">$ </span>claude plugin marketplace add Smart-AI-Memory/attune-ai
                  </div>
                </div>
              </div>

              {/* attune-help / attune-author install */}
              <div className="mt-10 bg-[var(--surface-container-low)] border border-[var(--border)] rounded-lg p-6">
                <h3 className="font-bold text-lg mb-2">
                  Installing attune-help and attune-author
                </h3>
                <p className="text-sm text-[var(--text-secondary)] mb-4">
                  Both ship as Python packages on PyPI, and their Claude
                  Code plugin versions now live in the same{" "}
                  <code className="text-xs bg-[var(--surface-container-high)] px-1 rounded">
                    Smart-AI-Memory/attune-ai
                  </code>{" "}
                  marketplace as attune-ai itself.
                </p>
                <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-xs p-4 leading-relaxed">
                  <div className="text-white/50"># Install from PyPI</div>
                  <div>pip install attune-help</div>
                  <div>pip install &apos;attune-author[plugin]&apos;</div>
                  <br />
                  <div className="text-white/50"># Or as Claude Code plugins from the attune-ai marketplace</div>
                  <div>claude plugin marketplace add Smart-AI-Memory/attune-ai</div>
                  <div>claude plugin install attune-help@attune-ai</div>
                  <div>claude plugin install attune-author@attune-ai</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Attune AI Framework */}
        <section id="attune-ai" className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-4">
                Attune AI Platform
              </h2>
              <p className="text-center text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto">
                Beyond AI workflows and verification, the platform keeps your
                docs grounded too: scan your codebase, generate templates,
                detect when code drifts, and regenerate stale content.
              </p>

              <div className="grid md:grid-cols-2 gap-8 mb-12">
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                  <h3 className="font-bold text-lg mb-2">1. Bootstrap</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-3">
                    Scan your project to discover features. The scanner reads
                    modules, classes, and functions, then proposes a
                    features.yaml manifest.
                  </p>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-sm p-3">
                    /coach init
                  </div>
                </div>

                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                  <h3 className="font-bold text-lg mb-2">2. Generate</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-3">
                    For each feature, three templates are created: concept
                    (what is it?), task (how to use it), and reference
                    (full API detail). Content comes from actual source code.
                  </p>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-sm p-3">
                    /coach maintain
                  </div>
                </div>

                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                  <h3 className="font-bold text-lg mb-2">3. Staleness Detection</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-3">
                    Source file SHA-256 hashes are stored in template
                    frontmatter. When code changes, stale templates are
                    flagged automatically.
                  </p>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-sm p-3">
                    /coach status
                  </div>
                </div>

                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                  <h3 className="font-bold text-lg mb-2">4. Maintenance</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-3">
                    Regenerate only the templates whose source changed.
                    Hand-written templates are preserved. Run on-demand
                    or via CI.
                  </p>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-sm p-3">
                    /coach maintain
                  </div>
                </div>
              </div>

              <div className="text-center">
                <Link
                  href="/framework-docs/"
                  className="inline-flex items-center gap-2 text-[var(--primary)] hover:underline font-semibold"
                >
                  Deep API reference in framework docs
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Attune Help (Standalone Reader) */}
        <section id="attune-help" className="py-20">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-4">
                Attune Help (Standalone Reader)
              </h2>
              <p className="text-center text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto">
                A lightweight Python package that reads .help/ templates.
                1 dependency, 6 files, embeddable anywhere.
              </p>

              <div className="grid md:grid-cols-2 gap-8 mb-10">
                <div>
                  <h3 className="font-bold text-lg mb-4">Features</h3>
                  <ul className="space-y-3">
                    <li className="flex items-start gap-2 text-[var(--text-secondary)]">
                      <span className="text-[var(--primary)] mt-1 font-bold">1</span>
                      <span>
                        <strong className="text-[var(--foreground)]">1 dependency</strong> &mdash;
                        python-frontmatter. No bloat.
                      </span>
                    </li>
                    <li className="flex items-start gap-2 text-[var(--text-secondary)]">
                      <span className="text-[var(--primary)] mt-1 font-bold">2</span>
                      <span>
                        <strong className="text-[var(--foreground)]">Progressive depth</strong> &mdash;
                        concept on first ask, task on repeat, reference on third.
                      </span>
                    </li>
                    <li className="flex items-start gap-2 text-[var(--text-secondary)]">
                      <span className="text-[var(--primary)] mt-1 font-bold">3</span>
                      <span>
                        <strong className="text-[var(--foreground)]">Session storage</strong> &mdash;
                        file-based or custom backend. Tracks depth per topic.
                      </span>
                    </li>
                    <li className="flex items-start gap-2 text-[var(--text-secondary)]">
                      <span className="text-[var(--primary)] mt-1 font-bold">4</span>
                      <span>
                        <strong className="text-[var(--foreground)]">Multiple renderers</strong> &mdash;
                        plain text, CLI, Claude Code, marketplace.
                      </span>
                    </li>
                  </ul>
                </div>

                <div>
                  <h3 className="font-bold text-lg mb-4">Usage</h3>
                  <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-sm p-5 leading-relaxed">
                    <div className="text-white/50 mb-2"># Install</div>
                    <div className="mb-4">pip install attune-help</div>
                    <div className="text-white/50 mb-2"># Use</div>
                    <div className="text-blue-300">from</div>{' '}
                    attune_help{' '}
                    <div className="text-blue-300 inline">import</div>{' '}
                    HelpEngine
                    <br />
                    <br />
                    engine = HelpEngine(
                    <br />
                    <span className="ml-4">template_dir=</span>
                    <span className="text-green-300">&quot;.help/templates&quot;</span>
                    <br />
                    )
                    <br />
                    result = engine.lookup(
                    <span className="text-green-300">&quot;security-audit&quot;</span>
                    )
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Attune Author (AI authoring companion) */}
        <section id="attune-author" className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-4">
                Attune Author
              </h2>
              <p className="text-center text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto">
                The AI authoring companion for attune-help. Generates
                source-grounded templates from your codebase and
                polishes them with per-type LLM prompts.
              </p>

              <div className="grid md:grid-cols-2 gap-8 mb-10">
                <div>
                  <h3 className="font-bold text-lg mb-4">11 Template Kinds</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-4">
                    Up from 3 in v0.1.0. The generator produces the
                    full set of shapes attune-help renders:
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">concept</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">task</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">reference</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">error</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">warning</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">troubleshooting</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">faq</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">quickstart</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">tip</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">note</div>
                    <div className="bg-[var(--background)] border border-[var(--border)] rounded px-2 py-1">comparison</div>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)] mt-4">
                    Default calls produce the original three kinds
                    unchanged. The eight new kinds are strictly
                    opt-in via the <code className="text-xs bg-[var(--surface-container-high)] px-1 rounded">depths=</code> kwarg.
                  </p>
                </div>

                <div>
                  <h3 className="font-bold text-lg mb-4">Per-Type Polish</h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-4">
                    Each template kind gets its own system prompt
                    that teaches the LLM what &ldquo;good&rdquo; looks
                    like for that shape:
                  </p>
                  <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                    <li>
                      <strong className="text-[var(--foreground)]">Concept</strong> &mdash;
                      definitional clarity and mental models
                    </li>
                    <li>
                      <strong className="text-[var(--foreground)]">Task</strong> &mdash;
                      &ldquo;Use X when&hellip;&rdquo; openers and
                      verifiable success criteria
                    </li>
                    <li>
                      <strong className="text-[var(--foreground)]">Troubleshooting</strong> &mdash;
                      symptom tables and step-by-step diagnosis
                    </li>
                    <li>
                      <strong className="text-[var(--foreground)]">Comparison</strong> &mdash;
                      decision tables with &ldquo;Use X when&hellip;&rdquo;
                      recommendations
                    </li>
                  </ul>
                  <p className="text-sm text-[var(--text-secondary)] mt-4">
                    Plus signature-aware source summaries that feed
                    the LLM typed function and method signatures, so
                    the polished output stays factually grounded in
                    your actual code.
                  </p>
                </div>
              </div>

              <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                <h3 className="font-bold text-lg mb-4">Install and Generate</h3>
                <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-xs p-4 leading-relaxed mb-4">
                  <div className="text-white/50"># PyPI install (includes the polish runtime)</div>
                  <div>pip install &apos;attune-author[plugin]&apos;</div>
                  <br />
                  <div className="text-white/50"># Or the Claude Code plugin from the attune-ai marketplace</div>
                  <div>claude plugin install attune-author@attune-ai</div>
                </div>
                <p className="text-sm text-[var(--text-secondary)]">
                  Requires <code className="text-xs bg-[var(--surface-container-high)] px-1 rounded">ANTHROPIC_API_KEY</code> for
                  the polish pass. Without it, the generator falls
                  back to the raw Jinja2 drafts. Set
                  <code className="text-xs bg-[var(--surface-container-high)] px-1 rounded">ATTUNE_AUTHOR_STRICT_POLISH=1</code> to
                  make polish failures hard errors for CI.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Claude Code Plugin */}
        <section id="plugin" className="py-20">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-4">
                Claude Code Plugin
              </h2>
              <p className="text-center text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto">
                Install from the marketplace. Progressive help, project
                bootstrapping, and 24 skills right in your terminal.
              </p>

              <div className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-8 mb-8">
                <h3 className="font-bold text-lg mb-4">Install</h3>
                <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-sm p-4 mb-2">
                  <span className="text-white/50">$ </span>
                  claude plugin marketplace add Smart-AI-Memory/attune-ai
                </div>
                <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-sm p-4">
                  <span className="text-white/50">$ </span>
                  claude plugin install attune-ai@attune-ai
                </div>
              </div>

              <h3 className="font-bold text-lg mb-4">/coach Commands</h3>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-5">
                  <code className="text-[var(--primary)] font-bold text-sm">
                    /coach &lt;topic&gt;
                  </code>
                  <p className="text-sm text-[var(--text-secondary)] mt-2">
                    Progressive lookup. First call returns concept, repeat
                    returns task, third returns reference.
                  </p>
                </div>
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-5">
                  <code className="text-[var(--primary)] font-bold text-sm">
                    /coach init
                  </code>
                  <p className="text-sm text-[var(--text-secondary)] mt-2">
                    Bootstrap a .help/ directory for your project. Scans
                    source code and generates features.yaml.
                  </p>
                </div>
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-5">
                  <code className="text-[var(--primary)] font-bold text-sm">
                    /coach status
                  </code>
                  <p className="text-sm text-[var(--text-secondary)] mt-2">
                    Check template freshness. Shows which features have
                    drifted from their source files.
                  </p>
                </div>
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-5">
                  <code className="text-[var(--primary)] font-bold text-sm">
                    /coach maintain
                  </code>
                  <p className="text-sm text-[var(--text-secondary)] mt-2">
                    Regenerate stale templates. Only updates files whose
                    source hashes changed.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Workflows & Skills */}
        <section id="workflows" className="py-20">
          <div className="container">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-4">
                Workflows &amp; Skills
              </h2>
              <p className="text-center text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto">
                The build half of the loop: 20 workflows,
                24 auto-triggering Claude Code skills,
                and an MCP server with 47 registered tools — review, tests,
                bug prediction, refactor, and release prep.
              </p>

              <div className="grid md:grid-cols-2 gap-8 mb-12">
                <div>
                  <h3 className="font-bold text-lg mb-4">Key Workflows</h3>
                  <div className="space-y-3">
                    {workflows.map((wf) => (
                      <div
                        key={wf.name}
                        className="flex items-start gap-3 bg-[var(--background)] border border-[var(--border)] rounded-lg p-3"
                      >
                        <div>
                          <div className="font-semibold text-sm">{wf.name}</div>
                          <div className="text-xs text-[var(--text-secondary)]">
                            {wf.description}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-bold text-lg mb-4">
                    24 Claude Code Skills
                  </h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-4">
                    Skills auto-invoke from natural language. Type the topic
                    and the right skill fires.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-block bg-[var(--surface)] text-[var(--foreground)] border border-[var(--border)] rounded-full px-3 py-1 text-sm font-mono"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>

                  <div className="mt-8">
                    <h4 className="font-bold text-sm mb-3">Run from CLI</h4>
                    <div className="bg-[#213145] text-white/90 rounded-xl font-mono text-sm p-4 leading-relaxed">
                      <div className="text-white/50"># Run a workflow</div>
                      <div>attune workflow run security-audit \</div>
                      <div className="ml-4">--input &apos;{'{'}&#34;path&#34;:&#34;./src&#34;{'}'}&apos;</div>
                      <br />
                      <div className="text-white/50"># Or use Claude Code</div>
                      <div>/security scan my auth module</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="text-center">
                <Link
                  href="/framework-docs/"
                  className="inline-flex items-center gap-2 text-[var(--primary)] hover:underline font-semibold"
                >
                  Full workflow documentation
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-12">
                Frequently Asked Questions
              </h2>

              <div className="space-y-6">
                {faqItems.map((item) => (
                  <div
                    key={item.question}
                    className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6"
                  >
                    <h3 className="font-bold mb-2">{item.question}</h3>
                    <p className="text-sm text-[var(--text-secondary)]">
                      {item.answer}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-4xl font-bold mb-6">Ready to Get Started?</h2>
              <p className="text-xl mb-8 opacity-90">
                Install in one command, then run /spec on your next feature
                and turn requirements into reliable software.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >
                  View on GitHub
                </a>
                <a
                  href="#quickstart"
                  className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >
                  Install Now
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
