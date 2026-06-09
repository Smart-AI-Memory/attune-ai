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

---

### B6 execution record — blog date-classification (2026-06-09)

**Result: closed empty. 0 archived, all 55 blog docs in-scope.**

Applied decision Q1's rule (git first-commit date vs a 6-month
cutoff). Basis: v8.0.1 released 2026-06-07 → cutoff **2025-12-07**.
Every doc in the cohort (`git ls-files 'docs/blog/*.md'
'docs/BLOG_*.md'`, 55 files) was first-committed *after* the
cutoff — oldest is `2025-12-14` (seven days inside the window),
newest `2026-05-09`. No file qualifies for
`docs/archive/blog/<year>/`, so the archive move is a no-op.

**Weak-proxy caveat (deferred to B5, not acted on):** git
first-commit date marks several posts "recent" even though their
*content* describes superseded versions — `attune-ai-v4-agent-sdk.md`,
the `*-v520-*` trio, `discord-v6-release.md`. These are the
historical record-keeping cohort Q1's rationale wanted to exempt,
but the blog dir was bulk-committed 2026-01..05 so the date proxy
can't see content age. Per Q1's own "threshold is revisitable"
note, the content-vs-version judgment is deferred to the B5
content-verify pass (which reads each doc) rather than guessed
from filenames here. B5 may flag genuine-historical posts for
archive when it reads them.

**Net effect on B5 budget:** all 55 blog docs remain in the
PENDING content-verify queue (no pruning from the date pass).
