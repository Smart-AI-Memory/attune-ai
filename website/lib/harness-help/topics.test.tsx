import { describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import HelpArticle, { generateMetadata, generateStaticParams } from '@/app/harness/help/[slug]/page';
import HelpHome from '@/app/harness/help/page';
import HelpLayout from '@/app/harness/help/layout';
import NextReleaseHelp from '@/app/harness/help/next-release/page';
import readiness from '@/content/harness-help/next-release.json';
import { getTopic, HELP_ROOT, provenance, RELEASE_COMMIT, topics, topicHref } from './topics';

// CSS layout/contrast is exercised in Chromium; keep the server-render unit
// probe independent of Vite's different PostCSS config format.
vi.mock('@/app/harness/help/help.css', () => ({}));

describe('Harness Help Center', () => {
  it('renders every registered topic with one title and valid help links', async () => {
    const routes = new Set([HELP_ROOT, '/harness/help/next-release/', ...topics.map((topic) => topicHref(topic.slug))]);
    expect(generateStaticParams()).toHaveLength(7);
    for (const topic of topics) {
      const page = await HelpArticle({ params: Promise.resolve({ slug: topic.slug }) });
      const html = renderToStaticMarkup(<HelpLayout>{page}</HelpLayout>);
      expect((html.match(/<h1[ >]/g) || []).length).toBe(1);
      expect(html).toContain('id="main-content"');
      expect(html).toContain('released 1.3.0');
      expect(await generateMetadata({ params: Promise.resolve({ slug: topic.slug }) })).toMatchObject({ title: topic.title });
      for (const match of html.matchAll(/href="(\/harness\/help\/[^"#]*)"/g)) {
        expect(routes.has(`${match[1].replace(/\/$/, '')}/`), `missing route ${match[1]}`).toBe(true);
      }
    }
    const home = renderToStaticMarkup(<HelpHome />);
    for (const route of routes) {
      if (route !== HELP_ROOT && route !== '/harness/help/next-release/') expect(home).toMatch(new RegExp(`href="${route.replace(/\/$/, '')}/?"`));
    }
  });

  it('returns the actual not-found boundary for unregistered input', async () => {
    expect(getTopic('../docs')).toBeUndefined();
    await expect(HelpArticle({ params: Promise.resolve({ slug: 'missing-topic' }) })).rejects.toThrow('NEXT_HTTP_ERROR_FALLBACK;404');
    expect(await generateMetadata({ params: Promise.resolve({ slug: 'missing-topic' }) })).toMatchObject({ title: 'Help topic unavailable' });
  });

  it('preserves canonical provenance, projection and release boundaries', () => {
    const source = readFileSync('content/harness-help/tutorials-1.3.0.source.md', 'utf8');
    expect(createHash('sha256').update(source).digest('hex')).toBe(provenance.source_sha256);
    expect(provenance.behavior_commit).toBe(RELEASE_COMMIT);
    expect(execFileSync('python3', ['scripts/project-harness-walkthroughs.py', '--check'], { encoding: 'utf8' })).toContain('Four walkthrough projections');
    for (const slug of ['start-and-continue', 'plan-and-accept', 'research', 'save-and-resume']) {
      const topic = getTopic(slug)!;
      expect(topic.content).toContain('1. ');
      expect(topic.content).toContain('Expected:');
      expect(topic.content).toContain('Limit:');
      expect(topic.content).not.toMatch(/\]\((cli-guide|local-workflow|memory-saving)\.md/);
    }
    expect(getTopic('research')!.content).toContain('semantic_ran is false');
    expect(getTopic('start-and-continue')!.content).toContain('Execution requires separate authority');
    expect(getTopic('save-and-resume')!.content).toContain("TASK='/absolute/path/to/training-form/saved-task'");
    expect(getTopic('research')!.content).toContain('older optional-extra installation instructions');
    expect(getTopic('dependencies')!.content).toContain('Current main documentation — development');
    expect(getTopic('dependencies')!.content).toContain('Prototypes — unreleased');
  });

  it('stages the next release separately without inventing version or unverified steps', () => {
    const html = renderToStaticMarkup(<NextReleaseHelp />);
    expect(readiness.target_version).toBeNull();
    expect(readiness.publication_date).toBeNull();
    expect(html).toContain('Next release · unreleased');
    expect(html).toContain('released 1.3.0');
    expect(html).toContain('149d8725f7636bec1a9201124e798cf8641c01ac');
    const journey = readiness.candidates.find((candidate) => candidate.id === 'first-gui-journey')!;
    expect(journey.source_commit).toBe('a51460dfcd15701b36955d74a5e1324adc1a4f80');
    expect(journey.capture_provenance).toMatchObject({ published_release_claim: false, forms_pr242_included: false, capture_count: 10 });
    expect(html).toContain('integration and instructions pending');
    expect(html).toContain('read-only');
    expect(html).toContain('<strong>View accepted request</strong>');
    expect(html).not.toContain('WCAG compliant');
  });
});
