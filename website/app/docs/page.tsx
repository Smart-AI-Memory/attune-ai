import type { Metadata } from 'next';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';
import { HARNESS_FAQ_ITEMS } from '@/lib/harness-faq';

export const metadata: Metadata = genMeta({
  title: 'Documentation',
  description:
    'Start with Attune Harness for scoped engineering work, checked results and retained context. Attune AI and companion-package references remain available for existing users.',
  url: 'https://smartaimemory.com/docs',
});

const faqItems = [
  {
    question: 'What is attune-ai?',
    answer:
      'Attune AI combines specification development, AI workflows, project memory, retrieval and verification tools. It is a separate project from Attune Harness. Use the retained references for your installed version, and inspect generated output and the checks that ran.',
  },
  {
    question: 'How can I check generated content for drift?',
    answer:
      'Retrieval through attune-rag supplies source context for review. Source hashes can flag tracked templates for maintenance when the corresponding code changes. These checks cover particular sources and properties; they do not establish the accuracy of every generated answer.',
  },
  {
    question: 'Do I need attune-ai to read templates?',
    answer:
      'No. The standalone attune-help reader can read existing help templates without the full Attune AI framework or an API key. Point it at the template directory described in its package reference. Generating or updating templates is a separate task.',
  },
  {
    question: 'Can I write templates by hand?',
    answer:
      'Yes. Use maintenance: manual in template frontmatter to mark a page as human-maintained and have regeneration skip it. Review the maintenance instructions for your installed Attune AI version before updating templates.',
  },
  {
    question: 'How does staleness detection work?',
    answer:
      'Generated templates can record source hashes. Maintenance compares the recorded and current hashes to identify affected templates. A stale flag identifies a review or regeneration task; it is not proof that the replacement content is correct.',
  },
  {
    question: 'Is it free? What do I need to run it?',
    answer:
      'Attune AI is open source under Apache 2.0, subject to the license conditions. Runtime requirements depend on the workflow; model providers and other external services may require separate credentials and incur charges.',
  },
  {
    question: 'What Claude Code skills are included?',
    answer: 'The retained Attune AI skill reference covers development tasks such as review, testing, specifications and documentation. Skill availability depends on the installed plugin version and host. Inspect that installation rather than treating a website count as an environment check.',
  },
  {
    question: 'Where do I install attune-help from?',
    answer:
      'The standalone attune-help reader is available on PyPI. See its package reference for installation and template-directory setup. Installing a Python reader is separate from installing a host plugin.',
  },
  {
    question: 'What happened to attune-author?',
    answer:
      'Its AI authoring capabilities were consolidated into attune-ai in July 2026, and the standalone package is archived. Already-released versions stay installable from PyPI, but no further releases are planned — for template authoring, install attune-ai and use the author-feature skill or /coach maintain.',
  },
];

