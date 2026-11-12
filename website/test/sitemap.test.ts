import { expect, it } from 'vitest';
import sitemap from '../app/sitemap';

it('lists canonical indexable routes and preserves file-like tag URLs', () => {
  const paths = sitemap().map(({ url }) => new URL(url).pathname);

  expect(paths).toEqual(expect.arrayContaining([
    '/docs/',
    '/faq/',
    '/blog/tag/v4.4.0',
    '/blog/tag/v5.2.0',
    '/harness/help/',
    '/harness/help/get-started/',
    '/harness/help/ai-tools-and-integrations/',
  ]));
  expect(paths).not.toContain('/blog/tag/v4.4.0/');
  expect(paths).not.toContain('/blog/tag/v5.2.0/');
  expect(paths).not.toContain('/harness/help/1-5-1-preparation/');
  expect(paths).not.toContain('/harness/help/1-7-0-preparation/');
  expect(paths).not.toContain('/harness/learn/1.7.0-preparation/');
  expect(paths).not.toContain('/harness/learn/reporting/');
});
