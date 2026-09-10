# Handoff — cross-review host-relative resolution

**Branch:** `claude/claude-subscription-codex-1c4c50`
**PR:** [#2504](https://github.com/Smart-AI-Memory/attune-ai/pull/2504) (open)
**Base:** `main` @ `b112f8714`
**Commits:** `a56a4a52b` (feature + D11 fixes), `9988a3f0c` (verified markers)

A handoff is context, not authority — verify against the current Git
state and tests before continuing.

## Why this exists

A bare `/cross-review` run from a Codex host briefed **Codex on Codex's
own diff**. A self-review returns a clean-looking verdict that means
nothing, and nothing in the result said so. Two defaults caused it; both
were correct when Claude was the only host with an invocation surface,
and both silently became wrong once Codex had one.

## Files changed and what was done

### Behavior

| File | What |
|---|---|
| `src/attune/roundtable/review.py` | `HOST_ENV_PREFIXES` + `detect_moderator_host()` (prefix match, returns `None` when absent OR ambiguous); `resolve_default_seat()` (non-host seat); `_resolve_seat()`, `_resolve_claude_auth()`, `_independence()` helpers; `run_review()` signature `seat: str \| None = None`, `claude_auth: str = "auto"`; result stamps `host` + `self_review` |
| `tests/unit/roundtable/test_review.py` | 10 new tests + an autouse `_neutral_host` fixture clearing ambient host markers so no test's route depends on the shell it ran in |
| `CHANGELOG.md` | Two `### Fixed` entries under `[Unreleased]` |

### Records

| File | What |
|---|---|
| `docs/specs/cross-review/decisions.md` | 2026-09-09 chair ruling: OPEN-1 refined (not reversed), the `claude_auth` narrow flip, both accepted costs, the D11 lane outcome, and the marker correction |
| `docs/specs/cross-review/receipts.md` | R5 ledger row for the codex D11 lane (2 findings, both real) |

### Projections (edit the master, re-run the projector — never hand-edit)

`content/features/cross-review.md` and `plugin/skills/cross-review/SKILL.md`
are the sources. Everything else regenerated:

```bash
python3 scripts/sync_agents_skills.py --write     # .agents/skills mirror
python3 scripts/project_features.py cross-review  # .help/templates + docs/{how-to,reference,architecture}
python3 scripts/generate_reference_templates.py   # plugin/help/generated/references
python3 scripts/sync_help_bundle.py               # plugin/help bundle
```

## Resulting behavior

| Moderating host | Seat | Auth route | `self_review` |
|---|---|---|---|
| Claude | `codex` | `api` | `false` |
| Codex | `claude` | `subscription` | `false` |
| none (CI/shell) | `codex` | `api` | `null` (unverified) |
| ambiguous (nested) | `codex` | `api` | `null` (unverified) |

Row 1 is byte-identical to prior behavior — OPEN-1's ruled `codex` is
preserved everywhere the ruling could apply.

## Receipts actually run

- Full tree **1 failed / 26291 passed**. That failure
  (`test_related_packages_broken_metadata`) is verified **pre-existing** —
  it fails identically on a pristine `git archive HEAD` export, and
  main's last three `tests.yml` runs are green. Local env artifact.
- **Environment independence:** `72 passed` identically under
  `CLAUDECODE=1`, `CODEX_SESSION_ID=s1`, and no-host ambients.
- **Mutation checks:** deleting the host-relative branch fails 3 tests;
  un-narrowing `cross_host` fails 4, including Codex's pre-existing
  `test_default_claude_still_refuses_zero_api_budget`.
- **Live end-to-end:** bare run from a Codex host at a zero cap returns
  `host='codex' seat='claude' route='subscription' status='clean'`;
  it was `SessionSpendCapError` before.
- **D11 lane:** codex seat, scoped to 5 paths, 5 sent / 0 omitted, 2
  findings, both real, both fixed in-branch.

## Two corrections made mid-session — do not re-derive them

1. **OPEN-1 was already ruled** (2026-07-28), not provisional. The
   `PROVISIONAL until OPEN-1 is ruled` line in the skill was stale and is
   now removed. Read `decisions.md` for governance status, never a
   projection.
2. **The inferred Codex marker list was wrong.** A live probe exported
   none of the four names harvested from `~/.codex/shell_snapshots/`.
   Detection now matches the `CODEX_` prefix. If you touch detection,
   probe a live shell — do not harvest names from snapshot files.

## Open / not done

- **F1 — no aggregate surfaces non-billable usage.** Subscription rows
  ARE written to `~/.attune/telemetry/session_spend.jsonl` (7 exist);
  `spent_usd()` sums dollars so they contribute 0, and no CLI surfaces a
  count. An earlier framing of this as "invisible" was overstated and
  corrected. Unbuilt; chair deferred.
- **Raised-cap footgun (accepted):** if the API cap is ever raised, a
  cross-host run still prefers the subscription. Override with an
  explicit `claude_auth="api"`.
- **P4 — PR #2496** fails `changelog-entry`: it touches
  `src/attune/elicitation/host_question_adapter.py`, does not touch
  `CHANGELOG.md`, and carries labels `tests`/`core` but not
  `no-changelog`. It is a `feat`, so the CHANGELOG line is the correct
  exit, not the label. It is another session's branch — NOT touched.
- **P3 — housekeeping:** 7 worktrees under `/private/tmp` or prunable,
  6 entries on the shared stash stack. Two superseded cross-review
  branches (`codex/cross-review-subscription`, absorbed by #2449, and
  `docs/feature-page-cross-review`, 2026-07-22) are reaping candidates.

## Four lessons are queued in the docs outbox

`ruling-fixed-a-value-not-the-property`,
`governance-status-text-stales-in-projections`,
`fixing-one-default-exposes-the-next`,
`test-still-names-mark-deliberate-pins`.
Route via the curating sweep — do not append `.claude/lessons.md`.
