# Agent work handoff

## Goal

Complete Tasks 1–7 of `shared-command-workspaces`: characterize Fix,
implement the shared host runtime, migrate Fix behind compatibility wrappers,
ship the Roundtable adapter with live progress and paginated rulings, and ship
the resumable Spec adapter with exact lifecycle/task receipts, followed by the
ten cohort adapters in the chair-selected order.

## Acceptance criteria

- Existing Fix tests stay green before and after characterization.
- Canonical rebuild, altered binding, concurrent confirmation, terminal
  mutation, and widget/Markdown/headless fallback parity are explicit tests.
- Minimal Fix, nested Roundtable, and iterative Spec adapters prove that view
  phase names do not determine actions or transitions.
- The shared host owns canonical envelopes and at-most-once transitions.
- Existing Fix tool names and security behavior remain compatible.
- Changed production code reaches the initiative's 90% coverage bar.
- Roundtable preserves compiler, board, roster, invocation, round, and
  per-item promotion authority while seven candidates remain usable.
- A non-mocked Redis-thread replay reaches a terminal shared-renderer receipt.
- Release prep fails closed on missing/error gatekeepers and preserves four
  repeated gate approvals plus final confirmation.
- Bug prediction starts read-only without a synthetic confirmation and emits
  a truthful success or failure terminal receipt.
- Cohort examples 3–10 are selected from measured semantic gaps, not ease of
  implementation, with failure-sensitive receipts and rollback boundaries.
- Each of examples 3–10 independently clears its execution gate, verification
  gate, fallback/live-terminal receipt, and 90% changed-code coverage bar.
- The adapter interface is declared stable only after receipt 10.

## Scope and assumptions

- Branch/worktree: `codex/shared-command-workspaces-t1` at
  `/private/tmp/attune-shared-command-workspaces-t1-20260831`
- Provider/session: Codex, 2026-08-31
- Assumptions: Tasks 1 and 2 were separately chair-gated. At the Task 2 gate,
  the chair selected `Auto-run remaining tasks`, authorizing Tasks 3–7 while
  retaining their mechanical execution and verification gates.

## Current state

- Status: complete. Tasks 1–7, all eight separately gated Task 7 slices, and
  the final whole-cohort lifecycle verification gate pass. Embedded spec state
  records Tasks 1–7 complete with no current task.
