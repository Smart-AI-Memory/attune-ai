import type { Metadata } from 'next';
import Link from 'next/link';
import { HELP_ROOT, topics, topicHref } from '@/lib/harness-help/topics';
import './help.css';

export const metadata: Metadata = {
  title: { default: 'Attune Harness Help Center', template: '%s | Harness Help' },
  description: 'Install Attune Harness 1.5.0, check a local result and explore versioned workflow guidance.',
  robots: { index: true, follow: true },
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
            <ol>{topics.map((topic) => (
              <li key={topic.slug}><Link href={topicHref(topic.slug)}>{topic.title}</Link></li>
            ))}</ol>
          </nav>
          <p className="help-version">Current release <strong>1.5.0</strong><br />Older guides retain their stated versions.</p>
        </aside>
        <main id="main-content" tabIndex={-1} className="help-main">{children}</main>
      </div>
      <footer className="help-footer">
        <p>Current release: Harness 1.5.0. Historical guides describe their named release.</p>
        <Link href={topicHref('ai-tools-and-integrations')}>1.5.0 commands and integrations</Link>
        <p><Link href={topicHref('dependencies')}>Historical 1.3.0 dependency reference</Link></p>
      </footer>
    </div>
  );
}
