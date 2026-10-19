import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let fixtureRoot: string;

function writePost(slug: string, frontmatter: string, body = 'Retained article body.\n', language = '') {
  writeFileSync(
    join(fixtureRoot, 'content/blog', `${slug}.md`),
    `---${language}\n${frontmatter}\n---\n${body}`,
  );
}

beforeEach(() => {
  fixtureRoot = mkdtempSync(join(tmpdir(), 'attune-blog-frontmatter-'));
  mkdirSync(join(fixtureRoot, 'content/blog'), { recursive: true });
  vi.spyOn(process, 'cwd').mockReturnValue(fixtureRoot);
  vi.resetModules();
});

afterEach(() => {
  vi.restoreAllMocks();
  rmSync(fixtureRoot, { recursive: true, force: true });
});

describe('blog frontmatter dependency migration', () => {
  it('retains quoted dates as strings and unquoted YAML dates as Date values', async () => {
    writePost('quoted', "title: Quoted date\ndate: '2026-10-19'\ntags: [dates]");
    writePost('date', 'title: YAML date\ndate: 2026-10-19\ntags: [dates]');
    writePost('timestamp', 'title: YAML timestamp\ndate: 2026-10-19T16:00:00Z\ntags: [dates]');
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    const summaries = getAllPosts();
    expect(getPostBySlug('quoted')?.date).toBe('2026-10-19');
    expect(summaries.find((post) => post.slug === 'quoted')?.date).toBe('2026-10-19');
    for (const [slug, value] of [['date', '2026-10-19T00:00:00Z'], ['timestamp', '2026-10-19T16:00:00Z']]) {
      expect(getPostBySlug(slug)?.date).toEqual(new Date(value));
      expect(summaries.find((post) => post.slug === slug)?.date).toEqual(new Date(value));
    }
  });

  it('retains flow/block tags and the existing literal-false publication filter', async () => {
    writePost('flow', "title: Flow tags\ndate: '2026-10-19'\ntags: [alpha, beta]\npublished: true");
    writePost('block', "title: Block tags\ndate: '2026-10-19'\ntags:\n  - yes\n  - on\npublished: off");
    writePost('hidden', "title: Hidden post\ndate: '2026-10-19'\ntags: [hidden]\npublished: false");
    writePost('string-false', "title: String false\ndate: '2026-10-19'\ntags: [visible]\npublished: 'false'");
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    expect(getPostBySlug('flow')?.tags).toEqual(['alpha', 'beta']);
    expect(getPostBySlug('block')?.tags).toEqual(['yes', 'on']);
    expect(getPostBySlug('hidden')?.published).toBe(false);
    expect(getPostBySlug('string-false')?.published).toBe(true);
    expect(getAllPosts().map((post) => post.slug).sort()).toEqual(['block', 'flow', 'string-false']);
  });

  it('retains literal/folded excerpts and safe merge-key metadata', async () => {
    writePost('literal', "title: Literal excerpt\ndate: '2026-10-19'\nexcerpt: |\n  First line\n  Second line\ntags: [text]");
    writePost('folded', "defaults: &defaults\n  author: Example author\n  published: true\n<<: *defaults\ntitle: Folded excerpt\ndate: '2026-10-19'\nexcerpt: >-\n  First line\n  second line\ntags: [text]");
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    expect(getPostBySlug('literal')?.excerpt).toBe('First line\nSecond line\n');
    expect(getPostBySlug('folded')).toMatchObject({ author: 'Example author', excerpt: 'First line second line', published: true });
    expect(getAllPosts().find((post) => post.slug === 'literal')?.excerpt).toBe('First line\nSecond line\n');
    expect(getAllPosts().find((post) => post.slug === 'folded')?.author).toBe('Example author');
  });

  it('retains defaults for empty frontmatter and files without frontmatter', async () => {
    writePost('empty', '');
    writeFileSync(join(fixtureRoot, 'content/blog/plain.md'), 'A plain article body.\n');
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    for (const slug of ['empty', 'plain']) {
      expect(getPostBySlug(slug)).toMatchObject({
        title: 'Untitled', author: 'Smart AI Memory Team', excerpt: '', tags: [], published: true,
      });
      expect(getAllPosts().find((post) => post.slug === slug)).toMatchObject({
        title: 'Untitled', author: 'Smart AI Memory Team', excerpt: '', tags: [], published: true,
      });
    }
    expect(getPostBySlug('empty')?.content).toBe('Retained article body.\n');
    expect(getPostBySlug('plain')?.content).toBe('A plain article body.\n');
  });

  it.each([
    ['malformed sequence', 'title: [unterminated'],
    ['duplicate keys', 'title: First\ntitle: Second'],
    ['JavaScript function tag', "title: !!js/function 'function () { return 1; }'"],
    ['JavaScript regexp tag', 'title: !!js/regexp /example/i'],
    ['JavaScript undefined tag', "title: !!js/undefined ''"],
  ])('retains the existing failure boundary for %s', async (_name, frontmatter) => {
    writePost('invalid', frontmatter);
    const error = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    expect(getPostBySlug('invalid')).toBeNull();
    expect(error).toHaveBeenCalledOnce();
    // Give the list reader a fresh raw-content cache key for its own cold parse.
    writePost('invalid', frontmatter, 'Independent list-reader body.\n');
    expect(getAllPosts).toThrow();
  });

  it.each(['json', 'javascript', 'js'])('preserves the existing %s alternate engine for repository-controlled content', async (language) => {
    const metadata = language === 'json'
      ? '{"title":"Alternate metadata","date":"2026-10-19","tags":["alternate"],"published":true}'
      : '({ title: "Alternate metadata", date: "2026-10-19", tags: ["alternate"], published: true })';
    writePost('alternate', metadata, 'Alternate article body.\n', language);
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    expect(getPostBySlug('alternate')).toMatchObject({
      title: 'Alternate metadata', date: '2026-10-19', tags: ['alternate'], published: true,
      content: 'Alternate article body.\n',
    });
    expect(getAllPosts()).toMatchObject([{ title: 'Alternate metadata', tags: ['alternate'], published: true }]);
  });
});
