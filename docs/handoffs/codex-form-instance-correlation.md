# Form/workspace instance correlation and browser latency

## Goal and acceptance criteria

Pair overlapping displays correctly. Count workspace acceptance only after
canonical successor storage. Compare identical baseline and batched scenarios
in an observable host, separating paint, dwell, and accepted acknowledgment.

## Original implementation scope

- attune-ai branch: `codex/form-instance-correlation`, base `1aab6bebe`.
- attune-forms isolated clone: `/private/tmp/attune-forms-instance-correlation`,
  branch `codex/form-instance-correlation`, base `cc94fc2`.
- Codex advisory to Patrick. User approved implementation, workspace acceptance
  instrumentation, final verification and loading an isolated observable host.
- XML task: unique render tokens travel through ordinary form envelopes and
  workspace action envelopes; exact joins use form identity or workspace/revision.
  Test invalid inputs, overlaps, replay, canonical failures and real stdio.
  Then compare seven single rulings with 3+3+1 batches over identical fixtures.

## Current state

Implementation and measurements are complete in both repos. Git history and
the paired PRs record the publishing state.

- Form response envelopes carry a unique display token through MCP Apps and both
  collectors. Legacy events retain counts but do not invent wait samples.
- Workspace tokens are optional validated metadata, outside nonce/HMAC authority.
  The host emits acceptance after storing the canonical successor. Rejections,
  adapter failures and replay attempts do not produce acceptance events.
- Older installed forms wheels retain functional rendering/collection and report
  missing workspace timing explicitly.
- Final reviewed wheels were built and byte-checked against source, installed
  with no dependency resolution into `/private/tmp/latency-host-site`, and run
  through public MCP stdio and an isolated visible in-app browser host.
- The original browser measurement used an isolated install. The later release
  and machine update are recorded below; those original receipts are unchanged.

## Verification receipts

- 994 attune-forms tests and 129 focused attune-ai tests passed.
- Changed executable Python coverage: forms 57/57, ai 19/19. Shipped JavaScript
  has a separate Node transport receipt; both servers have real stdio receipts.
- Pinned Ruff 0.8.4 and Black from the cached 24.10.0 pre-commit checkout pass.
- Different-model review: gpt-5.6-sol closed the first two receipt gaps, then
  reviewed workspace acceptance, backward compatibility and the browser probe
  with no blockers.
- Four visible-browser runs in ABBA order completed with identical terminal
  Markdown. Baseline requires seven accepted submissions; batched requires three.
  The actual server logged 20 accepted actions and 20 exact instance joins.
- Raw observations, wheel hashes, definitions, limitations and reproduction:
  `docs/probes/latency/README.md`, `browser-receipts.json`,
  `workspace-events.jsonl`, and `wheel-manifest.json`.
- Native Codex UI observation remains blocked. The earlier installed-wheel
  receipt `resp-20260904-220004-85d8004d` is successful behavior evidence only.
  The completed measurements describe the isolated browser + real stdio path,
  not native Codex or Claude latency. Human completion speed remains unmeasured.

## CI fix by the Claude lead session (2026-09-04 late, chair: "fix 2421")

- `wiring-audit` failed: `docs/probes/latency/README.md` builds but is
  nav-unreachable. Fixed by allowlisting `docs/probes/` in
  `.audit/orphans.yml` with a reason (repo-only evidence, not site content);
  `scripts/audit_docs_wiring.py --format json` returns no findings locally.
- `changelog-entry` failed: shipped `src/` paths without a CHANGELOG line.
  Added an `[Unreleased]` "Added" entry describing the user-visible receipt
  behaviour and the older-wheel fallback.
- NOT fixed here, and not fixable in this repo: the new tests import
  `attune_forms.form_events.workspace_latency`, which public attune-forms
  0.12.2 does not provide; that wheel has `stage_latency` but no display-instance
  token in its widget output. Those failures were captured before release prep.
  Forms #76 and #77 subsequently merged and 0.12.3 is now published. The
  integration owner has raised the dependency floor and updated `uv.lock`.
- Written from a detached scratch worktree and pushed by refspec; the Codex
  worktree at `~/.codex/worktrees/c655/attune-ai` was not touched — pull
  before committing again there.

## Next action

