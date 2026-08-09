import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata } from '@/lib/metadata';

export const metadata: Metadata = generateMetadata({
  title: 'attune-gui is archived — Attune AI',
  description:
    'The standalone attune-gui dashboard is parked: the repository is archived and no further releases are planned. Released versions stay installable from PyPI. The previously announced fold into attune-ai was cancelled.',
  url: 'https://smartaimemory.com/migrate',
  keywords: ['attune-gui', 'attune-gui archived', 'attune-ai dashboard'],
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
                <code className="font-mono">attune-gui</code> is archived
              </h1>
              <p className="text-xl !text-white opacity-90">
                The standalone dashboard is parked. Released versions stay
                installable, but no further releases are planned &mdash; and
                the previously announced fold into attune-ai was cancelled.
              </p>
            </div>
          </div>
        </section>

        <section className="py-16">
          <div className="container">
            <div className="max-w-3xl mx-auto prose prose-lg">
              <h2>What happened</h2>
              <p>
                This page used to be a heads-up that the dashboard would fold
                into <code className="font-mono">attune-ai</code> as an
                install extra. That fold was cancelled: in July 2026 the
                project was parked instead &mdash; the{' '}
                <code className="font-mono">attune-gui</code> repository is
                archived and no further releases are planned. There is no{' '}
                <code className="font-mono">pip install attune-ai[gui]</code>.
              </p>

              <h2>What this means for you</h2>
              <ul>
                <li>
                  Already-released versions stay installable from PyPI
                  (<code className="font-mono">pip install attune-gui</code>),
                  and an existing install keeps running &mdash; it just
                  won&rsquo;t receive updates.
                </li>
                <li>
                  The <code className="font-mono">attune</code> CLI and the
                  attune-ai platform are unaffected: workflows, the spec
                  engine, memory, and the Claude Code plugin all continue
                  unchanged.
                </li>
                <li>
                  Nothing in your project directory or{' '}
                  <code className="font-mono">.help/</code> state depends on
                  the dashboard.
                </li>
              </ul>

              <h2>Where to follow along</h2>
              <ul>
                <li>
                  <Link href="/changelog" className="text-[var(--primary)] hover:underline">
                    Changelog
                  </Link>{' '}
                  &mdash; attune-ai release notes land here.
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
                  &mdash; questions about the archive are welcome there.
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
