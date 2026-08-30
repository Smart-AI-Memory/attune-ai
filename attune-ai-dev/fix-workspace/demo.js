const SHELL_METACHARACTERS = new Set([';', '|', '&', '<', '>', '`', '$']);
const SAFE_SHELL_TOKEN = /^[A-Za-z0-9_@%+=:,./-]+$/;

export function parseArgv(raw) {
  if (typeof raw !== 'string' || !raw.trim()) {
    throw new Error('Verification probes must contain non-empty commands.');
  }
  const bad = [...raw].filter((character) => SHELL_METACHARACTERS.has(character));
  if (bad.length) {
    throw new Error(
      `Probe contains shell metacharacters (${[...new Set(bad)].sort().join('')}); ` +
        'probes are argv lists and never run through a shell.',
    );
  }

  const tokens = [];
  let current = '';
  let quote = null;
  let escaped = false;
  let started = false;

  for (const character of raw.trim()) {
    if (escaped) {
      current += character;
      escaped = false;
      started = true;
      continue;
    }
    if (quote === "'") {
      if (character === "'") quote = null;
      else current += character;
      continue;
    }
    if (quote === '"') {
      if (character === '"') quote = null;
      else if (character === '\\') escaped = true;
      else current += character;
      continue;
    }
    if (character === "'" || character === '"') {
      quote = character;
      started = true;
    } else if (character === '\\') {
      escaped = true;
      started = true;
    } else if (/\s/.test(character)) {
      if (started) tokens.push(current);
      current = '';
      started = false;
    } else {
      current += character;
      started = true;
    }
  }

  if (quote) throw new Error('Probe contains an unclosed quote.');
  if (escaped) throw new Error('Probe ends with an incomplete escape.');
  if (started) tokens.push(current);
  if (!tokens.length || tokens.some((token) => !token)) {
    throw new Error('Verification probes must contain non-empty argv tokens.');
  }
  return tokens;
}

export function shellQuote(token) {
  if (SAFE_SHELL_TOKEN.test(token)) return token;
  return `'${token.replaceAll("'", `'"'"'`)}'`;
}

export function shellJoin(argv) {
  return argv.map(shellQuote).join(' ');
}

function normalizeScope(raw) {
  if (typeof raw !== 'string' || !raw.trim()) {
    throw new Error('Scope must be a non-empty repository-relative path.');
  }
  const value = raw.trim().replaceAll('\\', '/');
  if (value.startsWith('/') || /^[A-Za-z]:\//.test(value)) {
    throw new Error('Scope must be repository-relative, not absolute.');
  }
  const parts = value.split('/').filter((part) => part && part !== '.');
  if (!parts.length || parts.includes('..')) {
    throw new Error('Scope must stay inside the repository.');
  }
  return parts.join('/');
}

function normalizedAnswers(raw) {
  const request = typeof raw.request === 'string' ? raw.request.trim() : '';
  if (!request) throw new Error('Request must be a non-empty string.');
  const scope = normalizeScope(raw.scope);
  const probeLines = Array.isArray(raw.probes)
    ? raw.probes
    : String(raw.probes ?? '').split('\n');
  const probes = probeLines.map((probe) => String(probe).trim()).filter(Boolean);
  if (!probes.length) throw new Error('Add at least one verification probe.');
  probes.forEach(parseArgv);
  return { request, scope, probes };
}

export function buildPreview(rawAnswers) {
  const answers = normalizedAnswers(rawAnswers);
  const probes = answers.probes.map((probe) => ({
    argv: parseArgv(probe),
    description: '',
    expected_exit: 0,
  }));
  const doneConditions = [
    ...probes.map(
      (probe) =>
        `probe passes: ${probe.argv.join(' ')} (expect exit ${probe.expected_exit})`,
    ),
    `diff confined to ${answers.scope}`,
  ];
  const constraints = [
    `workflow edits confined to ${answers.scope}`,
    'verification probes run independently as argv without a shell',
  ];
  const commandArgv = ['attune', 'fix', answers.request, '--workflow', 'fix'];
  for (const probe of probes) {
    commandArgv.push('--probe', shellJoin(probe.argv));
  }
  commandArgv.push('--scope', answers.scope, '--run');

  return {
    answers,
    preview: {
      schema_version: 1,
      goal: answers.request,
      scope: answers.scope,
      done_conditions: doneConditions,
      constraints,
      probes,
      workflow: 'fix',
      command_argv: commandArgv,
    },
  };
}