Patrick authorized releasing the merged forms fix and unblocking AI integration
on 2026-09-04. Forms #76 and release-prep #77 are merged. The release target is
`961e39c756fc069a3cbe8a8fe3e330ea8ee389e6`, whose post-merge CI passed.
AI prerequisite #2422 merged as `f51a2dd6491b5517346a07aec9978eef559fb7dd`
with all checks green, including Windows. Its merged tree matches the tested
`7d9303b096ba9f0e2ffe26083c8d529ab4f6335b` tree exactly.
Forms tag `v0.12.3` points at the verified release target. Patrick manually
approved the `pypi` gate; build and publication in
https://github.com/Smart-AI-Memory/attune-forms/actions/runs/33941150280 passed.
Both public artifacts were downloaded and match the CI artifact hashes exactly.
Four public-wheel stdio and acceptance-boundary tests passed.
The existing Claude Fable 5.1 session owns AI #2421 integration. Its head
`3a341741c7b1903461100373abbac78339276d0f` incorporates main and raises the forms
floor and lock to 0.12.3. Codex verified the artifact hashes and reviewed the
three-file integration commit; the independent review found no blocker.
Completed applicable CI jobs were green, with required jobs still running at
review time. Recheck the current head and all required checks before merging.
Codex owns the release/machine receipts; do not duplicate either lane.
The Claude lead's AI gate fixes were preserved by fast-forwarding this worktree
to `9560c9cb56a067189037c4942ef43d53d4e4ee49` before further edits.
This worktree remains at that source commit with local receipt updates; it has
not incorporated Fable's newer integration head. Use current remote state for
integration, and do not push this older branch tip over the lead's work.

```xml
<task id="latency-release-integration">
  <objective>Publish the reviewed forms patch and validate AI against its public wheel.</objective>
  <steps>
    <step>Land the alias-test correction on AI main so its open dependency range safely admits forms 0.12.3.</step>
    <step>Pass forms release CI, merge, verify the full merge SHA, tag, and verify PyPI artifacts.</step>
    <step>Raise the AI forms dependency floor and lock to the published version.</step>
    <step>Run public-wheel integration receipts and required CI before completing AI PR #2421.</step>
  </steps>
  <acceptance>Public forms wheel contains correlation and workspace events; AI CI passes with that wheel.</acceptance>
  <constraint>Retain the browser receipts and their limits. Native-host timing remains unmeasured.</constraint>
</task>
```

Release-prep receipts: forms 994 tests, complete pinned pre-commit, wheel and
sdist build, and all 19 packaged Python/data files matched the reviewed source.
The independent review found an AI main test expecting an unkeyed latency
join; the prerequisite correction retains `joined == 1` and supplies a shared
token only when both installed logger signatures support it. A second widget
test now normalizes only the new per-display token before exact HTML equality.
The 45 changed-area tests passed with published 0.12.2; all 1,988 downstream
forms/workspace consumer-subset tests passed against the installed candidate
0.12.3 wheel (36 skipped). All three projected forms test files are in sync.

The broader downstream unit run recorded 21,789 passed, 1 failed, 119 skipped,
and 4 xfailed. Its sole failure was the old fixed-DOM HTML equality assertion,
loaded before its correction. The corrected failed-case rerun recorded
1 passed, 1 skipped, and 21,911 deselected. This is a failed run followed by a
successful repair receipt, not a claim that the initial full run was green.
The built candidate artifacts and public artifacts are recorded separately in
`docs/probes/latency/release-machine-receipts.json`. All 19 packaged Python/data
files in the CI wheel equal release source. The public wheel and sdist equal
the CI artifacts byte for byte. AI #2421 is now ready for review; its owner is
waiting for the remaining required CI checks before integration.

## Machine update and coordination (2026-09-05 UTC)

Patrick requested the new version on his machine and all surfaces, then asked
whether Fable should lead and Codex coordinate. The recommended split retains
Fable as integration lead and Codex as release/runtime verifier. Codex cannot
address the external Fable conversation directly through the available task
tools; the shared handoff and PR receipt are the coordination surfaces.

- Updated Claude Forms plugin from 0.10.0 to 0.12.3, Claude AI plugin from
  16.1.0 to the published 16.2.1, and Codex's standalone Forms MCP pin from
  0.11.0 to 0.12.3. Codex AI plugin was already 16.2.1.
- Installed the verified public Forms wheel into global pyenv Python, main AI
  venv, IndianRailroadTicketing venv and Metalens venv. All four import probes
  report 0.12.3. Refreshed both Forms and AI uvx launch families.
- Six fresh MCP stdio launch paths render distinct per-display tokens and
  successfully collect two synthetic responses each. Both Forms launch paths
  record two exact joins. Published AI paths expose no collector instance
  parameter and record zero joins: #2421 is still needed for that integration.
- The initial main-venv probe used the home directory and returned `Connection
  closed`; retained stderr identifies an AI import failure. Its rerun from the
  actual project directory passed. Both results and that stderr are retained.
- Existing Claude/Codex processes were not interrupted; reload those sessions
  to activate updated plugins and MCP launch configuration. These fresh stdio
  probes do not prove that already-running host sessions reloaded.
- The main AI checkout has untracked work and an older Forms lock. Its `uv run`
  launcher can resync to 0.12.2 until #2421 merges and that checkout is safely
  updated. Other agents' worktrees, the Forms editable development checkout,
  historical cache archives and original measurement site were preserved.
- No extra Attune MCP launchers were found in the inspected standard Claude
  Desktop, VS Code, Cursor, Windsurf or JetBrains configurations.

The next integration receipt is the same baseline/batched scenario after the
AI change is available in the actual host, measuring time until visible and
time until accepted separately. Roundtable action counts remain counts until
canonical acceptance timestamps are observed. No renderer optimization or
native-host speedup claim is justified by these installation probes.
