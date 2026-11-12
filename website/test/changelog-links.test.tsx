import fs from 'node:fs';
import path from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import { expect, it } from 'vitest';
import { resolveChangelogLink } from '../lib/changelog-links';
import historical from '../lib/changelog-historical-links.json';

it('preserves website and external destinations', () => {
  for (const href of ['', '/help/', '//example.com/a', '#release', '?page=2', 'https://example.com', 'mailto:hello@example.com']) expect(resolveChangelogLink(href)).toBe(href);
});
it('preserves query and fragment on current and archived references', () => {
  expect(resolveChangelogLink('./README.md?plain=1#setup')).toBe('https://github.com/Smart-AI-Memory/attune-ai/blob/main/README.md?plain=1#setup');
  expect(resolveChangelogLink('docs/')).toBe('https://github.com/Smart-AI-Memory/attune-ai/tree/main/docs/');
  const [old, destination] = Object.entries(historical).find(([, value]) => value !== null)!;
  expect(resolveChangelogLink(`${old}?plain=1#example`)).toBe(`${destination}?plain=1#example`);
  expect(resolveChangelogLink('TIER_FALLBACK_TEST_REPORT.md')).toBeNull();
  expect(resolveChangelogLink('tests/integration/cache/#example')).toBeNull();
});
it('requires every relative release reference to exist or have an explicit historical decision', () => {
  const root = path.resolve(import.meta.dirname, '../..');
  const hrefs: string[] = [];
  renderToStaticMarkup(<ReactMarkdown components={{ a: ({ href = '', children }) => {
    hrefs.push(href);
    return <span>{children}</span>;
  } }}>{fs.readFileSync(path.join(root, 'CHANGELOG.md'), 'utf8')}</ReactMarkdown>);
  const relative = hrefs.filter(href => href && !/^(?:[a-z][a-z0-9+.-]*:|[/#?])/i.test(href));
  expect(relative.length).toBeGreaterThan(90);
  for (const href of relative) {
    const target = href.split(/[?#]/)[0].replace(/^\.\//, '');
    expect(Object.hasOwn(historical, target) || fs.existsSync(path.join(root, target)), target).toBe(true);
    expect(resolveChangelogLink(href) ?? "").not.toMatch(/^https:\/\/smartaimemory.com\/changelog\//);
  }
});
