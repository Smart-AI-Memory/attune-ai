# Auto-Merge-Safe Class — Decisions

**Status:** approved (2026-06-14, amended with D5–D6 2026-06-14)

---

## D1 — Class definition (the pre-authorized set)

A PR is **auto-merge-safe** iff ALL of these hold (fail-closed on
any failure or ambiguity):

| # | Gate | Detail |
|---|------|--------|
| 1 | Label | `auto-merge-safe` present |
| 2 | Path class | every changed path (incl. rename's previous path) under `tests/`, `docs/`, `.help/`, or a root-level `*.md` |
| 3 | Coverage | `coverage` required check == `success` on PR head |
| 4 | Author | login == `silversurfer562` (repo owner) |
| 5 | Provenance | head repo == base repo (no forks); not a draft |

The merge bypasses only the **redundant hung lane** (e.g.
`test (ubuntu-latest, 3.12)`). The `coverage` job re-runs the
**full** suite, so for a test/docs-only PR coverage-green ⇒ the
suite is verified ⇒ the redundant matrix lane is safe to skip
(established lesson, 2026-06-13/14).

**Why these paths:** `tests/` + `docs/` is the literal scope.
`.help/` and root `*.md` were added (D-path) because docs
auto-runs routinely touch `.help/` templates and root markdown
(README/CHANGELOG); excluding them would make the class "so tight
it never fires." Everything else — `src/`, `.github/`,
`pyproject.toml`, lockfiles, `mkdocs.yml` — stays out by
construction.

---

## D2 — The classifier is the wrong layer; move the merge into CI

The harness safety classifier requires conversational
authorization for admin-merge and does not honor any
settings/label/starter-file grant. Rather than fight that, the
**agent is removed from the merge loop entirely**: a GitHub
Actions workflow performs the merge deterministically. No
agent, no classifier.

---

## D3 — Merge credential: fine-grained admin PAT (not GITHUB_TOKEN)

`GITHUB_TOKEN` runs as `github-actions[bot]`, which is **not** a
repo admin, and there is **no ruleset bypass** configured
(`rulesets == []`, classic protection with `restrictions: null`).
Verified: with `enforce_admins: false`, only an **admin actor**
bypasses required checks. So:

- The merge job authenticates with a **fine-grained PAT** owned
  by `silversurfer562` (an admin), stored as the Actions secret
  `ADMIN_MERGE_TOKEN`.
- Scope: **this repo only**; permissions **Contents: Read/Write**
  + **Pull requests: Read/Write**; **NOT** Administration.
- Tradeoff: a long-lived admin-capable secret. Mitigated by the
  five gates in D1 (label + ALL-in-class path filter + coverage +
  author + no-fork), the merge job re-verifying the path class
  independent of the label, and the guard living under `.github/`
  (out-of-class, so it can't self-merge). Rotate per normal PAT
  hygiene.

Rejected for now: a GitHub App (auto-expiring tokens, more
secure) — materially more setup; revisit if PAT hygiene becomes a
burden.

---

## D4 — Label is applied by automation, re-verified at merge

The `auto-merge-safe` label is applied/removed by the workflow's
label job (computed from the path class + author) on every PR
update, so it tracks reality (a later push that adds a `src/`
file removes the label). The **merge job re-runs the path-class
guard** before merging, so even a hand-applied label on an
out-of-class PR will not merge. Label = necessary, not
sufficient.

---

## D5 — Merge trigger: `workflow_run`, not `check_run`

**Shipped in [PR #883](https://github.com/Smart-AI-Memory/attune-ai/pull/883)
(`0bc16edf9`, 2026-06-14); recorded here for completeness.**

The merge job was originally triggered by `check_run: completed`
for the `coverage` check. That trigger is **dead**: GitHub does
not start a new workflow run from an event produced by the repo's
own `GITHUB_TOKEN` (anti-recursion). The `coverage` check_run is
produced by the `Tests` workflow under `GITHUB_TOKEN`, so its
completion never reached this workflow (verified empirically:
coverage went `success`, and >4 min later zero new runs existed,
the PR stayed open).

Fix: trigger on `workflow_run: workflows: ["Tests"], types:
[completed]`. It fires when the whole `Tests` workflow finishes
regardless of conclusion, so a hung/failed redundant lane does not
suppress it, and the merge job re-checks `coverage` independently.

**Caveat (out of scope):** `workflow_run` fires only when the
ENTIRE `Tests` matrix completes, so a genuinely hung lane still
delays the merge. Right-sizing the matrix is tracked separately.

---

## D6 — true root cause: malformed `ADMIN_MERGE_TOKEN` (+ resolution hardening)

**Bug (found on [PR #884](https://github.com/Smart-AI-Memory/attune-ai/pull/884),
2026-06-14):** with the D5 trigger live, #884's `Tests` completion
DID invoke the merge job, but it logged `No open PR against main
for <sha>` and bailed. The lookup
`gh api repos/$REPO/commits/$SHA/pulls` appeared to return EMPTY
despite #884 being open against `main` with exactly that head.

**Root cause — VERIFIED, malformed token secret (NOT
eventual-consistency lag).** An initial hypothesis blamed
eventual-consistency lag in the `commits/{sha}/pulls` association
index. That was **wrong** — corrected once the merge job finally
failed loudly. The `ADMIN_MERGE_TOKEN` secret (created
2026-06-14 12:38:34Z, never updated) was stored with a **trailing
newline**, which makes the HTTP `Authorization` header invalid, so
EVERY `gh api` call in the merge job fails with:

```
net/http: invalid header field value for "Authorization"
```

The original code ran `gh api commits/$SHA/pulls` inside a
`mapfile < <(…)` process substitution; under `set -e` the
process-substitution exit status is not checked, so the auth error
was **swallowed** and surfaced as an empty array → "No open PR".
The earlier "natural experiment" (querying the same SHAs hours
later) was flawed: it used a *different, valid* token, so it never
exercised the broken PAT. Direct evidence — run `27500989084`'s log
contains the `invalid header field value` line immediately above
its "No open PR" line; the error was present the whole time and was
missed by a too-narrow log grep.

**Fix (two parts):**

1. **Strip whitespace from the token (the actual fix).**
   `GH_TOKEN="$(printf '%s' "$GH_TOKEN" | tr -d '[:space:]')"` at
   the top of the merge step. A PAT never contains whitespace, so
   this is safe and makes the job robust to a secret stored with a
   stray newline. Companion hygiene action: re-enter the secret
   cleanly (`printf %s "$PAT" | gh secret set ADMIN_MERGE_TOKEN`,
   no trailing newline).
2. **sha→PR resolution hardening (robustness, independent of the
   token bug).** Prefer `github.event.workflow_run.pull_requests[]`
   (event payload — synchronous, populated for same-repo PRs, which
   our no-fork class guarantees); fall back to `commits/{sha}/pulls`
   with retry/backoff. Open/base re-checks moved into the per-PR
   loop (`state == open`, `base.ref == main`) so correctness is
   independent of which source resolved the PR. This both reduces
   API calls and guards against *genuine* indexing lag — confirmed
   working: it resolved #881 from the payload instantly.

**Lesson:** a hard auth failure inside a `mapfile < <(gh api …)`
process substitution is silently swallowed under `set -e` and looks
identical to "no data." Prefer surfacing such errors (the per-PR
loop's bare `gh api` call, which is NOT in a process substitution,
is what finally exposed it). And grep logs for `error`/`invalid`,
not just the expected success/skip strings.

All D1 gates are preserved unchanged.

---

## Rejected alternatives

### A — Drop the redundant `test (ubuntu-latest, 3.12)` from required checks

**Rejected: too broad.** It weakens the gate for **all** PRs
(including `src/` changes), not just the test/docs class. The
hung lane is redundant *only for test/docs-only PRs where
coverage re-runs the suite*; for code PRs the matrix lane carries
real per-platform signal. Removing it from branch protection
throws away that signal globally to fix a narrow case.

### B — Any starter-file or settings "authorization" note

**Rejected: not durable.** The harness safety classifier ignores
it and demands conversational authorization every session (proven
2026-06-14, PR #865). A note cannot close an unattended-run gap.

### C — `gh pr merge --auto --squash` (the dependabot pattern)

**Rejected: does not close the gap.** `--auto` **waits** for the
required checks; the whole problem is that a required check
**hangs and never completes**. Auto-merge would wait forever.

### D — Merge via `GITHUB_TOKEN` with `--admin`

**Rejected: cannot work here.** The bot is not an admin and there
is no ruleset bypass, so `--admin` fails on exactly the
hung-check case. (See D3.)

---

## D7 — Retry the admin merge on the concurrent-merge race

**Date:** 2026-06-14
**Status:** adopted

**Symptom.** Three in-class PRs (#892, #893, #894) went green
together and their merge jobs fired within ~3 seconds. #892 and
#893 squash-merged first, advancing `main`. #894's merge fired ~2s
later and GitHub rejected it:

```text
GraphQL: Base branch was modified. Review and try the merge again.
(mergePullRequest)
```

The old code swallowed this with `|| echo "merge call failed
(possibly already merged)"` and exited 0 — so #894 sat OPEN with
**every gate green** (path-class ✓, coverage=success ✓, label ✓)
and no retry. Any batch of ≥2 simultaneously-green in-class PRs can
hit this; it is not specific to the cancel-to-bypass flow.

**Fix.** Wrap the `gh pr merge --squash --admin --delete-branch`
call in a 5-attempt loop with a 6s backoff. "Base branch was
modified" is transient — `main` is stable once the racing siblings
land — so a re-fetch + retry succeeds. A concurrent job that already
merged the PR (`pulls/$pr .merged == true`) is treated as success,
not failure. Exhausting all attempts emits a `::warning::` and
leaves the PR open (fail-open, visible).

**Scope.** This is a `.github/workflows/` change, so the fix PR is
**out-of-class** and merges via human review (CI files cannot
self-merge — correct). Pairs with D6 (the token-newline auth fix):
both are "the merge job resolved the PR but the merge call failed"
shapes — D6 was an auth error swallowed by process substitution,
D7 is a race swallowed by `|| echo`.

---

## D8 — Class 2: opt-in `auto-merge-when-green` (native auto-merge)

**Date:** 2026-07-20
**Status:** chair-approved (Patrick — Option A, `.github/`-only
carve-out)

**Problem.** Class 1 covers only tests/docs PRs, so a routine
cascade of green src PRs (e.g. the 2026-07-20 overnight
advanced-debugging/claim-gates run, ~10 PRs) still needed a session
babysitting every merge with a gated one-liner.

**Class definition** (all fail-closed):

| # | Gate | Detail |
|---|------|--------|
| 1 | Opt-in label | `auto-merge-when-green`, applied by a HUMAN only — semantics "PR is final; merge when fully green." Automation never applies it (inverse of Class 1's label ownership). Resolves the stranded-follow-ups trap (2026-06-20 lesson) by intent instead of a settle-timer |
| 2 | Author/provenance | author == `silversurfer562`, head repo == base repo, not draft, open, base `main` (same as Class 1) |
| 3 | Path carve-out | no changed path (incl. rename origins) under `.github/` — merge automation can never self-merge, even labeled (`auto_merge_guard.py --mode when-green`) |
| 4 | Full green | ALL required contexts must pass — enforced by GitHub's NATIVE auto-merge engine, never by our own check parsing. **No `--admin` for this class**; branch protection stays fully enforced |
| 5 | Re-verify on push | `synchronize` re-runs the carve-out; a push that goes out-of-class disarms (`--disable-auto`) and strips the label; `unlabeled` disarms |

**Why native auto-merge (Option A), not a custom evaluator
(Option B).** The check-bucket-parsing trap (`gh pr checks` exits 0
with failures) is eliminated rather than mitigated — GitHub's own
engine decides green-ness. The original Rejected-C ("`--auto` waits
forever on a hung required check") was a rejection for **Class 1**,
whose purpose was to bypass a hung redundant lane; for Class 2 a
hung lane correctly blocks the merge (for src PRs the full matrix
is signal, not redundancy) — fail-closed and visible. Prereq
`allow_auto_merge: true` verified live; the pattern is already
proven in-repo by `dependabot-auto-merge.yml`. Arming uses
`ADMIN_MERGE_TOKEN` (not `GITHUB_TOKEN`) so the eventual merge is
user-attributed and downstream main-push workflows are not
anti-recursion suppressed.

**Receipt (D1 red-first, claim-drift-gates protocol).** Guard-mode
tests (`tests/unit/github_scripts/test_auto_merge_guard.py`) and
workflow invariants (`tests/unit/ci/test_workflow_yaml.py`:
`TestAutoMergeWhenGreen` — job exists, label-lifecycle triggers,
owner+label gate, `--auto` never `--admin`, guard re-verification,
disarm on unlabeled) landed red first; the implementation commits
in the same PR turned them green.

## D11 — chair-read gate: read-gated PRs are out of the Class-1 lane

**Date:** 2026-08-10
**Status:** implemented (incident-driven)

(D9 — standing docs-only authorization — and D10 — chair's
"merge N" message as label authorization — are chair rulings from
2026-08-09, recorded in session memory/governance notes; numbered
here to keep one sequence for this class.)

**Incident.** PR #2043 (spec design/tasks text) was deliberately
opened chair-read — "(chair-read)" in the title, no
`auto-merge-when-green` label — but its diff was docs-only, so the
Class-1 auto-labeler applied `auto-merge-safe` and the merge job
squashed it ~1.7h before the chair's authorization. The read gate
held only socially; nothing mechanical knew "chair-read" existed.

**Decision.** A PR whose title contains `(chair-read)` OR which
carries a `chair-read` label is skipped by BOTH Class-1 jobs:

- the `label` job never applies `auto-merge-safe` to it (and
  removes the label if present);
- the `merge` job re-verifies the marker independently, from a
  fresh API read (label = necessary, not sufficient — same
  philosophy as the path-class re-check), fail-closed: anything
  but a clean `false` skips.

Class 2 (`when-green`) is deliberately NOT gated on the marker:
per D10 the chair's "merge N" is executed by applying
`auto-merge-when-green` to a PR that still carries "(chair-read)"
in its title — gating that lane would break the authorized merge
path.

**Receipt.** Drift guard
`tests/unit/ci/test_workflow_yaml.py::TestAutoMergeChairReadGate`
pins: title-marker check in the label job, `chair-read` label
honored, independent fail-closed re-check in the merge job, and
when-green left ungated.

**Live-fire receipt (2026-08-10).** Probe PR: docs-only diff
(this edit), title carrying "(chair-read)" — label job observed
skipping ("chair-read marker -> never auto-labeling"), no
`auto-merge-safe` label applied. Control: the same diff re-opened
UNMARKED auto-labeled and auto-merged normally, proving the
Class-1 lane is intact for everything without the marker.
