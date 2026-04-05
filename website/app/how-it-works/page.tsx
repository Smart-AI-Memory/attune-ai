import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';

export const metadata: Metadata = genMeta({
  title: 'How It Works',
  description:
    'From source code to living documentation. Learn how Attune AI generates, serves, and maintains help content.',
  url: 'https://smartaimemory.com/how-it-works',
});

const steps = [
  {
    number: 1,
    name: 'Bootstrap',
    summary: 'Scan your codebase and discover features',
    detail:
      'The scanner reads your project structure, finds modules, classes, and functions, then proposes features with source-glob patterns and tags. Everything lands in .help/features.yaml as the single source of truth.',
  },
  {
    number: 2,
    name: 'Generate',
    summary: 'AI creates templates from your source code',
    detail:
      'For each feature, three Jinja-based templates are generated from actual source code: concept (what is it?), task (how to use it), and reference (full API detail). Each template includes a source hash in its frontmatter for staleness tracking.',
  },
  {
    number: 3,
    name: 'Serve',
    summary: 'Progressive help via attune-help or /coach',
    detail:
      'Ask about a topic and get the concept overview first. Ask again and you auto-advance to the task walkthrough. A third ask delivers the full reference. New topics always reset to concept depth.',
  },
  {
    number: 4,
    name: 'Maintain',
    summary: 'Detect drift and regenerate stale templates',
    detail:
      'Source hashes in each template\'s frontmatter are compared against the current codebase. Only stale templates are regenerated. Hand-written templates marked status: manual are always preserved.',
  },
];

const depthLevels = [
  {
    name: 'Concept',
    color: 'var(--primary)',
    bgClass: 'border-[var(--primary)]',
    tagClass: 'bg-[var(--primary)]',
    description: 'What is it? When to use it?',
    detail: 'A high-level overview that orients you. Explains purpose, context, and when to reach for this feature.',
  },
  {
    name: 'Task',
    color: 'var(--secondary)',
    bgClass: 'border-[var(--secondary)]',
    tagClass: 'bg-[var(--secondary)]',
    description: 'Step-by-step: how to do it',
    detail: 'A practical walkthrough with commands, code snippets, and expected output. Gets you from zero to working.',
  },
  {
    name: 'Reference',
    color: 'var(--accent)',
    bgClass: 'border-[var(--accent)]',
    tagClass: 'bg-[var(--accent)]',
    description: 'Full detail, edge cases, API',
    detail: 'Complete API surface, configuration options, edge cases, and caveats. The exhaustive resource.',
  },
];

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
                From source code to living documentation in four steps.
              </p>
            </div>
          </div>
        </section>

        {/* Four-Step Lifecycle */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-3xl font-bold text-center mb-16">
                The Lifecycle
              </h2>

              <div className="relative">
                {/* Vertical timeline line (desktop only) */}
                <div className="hidden md:block absolute left-1/2 top-0 bottom-0 w-px bg-[var(--border)] -translate-x-1/2" />

                <div className="space-y-12 md:space-y-20">
                  {steps.map((step, index) => {
                    const isLeft = index % 2 === 0;
                    return (
                      <div key={step.number} className="relative">
                        {/* Timeline dot (desktop only) */}
                        <div className="hidden md:flex absolute left-1/2 top-8 -translate-x-1/2 -translate-y-1/2 z-10 w-12 h-12 rounded-full bg-[var(--primary)] text-white items-center justify-center font-bold text-lg shadow-lg">
                          {step.number}
                        </div>

                        {/* Card */}
                        <div
                          className={`md:w-[calc(50%-2.5rem)] ${
                            isLeft ? 'md:mr-auto' : 'md:ml-auto'
                          }`}
                        >
                          <div className="glass-panel rounded-xl p-8">
                            {/* Step number (mobile only) */}
                            <div className="md:hidden flex items-center gap-3 mb-4">
                              <div className="w-10 h-10 rounded-full bg-[var(--primary)] text-white flex items-center justify-center font-bold text-sm shrink-0">
                                {step.number}
                              </div>
                              <h3 className="text-2xl font-bold">
                                {step.name}
                              </h3>
                            </div>
                            {/* Step name (desktop only) */}
                            <h3 className="hidden md:block text-2xl font-bold mb-2">
                              {step.name}
                            </h3>
                            <p className="text-lg font-medium text-[var(--primary)] mb-3">
                              {step.summary}
                            </p>
                            <p className="text-[var(--text-secondary)] leading-relaxed">
                              {step.detail}
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

        {/* Progressive Depth */}
        <section className="py-20 bg-[var(--surface-container-low)]">
          <div className="container">
            <div className="max-w-5xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-3xl font-bold mb-4">
                  Progressive Depth
                </h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  Each topic has three layers. Ask once for the overview,
                  again for the walkthrough, a third time for the full
                  reference.
                </p>
              </div>

              <div className="grid md:grid-cols-3 gap-8">
                {depthLevels.map((level) => (
                  <div
                    key={level.name}
                    className={`bg-[var(--background)] rounded-xl p-8 border-t-4 ${level.bgClass} border-b border-l border-r border-b-[var(--border)] border-l-[var(--border)] border-r-[var(--border)]`}
                  >
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-semibold text-white mb-4 ${level.tagClass}`}
                    >
                      {level.name}
                    </span>
                    <h3 className="text-xl font-bold mb-2">
                      {level.description}
                    </h3>
                    <p className="text-[var(--text-secondary)] text-sm leading-relaxed">
                      {level.detail}
                    </p>
                  </div>
                ))}
              </div>

              <p className="text-center text-sm text-[var(--text-secondary)] mt-8">
                Repeat calls auto-advance. New topic resets to concept.
              </p>
            </div>
          </div>
        </section>

        {/* Human Enhancement */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-3xl font-bold mb-4">
                  AI Writes the First Draft. You Make It Yours.
                </h2>
                <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                  Templates are generated from your source code, but
                  you always have the final say.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4">&#x1f916;</div>
                  <h3 className="text-xl font-bold mb-3">
                    Generated Templates
                  </h3>
                  <ul className="space-y-3 text-[var(--text-secondary)]">
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Created automatically from source code using
                        Jinja templates
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Frontmatter tracks source hash, status, and
                        generation timestamp
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--primary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Regenerated when source code changes and the
                        hash drifts
                      </span>
                    </li>
                  </ul>
                </div>

                <div className="glass-panel rounded-xl p-8">
                  <div className="text-3xl mb-4">&#x270d;&#xfe0f;</div>
                  <h3 className="text-xl font-bold mb-3">
                    Hand-Written Content
                  </h3>
                  <ul className="space-y-3 text-[var(--text-secondary)]">
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Edit any generated template or create new ones
                        from scratch
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        Mark with{' '}
                        <code className="text-sm">status: manual</code>{' '}
                        to protect from regeneration
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--secondary)] mt-1 shrink-0">&#x2022;</span>
                      <span>
                        The maintenance pass always preserves
                        hand-written templates
                      </span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 bg-[var(--surface-container-low)]">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl font-bold mb-4">
                Ready to bootstrap your help system?
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                One command scans your codebase and generates living
                documentation.
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
