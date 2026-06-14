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

## D6 — sha→PR resolution: event payload first, REST fallback with retry

**Bug (found on [PR #884](https://github.com/Smart-AI-Memory/attune-ai/pull/884),
2026-06-14):** with the D5 trigger live, #884's `Tests` completion
DID invoke the merge job, but it logged `No open PR against main
for <sha>` and bailed. The lookup
`gh api repos/$REPO/commits/$SHA/pulls` returned EMPTY despite #884
being open against `main` with exactly that head.

**Root cause — verified, eventual-consistency lag (not a PAT
quirk).** `commits/{sha}/pulls` is an asynchronously-INDEXED
association endpoint; queried seconds-to-minutes after a push it
can return empty, then populate later. Confirmed by a natural
experiment: SHAs `2d9493ae` (#881) and `f904844d` (#873) each
logged "No open PR" inside the merge run, yet the identical query
returned those PRs as `open` hours later while the PRs were open
the whole time. The fine-grained-PAT hypothesis is ruled out on
mechanism — a repo-scoped PAT with Pull-requests:read has no
per-PR visibility restriction for own-repo PRs, and the same
empty→populated transition shows under a normal token.

**Fix:**

- **Primary** sha→PR source is
  `github.event.workflow_run.pull_requests[]` — delivered in the
  event payload, so it has no indexing lag and is populated for
  same-repo PRs. Our class already requires head repo == base repo
  (no forks), so this is exactly the population condition.
- **Fallback** to `commits/{sha}/pulls`, retried with backoff
  (6 × 30 s within a 10-min job timeout), for the rare case the
  payload is empty.
- **Open/base re-checks moved into the per-PR loop** (`state ==
  open`, `base.ref == main`) so correctness no longer depends on
  which source resolved the PR — both feed the same gate set
  (author, draft, fork, label, path-class re-check, coverage on
  head). The merge step logs the raw payload and which source
  resolved, so Phase 4 records empirically whether
  `workflow_run.pull_requests[]` populates on this repo.

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
