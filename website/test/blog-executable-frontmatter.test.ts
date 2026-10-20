import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const aliases = ['js', 'javascript', 'JS', 'JavaScript', 'JAVASCRIPT'];
const rejection = 'Executable JavaScript frontmatter is disabled for blog posts';
const welcomeSource = readFileSync(new URL('../content/blog/welcome.mdx', import.meta.url), 'utf8');
let fixtureRoot: string;
let executableEngine: MockInstance<(source: string) => unknown>;

function writePost(source: string, extension = 'md') {
  writeFileSync(join(fixtureRoot, 'content/blog', `example.${extension}`), source);
}

beforeEach(async () => {
  fixtureRoot = mkdtempSync(join(tmpdir(), 'attune-blog-engine-'));
  mkdirSync(join(fixtureRoot, 'content/blog'), { recursive: true });
  vi.spyOn(process, 'cwd').mockReturnValue(fixtureRoot);
  vi.resetModules();

  // Guard the real dependency's executable engine: a regression fails without
  // ever evaluating a frontmatter payload, including on the unfixed baseline.
  const matter = (await import('gray-matter')).default;
  const engines = Reflect.get(matter, 'engines') as {
    javascript: { parse: (source: string) => unknown };
  };
  executableEngine = vi.spyOn(engines.javascript, 'parse').mockImplementation(() => {
    throw new Error('Original executable engine was reached');
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  rmSync(fixtureRoot, { recursive: true, force: true });
});

describe('blog executable frontmatter boundary', () => {
  it.each(aliases)('rejects %s in the list reader without dispatching its engine', async (language) => {
    writePost(`---${language}\n({ title: "Untrusted" })\n---\nList reader ${language}.\n`);
    const { getAllPosts } = await import('../lib/blog');
    expect(getAllPosts).toThrow(rejection);
    expect(executableEngine).not.toHaveBeenCalled();
  });

  it.each(aliases)('rejects %s in the article reader with its existing null/error boundary', async (language) => {
    writePost(`---${language}\n({ title: "Untrusted" })\n---\nArticle reader ${language}.\n`, 'mdx');
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { getPostBySlug } = await import('../lib/blog');
    expect(getPostBySlug('example')).toBeNull();
    expect(errors).toHaveBeenCalledWith('Error reading post example:', expect.objectContaining({ message: rejection }));
    expect(executableEngine).not.toHaveBeenCalled();
  });

  it.each(aliases)('rejects unpublished %s content before publication filtering', async (language) => {
    writePost(`---${language}\n({ title: "Hidden", published: false })\n---\nUnpublished reader ${language}.\n`);
    const { getAllPosts } = await import('../lib/blog');
    expect(getAllPosts).toThrow(rejection);
    expect(executableEngine).not.toHaveBeenCalled();
  });

  it('preserves the existing Welcome article YAML metadata in both readers', async () => {
    writePost(welcomeSource, 'mdx');
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    const expected = {
      slug: 'example',
      title: 'Welcome to Smart AI Memory: Building the Future of AI-Human Collaboration',
      date: '2025-12-10',
      author: 'Smart AI Memory Team',
      excerpt: 'Introducing Attune AI - production-ready tools for building Level 4 Anticipatory Intelligence systems with built-in memory.',
      tags: ['announcement', 'attune-ai', 'ai', 'anticipatory-intelligence'],
      published: true,
    };
    expect(getAllPosts()).toMatchObject([expected]);
    expect(getPostBySlug('example')).toMatchObject(expected);
    expect(getPostBySlug('example')?.content).toContain('# Welcome to Smart AI Memory');
    expect(executableEngine).not.toHaveBeenCalled();
  });

  it('preserves normal unpublished YAML metadata while omitting it from the list', async () => {
    writePost('---\ntitle: Hidden YAML\ndate: "2026-10-19"\ntags: [hidden]\npublished: false\n---\nRetained body.\n');
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    expect(getAllPosts()).toEqual([]);
    expect(getPostBySlug('example')).toMatchObject({
      title: 'Hidden YAML', date: '2026-10-19', tags: ['hidden'], published: false,
      content: 'Retained body.\n',
    });
    expect(executableEngine).not.toHaveBeenCalled();
  });

  it('keeps non-executable JSON frontmatter supported', async () => {
    writePost('---json\n{"title":"JSON metadata","date":"2026-10-19","tags":["json"]}\n---\nJSON body.\n');
    const { getAllPosts, getPostBySlug } = await import('../lib/blog');
    expect(getAllPosts()).toMatchObject([{ title: 'JSON metadata', date: '2026-10-19', tags: ['json'] }]);
    expect(getPostBySlug('example')).toMatchObject({ title: 'JSON metadata', content: 'JSON body.\n' });
    expect(executableEngine).not.toHaveBeenCalled();
  });
});
