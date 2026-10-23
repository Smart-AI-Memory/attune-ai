import { describe, expect, it } from 'vitest';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import config from '@/next.config';
import { checkExport, defaultOutput, importExport } from '../../scripts/harness-help-export.mjs';

const digest = (bytes: string | Buffer) => createHash('sha256').update(bytes).digest('hex');
function copyExport() {
  const directory = mkdtempSync(path.join(realpathSync(tmpdir()), 'harness-help-test-'));
  const output = path.join(directory, 'export');
  cpSync(defaultOutput, output, { recursive: true });
  return output;
}

describe('Harness-owned Help Center export', () => {
  it('checks the committed export and all ten current routes', () => {
    expect(checkExport()).toMatchObject({ version: '1.5.0', pages: 10, files: 14 });
    const build = JSON.parse(readFileSync(path.join(defaultOutput, 'build.json'), 'utf8'));
    for (const name of Object.keys(build.files).filter((name) => name.endsWith('index.html'))) {
      const html = readFileSync(path.join(defaultOutput, name.replace('harness/help/', '')), 'utf8');
      expect(html).toContain('published <strong>Harness 1.5.0</strong>');
      expect(html).toContain('aria-label="On this page"');
    }
  });

  it('refuses edited bytes, unknown files and paths outside the export', () => {
    const changed = copyExport();
    writeFileSync(path.join(changed, 'index.html'), 'changed');
    expect(() => checkExport(changed)).toThrow('Export byte drift');
    const extra = copyExport();
    writeFileSync(path.join(extra, 'unknown.html'), 'extra');
    expect(() => checkExport(extra)).toThrow('Export file set drift');
    const escaped = copyExport();
    const build = JSON.parse(readFileSync(path.join(escaped, 'build.json'), 'utf8'));
    build.files['harness/help/../outside.html'] = '0'.repeat(64);
    const bytes = JSON.stringify(build);
    writeFileSync(path.join(escaped, 'build.json'), bytes);
    const receipt = JSON.parse(readFileSync(path.join(escaped, 'import.json'), 'utf8'));
    receipt.build_sha256 = digest(bytes);
    writeFileSync(path.join(escaped, 'import.json'), JSON.stringify(receipt));
    expect(() => checkExport(escaped)).toThrow('Invalid export path');
  });

  it('retains the 1.3.0 snapshot and original projection', () => {
    const provenance = JSON.parse(readFileSync('content/harness-help/walkthrough-provenance.json', 'utf8'));
    expect(digest(readFileSync('content/harness-help/tutorials-1.3.0.source.md'))).toBe(provenance.source_sha256);
    expect(execFileSync('python3', ['scripts/project-harness-walkthroughs.py', '--check'], { encoding: 'utf8' })).toContain('Four walkthrough projections');
    const history = JSON.parse(readFileSync('content/harness-help/next-release.json', 'utf8'));
    expect(history.target_version).toBeNull();
    expect(history.publication_date).toBeNull();
  });

  it('refuses a lookalike remote before building any committed code', () => {
    const repo = mkdtempSync(path.join(realpathSync(tmpdir()), 'harness-help-origin-'));
    execFileSync('git', ['init', '--initial-branch=main', repo]);
    execFileSync('git', ['-C', repo, 'remote', 'add', 'origin', 'https://example.invalid/Smart-AI-Memory/attune-harness.git']);
    expect(() => importExport({ repo, commit: '1'.repeat(40), output: path.join(repo, 'export') })).toThrow('not Harness on GitHub');
  });

  it('refuses symlink roots, nested files and output parents', () => {
    const directory = mkdtempSync(path.join(realpathSync(tmpdir()), 'harness-help-links-'));
    const copied = copyExport();
    const linked = path.join(directory, 'linked');
    symlinkSync(copied, linked, 'dir');
    expect(() => checkExport(linked)).toThrow('symlinks');
    expect(() => checkExport(path.join(linked, 'plan-and-accept'))).toThrow('symlinks');
    symlinkSync(path.join(copied, 'index.html'), path.join(copied, 'extra.html'));
    expect(() => checkExport(copied)).toThrow('symlinks');
    const repo = path.join(directory, 'repo');
    mkdirSync(repo);
    expect(() => importExport({ repo, commit: '1'.repeat(40), output: path.join(linked, 'fresh') })).toThrow('symlinks');
  });

  it('keeps public routes and serves generated files through rewrites', async () => {
    const rewrites = await config.rewrites!();
    expect(rewrites).toEqual(expect.arrayContaining([
      { source: '/harness/help/', destination: '/harness-help-static/index.html' },
      { source: '/harness/help/:topic([a-z0-9-]+)/', destination: '/harness-help-static/:topic/index.html' },
      { source: '/harness/help/help.css', destination: '/harness-help-static/help.css' },
    ]));
    const redirects = await config.redirects!();
    expect(redirects.find((item) => item.source === '/harness/help/next-release/')?.destination).toContain('6695106f8a185e310b7b8f9d463395cb0752c22a');
  });
});
