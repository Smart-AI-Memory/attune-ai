import type { Metadata } from 'next';
import Link from 'next/link';
import { HELP_ROOT, topics, topicHref } from '@/lib/harness-help/topics';
import './help.css';
import { HARNESS_PUBLISHED, HARNESS_RELEASE_NOTICE, HARNESS_VERSION } from '@/lib/harness-help/release';

export const metadata: Metadata = {
  title: { default: 'Attune Harness Help Center', template: '%s | Harness Help' },
  description: `Choose a goal, install Attune Harness ${HARNESS_VERSION} and inspect the evidence for your work.`,
  robots: { index: HARNESS_PUBLISHED, follow: true },
};

export default function HelpLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="harness-help">
      <header className="help-header">
        <Link href={HELP_ROOT} className="help-brand">Attune Harness <span>Help Center</span></Link>
        <nav aria-label="Help Center context">
          <Link href="/">Smart AI Memory</Link>
          <Link href="/docs/">Documentation</Link>
        </nav>
      </header>
      <div className="help-shell">
        <aside className="help-sidebar">
          <nav aria-label="Help topics">
            <Link href={HELP_ROOT}>Help Center overview</Link>
            <Link href={topicHref('goals')} className="help-featured-nav">Browse all goals</Link>
            <ol>{topics.map((topic) => (
              <li key={topic.slug}><Link href={topicHref(topic.slug)}>{topic.title}</Link></li>
            ))}</ol>
          </nav>
          <p className="help-version">Guidance target <strong>{HARNESS_VERSION}</strong><br />{HARNESS_PUBLISHED ? 'Published release.' : 'Preparation; publication pending.'}<br />Older guides retain their stated versions.</p>
        </aside>
        <main id="main-content" tabIndex={-1} className="help-main">
          {!HARNESS_PUBLISHED && <p className="help-version-note" aria-label="Release status">{HARNESS_RELEASE_NOTICE}</p>}
          {children}
        </main>
      </div>
      <footer className="help-footer">
        <p>{HARNESS_RELEASE_NOTICE} Historical guides describe their named release.</p>
        <Link href={topicHref('goals')}>Browse all goals</Link> · <Link href={topicHref('ai-tools-and-integrations')}>{HARNESS_VERSION} commands and integrations</Link>
        <p><Link href={topicHref('dependencies')}>Historical 1.3.0 dependency reference</Link></p>
      </footer>
    </div>
  );
}
