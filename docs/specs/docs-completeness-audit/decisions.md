# Per-decision log — Docs completeness audit

Append-only log. Resolutions for the open questions enumerated in
[requirements.md](./requirements.md#open-questions). Each decision
moves the spec one step closer to Phase 1 execution.

---

## Phase 1 approval (2026-05-31)

Three open questions resolved in one session. Spec status flips
from `draft` to `approved`. Phase 1 (subagent triage of in-scope
docs) can spawn after this lands on `main`.

---

### Q1 — Blog-shaped docs (`docs/blog/*.md`, `docs/BLOG_*.md`): in or out?

**Decision:** **Date-cutoff IN.** Posts dated within 6 months of
release are in-scope for the completeness audit; older posts move
to `docs/archive/blog/<year>/` and are exempt.

**Rationale:** Recent blog posts ARE discoverable from the site
and behave as quasi-docs — a 4-month-old post claiming a feature
works one way contradicts current behaviour and counts as fiction.
Historical posts describing v3.x behaviour aren't fiction; they're
record-keeping. The date cutoff distinguishes the two without
forcing every historical post through audit (wrong) or letting
every recent post stay unaudited (also wrong).

**Alternatives considered:**

- **All blog OUT** — Smallest scope. Risk: recent posts stay
  unaudited and become drift sources.
- **All blog IN** — Largest scope. Risk: forces rewriting
  historical posts that intentionally describe old behaviour.

**Implementation note for Phase 1:**

- Stage A's subagent prompt classifies each blog post by date
  before triage.
- Posts older than 6 months from `pyproject.toml` version's
  release date → flag for archive move, skip content audit.
- Posts within 6 months → full triage like any other doc.
- The 6-month threshold is a starting value; revisit if it
  produces obviously-wrong categorizations.

---

### Q2 — `docs/PROJECT_OVERVIEW.md`: MECHANICAL, REWRITE, or evergreen?

**Decision:** **Evergreen rewrite, strip versions.** Rewrite to be
version-agnostic so the doc stops drifting at every release.

**Rationale:** This is the canonical "stale version in long-lived
doc" pattern. Mechanical sweeps fix today's drift but the same
doc will drift again at the next release. A top-level project
narrative shouldn't need to claim a specific version anyway — the
README badge and PyPI page handle that. One focused rewrite now
beats forever-recurring sweeps.

**Alternatives considered:**

- **MECHANICAL** — Cheapest fix; pure debt-paydown without
  addressing the root cause. The doc drifts again at 7.4.0.
- **REWRITE** — Full rework assuming framing is stale. Larger
  scope. If framing turns out fine in execution, evergreen
  collapses into MECHANICAL anyway, so picking evergreen
  pre-emptively gives optional headroom.

**Implementation note for Phase 1:**

- Treat `docs/PROJECT_OVERVIEW.md` as a single-subagent task
  (not part of a bucket).
- Removes version numbers, specific workflow counts, "as of
  vX.Y.Z" timestamps. Keeps narrative framing where current.
- Adds a footer note: "For current version, see [PyPI](
  https://pypi.org/project/attune-ai/) or the README badge."

---

### Q3 — Counting / sizing: verify the math before subagent spawning

**Decision:** **Verified now.** The spec's preliminary 203 number
holds (same methodology — `find docs/ -name '*.md'` excluding
`docs/archive/` and `docs/specs/`). My earlier session-time
verification using `git ls-files docs/` returned 400 because it
counts non-`.md` files (`.json`, `.txt`, sitemap, robots, etc.);
that was a methodology mismatch, not a sizing error in the spec.

**Verified baseline (2026-05-31):**

| Bucket | Count |
|--------|-------|
| Total in scope (find docs/ -name '*.md' \\| not archive/specs) | 203 |
| Tracked in `features.yaml` (already audited via help system) | 24 |
| PR-touched (PRs #506-510 doc-fiction-cleanup) | ~30 |
| Blog cohort (docs/blog/ + top-level BLOG_*.md) | 55 |
| Untracked .md (none — clean) | 0 |

**Implication for Phase 1 triage budget:**

After applying decisions Q1 (most blog → archive at 6mo cutoff)
and excluding already-audited / already-cleaned docs, in-scope
estimate is **~135 files** (203 baseline − ~24 features.yaml − ~30
PR-touched − ~15 blog moved to archive). At 15 files per
subagent, budget is **~9 subagents** — close to the spec's
original 10-subagent estimate.

**Implementation note for Phase 1:**

- Stage A's first task is to re-run the inventory immediately
  before spawning, using the same `find` invocation, and produce
  the final bucket list as a committed artefact under
  `.audit/completeness-inventory.md`. The 135 number is a
  planning estimate; the execution-time count is the budget.
