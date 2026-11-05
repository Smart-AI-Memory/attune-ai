import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { HARNESS_GET_STARTED, HARNESS_INSTALL_COMMAND, HARNESS_PACKAGE_URL, HARNESS_PREPARATION, HARNESS_PREPARATION_NOTICE, HARNESS_PREPARATION_SOURCE_ROOT, HARNESS_PUBLISHED_VERSION, HARNESS_SOURCE_ROOT, HARNESS_TARGET_VERSION } from './harness-release';

const output = path.resolve('public/harness-help-static');
const build = JSON.parse(readFileSync(path.join(output, 'build.json'), 'utf8'));

describe('current website release boundaries', () => {
  it('installs the published package while showing 1.7 preparation separately', () => {
    expect(HARNESS_PUBLISHED_VERSION).toBe('1.6.0');
    expect(HARNESS_TARGET_VERSION).toBe('1.7.0');
    expect(HARNESS_INSTALL_COMMAND).toContain("attune-harness==1.6.0");
    expect(HARNESS_INSTALL_COMMAND).not.toContain('1.7.0');
    expect(HARNESS_PACKAGE_URL).toBe('https://pypi.org/project/attune-harness/1.6.0/');
    expect(HARNESS_PREPARATION_NOTICE).toContain('in preparation');
    expect(build.version).toBe('1.5.1');
  });

  it('keeps published source and preparation provenance separate from reference history', () => {
    const published = JSON.parse(readFileSync(path.join(output, 'release-1.6.0.json'), 'utf8'));
    const imported = JSON.parse(readFileSync(path.join(output, 'import.json'), 'utf8'));
    expect(HARNESS_SOURCE_ROOT.endsWith(published.source_commit)).toBe(true);
    expect(HARNESS_PREPARATION_SOURCE_ROOT.endsWith(imported.source_commit)).toBe(true);
    expect(published.source_commit).not.toBe(build.behavior_commit);
    expect(imported.source_commit).not.toBe(build.behavior_commit);
  });

  it('points to existing canonical routes with the expected guide status', () => {
    for (const route of [HARNESS_GET_STARTED, HARNESS_PREPARATION]) {
      const file = path.join(output, route.replace('/harness/help/', ''), 'index.html');
      expect(existsSync(file)).toBe(true);
    }
    const prepared = readFileSync(path.join(output, '1-7-0-preparation/index.html'), 'utf8');
    expect(prepared).toContain('Unpublished; use published 1.6.0 until release.');
    expect(prepared).toContain('id="read-the-results-and-remaining-limits"');
  });
});
