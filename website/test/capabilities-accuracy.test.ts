import { describe, it, expect } from 'vitest';
import { execFileSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { CAPABILITIES } from '../lib/features';

// Accuracy guard for the homepage stat band / pillar copy.
//
// The website-content-accuracy rule requires every count shown on the
// site to match the live Python registry. This test is the automated
// enforcement of that rule for `CAPABILITIES` in lib/features.ts —
// it catches the "14 workflows / 10 wizards / 13 templates"-style drift
// that previously slipped onto the site.
//
// - The `skills` count is checked against the filesystem (plugin/skills),
//   so it runs in any environment with no Python required.
// - The remaining counts are checked against the live registry by
//   shelling out to Python. If attune isn't importable (e.g. a bare
//   node-only checkout), that assertion is skipped with a clear note
//   rather than failing. Point ATTUNE_PYTHON at a venv to force it
//   (e.g. ATTUNE_PYTHON=../.venv/bin/python npm test).

const repoRoot = resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..');
const pythonpath = resolve(repoRoot, 'src');

/** Find a python that can import attune, or null if none can. */
function resolvePython(): string | null {
  const candidates = [
    process.env.ATTUNE_PYTHON,
    'python3',
    'python',
    resolve(repoRoot, '.venv', 'bin', 'python'),
  ].filter(Boolean) as string[];

  for (const py of candidates) {
    try {
      execFileSync(py, ['-c', 'import attune'], {
        env: { ...process.env, PYTHONPATH: pythonpath },
        stdio: 'ignore',
      });
      return py;
    } catch {
      // try the next candidate
    }
  }
  return null;
}

const INTROSPECT = [
  'import json',
  'd = {}',
  // D4 (claim-drift-gates): workflows = distinct CLASSES, not slugs —
  // release-prep/release-gate are a deliberate alias pair. Must match
  // tests/unit/test_website_version_accuracy.py's counter exactly.
  'from attune.workflows import discover_workflows',
  "d['workflows'] = len(set(discover_workflows().values()))",
  'from attune.wizards import list_wizards',
  "d['wizards'] = len(list_wizards())",
  'from attune.mcp import tool_schemas as ts',
  "d['mcpTools'] = sum(len(getattr(ts, n)()) for n in dir(ts) if n.startswith('get_') and n.endswith('_tools'))",
  'try:',
  '    from attune_author.generator import _ALL_TEMPLATE_NAMES',
  "    d['templateKinds'] = len(_ALL_TEMPLATE_NAMES)",
  'except Exception:',
  '    pass',
  'print(json.dumps(d))',
].join('\n');

describe('website CAPABILITIES accuracy', () => {
  it('skills count matches the plugin/skills directory count', () => {
    const skillsDir = resolve(repoRoot, 'plugin', 'skills');
    const dirCount = readdirSync(skillsDir, { withFileTypes: true }).filter(
      (d) => d.isDirectory(),
    ).length;
    expect(CAPABILITIES.skills).toBe(dirCount);
  });

  const python = resolvePython();

  it.skipIf(!python)(
    'workflow / wizard / MCP-tool / template counts match the live registry',
    () => {
      const raw = execFileSync(python as string, ['-c', INTROSPECT], {
        env: { ...process.env, PYTHONPATH: pythonpath },
        encoding: 'utf8',
      });
      const real = JSON.parse(raw) as Record<string, number>;

      // Sanity: the registry calls we depend on must have resolved.
      expect(real.workflows).toBeTypeOf('number');
      expect(real.wizards).toBeTypeOf('number');
      expect(real.mcpTools).toBeTypeOf('number');

      expect(CAPABILITIES.workflows).toBe(real.workflows);
      expect(CAPABILITIES.wizards).toBe(real.wizards);
      expect(CAPABILITIES.mcpTools).toBe(real.mcpTools);

      // attune_author is a separate package; only assert when present.
      if (typeof real.templateKinds === 'number') {
        expect(CAPABILITIES.templateKinds).toBe(real.templateKinds);
      }
    },
  );
});