function sortForCanonicalJson(value) {
  if (Array.isArray(value)) return value.map(sortForCanonicalJson);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, sortForCanonicalJson(value[key])]),
    );
  }
  return value;
}

export function canonicalJson(preview) {
  return JSON.stringify(sortForCanonicalJson(preview));
}

export async function contractHash(preview) {
  const bytes = new TextEncoder().encode(canonicalJson(preview));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

function equalAuthority(left, right) {
  if (typeof left !== 'string' || typeof right !== 'string' || left.length !== right.length) {
    return false;
  }
  let different = 0;
  for (let index = 0; index < left.length; index += 1) {
    different |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return different === 0;
}

export async function createPreviewState(rawAnswers, current = null) {
  if (current && current.view !== 'intake') {
    throw new Error('Select Edit contract before replacing a Fix preview.');
  }
  const { answers, preview } = buildPreview(rawAnswers);
  const hash = await contractHash(preview);
  const revision = current ? current.revision + 1 : 0;
  return {
    schema_version: 1,
    workspace_id: current?.workspace_id ?? 'fix-public-demo',
    revision,
    view: 'preview',
    answers,
    preview,
    contract_hash: hash,
    approved_contract_hash: '',
    action_nonce: `demo-r${revision}-${hash.slice(0, 22)}`,
  };
}

export function actionResponse(state, action, confirmed) {
  return {
    __elicitation_response__: true,
    title: 'Fix preview',
    workspace_id: state.workspace_id,
    revision: state.revision,
    view: 'preview',
    action,
    action_nonce: state.action_nonce,
    contract_hash: state.contract_hash,
    confirmed,
  };
}

export async function collectAction(state, response) {
  if (!state?.preview || state.view !== 'preview') {
    throw new Error('Fix workspace is not awaiting a preview action.');
  }
  if (!state.action_nonce) {
    throw new Error('Fix workspace action nonce was already consumed.');
  }
  const rebuilt = buildPreview(state.answers).preview;
  const rebuiltHash = await contractHash(rebuilt);
  if (!equalAuthority(rebuiltHash, state.contract_hash)) {
    throw new Error('Fix contract changed after it was rendered.');
  }

  for (const key of ['workspace_id', 'action_nonce', 'contract_hash']) {
    if (!equalAuthority(String(response[key] ?? ''), String(state[key]))) {
      throw new Error(`Workspace action response ${key} does not match canonical state.`);
    }
  }
  if (response.revision !== state.revision) {
    throw new Error('Workspace action response revision does not match canonical state.');
  }
  if (!['edit_contract', 'run_fix'].includes(response.action)) {
    throw new Error('Workspace action is not declared by this view.');
  }

  if (response.action === 'edit_contract') {
    return {
      action: response.action,
      approved_command_argv: [],
      execution_started: false,
      state: {
        ...state,
        revision: state.revision + 1,
        view: 'intake',
        preview: null,
        contract_hash: '',
        approved_contract_hash: '',
        action_nonce: '',
      },
    };
  }
  if (response.confirmed !== true) {
    throw new Error('Run Fix requires explicit confirmation.');
  }
  return {
    action: response.action,
    approved_command_argv: [...rebuilt.command_argv],
    execution_started: false,
    state: {
      ...state,
      revision: state.revision + 1,
      approved_contract_hash: state.contract_hash,
      action_nonce: '',
    },
  };
}

function initDemo() {
  const byId = (id) => document.getElementById(id);
  const intake = byId('intake');
  const workspace = byId('workspace-view');
  const error = byId('form-error');
  const approval = byId('approval-dialog');
  const replay = byId('replay');
  let state = null;
  let lastResponse = null;

  const log = (message, tone = '') => {
    const item = document.createElement('li');
    item.textContent = message;
    if (tone) item.dataset.tone = tone;
    byId('events').prepend(item);
  };

  const postHeight = () => {
    if (window.parent !== window) {
      window.parent.postMessage(
        { type: 'attune-fix-demo-height', height: document.documentElement.scrollHeight },
        '*',
      );
    }
  };

  const showError = (message = '') => {
    error.textContent = message;
    error.hidden = !message;
    postHeight();
  };

  const renderState = () => {
    byId('stage').textContent = state?.view ?? 'intake';
    byId('workspace-id').textContent = state?.workspace_id ?? '—';
    byId('revision').textContent = state ? String(state.revision) : '—';
    byId('contract-hash').textContent = state?.contract_hash || 'invalidated';
    byId('nonce').textContent = state?.action_nonce
      ? `live · ${state.action_nonce.slice(0, 16)}…`
      : 'consumed / absent';
    byId('execution').textContent = 'not started';
  };

  const fillList = (id, rows) => {
    const list = byId(id);
    list.replaceChildren(...rows.map((row) => Object.assign(document.createElement('li'), { textContent: row })));
  };

  const showPreview = () => {
    const preview = state.preview;
    byId('goal').textContent = preview.goal;
    byId('scope-value').textContent = preview.scope;
    byId('workflow').textContent = preview.workflow;
    fillList('conditions', preview.done_conditions);
    fillList('constraints', preview.constraints);
    byId('command').textContent = shellJoin(preview.command_argv);
    byId('preview-hash').textContent = state.contract_hash;
    intake.hidden = true;
    workspace.hidden = false;
    byId('receipt').hidden = true;
    replay.hidden = true;
    renderState();
    postHeight();
  };

  const renderPreview = async () => {
    const renderButton = byId('render');
    renderButton.disabled = true;
    showError();
    try {
      state = await createPreviewState(
        {
          request: byId('request').value,
          scope: byId('scope').value,
          probes: byId('probes').value,
        },
        state,
      );
      showPreview();
      log(`Preview rendered · revision ${state.revision} · execution_started=false`);
    } catch (problem) {
      showError(problem.message);
      log(problem.message, 'error');
    } finally {
      renderButton.disabled = false;
    }
  };

  intake.addEventListener('submit', (event) => {
    event.preventDefault();
    void renderPreview();
  });

  byId('edit-contract').addEventListener('click', async () => {
    try {
      lastResponse = actionResponse(state, 'edit_contract', false);
      const result = await collectAction(state, lastResponse);
      state = result.state;
      workspace.hidden = true;
      intake.hidden = false;
      renderState();
      byId('request').focus();
      log('Edit accepted · preview hash and action authority invalidated');
      postHeight();
    } catch (problem) {
      log(problem.message, 'error');
    }
  });

  byId('run-fix').addEventListener('click', () => {
    byId('approval-command').textContent = shellJoin(state.preview.command_argv);
    byId('approval-hash').textContent = state.contract_hash;
    approval.showModal();
  });

  byId('cancel-approval').addEventListener('click', () => approval.close());
  byId('authorize-once').addEventListener('click', async () => {
    try {
      lastResponse = actionResponse(state, 'run_fix', true);
      const result = await collectAction(state, lastResponse);
      state = result.state;
      approval.close();
      renderState();
      byId('approved-argv').textContent = JSON.stringify(result.approved_command_argv);
      byId('approved-hash').textContent = state.approved_contract_hash;
      byId('receipt').hidden = false;
      replay.hidden = false;
      byId('edit-contract').disabled = true;
      byId('run-fix').disabled = true;
      log(`Approval validated · execution_started=${result.execution_started}`, 'success');
      postHeight();
    } catch (problem) {
      approval.close();
      log(problem.message, 'error');
    }
  });

  replay.addEventListener('click', async () => {
    try {
      await collectAction(state, lastResponse);
      log('Unexpected replay acceptance', 'error');
    } catch (problem) {
      log(`Replay rejected · ${problem.message}`, 'success');
    }
  });

  log('Sandbox initialized · no server or executor connected');
  void renderPreview();
  window.addEventListener('load', postHeight);
  new ResizeObserver(postHeight).observe(document.body);
}

if (typeof document !== 'undefined') initDemo();
