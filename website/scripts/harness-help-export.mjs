/** Import committed Harness documentation and check the published static bytes. */
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const defaultOutput = path.join(website, 'public/harness-help-static');
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');

function rejectSymlinkParents(output) {
  for (let current = output; ; current = path.dirname(current)) {
    if (lstatSync(current, { throwIfNoEntry: false })?.isSymbolicLink()) {
      throw new Error('Export path cannot contain symlinks');
    }
    if (current === path.dirname(current)) return;
  }
}

function relativeFile(name) {
  if (!/^[a-z0-9_/-]+\.(html|css|json)$/.test(name) || name.split('/').some((part) => part === '..' || !part)) {
    throw new Error(`Invalid export path: ${name}`);
  }
  return name;
}

function inventory(root, prefix = '') {
  return readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const name = prefix + entry.name;
    if (entry.isSymbolicLink()) throw new Error('Export cannot contain symlinks');
    return entry.isDirectory() ? inventory(path.join(root, entry.name), name + '/') : [name];
  });
}

/** Check the imported receipt, exact file set and hashes; make no network calls. */
export function checkExport(output = defaultOutput) {
  output = path.resolve(output);
  rejectSymlinkParents(output);
  const receipt = JSON.parse(readFileSync(path.join(output, 'import.json'), 'utf8'));
  if (receipt.source_repository !== 'Smart-AI-Memory/attune-harness' || !/^[a-f0-9]{40}$/.test(receipt.source_commit)) {
    throw new Error('Export requires an exact Harness source commit');
  }
  const buildBytes = readFileSync(path.join(output, 'build.json'));
  if (hash(buildBytes) !== receipt.build_sha256) throw new Error('Build record drift');
  const build = JSON.parse(buildBytes);
  if (build.version !== '1.5.0' || build.source_repository !== receipt.source_repository) throw new Error('Unexpected Harness release');
  const files = Object.fromEntries(Object.entries(build.files).map(([name, digest]) => {
    if (!name.startsWith('harness/help/')) throw new Error('Export leaves its public root');
    return [relativeFile(name.slice('harness/help/'.length)), digest];
  }));
  const actual = inventory(output).sort();
  const expected = [...Object.keys(files), 'build.json', 'import.json'].sort();
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error('Export file set drift');
  for (const [name, digest] of Object.entries(files)) {
    if (hash(readFileSync(path.join(output, name))) !== digest) throw new Error(`Export byte drift: ${name}`);
  }
  return { source: receipt.source_commit, version: build.version, pages: build.pages, files: actual.length };
}

/** Build an exact committed source in scratch space, then create a fresh export. */
export function importExport({ repo, commit, python = 'python3', output = defaultOutput }) {
  if (!/^[a-f0-9]{40}$/.test(commit ?? '')) throw new Error('Use a full source commit');
  repo = realpathSync(repo);
  output = path.resolve(output);
  rejectSymlinkParents(output);
  if (existsSync(output)) throw new Error('Choose a fresh export directory; review replacements separately');
  const origin = execFileSync('git', ['-C', repo, 'remote', 'get-url', 'origin'], { encoding: 'utf8' }).trim();
  if (!/^(?:https:\/\/github\.com\/|git@github\.com:|ssh:\/\/git@github\.com\/)Smart-AI-Memory\/attune-harness(?:\.git)?$/.test(origin)) throw new Error('Source repository is not Harness on GitHub');
  const temporary = mkdtempSync(path.join(realpathSync(tmpdir()), 'harness-help-import-'));
  const source = path.join(temporary, 'source');
  mkdirSync(source);
  const archive = execFileSync('git', ['-C', repo, 'archive', '--format=tar', commit, '--', 'help', 'scripts/build_help.py']);
  execFileSync('tar', ['-xf', '-', '-C', source], { input: archive });
  const built = path.join(temporary, 'export');
  execFileSync(python, [path.join(source, 'scripts/build_help.py'), '--output', built]);
  const publicRoot = path.join(built, 'harness/help');
  const buildBytes = readFileSync(path.join(publicRoot, 'build.json'));
  const build = JSON.parse(buildBytes);
  mkdirSync(output, { recursive: true });
  for (const filename of inventory(publicRoot)) {
    relativeFile(filename);
    const target = path.join(output, filename);
    mkdirSync(path.dirname(target), { recursive: true });
    writeFileSync(target, readFileSync(path.join(publicRoot, filename)));
  }
  writeFileSync(path.join(output, 'import.json'), JSON.stringify({
    source_repository: build.source_repository,
    source_commit: commit,
    source_url: `https://github.com/Smart-AI-Memory/attune-harness/tree/${commit}`,
    build_sha256: hash(buildBytes),
  }, null, 2) + '\n');
  return checkExport(output);
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  const [command = 'check', ...args] = process.argv.slice(2);
  const options = {};
  for (let index = 0; index < args.length; index += 2) {
    const name = args[index].replace(/^--/, '');
    if (!['repo', 'commit', 'python', 'output'].includes(name) || !args[index + 1]) throw new Error('Invalid import arguments');
    options[name] = args[index + 1];
  }
  if (!['check', 'import'].includes(command)) throw new Error('Use check or import');
  console.info(JSON.stringify(command === 'import' ? importExport(options) : checkExport(options.output), null, 2));
}
