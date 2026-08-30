import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  actionResponse,
  buildPreview,
  canonicalJson,
  collectAction,
  contractHash,
  createPreviewState,
  parseArgv,
  shellJoin,
} from '../../attune-ai-dev/fix-workspace/demo.js';

const answers = {
  request: 'Prevent replayed Fix approvals after a contract edit',
  scope: 'src/attune/elicitation/fix_workspace.py',
  probes: ['python -m pytest -q tests/unit/elicitation/test_fix_workspace.py'],
};

describe('public Fix workspace contract', () => {
  it('matches the production canonical hash fixture', async () => {
    const { preview } = buildPreview(answers);
    expect(await contractHash(preview)).toBe(
      '487ff289e11a87006d0d98c01a5c63b1cebc984fe035e02e28370dbba1d7b9e5',
    );
    expect(JSON.parse(canonicalJson(preview))).toEqual(preview);
    expect(shellJoin(preview.command_argv)).toContain("attune fix 'Prevent replayed");
  });

  it('invalidates authority on edit, approves once, and rejects replay', async () => {
    const initial = await createPreviewState(answers);
    const edit = await collectAction(
      initial,
      actionResponse(initial, 'edit_contract', false),
    );
    expect(edit.state).toMatchObject({
      revision: 1,
      view: 'intake',
      preview: null,
      contract_hash: '',
      action_nonce: '',
    });

    const revised = await createPreviewState(
      { ...answers, request: `${answers.request} safely` },
      edit.state,
    );
    expect(revised.revision).toBe(2);
    expect(revised.contract_hash).not.toBe(initial.contract_hash);

    const response = actionResponse(revised, 'run_fix', true);
    const approved = await collectAction(revised, response);
    expect(approved.execution_started).toBe(false);
    expect(approved.approved_command_argv.at(-1)).toBe('--run');
    expect(approved.state.approved_contract_hash).toBe(revised.contract_hash);
    expect(approved.state.action_nonce).toBe('');
    await expect(collectAction(approved.state, response)).rejects.toThrow(
      'action nonce was already consumed',
    );
  });

  it('rejects shell syntax and stale binding mutations', async () => {
    expect(() => parseArgv('pytest -q; touch nope')).toThrow('shell metacharacters');
    const state = await createPreviewState(answers);
    const response = actionResponse(state, 'run_fix', true);
    await expect(
      collectAction(state, { ...response, contract_hash: '0'.repeat(64) }),
    ).rejects.toThrow('contract_hash does not match canonical state');
  });

  it('keeps the smartaimemory.com projection in sync with its asset root', () => {
    const root = resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..');
    for (const name of ['demo.css', 'demo.js']) {
      const source = readFileSync(resolve(root, 'attune-ai-dev', 'fix-workspace', name));
      const projection = readFileSync(
        resolve(root, 'website', 'public', 'fix-workspace-demo', name),
      );
      expect(projection.equals(source)).toBe(true);
    }

    const sourceHtml = readFileSync(
      resolve(root, 'attune-ai-dev', 'fix-workspace', 'index.html'),
      'utf8',
    );
    const expectedHtml = sourceHtml
      .replaceAll('/fix-workspace/demo.css', '/fix-workspace-demo/demo.css')
      .replaceAll('/fix-workspace/demo.js', '/fix-workspace-demo/demo.js');
    const projectionHtml = readFileSync(
      resolve(root, 'website', 'public', 'fix-workspace-demo', 'index.html'),
      'utf8',
    );
    expect(projectionHtml).toBe(expectedHtml);
  });
});