- Changed files:
  - `docs/specs/shared-command-workspaces/{requirements,design,tasks,decisions}.md`
  - `docs/specs/shared-command-workspaces/cohort.md`
  - `docs/specs/cross-review/receipts.md`
  - `src/attune/elicitation/command_workspace.py`
  - `src/attune/elicitation/fix_workspace.py`
  - `src/attune/mcp/server.py`
  - `src/attune/mcp/tool_schemas.py`
  - `src/attune/roundtable/{__init__,workspace}.py`
  - `src/attune/spec/{__init__,workspace}.py`
  - `src/attune/workspaces/{__init__,release_prep,bug_predict}.py`
  - `src/attune/workspaces/bulk.py`
  - `src/attune/workspaces/memory_context.py`
  - `src/attune/workspaces/smart_test.py`
  - `src/attune/workspaces/doc_gen.py`
  - `src/attune/workspaces/workflow_orchestration.py`
  - `src/attune/workspaces/image_analysis.py`
  - `src/attune/workspaces/verify.py`
  - `src/attune/workspaces/security_audit.py`
  - `plugin/skills/roundtable/SKILL.md`
  - `.claude/skills/roundtable/SKILL.md`
  - `.agents/skills/roundtable/SKILL.md`
  - `plugin/skills/spec/SKILL.md`
  - `.claude/skills/spec/SKILL.md`
  - `.agents/skills/spec/SKILL.md`
  - `plugin/skills/{release-prep,bug-predict}/SKILL.md`
  - `.agents/skills/{release-prep,bug-predict}/SKILL.md`
  - `plugin/skills/bulk/SKILL.md`
  - `.agents/skills/bulk/SKILL.md`
  - `plugin/skills/memory-and-context/SKILL.md`
  - `.agents/skills/memory-and-context/SKILL.md`
  - `plugin/skills/smart-test/SKILL.md`
  - `.agents/skills/smart-test/SKILL.md`
  - `plugin/skills/doc-gen/SKILL.md`
  - `.agents/skills/doc-gen/SKILL.md`
  - `plugin/skills/workflow-orchestration/SKILL.md`
  - `.agents/skills/workflow-orchestration/SKILL.md`
  - `plugin/skills/image-analysis/SKILL.md`
  - `.agents/skills/image-analysis/SKILL.md`
  - `plugin/skills/verify/SKILL.md`
  - `.agents/skills/verify/SKILL.md`
  - `plugin/skills/security-audit/SKILL.md`
  - `.agents/skills/security-audit/SKILL.md`
  - `tests/unit/elicitation/test_command_workspace.py`
  - `tests/unit/elicitation/test_fix_workspace.py`
  - `tests/unit/elicitation/test_command_workspace_contract.py`
  - `tests/unit/mcp/test_tool_schemas.py`
  - `tests/unit/roundtable/test_workspace.py`
  - `tests/unit/spec/test_workspace.py`
  - `tests/unit/workspaces/{test_release_prep,test_bug_predict}.py`
  - `tests/unit/workspaces/test_bulk.py`
  - `tests/unit/workspaces/test_memory_context.py`
  - `tests/unit/workspaces/test_smart_test.py`
  - `tests/unit/workspaces/test_doc_gen.py`
  - `tests/unit/workspaces/test_workflow_orchestration.py`
  - `tests/unit/workspaces/test_image_analysis.py`
  - `tests/unit/workspaces/test_verify.py`
  - `tests/unit/workspaces/test_security_audit.py`
  - `tests/unit/workspaces/test_cohort.py`
  - `tests/unit/test_mcp_memory_tools.py`
  - `README.md`
  - `plugin/README.md`
  - `docs/getting-started/{mcp-integration,quickstart-plugin}.md`
  - `plugin/help/generated/references/skill-*.md`
  - `plugin/help/generated/tasks/use-*.md`
  - `website/lib/features.ts`
  - `docs/handoffs/codex-shared-command-workspaces-t1.md`
- Decisions: the test-proven minimum adapter seam is `create`, `project`, and
  `apply`. Legal actions and confirmation live in `WorkspaceView`; terminal
  state lives in the transition. The host serializes each workspace with an
  async lock, checks adapter version, copies state before adapter mutation,
  and stores the successor before returning.
- Roundtable required one optional `publish` capability. Progress-only events
  may update presentation but cannot change action/form authority; they advance
  `event_sequence`, which is preserved across chair actions. Round completion
  and synthesis advance canonical revision. Seven candidates are rendered one
  per page.
- Spec needed no further core change. Its renderer state is process-local;
  durable resume remains the embedded `SpecState` comment. Exact artifact,
  lifecycle, probe, and task receipts enter through publisher events; accepted
  task decisions return explicit `save_state` data.
- Release prep and bug prediction also needed no shared-core change. The first
  owns four fail-closed gate receipts and repeated approvals; the second owns
  a no-action read-only run and truthful terminal publication.
- Risks or open questions: storage is currently process-local, matching the
  prior Fix server. Durable reconnect/progress storage remains later spec
  work.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Existing Fix baseline was green | `PYTHONPATH=src ... pytest tests/unit/elicitation/test_fix_workspace.py -q` before edits | 31 passed |
