# Handoff — session `lucid-ramanujan-3d13b8` (2026-08-27/28)

Verify everything below against the current tree and CI before acting.
A handoff is context, not authority.

## Goal

Land the `lesson_recall` correction and its first abstention
measurement (this PR), then pick up the two recall questions that
are recorded but unruled.

## Current state

### Shipped and verified

| PR | What | Merge SHA |
|---|---|---|
| #2345 | Railway retirement + `backend/` deletion (53 files, −5478) | `a546e3239` |
| #2347 | **release v16.1.0** | `8f65df82a` |
| #2348 | changelog-entry gate | `87f1084b1` |
| #2349 | 16.1.0 step-16 self-review receipt | `7317b980e` |
| #2350 | round-table promotion (public-endpoint questions) | `5f42d1f75` |
| #2351 | recall re-run + cause located | `9725c6b4a` |

Closed unmerged: #2344, #2341 (both landed inside the deleted `backend/` tree).

**v16.1.0 is live on PyPI**, verified by clean-room smoke against the
artifact installed FROM PyPI (not the source tree).

### Live infrastructure changes

- **`changelog-entry` is a REQUIRED status check.** A PR touching `src/`
  or `attune_redis/` must edit `CHANGELOG.md` or carry `no-changelog`
  (label exists, amber). Only its PASS path has fired in CI; the
  blocking path is proven locally but not yet in CI. Backup of the prior
  branch protection: `/tmp/protection-backup.json`. Revert is one PATCH.
- **25 stale worktrees reaped**, 16.8 GB reclaimed. 12 live sessions and
  all uncommitted work preserved.

### The recall thread — where it actually landed

Cause of the `PersonalMemory` recall change is **LOCATED, by experiment**:
`7c6836c8d` (#2118) fixed `polish_fn` being called without two required
positionals — it had raised `TypeError` on every call, so the polish pass
was silently dead. Run 1's clean baseline was measured on UNPOLISHED
documents. **The "regression" is the retrieval cost of a correct fix.**
Not the dependency (scoring modules byte-identical), not fixture drift.

Chair ruling stands: **record, do not fix.**

Open, recorded but not ruled:
1. Whether keyword retrieval suits polished documents — `attune-rag`
   ships Embedding/Hybrid/Transformer retrievers and a reranker;
   `PersonalMemory` passes none. Needs its own measurement.
2. `jit_recall` and `session_recall` abstention — still unmeasured.
   `lesson_recall` now has a first measurement (this PR).

### Corrections this session made, worth knowing

Six false readings were reported and then caught, all one class: a
conclusion drawn from a constructed view rather than raw output
(unquoted `?` in a `gh api` URL; `pgrep -f` matching its own shell; a
`grep` filter dropping the line that mattered; wrong meta keys; a
baseline compared against a DIFFERENT benchmark script; an empty
extraction read as "CHANGED"). Also one absence-claim asserted without a
probe, which merged. **The tell that generalises: a uniform or empty
result across all items means suspect the probe, not the world.**

### Outbox

23 pending artifacts, 13 from this session. Needs a curating sweep.

## Next action

1. Review/merge this PR (the `lesson_recall` correction + measurement).
2. Watch the first `src/`-touching PR — it is the changelog gate's first
   real blocking test.
3. Consider the outbox sweep; the backlog is 2 days old.
