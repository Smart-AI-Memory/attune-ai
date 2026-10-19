import type { Metadata } from 'next';
import Link from 'next/link';
import readiness from '@/content/harness-help/next-release.json';
import { topicHref } from '@/lib/harness-help/topics';

export const metadata: Metadata = {
  title: 'Historical release preparation',
  description: 'Retained prepublication candidate observations, separate from published Harness 1.5.0 guidance.',
  robots: { index: false, follow: true },
};

export default function NextReleaseHelp() {
  return (
    <>
      <p className="help-eyebrow">Historical preparation</p>
      <h1>Retained candidate observations</h1>
      <p className="help-lead">This record preserves earlier preparation evidence and its original pending items. It does not describe current release readiness. <Link href={topicHref('1-5-0')}>Use the published 1.5.0 guide</Link> for current installation and scope.</p>
      <p className="help-callout">The seven historical task guides describe <strong>released 1.3.0</strong>. Candidate observations below retain their original source and capture boundaries; they are not newly verified 1.5.0 walkthroughs.</p>
      {readiness.candidates.map((candidate) => (
        <section key={candidate.id} className="help-learning">
          <p className="help-eyebrow">{candidate.status}</p>
          <h2>{candidate.title}</h2>
          {candidate.behavior && <p>{candidate.behavior}</p>}
          {candidate.required_hint && <p>When its owner marks a question required, the candidate shows: “{candidate.required_hint}”</p>}
          {candidate.unchanged && <p>{candidate.unchanged}</p>}
          <p>Visible candidate controls: {candidate.controls.map((label, index) => (
            <span key={label}>{index > 0 && ' · '}<strong>{label}</strong></span>
          ))}</p>
          <p>{candidate.evidence}</p>
          <p><strong>Recorded pending work:</strong> {candidate.remaining}</p>
          <p>Affected guidance: {candidate.affected_topics.map((slug, index) => (
            <span key={slug}>{index > 0 && ' · '}<Link href={topicHref(slug)}>{slug.replaceAll('-', ' ')}</Link></span>
          ))}</p>
          {candidate.pull_request && candidate.source_commit && candidate.source_path && <p>
            <a href={candidate.pull_request}>Candidate pull request</a> · <a href={`https://github.com/Smart-AI-Memory/attune-harness/blob/${candidate.source_commit}/${candidate.source_path}`}>Pinned candidate source</a>
          </p>}
        </section>
      ))}
      <section className="help-learning">
        <h2>Documentation is part of release preparation</h2>
        <p>For every new version, review affected official topics and their actual help, tutorial and deck derivatives. Record changed or unchanged-but-reviewed content, the tested version, examples, expected results, limits and checked links. Retain or explicitly supersede relevant old-version guidance.</p>
        <p>Versioned code and reproducible tests ground behavior. Approved policies and style requirements govern content, with approved project exceptions ahead of general Google guidance. Resolve conflicts explicitly; build and link checks support the walkthrough review.</p>
        <p>This historical readiness record is retained without relabeling its observations as published-wheel acceptance.</p>
        <Link href={topicHref('1-5-0')}>Use the current 1.5.0 guide →</Link>
      </section>
    </>
  );
}
