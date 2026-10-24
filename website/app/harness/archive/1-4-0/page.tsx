import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta } from '@/lib/metadata';

export const metadata: Metadata = {
  ...genMeta({
    title: 'Historical Harness 1.4.0 Quick Start',
    description: 'Archived Harness 1.4.0 setup. Use the canonical Help Center for current preparation and published-release guidance.',
    url: 'https://smartaimemory.com/harness/archive/1-4-0/',
  }),
  robots: { index: false, follow: true },
};

// Original section from attune-ai 6695106f8a185e310b7b8f9d463395cb0752c22a.
// Preserve its versioned instructions and #quickstart bookmark as history.
export default function HistoricalHarnessQuickStart() {
  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        <header className="container max-w-5xl pt-12">
          <p className="text-sm font-bold uppercase tracking-wider mb-4">Documentation archive</p>
          <h1 className="text-4xl font-bold mb-4">Harness 1.4.0 archive</h1>
          <p className="text-xl text-[var(--text-secondary)] mb-6">
            This historical setup retains its original commands and version labels.
            Use the <Link className="underline" href="/harness/help/get-started/">current Harness Quick Start</Link> to
            choose a reviewed candidate or the published package.
          </p>
          <p className="text-sm text-[var(--text-secondary)]">
            <a className="underline" href="https://github.com/Smart-AI-Memory/attune-ai/blob/6695106f8a185e310b7b8f9d463395cb0752c22a/website/app/docs/page.tsx">Original documentation source</a>
          </p>
        </header>
        <section id="quickstart" className="py-20 bg-[var(--surface-container-low)]">
          <div className="container max-w-5xl">
            <h2 className="text-4xl font-bold mb-4">Historical Harness 1.4.0 Quick Start</h2>
            <p className="text-xl text-[var(--text-secondary)] mb-6">
              Install Harness and try a small local check before connecting an agent.
              This retained setup uses the released 1.4.0 package. <Link className="underline" href="/harness/help/1-5-0/">Use the Help Center for current 1.5.0 instructions.</Link>
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
                <pre className="bg-[#263c30] text-white/90 rounded-xl font-mono text-sm p-4 overflow-x-auto"><code>{"python -m pip install 'attune-harness[all]==1.4.0'\npython -c \"from importlib.metadata import version; print(version('attune-harness'))\""}</code></pre>
                <p className="mt-3 text-sm text-[var(--text-secondary)]">
                  The version check should print <code>1.4.0</code>. This
                  recommended install adds Redis and Voyage support. The local
                  example below needs no API key. Redis use needs a running
                  Redis service; Voyage retrieval needs a Voyage API key and
                  makes paid calls. Integration requirements are covered in the{' '}
                  <a className="underline" href="https://pypi.org/project/attune-harness/1.4.0/#user-content-installation">released installation guide</a>.
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
                <a className="btn btn-primary" href="https://pypi.org/project/attune-harness/1.4.0/#user-content-use-harness-with-codex-claude-or-other-models">Set up your agent</a>
                <a className="btn btn-outline" href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.4.0/docs/cli-guide.md">Choose a Harness workflow</a>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