| Task 1 behavior is pinned | `PYTHONPATH=src ... pytest tests/unit/elicitation/test_fix_workspace.py tests/unit/elicitation/test_command_workspace_contract.py -q` | 44 passed, 1 strict xfail for the named Task 2 module |
| Formatting is clean | `python -m black --check --fast` on both test files | pass |
| Lint is clean | `ruff check` on both test files | pass |
| No production host was added | `test ! -e src/attune/elicitation/command_workspace.py` | pass |
| Patch is whitespace-clean | `git diff --check` | pass |
| Lifecycle execution gate permits Task 1 | `attune gates check execution --spec shared-command-workspaces --changed ...` | pass |
| Lifecycle verification gate accepts Task 1 | `attune gates check verification --spec shared-command-workspaces --changed ...` | pass |
| Task 2 focused behavior | `pytest test_command_workspace.py test_command_workspace_contract.py test_fix_workspace.py test_tool_schemas.py -q -n 0` | 105 passed |
| Shared host branch coverage | `coverage run --branch ...` + module report | 100% |
| Full Fix workspace branch coverage | same coverage receipt | 96.19% |
| Changed production line+branch coverage | diff lines intersected with coverage JSON | 373/379 = 98.42% |
| Full elicitation + MCP surface | `pytest tests/unit/elicitation tests/unit/mcp -q` | 964 passed; 2 unrelated theme-drift failures; 4 sandbox-only memory failures |
| Sandbox-only memory rerun | four failing memory nodes, escalated | 4 passed |
| Pinned formatter | `pre-commit run black --files ...` | pass |
| Task 2 lifecycle verification | `attune gates check verification --spec shared-command-workspaces --changed ...` | pass |
| Roundtable + core focused behavior | `pytest -n 0 tests/unit/roundtable/test_workspace.py tests/unit/elicitation/test_command_workspace.py -q` | 42 passed |
| Shared-core + Roundtable branch coverage | `coverage run --branch ...` + `coverage combine/report` | 97.82% combined; Roundtable 98.92%, core 96.35% |
| Roundtable projection drift | `python scripts/sync_agents_skills.py --write` then `--check` + drift tests | generated; 120 passed, 11 skipped in the combined projection/board surface |
| Broad Roundtable + elicitation + MCP surface | `pytest tests/unit/roundtable tests/unit/elicitation tests/unit/mcp -q` | 1312 passed, 35 skipped; 2 verified unrelated theme-drift failures; 4 sandbox-only memory failures |
| Sandbox-only memory rerun | exact four failing memory nodes, escalated | 4 passed |
| Non-mocked Roundtable receipt | real Redis thread `shared-renderer-command-workspaces-001` replayed through `CommandWorkspaceHost` | 9 seat receipts, synthesis 13, seven ruling pages for ids 14–18/20/21, stale nested action rejected, terminal receipt, event sequence 13 |
| Task 3 lifecycle execution | `attune gates check execution --spec shared-command-workspaces --changed ...` | pass |
| Task 3 lifecycle verification | `attune gates check verification --spec shared-command-workspaces --changed ...` | pass |
| Spec focused behavior + intake | `pytest -n 0 tests/unit/spec/test_workspace.py tests/unit/elicitation/test_spec_intake.py -q` | 41 passed |
| Spec adapter branch coverage | `coverage run --branch ...` + `coverage combine/report` | 98.85%; adapter + existing intake 97.51% combined |
| Spec projection + state surface | projection drift plus Spec workspace/intake/state tests | 107 passed |
| Broad Spec/core/schema surface | `pytest tests/unit/spec test_spec_intake.py test_command_workspace.py test_tool_schemas.py -q` | 164 passed |
| Non-mocked Spec creation receipt | actual `shared-command-workspaces` artifacts parsed and replayed through `CommandWorkspaceHost` | 7 real XML task ids; exact requirements/design/tasks/decisions paths and two executed probes rendered in widget + Markdown at review |
| Task 4 lifecycle execution | `attune gates check execution --spec shared-command-workspaces --changed ...` | pass |
| Task 4 lifecycle verification | `attune gates check verification --spec shared-command-workspaces --changed ...` | pass |
| Task 5 lifecycle execution | `attune gates check execution --spec shared-command-workspaces --changed ...` | pass |
| Task 5 focused adapters/projections | projection drift check plus release-prep, bug-predict, workflow, and release orchestration tests | 102 passed in sandbox; 2 loopback-only nodes rerun with permission and passed |
| Task 5 changed-production branch coverage | `coverage run --branch` + combined module report | release-prep 97.56%, bug-predict 99.08% |
| Task 5 style | `ruff check` and `black --check` on adapters, server, and tests | pass |
| Release-prep live host receipt | actual probes published through `CommandWorkspaceHost`, four bound gate accepts, final confirmed approval | terminal revision 7/event 5; widget and Markdown receipt; all four gate receipts named |
| Bug-predict live host receipt | validated real repository path opened and completed through `CommandWorkspaceHost` with no model spend | zero initial actions; terminal revision 1/event 2; widget and Markdown receipt; producer explicitly identified as renderer replay |
| Task 5 lifecycle verification | `attune gates check verification --spec shared-command-workspaces --changed ...` | symbol-reality PASS; falsifiability PASS |
| Task 6 lifecycle execution | `attune gates check execution --spec shared-command-workspaces --changed ...` | symbol-reality PASS; falsifiability PASS |
| Task 6 lifecycle verification | same gate at `verification` for cohort/decision/handoff artifacts | symbol-reality PASS; falsifiability PASS |
| `/bulk` slice execution gate | Task 7 slice files at `execution` | symbol-reality PASS; falsifiability PASS |
| `/bulk` focused surface | bulk/core/schema/projection tests | 121 passed |
| `/bulk` branch coverage | `coverage run --branch` + combine/report | 99.22% |
| `/bulk` live terminal | confirmed submit plus read-only reconnect through real `CommandWorkspaceHost` | 2/2 accepted terminal; pending reconnect terminal does not claim completed; deterministic provider fixture, no paid API call |
| `/bulk` slice verification gate | Task 7 slice files at `verification` | symbol-reality PASS; falsifiability PASS |
| Memory registration/core/projection surface | memory-context, bulk, core, memory MCP, projection tests | 122 passed; stale exact tool-count ratchet updated for the three Task 2 generic workspace tools |
| `/memory-and-context` branch coverage | `coverage run --branch` + combine/report | 90.51% |
| `/memory-and-context` live terminal | real host with an ephemeral live dictionary backend | same classified value stored/retrieved by digest, value not rendered; confirmed forget followed by miss; no durable user memory changed |
| `/memory-and-context` slice verification gate | Task 7 slice files at `verification` | symbol-reality PASS; falsifiability PASS |
| `/smart-test` focused surface | smart-test, memory, core, schema, and projection tests | 128 passed |
| `/smart-test` branch coverage | `coverage run --branch` + combine/report | 92.96% |
| `/smart-test` live terminal | real host, real disk hash, exact pytest receipt | existing test file used as a non-mutating write-boundary fixture; SHA-256 recorded; 14-test probe exited 0 |
| `/smart-test` slice verification gate | Task 7 slice files at `verification` | symbol-reality PASS; falsifiability PASS |
| `/doc-gen` focused surface | doc-gen, smart-test, core, schema, and projection tests | 124 passed |
| `/doc-gen` branch coverage | `coverage run --branch` + combine/report | 90.28% |
| `/doc-gen` live terminal | real host, real disk hash, executed heading-reality probe | existing changed cohort doc used as a non-mutating artifact fixture; SHA-256 recorded; probe found exact heading |
| `/doc-gen` slice verification gate | Task 7 slice files at `verification` | symbol-reality PASS; falsifiability PASS |
| `/workflow-orchestration` focused surface | orchestration, doc-gen, core, schema, and projection tests | 124 passed |
| `/workflow-orchestration` branch coverage | `coverage run --branch` + combine/report | 98.01% |
| `/workflow-orchestration` live terminal | real host with three exact already-executed local probes | out-of-order progress rendered security/tests/docs order; all PASS; event sequence 4; no paid child workflows invoked |
| `/workflow-orchestration` slice verification gate | Task 7 slice files at `verification` | symbol-reality PASS; falsifiability PASS |
| `/image-analysis` focused surface | image, orchestration, core, real-handler early paths, schema, and projection tests | 139 passed |
| `/image-analysis` branch coverage | `coverage run --branch` + combine/report | 98.42% |
| `/image-analysis` live terminal | real MCP server + real `attune-ai-dev/og.png` decoder + actual no-key provider call | 1200×630 PNG, 35,420 bytes, SHA-256 recorded; provider returned `ANTHROPIC_API_KEY not set`; terminal truthfully failed with no spend |
| Image boundary discovery | `file` plus adapter open on `docs/assets/images/empathy-brain-logo.png` | asset is JPEG bytes with `.png` suffix; rejected before provider; asset not changed |
| `/image-analysis` slice verification gate | Task 7 slice files at `verification` | symbol-reality PASS; falsifiability PASS |
| `/verify` focused surface | verify, image, core, schema, and projection tests | 130 passed |
| `/verify` branch coverage | `coverage run --branch` + combine/report after exact-shape correction | 93.18% |
| `/verify` live terminal | real `attune_verify.verify` over `cohort.md`, then real shared host | categories imports/flags/links/counts; no findings; explicit empty ambient cross-check; hard gate passed |
| Verify boundary discovery | first real result inspected before replay | `checked` is `list[str]`, not count; adapter corrected and regression-covered before gate |
| `/verify` slice verification gate | Task 7 slice files at `verification` | symbol-reality PASS; falsifiability PASS |
| `/security-audit` focused surface | security-audit, verify, core, schema, projection, and all workspace tests | 131 passed focused; 268 passed combined cohort subset |
| `/security-audit` branch coverage | `coverage run --branch` + combine/report | 96.15% |
| `/security-audit` live terminal | actual MCP audit with API key removed, then real shared host | SDK/CLI returned `Not logged in`; terminal truthfully reported incomplete scan, with no score, clean claim, or spend |
| `/security-audit` slice verification gate | Task 7 slice files at `verification` | symbol-reality PASS; falsifiability PASS |
| Whole workspace suite | all workspace adapters | 162 passed |
| Whole shared-host/cohort surface | workspace, elicitation, Roundtable, Spec, MCP, and projections | 1,636 passed; four real-backend memory tests were sandbox-blocked and then passed with required permission; two unrelated form-theme/projection failures remain outside this branch |
| Whole cohort branch coverage | all ten `src/attune/workspaces` adapters plus package exports | 95.34%; every adapter individually at least 90% |
| Final style and projections | Black, Ruff, skill projection drift, and `git diff --check` | 37 Python files unchanged; all checks pass; 38 projection tests pass |
| Final Task 7 lifecycle verification | full shared host, ten adapters, registration, spec artifacts, handoff, and cohort order test | symbol-reality PASS (`8affb219609f`); falsifiability PASS (`623a7b84549a`) |
| Required different-model review | Antigravity over the complete staged diff, re-laning every omitted path and re-reviewing remediations | 31 real board-posted runs; union covers the original 69 files plus the final projector/test closure; 51 real findings accepted/fixed or accepted-modified; 10 rejected with verbatim claims/reasons in the R5 ledger; final design, skill, reference, and task-projector packs clean |
| Production MCP `/roundtable` acceptance | actual `AttuneMCPServer` open/publish/collect flow, rendered as HTML and Markdown | seven one-candidate ruling pages; stale replay rejected; terminal receipt at revision 11/event sequence 2; 6,642 HTML chars and 246 Markdown chars |
| Production MCP `/spec` acceptance | actual `AttuneMCPServer` create/tasks/redo/approve/execution/resume flow, rendered as HTML and Markdown | redo, approval, execution gate, and incomplete-plan resume all passed; executing state at revision 9/event sequence 5; 6,492 HTML chars and 179 Markdown chars |
| Public capability projection | `project_capabilities.py --check`, reference/task template projectors, and claim/help drift tests | advertised counts now match 64 total MCP tools and 53 core tools; all projectors clean; 19 focused drift tests passed |
| Complexity ratchet remediation | Radon plus complexity and six affected adapter suites after splitting event parsing and media decoding | no new D-or-worse blocks; 121 passed after pinned Black formatting |
| Complete unit suite | `python -m pytest -n0 tests/unit -q` with localhost and real-backend fixture permissions | 21,629 passed, 109 skipped, 16 deselected, 3 expected failures in 8m53s |
| Review-finding remediation | preserve Markdown paragraphs, bind prose to its own fence, distinguish runnable/output/guidance steps, match backtick/tilde delimiters by type and length, indent multiline detail in the canonical Jinja template, and regenerate all 26 task pages | all 16 remediation findings fixed at the source; 79 focused generator/help tests passed; generator `--check` clean; final 20-file Antigravity re-lane returned `NO FINDINGS` with no omissions |
| Repository-wide pre-commit | `pre-commit run --all-files` after remediation | all blocking hooks passed; two pre-existing unresolved-doc-link warnings remain warn-only and outside this branch |

## Next action

After this handoff and its R5 receipt are committed and pushed, review the one
feature PR and merge only on the chair's explicit action; this governance/spec
diff is intentionally not eligible for lead-armed auto-merge.
