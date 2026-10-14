import type { Metadata } from 'next';
import Link from 'next/link';
import readiness from '@/content/harness-help/next-release.json';
import { topicHref } from '@/lib/harness-help/topics';

export const metadata: Metadata = {
  title: 'Next release — staged guidance',
  description: 'Verified candidate guidance and documentation readiness for the next Harness release. Unreleased, with version and date undecided.',
};

export default function NextReleaseHelp() {
  return (
    <>
      <p className="help-eyebrow">Next release · unreleased</p>
      <h1>Preparing the next release</h1>
      <p className="help-lead">Review candidate guidance alongside the code it describes. The release version and publication date have not been set.</p>
      <p className="help-callout">The seven current task guides describe <strong>released 1.3.0</strong>. This page stages candidate changes separately; it grants no release, execution or publication authority.</p>
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
          <p><strong>Before release:</strong> {candidate.remaining}</p>
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
        <p>The existing release runbook addition and this readiness record are prepared locally. Release and website publication remain separate decisions.</p>
        <Link href={topicHref('get-started')}>Use the current 1.3.0 guide →</Link>
      </section>
    </>
  );
}
