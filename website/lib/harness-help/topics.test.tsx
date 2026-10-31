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
  it('checks the committed export and all fourteen current and archived routes', () => {
    expect(checkExport()).toMatchObject({ version: '1.5.1', pages: 14, files: 29 });
    const build = JSON.parse(readFileSync(path.join(defaultOutput, 'build.json'), 'utf8'));
    for (const name of Object.keys(build.files).filter((name) => name.endsWith('index.html'))) {
      const html = readFileSync(path.join(defaultOutput, name.replace('harness/help/', '')), 'utf8');
      if (name.includes('/get-started/')) expect(html).toContain('published <strong>Harness 1.6.0</strong>');
      else if (name.includes('/1-5-0/')) expect(html).toContain('published <strong>Harness 1.5.0</strong>');
      else if (name.includes('/1-5-1-preparation/')) expect(html).toContain('Archived guide:');
      else if (name.includes('/goals/')) expect(html).toContain('Published guidance.');
      else expect(html).toContain('published <strong>Harness 1.5.1</strong>');
      expect(html).toContain(name.includes('/goals/') ? 'class="goal-index"' : 'aria-label="On this page"');
      expect(html).toContain('src="/harness/help/code-copy.js"');
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

  it('retains historical guides and refuses stale current release metadata', () => {
    const release = JSON.parse(readFileSync(path.join(defaultOutput, 'release-1.5.1.json'), 'utf8'));
    expect(release.status).toBe('published');
    expect(release.source_commit).toBe('ebb5b03b8a4398325df7ddabd28c08186451452e');
    const current = JSON.parse(readFileSync(path.join(defaultOutput, 'release-1.6.0.json'), 'utf8'));
    expect(current.version).toBe('1.6.0');
    expect(current.status).toBe('published');
    expect(current.source_commit).toBe('af2159516a67172cc8f2a1ff62213296b1b67112');
    const archive = readFileSync(path.join(defaultOutput, 'archive/index.html'), 'utf8');
    expect(archive).toContain('/harness/help/1-5-0/');
    expect(archive).toContain('/harness/help/1-5-1-preparation/');
    for (const change of [
      { status: 'preparation' },
      { status: 'unknown' },
      { published_version: '1.5.1' },
      { version: '1.6.0' },
      { behavior_commit: '1'.repeat(40) },
    ]) {
      const output = copyExport();
      const build = JSON.parse(readFileSync(path.join(output, 'build.json'), 'utf8'));
      Object.assign(build, change);
      const bytes = JSON.stringify(build);
      writeFileSync(path.join(output, 'build.json'), bytes);
      const receipt = JSON.parse(readFileSync(path.join(output, 'import.json'), 'utf8'));
      receipt.build_sha256 = digest(bytes);
      writeFileSync(path.join(output, 'import.json'), JSON.stringify(receipt));
      expect(() => checkExport(output)).toThrow('Unexpected Harness published release');
    }
  });

  it('allows only the named dotted release records', () => {
    const output = copyExport();
    const build = JSON.parse(readFileSync(path.join(output, 'build.json'), 'utf8'));
    build.files['harness/help/release-1.6.1.json'] = '0'.repeat(64);
    const bytes = JSON.stringify(build);
    writeFileSync(path.join(output, 'build.json'), bytes);
    const receipt = JSON.parse(readFileSync(path.join(output, 'import.json'), 'utf8'));
    receipt.build_sha256 = digest(bytes);
    writeFileSync(path.join(output, 'import.json'), JSON.stringify(receipt));
    expect(() => checkExport(output)).toThrow('Invalid export path');
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
      { source: '/harness/help/code-copy.js', destination: '/harness-help-static/code-copy.js' },
      { source: '/harness/help/release-1.5.1.json', destination: '/harness-help-static/release-1.5.1.json' },
      { source: '/harness/help/release-1.6.0.json', destination: '/harness-help-static/release-1.6.0.json' },
    ]));
    const redirects = await config.redirects!();
    expect(redirects.find((item) => item.source === '/harness/help/next-release/')?.destination).toContain('6695106f8a185e310b7b8f9d463395cb0752c22a');
  });
});
