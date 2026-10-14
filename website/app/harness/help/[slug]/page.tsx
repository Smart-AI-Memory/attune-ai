import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getTopic, HELP_ROOT, provenance, RELEASE_ROOT, topics, topicHref } from '@/lib/harness-help/topics';

export function generateStaticParams() {
  return topics.map(({ slug }) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const topic = getTopic(slug);
  if (!topic) return { title: 'Help topic unavailable' };
  return { title: topic.title, description: topic.goal };
}

export default async function HelpArticle({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const topic = getTopic(slug);
  if (!topic) notFound();
  const index = topics.indexOf(topic);
  const next = topics[index + 1];

  return (
    <>
      <nav aria-label="Breadcrumb" className="help-breadcrumb">
        <Link href={HELP_ROOT}>Help Center</Link><span aria-hidden="true"> / </span><span aria-current="page">{topic.title}</span>
      </nav>
      <p className="help-eyebrow">{topic.kind} · Harness 1.3.0</p>
      <h1>{topic.title}</h1>
      <p className="help-lead">{topic.goal}</p>
      <p className="help-version-note">Version: <strong>released 1.3.0</strong>. The instructions describe this release; newer main and prototypes have separate labels in <Link href={topicHref('dependencies')}>version guidance</Link>.</p>
      <div className="help-prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
          h2: ({ children }) => <h2 id={String(children).toLowerCase().replace(/[^a-z0-9 -]/g, '').replace(/ /g, '-')}>{children}</h2>,
          a: ({ href, children }) => href?.startsWith('/')
            ? <Link href={href}>{children}</Link>
            : <a href={href}>{children}</a>,
          table: ({ children }) => <div className="help-table-scroll" tabIndex={0} role="region" aria-label="Reference table, scroll horizontally if needed"><table>{children}</table></div>,
        }}>{topic.content}</ReactMarkdown>
      </div>
      <details className="help-sources">
        <summary>Sources and verification boundary</summary>
        <p>Behavior baseline: Harness 1.3.0. Follow the installed route help when your version differs. Tests ground behavior; approved project policy and style requirements govern presentation. Resolve source conflicts before revising instructions.</p>
        <ul>{topic.sourcePaths.filter((path) => path !== 'docs/tutorials-1.3.0.md').map((path) => (
          <li key={path}><a href={`${RELEASE_ROOT}/${path}`}>1.3.0: {path}</a>{path === 'docs/local-workflow.md' && ' — historical setup; use this Help Center’s release installation guidance'}</li>
        ))}</ul>
        {topic.sourcePaths.includes('docs/tutorials-1.3.0.md') && <p>Shared canonical walkthrough: <code>{provenance.source_path}</code>, source commit <code>{provenance.source_commit}</code>. This reviewed tutorial source is unpublished; the website renders a pinned projection with its expected results and limits. Its instructions remain owned by the tutorial source.</p>}
      </details>
      <nav aria-label="Continue learning" className="help-next">
        <Link href={HELP_ROOT}>← All help topics</Link>
        {next && <Link href={topicHref(next.slug)}>Next: {next.title} →</Link>}
      </nav>
    </>
  );
}