export default function DocsPage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Docs', url: 'https://smartaimemory.com/docs' },
    ],
  });

  const faqSchema = generateStructuredData('faq', {
    questions: [...HARNESS_FAQ_ITEMS],
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
              <h1 className="text-5xl font-bold mb-6">Harness docs and project references</h1>
              <p className="text-xl opacity-90 mb-8">
                Start with Attune Harness. Find guidance for useful work,
                execution permissions, checkable results and retained context.
                Earlier Attune AI references follow for existing users.
              </p>
              <nav className="flex flex-wrap justify-center gap-3">
                <a href="#harness-docs" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">Harness</a>
                <a href="#quickstart" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  Harness Quick Start
                </a>
                <a href="#faq" className="px-5 py-2 text-sm rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors">
                  FAQ
                </a>
              </nav>
            </div>
          </div>
        </section>

        <section id="harness-docs" className="py-20">
          <div className="container max-w-5xl">
            <h2 className="text-4xl font-bold mb-4">Start with Attune Harness</h2>
            <p className="text-xl text-[var(--text-secondary)] mb-6">Define a useful next step, build or repair within scope, check the result, and return with the context intact. Choose a workflow from the guide; command syntax is available when you need it.</p>
            <div className="flex flex-wrap gap-4 mb-6">
              <a className="btn btn-primary" href="https://pypi.org/project/attune-harness/1.3.0/#installation">Install Harness</a>
              <a className="btn btn-outline" href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md">Read the Harness guide</a>
              <a className="btn btn-outline" href="https://pypi.org/project/attune-harness/1.3.0/#what-is-qualified-and-what-is-not">Check the qualification limits</a>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">Claude Code and Codex have documented setup paths. Native planning and building remain experimental; Antigravity integration is unverified here. Intent acceptance is separate from paid execution permission.</p>
            <p className="text-sm text-[var(--text-secondary)] mt-4">Harness does not yet replace every Attune AI workflow. <a className="underline" href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/migration-from-attune-ai.md">Review the migration boundaries</a> before changing an existing setup.</p>
          </div>
        </section>

        {/* Harness Quick Start; earlier toolkit references remain below. */}
        <section id="quickstart" className="py-20 bg-[var(--surface-container-low)]">
          <div className="container max-w-5xl">
            <h2 className="text-4xl font-bold mb-4">Harness Quick Start</h2>
            <p className="text-xl text-[var(--text-secondary)] mb-6">
              Install Harness and try a small local check before connecting an agent.
              This setup uses the released 1.3.0 package.
            </p>
            <p className="text-[var(--text-secondary)] mb-8">
              You need Python 3.10 or later. Start in a new working directory and
              keep Harness in its own environment, separate from Attune AI.
              The commands below are for macOS and Linux.
            </p>
            <ol className="space-y-6">
              <li className="p-6">
                <h3 className="text-xl font-bold mb-3">1. Create an environment</h3>
                <pre className="bg-[#263c30] text-white/90 rounded-xl font-mono text-sm p-4 overflow-x-auto"><code>{'python3 -m venv .venv\nsource .venv/bin/activate'}</code></pre>
                <details className="mt-4 text-sm text-[var(--text-secondary)]">
                  <summary className="cursor-pointer font-medium">Windows PowerShell</summary>
                  <p className="my-3">With Python 3.10 or later installed, use these commands instead:</p>
                  <pre className="bg-[#263c30] text-white/90 rounded-xl font-mono text-sm p-4 overflow-x-auto"><code>{'py -3 -m venv .venv\n.venv\\Scripts\\Activate.ps1'}</code></pre>
                </details>
              </li>
              <li className="p-6">
                <h3 className="text-xl font-bold mb-3">2. Install and confirm the version</h3>
                <pre className="bg-[#263c30] text-white/90 rounded-xl font-mono text-sm p-4 overflow-x-auto"><code>{"python -m pip install 'attune-harness[all]==1.3.0'\npython -c \"from importlib.metadata import version; print(version('attune-harness'))\""}</code></pre>
                <p className="mt-3 text-sm text-[var(--text-secondary)]">
                  The version check should print <code>1.3.0</code>. This
                  recommended install adds Redis and Voyage support. The local
                  example below needs no API key. Redis use needs a running
                  Redis service; Voyage retrieval needs a Voyage API key and
                  makes paid calls. Integration requirements are covered in the{' '}
                  <a className="underline" href="https://pypi.org/project/attune-harness/1.3.0/#installation">released installation guide</a>.
                </p>
              </li>
              <li className="p-6">
                <h3 className="text-xl font-bold mb-3">3. Run the local example</h3>
                <pre className="bg-[#263c30] text-white/90 rounded-xl font-mono text-sm p-4 overflow-x-auto"><code>python -m attune_harness</code></pre>
                <p className="mt-3 text-sm text-[var(--text-secondary)]">
                  Expect a JSON receipt with a <code>verified</code> result.
                  A deterministic worker supplies the answer and a separate
                  arithmetic check assesses it. This example makes no model
                  call and needs no API key; it demonstrates the check and receipt,
                  rather than measuring an AI agent&apos;s reliability.
                </p>
              </li>
            </ol>
            <div className="mt-8">
              <h3 className="text-xl font-bold mb-3">Continue with your agent</h3>
              <p className="text-[var(--text-secondary)] mb-5">
                Choose the Claude Code or Codex setup in the release guide.
                Installing the Python package does not install an agent plugin
                or skill. Develop the specification and agree with the scope
                before authorizing execution.
              </p>
              <div className="flex flex-wrap gap-4">
                <a className="btn btn-primary" href="https://pypi.org/project/attune-harness/1.3.0/#use-harness-with-codex-claude-or-other-models">Set up your agent</a>
                <a className="btn btn-outline" href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md">Choose a Harness workflow</a>
              </div>
            </div>
          </div>
        </section>

        {/* Attune Author — consolidated into attune-ai */}
        <section id="attune-author" className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-4">
                Attune Author
              </h2>
              <p className="text-center text-[var(--text-secondary)] mb-8 max-w-2xl mx-auto">
                Consolidated into attune-ai as of July 2026. The
                standalone package is archived on PyPI &mdash; released
                versions stay installable, but no further releases are
                planned.
              </p>

              <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6 max-w-2xl mx-auto">
                <p className="text-sm text-[var(--text-secondary)] mb-4">
                  Its authoring capabilities now ship with the attune-ai
                  platform: the{" "}
                  <code className="text-xs bg-[var(--surface-container-high)] px-1 rounded">
                    author-feature
                  </code>{" "}
                  skill writes a single code-verified master per feature
                  and projects it to the .help template kinds and docs
                  pages, and{" "}
                  <code className="text-xs bg-[var(--surface-container-high)] px-1 rounded">
                    /coach maintain
                  </code>{" "}
                  keeps generated templates in sync with your source.
                  attune-help remains the standalone reader.
                </p>
                <div className="bg-[#263c30] text-white/90 rounded-xl font-mono text-xs p-4 leading-relaxed">
                  <div className="text-white/50"># Authoring now ships with attune-ai</div>
                  <div>pip install attune-ai</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Standalone reader reference; retain the earlier link target. */}
        <section id="attune-help" className="py-8">
          <div className="container max-w-5xl">
            <h2 className="!text-xl font-bold mb-3">Standalone help reader</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Attune Help reads existing <code>.help/</code> templates.
              If you need the reader independently, see the{' '}
              <a className="underline" href="https://pypi.org/project/attune-help/">standalone package reference</a>.
            </p>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-12">
                Attune Harness FAQ
              </h2>

              <div className="space-y-6 mb-8">
                {HARNESS_FAQ_ITEMS.map((item) => (
                  <div key={item.question} className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                    <h3 className="!text-xl font-bold mb-2">{item.question}</h3>
                    <p className="text-sm text-[var(--text-secondary)]">{item.answer}</p>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-4 mb-12">
                <a href="#quickstart" className="btn btn-primary">Open the Harness Quick Start</a>
                <a href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md" className="btn btn-outline">Read the release guide</a>
                <a href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/migration-from-attune-ai.md" className="btn btn-outline">Check migration boundaries</a>
                <a href="/faq" className="btn btn-outline">Full FAQ and project references</a>
              </div>
              <details id="attune-ai-reference-questions" className="border border-[var(--border)] rounded-lg p-6">
                <summary className="min-h-11 flex items-center text-lg font-semibold cursor-pointer">Earlier Attune AI references</summary>
                <p className="text-sm text-[var(--text-secondary)] my-6">
                  The questions below describe earlier Attune AI tooling and companion packages.
                  Their workflows and commands apply to those projects.
                </p>
                <div className="space-y-6">
                  {faqItems.map((item) => (
                    <div
                      key={item.question}
                      className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6"
                    >
                      <h3 className="!text-lg font-bold mb-2">{item.question}</h3>
                      <p className="text-sm text-[var(--text-secondary)]">
                        {item.answer}
                      </p>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-4xl font-bold mb-6">Choose a Harness workflow</h2>
              <p className="text-xl mb-8 opacity-90">
                Start with a concrete goal and a result you can assess.
                The guide explains the available workflows and their limits.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="https://github.com/Smart-AI-Memory/attune-harness"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >
                  Harness on GitHub
                </a>
                <a
                  href="#harness-docs"
                  className="px-8 py-4 text-lg rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors"
                >
                  Harness guide
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
