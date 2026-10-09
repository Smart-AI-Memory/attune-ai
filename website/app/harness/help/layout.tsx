import type { Metadata } from 'next';
import Link from 'next/link';
import { HELP_ROOT, topics, topicHref } from '@/lib/harness-help/topics';
import './help.css';

export const metadata: Metadata = {
  title: { default: 'Attune Harness Help Center', template: '%s | Harness Help' },
  description: 'Task walkthroughs, recovery guidance and release reference for Attune Harness 1.3.0.',
  // This first increment is a review draft. Publication and indexing need approval.
  robots: { index: false, follow: false },
};

export default function HelpLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="harness-help">
      <header className="help-header">
        <Link href={HELP_ROOT} className="help-brand">Attune Harness <span>Help Center</span></Link>
        <nav aria-label="Help Center context">
          <Link href="/">Smart AI Memory</Link>
          <Link href="/docs/">Attune-AI docs</Link>
        </nav>
      </header>
      <div className="help-shell">
        <aside className="help-sidebar">
          <nav aria-label="Help topics">
            <Link href={HELP_ROOT}>Help Center overview</Link>
            <ol>{topics.map((topic) => (
              <li key={topic.slug}><Link href={topicHref(topic.slug)}>{topic.title}</Link></li>
            ))}</ol>
            <Link href="/harness/help/next-release/">Next release — staged guidance</Link>
          </nav>
          <p className="help-version">Guide version <strong>1.3.0</strong><br />Released behavior · review draft</p>
        </aside>
        <main id="main-content" tabIndex={-1} className="help-main">{children}</main>
      </div>
      <footer className="help-footer">
        <p>Current release baseline: Harness 1.3.0. Staged guidance is labeled separately.</p>
        <Link href={topicHref('dependencies')}>Versions, integrations and reference</Link>
      </footer>
    </div>
  );
}
