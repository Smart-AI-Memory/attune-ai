/** Import reviewed Harness training bytes without creating another content owner. */
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const defaultOutput = path.join(website, 'public/harness-training-static');
const repository = 'Smart-AI-Memory/attune-harness';
const course = '1.7.0-preparation';
const roots = [course, 'archive'];
const entryPoints = [`${course}/index.html`, `${course}/setup.html`, 'archive/index.html'];
const extensions = new Set(['.html', '.css', '.js', '.json', '.svg', '.py', '.csv', '.txt', '.ini', '.md', '.zip']);
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');

function rejectSymlinkParents(filename) {
  for (let current = filename; ; current = path.dirname(current)) {
    if (lstatSync(current, { throwIfNoEntry: false })?.isSymbolicLink()) {
      throw new Error('Training paths cannot contain symlinks');
    }
    if (current === path.dirname(current)) return;
  }
}

function relativeFile(name) {
  const parts = typeof name === 'string' ? name.split('/') : [];
  if (parts.length < 2 || !roots.includes(parts[0])
      || parts.some((part) => !/^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$/.test(part))
      || !extensions.has(path.posix.extname(name))) {
    throw new Error(`Invalid training export path: ${name}`);
  }
  return name;
}

function inventory(root, prefix = '') {
  return readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const name = prefix + entry.name;
    if (entry.isSymbolicLink()) throw new Error('Training export cannot contain symlinks');
    if (entry.isDirectory()) return inventory(path.join(root, entry.name), name + '/');
    if (!entry.isFile()) throw new Error('Training export requires regular files');
    return [name];
  }).sort();
}

function payload(root) {
  return Object.fromEntries(roots.flatMap((directory) => (
    inventory(path.join(root, directory), directory + '/')
  )).sort().map((name) => [relativeFile(name), hash(readFileSync(path.join(root, name)))]));
}

/** Verify source identity, the complete payload inventory and every recorded hash. */
export function checkTrainingExport(output = defaultOutput) {
  output = path.resolve(output);
  rejectSymlinkParents(output);
  const actual = inventory(output);
  const receipt = JSON.parse(readFileSync(path.join(output, 'import.json'), 'utf8'));
  if (receipt.schema_version !== 1 || receipt.source_repository !== repository
      || typeof receipt.source_commit !== 'string' || !/^[a-f0-9]{40}$/.test(receipt.source_commit)
      || receipt.source_url !== `https://github.com/${repository}/tree/${receipt.source_commit}`
      || receipt.course !== course || receipt.status !== 'published') {
    throw new Error('Training export requires exact Harness published course provenance');
  }
  if (!receipt.files || typeof receipt.files !== 'object' || Array.isArray(receipt.files)) {
    throw new Error('Training export requires a file-hash map');
  }
  for (const [name, digest] of Object.entries(receipt.files)) {
    relativeFile(name);
    if (typeof digest !== 'string' || !/^[a-f0-9]{64}$/.test(digest)) throw new Error(`Invalid training file hash: ${name}`);
  }
  if (entryPoints.some((name) => !Object.hasOwn(receipt.files, name))) {
    throw new Error('Training export requires current-course and archive entry points');
  }
  const expected = [...Object.keys(receipt.files), 'import.json'].sort();
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error('Training export file set drift');
  for (const [name, digest] of Object.entries(receipt.files)) {
    if (hash(readFileSync(path.join(output, name))) !== digest) throw new Error(`Training export byte drift: ${name}`);
  }
  return { source: receipt.source_commit, course, status: receipt.status, files: Object.keys(receipt.files).length };
}

/** Check a trusted committed source in scratch space and copy its unmodified payload. */
export function importTrainingExport({ repo, commit, python = 'python3', output = defaultOutput }) {
  if (!/^[a-f0-9]{40}$/.test(commit ?? '')) throw new Error('Use a full source commit');
  repo = path.resolve(repo);
  output = path.resolve(output);
  rejectSymlinkParents(repo);
  rejectSymlinkParents(output);
  repo = realpathSync(repo);
  if (existsSync(output)) throw new Error('Choose a fresh training export directory; review replacements separately');
  const origin = execFileSync('git', ['-C', repo, 'remote', 'get-url', 'origin'], { encoding: 'utf8' }).trim();
  if (!/^(?:https:\/\/github\.com\/|git@github\.com:|ssh:\/\/git@github\.com\/)Smart-AI-Memory\/attune-harness(?:\.git)?$/.test(origin)) {
    throw new Error('Source repository is not Harness on GitHub');
  }
  const manifest = JSON.parse(execFileSync('git', ['-C', repo, 'show', `${commit}:help/manifest.json`], { encoding: 'utf8' }));
  if (manifest?.status !== 'published' || manifest.published_version !== '1.7.0') {
    throw new Error('Training source requires a published Harness 1.7.0 Help manifest');
  }
  const entries = execFileSync('git', ['-C', repo, 'ls-tree', '-rz', commit, '--', 'training'], { encoding: 'utf8' }).split('\0').filter(Boolean);
  if (entries.some((entry) => !/^100(?:644|755) blob /.test(entry))) {
    throw new Error('Training source must contain regular files, without symlinks');
  }
  const temporary = mkdtempSync(path.join(realpathSync(tmpdir()), 'harness-training-import-'));
  const source = path.join(temporary, 'source');
  mkdirSync(source);
  const archive = execFileSync('git', ['-C', repo, 'archive', '--format=tar', commit, '--', 'training'], { maxBuffer: 32 * 1024 * 1024 });
  execFileSync('tar', ['-xf', '-', '-C', source], { input: archive });
  const training = path.join(source, 'training');
  const files = payload(training);
  if (entryPoints.some((name) => !Object.hasOwn(files, name))) {
    throw new Error('Training source requires current-course and archive entry points');
  }
  execFileSync(python, [path.join(training, 'build_course.py'), '--check'], { cwd: source });
  if (JSON.stringify(payload(training)) !== JSON.stringify(files)) {
    throw new Error('Training source check changed committed payload bytes');
  }
  mkdirSync(output, { recursive: true });
  for (const name of Object.keys(files)) {
    const target = path.join(output, name);
    mkdirSync(path.dirname(target), { recursive: true });
    writeFileSync(target, readFileSync(path.join(training, name)));
  }
  writeFileSync(path.join(output, 'import.json'), JSON.stringify({
    schema_version: 1, source_repository: repository, source_commit: commit,
    source_url: `https://github.com/${repository}/tree/${commit}`, course,
    status: 'published', files,
  }, null, 2) + '\n');
  return checkTrainingExport(output);
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  const [command = 'check', ...args] = process.argv.slice(2);
  const options = {};
  for (let index = 0; index < args.length; index += 2) {
    const name = args[index].replace(/^--/, '');
    if (!['repo', 'commit', 'python', 'output'].includes(name) || !args[index + 1]) throw new Error('Invalid training import arguments');
    options[name] = args[index + 1];
  }
  if (!['check', 'import'].includes(command)) throw new Error('Use check or import');
  console.info(JSON.stringify(command === 'import' ? importTrainingExport(options) : checkTrainingExport(options.output), null, 2));
}
