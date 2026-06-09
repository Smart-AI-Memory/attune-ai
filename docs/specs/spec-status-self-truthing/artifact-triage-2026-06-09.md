# Artifact cross-reference triage — 2026-06-09

A one-shot run of the **artifact-presence cross-check** that
`spec-status-self-truthing`'s reconciler is blind to: for each
non-terminal spec, extract the artifacts it names (file paths, code
symbols, CLI subcommands) and grep the codebase. High artifact-presence
+ a non-terminal status header ⇒ the work likely shipped but the status
was never flipped (the "specs ship without status update" trap).

This file records the run and motivates the durable check (Phase 2 of
this spec — fold artifact-presence into the reconciler as a third
signal).

## Method

`scripts/audit_spec_status.py` (Phase 2 deliverable) — file paths are the
strongest signal (a NEW file named by the spec existing in the tree ⇒
shipped); symbols/CLI subcommands are corroborating. **Caveat learned
this run:** a naive status-line parser over-flagged 3 already-`complete`
specs (`spec-status-self-truthing`, `pattern-review-queue`,
`dashboard-pending-writes-journal`) because it missed the `**Status**:`
colon variant. The durable check MUST reuse the reconciler's robust
status parsing (`plugin/hooks/_state.py` `SpecInfo` /
`_TERMINAL_VERDICTS`), not reinvent it.

## Findings (13 non-terminal specs with artifacts present)

### Flipped this session (direct evidence)

- **collaboration-gates** — `approved` → `complete`. Spend gate (R1–R8)
  shipped #637/#638/#639; referent gate (R9/R10) shipped #694.
- **workflow-path-arg-unification** — `draft` → `complete`. All 5 target
  workflows accept `path`; `PathArgSpec` present, registry test green;
  doc-orchestrator closed #685.
- **test-quality-program** — `approved` → `living`. Ongoing program, not a
  one-shot spec; relabelled so the in-flight list stops treating it as
  unexecuted.

### Judgment calls — verify before flipping (not flipped here)

Many of these have **no `requirements.md`/Status line** — they are QA
docs / living roadmaps / decisions-only dirs, not uniform feature specs,
so "flip the status" is not mechanical:

- **ops-mutating-endpoint-auth** — `require_client_token` is in
  production (R6 uses it); decisions.md/tasks.md only, no Status header.
  Almost certainly shipped — add a terminal marker.
- **workflow-result-formatting** — `output.py` + 8 section classes
  present; proposal/design/tasks, no requirements. Likely shipped.
- **ops-session-discovery-cli** — `list_sessions`/sessions route present;
  decisions.md only.
- **ops-dashboard-polish** — `run_view_page`/`derive_project_name`
  present; decisions/tasks only.
- **ops-dashboard-qa-2026-05-14** — `punch-list.md` only (a QA punch
  list, not a feature spec).
- **spec-backlog-triage-2026-06-04** — `matrix.md` only (a triage doc).
- **release-train** — `roadmap.md` only (a living roadmap → `living`).
- **docs-completeness-audit** / **docs-release-prep** — `approved`; each
  names only ONE pre-existing file (`meta_orchestrator.py`,
  `publish-pypi.yml`) — weak signal, verify the actual feature shipped.
- **sibling-package-pre-commit** — `approved`; `format_on_save.py`
  present. Verify.

### Genuinely open (real backlog — no/missing artifacts)

`just-in-time-recall`, `website-update-dashboard-and-fold`,
`doc-stack-reference-subtypes`, `enforcement-vs-documentation`,
`integration-coverage`, `pipeline-learner`.

## Durable fix (Phase 2 — next PR)

Add an artifact-presence signal to the reconciler so this surfaces every
session instead of needing a manual sweep:

1. Optional `primary-artifact:` field in spec headers (a path or symbol).
2. `SpecInfo` gains `artifact_present` + an `artifact_shipped_conflict`
   flag (artifact resolves in repo AND `effective_status` non-terminal).
3. The session-start in-flight lister annotates flagged specs
   ("⚠ artifact present — may be shipped, verify status"). **Advisory,
   not a hard gate** (the heuristic is too noisy to fail CI on, per the
   over-flag caveat above) — matches the advisory-vs-enforceable rule.
4. `scripts/audit_spec_status.py` for the full on-demand matrix.
