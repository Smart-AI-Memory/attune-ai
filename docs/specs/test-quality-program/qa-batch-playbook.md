# QA Batch Playbook

The proven cadence for a test-quality coverage batch: one module
→ one behavioral net-new test file → one PR → merge on green.
Codified 2026-06-13 after the `attune.memory` batch (11 PRs,
94% overall). This is a playbook for an agent with judgment, not
an automation spec — test authoring stays a thinking task.

---

## The loop

One iteration per module. Keep each iteration a single net-new
test file so parallel sessions never conflict.

1. **Baseline.** Run `scripts/qa_coverage_baseline.sh` once per
   batch to get the authoritative ranked gap list for a package.
2. **Confirm the candidate.** A subset baseline lies (see
   [Gotchas](#gotchas)). Before writing, verify the module's TRUE
   coverage via its real test files:
   `find tests -name "*<mod>*"`. If it already has a suite
   elsewhere, the gap is smaller than the baseline claims — pick
   another.
3. **Read the module.** Understand its real behavior — branches,
   error paths, precedence — before touching a test.
4. **Write a behavioral, mutation-resistant net-new test file.**
   Assert exact outputs and error branches, not just line
   execution. See [Test-quality bar](#test-quality-bar).
5. **Verify coverage** with the worktree workaround
   ([Gotchas](#gotchas)). Confirm the module moved to ~95%+.
6. **Fresh branch off `origin/main`** (never reuse a branch):
   `git fetch origin main && git switch -c qa/<mod> origin/main`.
7. **Pre-flight black + ruff** on the new file BEFORE staging
   (pinned versions — see [Gotchas](#gotchas)).
8. **Commit, push, open one PR** (one module = one file = one PR).
9. **Merge on the 7 required greens** ([Merge gate](#merge-gate)),
   or let `scripts/qa_pr_babysitter.sh` do it.

---

## The two scripts

Both shipped in PR #822. Both are worktree-safe and keyless.

### `scripts/qa_coverage_baseline.sh`

Step 1 of every batch. Runs the full unit suite scoped to one
package, keyless, and prints modules under a threshold ranked by
missed lines.

```bash
bash scripts/qa_coverage_baseline.sh [package] [threshold] [out_file]
# defaults: attune.memory  80  <temp file>
bash scripts/qa_coverage_baseline.sh attune.workflows 85
```

It auto-locates the MAIN checkout's venv python (which has all
extras) and overrides `PYTHONPATH` so the worktree's code is what
gets measured. Every module it prints is a HYPOTHESIS — confirm
with step 2 before writing.

### `scripts/qa_pr_babysitter.sh`

A standing poller that squash-merges YOUR open PRs whose head
branch matches a prefix once their REQUIRED checks pass. Safe by
design: `--author "@me"`, plain `--squash --delete-branch`, no
`--admin`, no branch-protection changes.

```bash
bash scripts/qa_pr_babysitter.sh [branch_prefix] [deadline_min] [interval_sec]
# defaults: qa  90  60
```

Run it backgrounded or via `/loop`. The required-check list lives
in the script (`REQUIRED=...`); update it if branch protection
changes.

---

## Merge gate

Confirmed via the branch-protection API on 2026-06-13.

- **Reviews required: 0.** No approval needed for these PRs.
- **7 required checks:** `pre-commit`, `lint`, `code-quality`,
  `coverage`, `platform-compat`, `CodeQL`,
  `test (ubuntu-latest, 3.12)`.
- **Merge on those 7.** Do NOT wait on the Windows/macOS test
  lanes or the `security` scanner — all non-required/advisory.
- Normal `gh pr merge --squash --delete-branch`. No admin.

Re-verify if anything looks off:
`gh api repos/Smart-AI-Memory/attune-ai/branches/main/protection`.

---

## Gotchas

- **Worktree coverage reports 0% by default.** The rcfile
  `source` filter can't map the worktree path to the package via
  the main-pointing editable MAPPING. Measure with the MAIN
  venv's python + an absolute `PYTHONPATH` + `--cov-config=/dev/null`
  + a **path**, not a dotted module name, for `--cov` (see the next
  gotcha for why):

  ```bash
  ANTHROPIC_API_KEY="" PYTHONPATH="<wt>/src" <main-venv>/bin/python \
    -m pytest <wt>/tests/path/to/test_<mod>.py \
    --cov="<wt>/src/attune/<mod-path>" --cov-config=/dev/null \
    --cov-report=term-missing -o addopts= -p no:xdist
  ```

  (The baseline script already does this for the whole-suite run.)

- **A module loaded via `spec_from_file_location` under a synthetic
  name is invisible to `--cov=<dotted.module>`, even when
  thoroughly tested.** `config.py` (legacy-compat re-export) and
  every `hooks/scripts/*.py` test load their target this way, so
  `--cov=attune.config` / `--cov=attune.hooks.scripts.X` reports 0%
  regardless of real coverage — `pytest-cov` needs that exact
  dotted name imported to find what to report. A **directory**
  path (`--cov=<wt>/src/attune/hooks/scripts`) tracks by executed
  file location instead and gives the real number — verified
  identical to the dotted form for normally-imported modules, so
  it's a strict superset, not a tradeoff. Real numbers once fixed:
  `config.py` 98%, `worktree_path_guard.py` 93%,
  `starter_reconciler.py` 95%. `scripts/qa_coverage_baseline.sh`
  now does this automatically (converts the dotted `$PACKAGE` arg
  to a path before invoking `--cov`).

- **A whole-repo baseline can resurrect a module that's
  DELIBERATELY in `pyproject.toml`'s coverage `omit` list.** The
  baseline's `--cov-config=/dev/null` (needed for the worktree-path
  gotcha above) also discards the `omit` entries, so genuinely
  excluded dead-or-untestable code reappears as a fake "gap." Hit
  with `workflows/progress_server.py` (142 missed, 0%) — already
  flagged not-a-real-gap in this doc's Tier 4 and in `decisions.md`
  (2026-06-14); confirming it's also genuinely dead code (no
  `websockets` dependency declared, so it can never actually import
  the live path — always raises at construction) took a few
  minutes that a first glance at Tier 4 above would have saved.
  Before treating a baseline "0%" as new work, check whether it's
  already in the `omit` list (`grep <file> pyproject.toml`) and
  whether this doc's Tier 4 already settled it.

- **Keyless ALWAYS: `ANTHROPIC_API_KEY=""` (empty, not unset).**
  An UNSET key lets `load_dotenv` inject the real one and the run
  spends real money at integration scale. Empty string blocks the
  injection AND fires the `skipif(not key)` gates — matching CI.

- **Subset baselines undercount.** A coverage run over ONE test
  subdir (e.g. `tests/memory/`) misses modules whose tests live
  in `tests/security/`, `tests/unit/memory/`, etc. It made
  `audit_logger` look like 59% (really 94%) and `secrets_detector`
  56% (really 92%). Always confirm true coverage before picking.
  (Lesson banked in PR #821.)

- **Read-only facade props can't be assigned.**
  `RedisShortTermMemory.use_mock` and `_client` are read-only
  properties. For the non-mock branch of an index/manager, inject
  a tiny `FakeMemory` exposing only the attrs the SUT reads —
  don't try to mutate the real object. (Lesson banked in PR #810.)

- **`.help` regen hook re-polishes whole features on commit.**
  Adding a source file under a feature's glob triggers a full LLM
  re-polish of that feature's `.help/templates/`. Discard it from
  focused QA PRs: `git checkout -- .help/templates/<feature>/`.
  It is warn-only / not CI-required.

- **Pre-flight the PINNED black + ruff before `git add`.** The
  worktree `.venv`'s black can format differently from the pinned
  hook; CI black runs on the whole file you touched, not just your
  diff. Run
  `uv run --with pre-commit pre-commit run black --files <f>` and
  `uv run ruff check <f>` on the new file first.

- **Commit footer:**
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

## Test-quality bar

Coverage % is the floor, not the goal. A test that executes a
line without pinning its behavior is mutation-vulnerable theater.
Every net-new suite should include:

- **Exact-output assertions.** Assert the returned value /
  structure / message, not just that the call didn't raise.
- **Precedence and branch tests.** When behavior depends on
  ordering or conditionals, test each branch and the order
  between them.
- **Error-path coverage.** Exercise the `except`/`raise` arms —
  assert the exception type and message, not just that something
  failed.
- **Behavioral, not implementation-coupled.** Test what the
  module promises, so a refactor that preserves behavior keeps
  the tests green and a real regression turns them red.

NOT this: padding line coverage with smoke tests that would still
pass after a mutating bug.

---

## Exemplars

Net-new suites from the `attune.memory` batch that hit the bar:

- `tests/memory/test_long_term_operations.py` (PR #817)
- `tests/memory/test_short_term_mixin.py` (PR #818) — FakeMemory
  pattern for the non-mock branch.
- `tests/memory/test_handoff_mixin.py` (PR #819)
- `tests/unit/memory/test_cross_session_service_internals.py`
  (PR #820) — error-branch coverage of a background service.

---

## When to graduate to automation

This stays a playbook (option 3b) while test authoring needs
judgment. Build a thin orchestration skill (option 3c) ONLY if
the cadence repeats enough to earn it — the baseline + babysitter
scripts already remove the mechanical toil. The thinking step
(read module → design behavioral tests) does not automate well.
