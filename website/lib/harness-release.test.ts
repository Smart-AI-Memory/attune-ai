import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { HARNESS_GET_STARTED, HARNESS_INSTALL_COMMAND, HARNESS_PACKAGE_URL, HARNESS_PREPARATION, HARNESS_PREPARATION_NOTICE, HARNESS_PUBLISHED_VERSION, HARNESS_SOURCE_ROOT } from './harness-release';

const output = path.resolve('public/harness-help-static');
const build = JSON.parse(readFileSync(path.join(output, 'build.json'), 'utf8'));

describe('current website release boundaries', () => {
  it('installs the published package while keeping preparation evidence separate', () => {
    expect(HARNESS_PUBLISHED_VERSION).toBe('1.7.0');
    expect(HARNESS_INSTALL_COMMAND).toContain('attune-harness==1.7.0');
    expect(HARNESS_PACKAGE_URL).toBe('https://pypi.org/project/attune-harness/1.7.0/');
    expect(HARNESS_PREPARATION_NOTICE).toContain('original test results');
    expect(build.version).toBe('1.5.1');
  });

  it('links to the merged source shared by Help and training', () => {
    const help = JSON.parse(readFileSync(path.join(output, 'import.json'), 'utf8'));
    const training = JSON.parse(readFileSync('public/harness-training-static/import.json', 'utf8'));
    expect(HARNESS_SOURCE_ROOT).toBe(`https://github.com/Smart-AI-Memory/attune-harness/blob/${help.source_commit}`);
    expect(training.source_commit).toBe(help.source_commit);
    expect(help.source_commit).not.toBe(build.behavior_commit);
  });

  it('points to existing canonical routes with the expected guide status', () => {
    for (const route of [HARNESS_GET_STARTED, HARNESS_PREPARATION]) {
      const file = path.join(output, route.replace('/harness/help/', ''), 'index.html');
      expect(existsSync(file)).toBe(true);
    }
    const prepared = readFileSync(path.join(output, '1-7-0-preparation/index.html'), 'utf8');
    expect(prepared).toContain('Archived guide:');
    expect(prepared).toContain('id="read-the-results-and-remaining-limits"');
  });
});
