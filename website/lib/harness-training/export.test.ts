import { beforeAll, describe, expect, it } from 'vitest';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import config from '@/next.config';
import { checkTrainingExport, importTrainingExport } from '../../scripts/harness-training-export.mjs';

const course = 'reporting';
const legacyCourse = '1.7.0-preparation';
const origin = 'https://github.com/Smart-AI-Memory/attune-harness.git';
const importer = fileURLToPath(new URL('../../scripts/harness-training-export.mjs', import.meta.url));
const digest = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
const temporary = () => mkdtempSync(path.join(realpathSync(tmpdir()), 'harness-training-test-'));

/** Commit a harmless local source so tests cross the real Git archive boundary. */
function fixture({ remote = origin, check = 'import sys\nassert sys.argv[1:] == ["--check"]\n', extra = {} as Record<string, string> } = {}) {
  const repo = temporary();
  const files: Record<string, string> = {
    'help/manifest.json': '{"status":"published","published_version":"1.8.0"}\n',
    'training/build_course.py': check,
    'training/README.md': 'Maintainer instructions are not a course payload.\n',
    [`training/${course}/index.html`]: '<!doctype html><h1>Harness in practice</h1>\n',
    [`training/${course}/setup.html`]: '<h1>Set up the published package</h1>\n',
    [`training/${course}/01-define/index.html`]: '<h1>Define the outcome</h1>\n',
    [`training/${course}/01-define/lesson.json`]: '{"title":"Define the outcome"}\n',
    [`training/${course}/assets/report.py`]: 'print("local fixture")\n',
    [`training/${course}/assets/activity.csv`]: 'minutes\n15\n',
    [`training/${course}/assets/pytest.ini`]: '[pytest]\n',
    [`training/${course}/assets/report.txt`]: '15 minutes\n',
    [`training/${course}/assets/styles.css`]: 'body { color: green; }\n',
    [`training/${course}/assets/app.js`]: '"use strict";\n',
    [`training/${course}/assets/workflow.svg`]: '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n',
    [`training/${course}/assets/README.md`]: 'Use synthetic data.\n',
    [`training/${course}/assets/reporting-practice.zip`]: 'Practice bundle fixture.\n',
    [`training/${legacyCourse}/index.html`]: '<h1>Harness 1.7.0</h1>\n',
    [`training/${legacyCourse}/setup.html`]: '<h1>Historical setup</h1>\n',
    [`training/${legacyCourse}/02-build/read.html`]: '<h1>Historical lesson</h1>\n',
    'training/archive/index.html': '<h1>Historical training</h1>\n',
    'training/archive/example.zip': 'Synthetic binary fixture: ZIP bytes are transported, not executed.\n',
    ...extra,
  };
  for (const [name, text] of Object.entries(files)) {
    const target = path.join(repo, name);
    mkdirSync(path.dirname(target), { recursive: true });
    writeFileSync(target, text);
  }
  execFileSync('git', ['init', '--initial-branch=main', repo]);
  execFileSync('git', ['-C', repo, 'remote', 'add', 'origin', remote]);
  execFileSync('git', ['-C', repo, 'add', 'help', 'training']);
  execFileSync('git', ['-C', repo, '-c', 'user.name=Training fixture', '-c', 'user.email=fixture@example.invalid',
    '-c', 'commit.gpgSign=false', '-c', `core.hooksPath=${path.join(repo, 'no-hooks')}`, 'commit', '-m', 'Trusted local training fixture']);
  const commit = execFileSync('git', ['-C', repo, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  return { repo, commit, files };
}

let source: ReturnType<typeof fixture>;
let baseline: string;
beforeAll(() => {
  source = fixture();
  baseline = path.join(temporary(), 'export');
  importTrainingExport({ ...source, output: baseline });
});

function copyExport() {
  const output = path.join(temporary(), 'export');
  cpSync(baseline, output, { recursive: true });
  return output;
}

function rewriteReceipt(output: string, change: (receipt: Record<string, unknown>) => void) {
  const target = path.join(output, 'import.json');
  const receipt = JSON.parse(readFileSync(target, 'utf8'));
  change(receipt);
  writeFileSync(target, JSON.stringify(receipt));
}

describe('Harness-owned training export', () => {
  it('routes committed course files before the hosted filesystem lookup', async () => {
    const rewrites = await config.rewrites!();
    const paths = [
      ['reporting/setup\\.html', 'reporting/setup.html'],
      ['reporting/02-build/read\\.html', 'reporting/02-build/read.html'],
      ['reporting/assets/reporting-practice\\.zip', 'reporting/assets/reporting-practice.zip'],
      ['1\\.7\\.0-preparation/setup\\.html', '1.7.0-preparation/setup.html'],
      ['1\\.7\\.0-preparation/02-build/read\\.html', '1.7.0-preparation/02-build/read.html'],
      ['1\\.7\\.0-preparation/assets/reporting-example\\.zip', '1.7.0-preparation/assets/reporting-example.zip'],
    ];
    expect(rewrites).toMatchObject({
      beforeFiles: expect.arrayContaining(paths.map(([source, destination]) => ({
        source: `/harness/learn/${source}`,
        destination: `/harness-training-static/${destination}`,
      }))),
      afterFiles: expect.arrayContaining([
        { source: '/harness/learn/:path*/', destination: '/harness-training-static/:path*/index.html' },
      ]),
    });
    expect(await config.redirects!()).toContainEqual({
      source: '/harness/learn/', destination: '/harness/help/get-started/#set-up-the-practice-folder', permanent: false,
    });
  });

  it('imports committed current-course, legacy, and archive bytes through Git and generator check', () => {
    const receipt = JSON.parse(readFileSync(path.join(baseline, 'import.json'), 'utf8'));
    const roots = [course, legacyCourse, 'archive'];
    const expected = Object.keys(source.files).filter((name) => roots.some((root) => name.startsWith(`training/${root}/`)));
    expect(checkTrainingExport(baseline)).toEqual({ source: source.commit, course, status: 'published', files: expected.length });
    expect(Object.keys(receipt.files).sort()).toEqual(expected.map((name) => name.slice('training/'.length)).sort());
    for (const name of expected) {
      const relative = name.slice('training/'.length);
      const bytes = readFileSync(path.join(source.repo, name));
      expect(readFileSync(path.join(baseline, relative))).toEqual(bytes);
      expect(receipt.files[relative]).toBe(digest(bytes));
    }
    expect(receipt.source_url).toBe(`https://github.com/Smart-AI-Memory/attune-harness/tree/${source.commit}`);
    expect(existsSync(path.join(baseline, 'build_course.py'))).toBe(false);
  });

  it('ignores uncommitted working-tree changes and refuses an existing output', () => {
    const target = path.join(source.repo, `training/${course}/index.html`);
    writeFileSync(target, 'Uncommitted content must not ship.');
    const output = path.join(temporary(), 'export');
    importTrainingExport({ ...source, output });
    expect(readFileSync(path.join(output, `${course}/index.html`), 'utf8')).toBe(source.files[`training/${course}/index.html`]);
    expect(() => importTrainingExport({ ...source, output })).toThrow('fresh training export directory');
  });

  it('refuses changed payload bytes and both directions of inventory drift', () => {
    const changed = copyExport();
    writeFileSync(path.join(changed, `${course}/index.html`), 'Changed');
    expect(() => checkTrainingExport(changed)).toThrow('Training export byte drift');
    const extra = copyExport();
    writeFileSync(path.join(extra, `${course}/unknown.html`), 'Extra');
    expect(() => checkTrainingExport(extra)).toThrow('Training export file set drift');
    const missing = copyExport();
    rewriteReceipt(missing, (receipt) => { (receipt.files as Record<string, string>)[`${course}/missing.html`] = '0'.repeat(64); });
    expect(() => checkTrainingExport(missing)).toThrow('Training export file set drift');
  });

  it.each([
    '../outside.html', '/absolute.html', 'archive/../outside.html', 'archive\\outside.html',
    'other/index.html', `${course}/.hidden.html`, `${course}/assets/program.exe`, `${course}//index.html`,
    'C:/archive/index.html', `${course}/assets/two words.html`,
  ])('refuses unsafe or out-of-scope receipt path %s before reading it', (name) => {
    const output = copyExport();
    rewriteReceipt(output, (receipt) => { (receipt.files as Record<string, string>)[name] = '0'.repeat(64); });
    expect(() => checkTrainingExport(output)).toThrow('Invalid training export path');
  });

  it.each([
    { source_repository: 'lookalike/attune-harness' }, { source_commit: 'main' },
    { source_url: 'https://example.invalid/source' }, { schema_version: 2 },
    { course: '1.8.0' }, { status: 'preparation' },
  ])('refuses invalid published course provenance %j', (change) => {
    const output = copyExport();
    rewriteReceipt(output, (receipt) => Object.assign(receipt, change));
    expect(() => checkTrainingExport(output)).toThrow('exact Harness published course provenance');
  });

  it('refuses malformed hash maps, digests and missing entry indexes', () => {
    const map = copyExport();
    rewriteReceipt(map, (receipt) => { receipt.files = []; });
    expect(() => checkTrainingExport(map)).toThrow('file-hash map');
    const badHash = copyExport();
    rewriteReceipt(badHash, (receipt) => { (receipt.files as Record<string, string>)[`${course}/index.html`] = 'not-a-hash'; });
    expect(() => checkTrainingExport(badHash)).toThrow('Invalid training file hash');
    const missing = copyExport();
    rewriteReceipt(missing, (receipt) => { delete (receipt.files as Record<string, string>)['archive/index.html']; });
    expect(() => checkTrainingExport(missing)).toThrow('current-course and archive entry points');
  });

  it.each([
    { status: 'published', published_version: '1.8.0rc1' },
    { status: 'preparation', published_version: '1.8.0' },
  ])('refuses invalid publication metadata %j', (manifest) => {
    const preparation = fixture({
      extra: { 'help/manifest.json': JSON.stringify(manifest) },
      check: 'raise SystemExit("renderer must not run for a preparation source")\n',
    });
    const output = path.join(temporary(), 'export');
    expect(() => importTrainingExport({ ...preparation, output })).toThrow('published Harness Help manifest with a release version');
    expect(existsSync(output)).toBe(false);
  });

  it('keeps the course identity when the published Help release advances', () => {
    const later = fixture({ extra: {
      'help/manifest.json': JSON.stringify({ status: 'published', published_version: '1.9.0' }),
    } });
    const output = path.join(temporary(), 'export');
    expect(importTrainingExport({ ...later, output })).toMatchObject({ course, status: 'published' });
  });

  it('refuses lookalike origins and abbreviated source commits before output creation', () => {
    const wrong = fixture({ remote: 'https://example.invalid/Smart-AI-Memory/attune-harness.git' });
    const output = path.join(temporary(), 'export');
    expect(() => importTrainingExport({ ...wrong, output })).toThrow('not Harness on GitHub');
    expect(() => importTrainingExport({ ...source, commit: source.commit.slice(0, 8), output })).toThrow('full source commit');
    expect(existsSync(output)).toBe(false);
  });

  it('refuses linked export roots, parent directories, nested files and source roots', () => {
    const parent = temporary();
    const copied = copyExport();
    const linked = path.join(parent, 'linked');
    symlinkSync(copied, linked, 'dir');
    expect(() => checkTrainingExport(linked)).toThrow('symlinks');
    expect(() => checkTrainingExport(path.join(linked, course))).toThrow('symlinks');
    expect(() => importTrainingExport({ ...source, output: path.join(linked, 'fresh') })).toThrow('symlinks');
    symlinkSync(path.join(copied, `${course}/index.html`), path.join(copied, `${course}/linked.html`));
    expect(() => checkTrainingExport(copied)).toThrow('symlinks');
    const linkedRepo = path.join(parent, 'source');
    symlinkSync(source.repo, linkedRepo, 'dir');
    expect(() => importTrainingExport({ ...source, repo: linkedRepo, output: path.join(parent, 'export') })).toThrow('symlinks');
  });

  it('refuses symlink entries in the committed source before extraction', () => {
    const linked = fixture();
    symlinkSync('index.html', path.join(linked.repo, `training/${course}/linked.html`));
    execFileSync('git', ['-C', linked.repo, 'add', 'training']);
    execFileSync('git', ['-C', linked.repo, '-c', 'user.name=Training fixture', '-c', 'user.email=fixture@example.invalid',
      '-c', 'commit.gpgSign=false', '-c', `core.hooksPath=${path.join(linked.repo, 'no-hooks')}`, 'commit', '-m', 'Symlink refusal fixture']);
    linked.commit = execFileSync('git', ['-C', linked.repo, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    expect(() => importTrainingExport({ ...linked, output: path.join(temporary(), 'export') })).toThrow('without symlinks');
  });

  it('refuses a failed generator check and a check that changes payload bytes', () => {
    const failed = fixture({ check: 'raise SystemExit("deliberate check failure")\n' });
    const failedOutput = path.join(temporary(), 'export');
    expect(() => importTrainingExport({ ...failed, output: failedOutput })).toThrow('deliberate check failure');
    expect(existsSync(failedOutput)).toBe(false);
    const changed = fixture({ check: `from pathlib import Path\np = Path(__file__).parent / "${course}/index.html"\np.write_text("changed")\n` });
    const changedOutput = path.join(temporary(), 'export');
    expect(() => importTrainingExport({ ...changed, output: changedOutput })).toThrow('changed committed payload bytes');
    expect(existsSync(changedOutput)).toBe(false);
  });

  it('refuses an unexpected source extension before creating output', () => {
    const bad = fixture({ extra: { [`training/${course}/assets/unexpected.exe`]: 'unapproved' } });
    const output = path.join(temporary(), 'export');
    expect(() => importTrainingExport({ ...bad, output })).toThrow('Invalid training export path');
    expect(existsSync(output)).toBe(false);
  });

  it('supports the same integrity check through the CLI and refuses unknown arguments', () => {
    const result = execFileSync(process.execPath, [importer, 'check', '--output', baseline], { encoding: 'utf8' });
    expect(JSON.parse(result)).toMatchObject({ source: source.commit, course, status: 'published' });
    expect(() => execFileSync(process.execPath, [importer, 'check', '--unknown', 'value'])).toThrow();
  });
});
