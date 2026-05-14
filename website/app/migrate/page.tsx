import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata } from '@/lib/metadata';
import { CANONICAL_INSTALL, POST_FOLD_INSTALL } from '@/lib/install-command';

export const metadata: Metadata = generateMetadata({
  title: 'Migrating from attune-gui — Attune AI',
  description:
    'Heads-up for current attune-gui users: the dashboard is folding back into attune-ai as an install extra. What changes, what doesn’t, and when.',
  url: 'https://smartaimemory.com/migrate',
  keywords: ['attune-gui migration', 'attune-ai dashboard', 'pip install attune-ai[gui]'],
});

export default function MigratePage() {
  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-5xl font-bold mb-6 !text-white">
                Heads up: <code className="font-mono">attune-gui</code> is folding into <code className="font-mono">attune-ai</code>
              </h1>
              <p className="text-xl !text-white opacity-90">
                Pre-fold notice. Nothing breaks today.
              </p>
            </div>
          </div>
        </section>

        <section className="py-16">
          <div className="container">
            <div className="max-w-3xl mx-auto prose prose-lg">
              <h2>What&rsquo;s changing</h2>
              <p>
                Today the dashboard ships as a standalone PyPI package:
              </p>
              <pre><code>{CANONICAL_INSTALL}</code></pre>
              <p>
                In an upcoming release, it becomes an install extra on{' '}
                <code className="font-mono">attune-ai</code> itself:
              </p>
              <pre><code>{POST_FOLD_INSTALL}</code></pre>
              <p>
                Same dashboard, same surfaces (Living Docs, RAG search,
                Commands, Summaries). One package to install instead of two.
              </p>

              <h2>What stays the same</h2>
              <ul>
                <li>The dashboard URL, layout, and feature set.</li>
                <li>Your project directory and any{' '}
                  <code className="font-mono">.help/</code>{' '}
                  templates / corpus state.
                </li>
                <li>The CLI. <code className="font-mono">attune</code>{' '}
                  workflows continue to work unchanged.</li>
                <li>Your existing{' '}
                  <code className="font-mono">attune-gui</code>{' '}
                  install keeps running until you choose to migrate.
                </li>
              </ul>

              <h2>When does this happen</h2>
              <p>
                On the v7.0 release. We&rsquo;ll publish a banner here,
                on the homepage, and on the <code className="font-mono">attune-gui</code>{' '}
                PyPI page about 4&ndash;6 weeks before release day so you
                aren&rsquo;t blindsided. The banner phrasing is
                deliberately non-version-specific until the v7.0 RC cuts.
              </p>

              <h2>Do I need to do anything now?</h2>
              <p>
                No. This page is a heads-up. When v7.0 ships, the steps
                will be:
              </p>
              <ol>
                <li>
                  <code className="font-mono">pip uninstall attune-gui</code>
                </li>
                <li>
                  <code className="font-mono">{POST_FOLD_INSTALL}</code>
                </li>
              </ol>
              <p>
                The standalone <code className="font-mono">attune-gui</code>{' '}
                package will continue to publish as a deprecation shim that
                points at the new install path, so a stale install command
                in a CI script won&rsquo;t break overnight.
              </p>

              <h2>Where to follow along</h2>
              <ul>
                <li>
                  <Link href="/changelog" className="text-[var(--primary)] hover:underline">
                    Changelog
                  </Link>{' '}
                  &mdash; v7.0 release notes will land here with the
                  exact migration steps.
                </li>
                <li>
                  <Link href="/faq" className="text-[var(--primary)] hover:underline">
                    FAQ
                  </Link>{' '}
                  &mdash; &ldquo;What&rsquo;s the difference between attune-ai
                  and attune-gui?&rdquo; updates on fold day.
                </li>
                <li>
                  <Link
                    href="https://github.com/Smart-AI-Memory/attune-ai/issues"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--primary)] hover:underline"
                  >
                    GitHub issues
                  </Link>{' '}
                  &mdash; raise anything that surprises you in the
                  migration.
                </li>
              </ul>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
