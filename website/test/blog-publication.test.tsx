import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { renderToStaticMarkup } from 'react-dom/server';

// Test the actual article renderer while leaving unrelated client shell
// providers out of this server-rendered publication check.
vi.mock('@/components/Navigation', () => ({ default: () => null }));
vi.mock('@/components/Footer', () => ({ default: () => null }));
// The normal Next.js build checks CSS compilation. These server-rendering
// tests do not use Vite's incompatible interpretation of Next's PostCSS config.
vi.mock('../app/blog/[slug]/publication.css', () => ({}));

let fixtureRoot: string;

function writePost(slug: string, frontmatter: string, body = 'Approved **plan** copy.') {
  writeFileSync(
    join(fixtureRoot, 'content/blog', `${slug}.md`),
    `---\ntitle: "${slug === 'main' ? 'Main article heading' : 'Technical walkthrough'}"\ndate: '2026-10-14'\nauthor: Patrick Roebuck\nexcerpt: Approved article description.\ntags: [attune-harness]\n${frontmatter}\n---\n${body}\n`,
  );
}

beforeEach(() => {
  fixtureRoot = mkdtempSync(join(tmpdir(), 'attune-blog-publication-'));
  mkdirSync(join(fixtureRoot, 'content/blog'), { recursive: true });
  vi.spyOn(process, 'cwd').mockReturnValue(fixtureRoot);
  vi.resetModules();
});

afterEach(() => {
  vi.restoreAllMocks();
  rmSync(fixtureRoot, { recursive: true, force: true });
});

describe('blog publication metadata and companion navigation', () => {
  it('uses the approved SEO title while retaining the visible article heading and prose', async () => {
    writePost('main', 'seoTitle: Approved search title.\ncompanionSlug: technical');
    writePost('technical', 'companionSlug: main');
    const { default: Article, generateMetadata } = await import('../app/blog/[slug]/page');
    const params = Promise.resolve({ slug: 'main' });
    const metadata = await generateMetadata({ params });
    expect(metadata.title).toBe('Approved search title. | Smart AI Memory');
    expect(metadata.description).toBe('Approved article description.');
    const rendered = renderToStaticMarkup(await Article({ params }));
    expect(rendered).toMatch(/<h1[^>]*>Main article heading<\/h1>/);
    expect(rendered).toContain('Approved <strong>plan</strong> copy.');
    expect(rendered).toContain('article-publication-body');
    expect(rendered).toContain('aria-label="Companion article"');
    const mainNavigation = rendered.match(/<nav aria-label="Companion article"[^>]*>(.*?)<\/nav>/)?.[1];
    expect(mainNavigation).toMatch(/href="\/blog\/technical\/?"/);
    const technical = renderToStaticMarkup(await Article({ params: Promise.resolve({ slug: 'technical' }) }));
    const technicalNavigation = technical.match(/<nav aria-label="Companion article"[^>]*>(.*?)<\/nav>/)?.[1];
    expect(technicalNavigation).toMatch(/href="\/blog\/main\/?"/);
  });

  it('preserves existing article behavior when no optional publication fields are supplied', async () => {
    writePost('main', '');
    const { default: Article, generateMetadata } = await import('../app/blog/[slug]/page');
    const params = Promise.resolve({ slug: 'main' });
    expect((await generateMetadata({ params })).title).toBe('Main article heading | Smart AI Memory');
    const rendered = renderToStaticMarkup(await Article({ params }));
    expect(rendered).not.toContain('aria-label="Companion article"');
    expect(rendered).not.toContain('article-publication-body');
  });

  it('omits companion navigation when the target is missing or unpublished', async () => {
    writePost('main', 'companionSlug: technical');
    const { default: Article } = await import('../app/blog/[slug]/page');
    const render = async () => renderToStaticMarkup(await Article({ params: Promise.resolve({ slug: 'main' }) }));
    expect(await render()).not.toContain('aria-label="Companion article"');
    writePost('technical', 'published: false');
    expect(await render()).not.toContain('aria-label="Companion article"');
  });

  it('ignores invalid companion paths instead of reading outside the blog directory', async () => {
    writePost('main', 'companionSlug: ../../other-content\nseoTitle: [invalid]');
    const { getPostBySlug } = await import('../lib/blog');
    expect(getPostBySlug('main')).toMatchObject({ companionSlug: undefined, seoTitle: undefined });
  });
});
