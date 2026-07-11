# Spec: Spec-Status Integrity Hooks (attune-ai)

> Companion spec to the attune workspace spec
> [`specs/spec-status-integrity/`](https://github.com/Smart-AI-Memory/attune)
> (requirements + design + tasks all approved 2026-07-10). The workspace
> spec owns the full feature — problem analysis, cross-repo design, and
> the 9-task execution plan. This spec covers the attune-ai plugin slice
> (workspace tasks 1–6): the canonical hook changes and the reusable
> reminder workflow. Same companion pattern as fable-model-tiers ↔
> fable-premium-tier.

---

## Phase 1: Requirements

**Status**: approved (2026-07-10 — by reference: workspace spec
`specs/spec-status-integrity/requirements.md` approved by Patrick
2026-07-10; this companion restates the plugin-scoped subset)

### Problem statement

Spec status lines across the five attune repos drift from reality —
specs sit at `draft`/`approved` long after their implementing PRs merge
(the 2026-06-17 audit found the orientation hook advertising already-
shipped work). The attune-ai plugin owns the canonical spec tooling
(`plugin/hooks/_state.py`, `spec_audit.py`, `spec_orient.py`, vendored
into the four layer repos via `make sync-hooks`), so the drift-detection
machinery lands here: a PR-link signal (primary), a status-vocabulary
lint, a drift cache consumed offline at session start, and a reusable
PR-merge reminder workflow.

### Scope

**In scope (workspace tasks 1–6, all in this repo):**

- `plugin/hooks/_state.py` — `PrRef` + `extract_pr_refs()` (four
  citation styles), `lint_status_token()`, terminal-verdict additions
  (`implemented`, bare `✓`/`✅`), `parked`-semantics set (`parked`,
  `paused`, `blocked`, `deferred` — skipped by drift checks).
- `plugin/hooks/spec_audit.py` — `--pr-links` mode (gh-backed,
  merged-PRs-only, bounded + cached calls), `--offline` degradation,
  `--json` output, `.attune/spec-drift.json` cache write.
- `plugin/hooks/spec_orient.py` — drift-cache read (< 8 days fresh),
  `⚠ drifted: <repo> #<n> merged` annotation, `ATTUNE_SPEC_AUDIT=off`
  kill switch. The hook stays offline (no-network invariant).
- `.github/workflows/spec-status-reminder.yml` — reusable
  (`workflow_call` + own `pull_request: [closed]`): comments on merged
  PRs that reference still-in-flight specs, with a self-reference
  carve-out and a never-comment-twice guard.

**Out of scope (workspace tasks 7–9, other repos):**

- Sibling re-sync (`make sync-hooks` in attune-rag/gui/help/author) and
  their thin caller workflows.
- Umbrella `Makefile`, weekly `spec-audit.yml` CI, baseline validation
  sweep, and any hand-flipping of drifted statuses.
- Mass rewrite of historical status tokens (~127 `complete` variants) —
  aliases stay accepted; only new specs are linted toward the canonical 8.

### User stories

1. As a session starting in any attune repo, I want in-flight spec lines
   annotated `⚠ drifted` when a merged PR already implemented them, so I
   don't plan work that's already shipped.
2. As a maintainer running `spec_audit.py --pr-links`, I want merged-PR
   evidence (not just deliverable existence) driving the drift verdict,
   with `--json` output CI can upsert into a tracking issue.
3. As a PR author merging work that references a spec, I want one
   reminder comment when the spec's status is still in-flight — and no
   nag when my PR itself updates the spec.
4. As an offline or gh-less user, I want the audit to degrade to the
   existing deliverable-existence signal and the session hook to never
   make network calls.

### Affected components

- [ ] Skills (`plugin/skills/`) — none
- [ ] Agents (`plugin/agents/`) — none
- [x] Hooks (`plugin/hooks/_state.py`, `spec_audit.py`, `spec_orient.py`)
- [x] CI workflows (`.github/workflows/spec-status-reminder.yml`, reusable)
- [x] PyPI package (`pyproject.toml`) — ships as a plugin release before
  the sibling re-sync (workspace task 7) can run
- [ ] Personal command (`~/.claude/commands/`) — N/A

Cross-repo dependency: the four layer repos vendor these hooks
byte-for-byte (drift-guard tests); the umbrella weekly CI invokes
`spec_audit.py` from this package. Contract changes here propagate via
`make sync-hooks` under the workspace spec's tasks 7–8.

### Invocation & triggers

| Component | Trigger |
|-----------|---------|
| `spec_orient.py` | Existing SessionStart hook — gains the `⚠ drifted` suffix, no new invocation |
| `spec_audit.py` | `make spec-audit` / direct CLI; new flags `--pr-links`, `--offline`, `--json` |
| Reminder workflow | `pull_request: [closed]` (merged only) in this repo; `workflow_call` from sibling/umbrella callers |
| Kill switch | `ATTUNE_SPEC_AUDIT=off` env var suppresses session-start annotations |

### Tool scope

N/A — no new skill/agent. `spec_audit.py` shells out to `gh` (subprocess,
patched at that boundary in tests); `spec_orient.py` gains file reads
only. The reminder workflow needs `pull-requests: write` +
`contents: read`, nothing more.

### Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | Above; full analysis in workspace requirements.md |
| **Skill/agent contracts** | addressed | No SKILL.md changes; hook CLI gains flags, exit contract unchanged (warn + exit 0, `--strict` exits 1) |
| **User interaction** | addressed | One-line `⚠ drifted` suffix per spec (3-spec orientation budget unchanged); one reminder comment per merged PR |
| **Edge cases** | addressed | gh absent/failing → `--offline` degradation; stale (≥ 8 days)/absent/malformed cache → current behavior; bare `#NNN` may be an issue — resolved merged-PRs-only at check time |
| **Plugin compatibility** | addressed | `classify_staleness` behavior unchanged for already-recognized tokens; deliverable-existence signal kept as fallback; sibling parity via existing drift-guard suites |
| **Error handling** | addressed | Hook stays crash-proof (existing try/except); audit never blocks by default; workflow no-ops on closed-unmerged PRs |
| **Tradeoffs & alternatives** | addressed | Workspace design.md tradeoff table (extend `_state.py` vs standalone checker; cache vs gh-in-hook; lint-new vs mass rewrite) |
| **Rollback strategy** | addressed | `ATTUNE_SPEC_AUDIT=off`; drift cache disposable; workflow deletable; hooks revert via canonical repo + `make sync-hooks`; PyPI version pin |

### Edge cases & open questions

| Question / Edge case | Resolution |
|----------------------|------------|
| Bare `#NNN` cites an issue, not a PR | `gh api .../pulls/{n}` resolution at check time; non-PR / unmerged refs ignored |
| Cross-repo PR reference | Markdown pull-URL is the required style; `PrRef.repo` carries the explicit repo |
| gh unauthenticated / rate-limited / absent | Degrade to deliverable-existence signal; never block; `--offline` forces it |
| Unbounded gh calls on a big workspace | Per-run cap (mirrors `session_recall.py` `_MAX_PR_CHECKS`) + in-run cache |
| Drift cache goes stale between weekly CI runs | 8-day freshness window (one weekly period + slack); stale = ignored |
| Unknown status token | Linted as `unparseable`, never guessed; lint message names the canonical 8 |
| Spec intentionally on hold | `parked` family (`parked`/`paused`/`blocked`/`deferred`) skipped by drift checks, listed as parked |
| Reminder heckles spec-authoring PRs | Self-reference carve-out: PRs modifying files under the referenced spec dir are skipped (design §5 amendment 2026-07-10) |
| Reminder double-comments on re-run | Marker-comment guard: never comment twice on the same PR |

### Gaps (if any)

None plugin-side. The live baseline validation (workspace task 9) runs
in the umbrella after the release + re-sync and is tracked there.

---

## Phase 2: Design

**Status**: approved (2026-07-10 — by reference: workspace
`specs/spec-status-integrity/design.md` §1–3 + §5, approved via attune
PR #29 with the 2026-07-10 amendments)

The authoritative design lives in the workspace spec. Plugin-relevant
sections:

- **§1 Signal layer** — `extract_pr_refs()` citation-style table and
  `PrRef {repo: str|None, number: int, explicit: bool}`; vocabulary lint
  built on the existing `_TERMINAL_VERDICTS` / `_ONGOING_VERDICTS` sets.
- **§2 Checker** — `--pr-links` pipeline over `discover_specs()`;
  `.attune/spec-drift.json` schema
  `{generated_at, specs: {path: {verdict, prs, signal}}}`.
- **§3 Session surface** — cache-read-only annotation; no-network
  invariant preserved (`_state.py:2`, 4 s hook timeout).
- **§5 PR-merge reminder** — reusable workflow contract, self-reference
  carve-out, minimal permissions.

### Distribution

- [x] PyPI release required (plugin release precedes workspace task 7)
- [ ] Personal command update only
- [x] Plugin marketplace update (rides the release)
- [ ] No distribution change

---

## Phase 3: Tasks

**Status**: approved (2026-07-10 — by reference: workspace
`specs/spec-status-integrity/tasks.md`, approved by Patrick 2026-07-10)

The execution plan is workspace tasks 1–6, one commit each on
`feat/spec-status-integrity-hooks`:

| # | Task (workspace #) | Component | Status | Notes |
|---|--------------------|-----------|--------|-------|
| 1 | This companion spec (ws 1) | docs/specs | done | |
| 2 | `extract_pr_refs()` + `PrRef` (ws 2) | `_state.py` | done | 4 styles + negatives; 17 tests |
| 3 | `lint_status_token()` + vocabulary (ws 3) | `_state.py` | done | `implemented`/glyphs terminal; parked family |
| 4 | `--pr-links` + drift cache + `--json` (ws 4) | `spec_audit.py` | done | Golden test mirrors SPEC-AUDIT-2026-06-17 |
| 5 | Drift-cache read + `⚠ drifted` (ws 5) | `spec_orient.py` | done | 8-day freshness; `ATTUNE_SPEC_AUDIT=off` |
| 6 | Reusable reminder workflow (ws 6) | `.github/workflows` | done | yaml.safe_load test suite |

Testing strategy, rollback plan, and the full XML execution plan live in
the workspace `tasks.md` — not duplicated here.

---

## Phase 4: Implementation

**Status**: in-progress

### Completion checklist

- [x] All tasks marked done
- [x] pytest + ruff green after each task
- [x] No live gh calls in the default suite (testing-conventions) —
      gh is patched at the `_run_gh` subprocess boundary
- [x] Existing `classify_staleness` / `spec_orient` behavior unchanged
      for already-recognized tokens (regression check — full hook suite
      green)
- [ ] Version bumped for the plugin release (three files:
      pyproject.toml + plugin.json + uv.lock) — rides the release-prep
      PR per the standard flow, not this feature PR
- [x] Committed one task per commit, conventional messages
- [x] PR opened linking this spec and the workspace spec

---

## Cross-references

- Workspace spec: `specs/spec-status-integrity/` in the attune repo —
  [requirements](https://github.com/Smart-AI-Memory/attune/blob/main/specs/spec-status-integrity/requirements.md) ·
  [design](https://github.com/Smart-AI-Memory/attune/blob/main/specs/spec-status-integrity/design.md) ·
  [tasks](https://github.com/Smart-AI-Memory/attune/blob/main/specs/spec-status-integrity/tasks.md)
- Approval trail: attune PRs #29 (design), #32/#33 (tasks), #34
  (amendments: self-reference carve-out, CI token secret).
- Pattern precedent: `docs/specs/fable-premium-tier/` ↔ workspace
  `specs/fable-model-tiers/`.
- Existing machinery this extends: `plugin/hooks/_state.py`
  (`classify_staleness`, `_DRIFT_OPT_OUT`), `plugin/hooks/spec_audit.py`,
  `plugin/hooks/spec_orient.py`, `Makefile: spec-audit`.
