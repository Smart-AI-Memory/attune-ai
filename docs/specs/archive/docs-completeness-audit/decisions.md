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

## Stage B5 — content-verify + close (2026-06-09)

B5 content-verified the PENDING queue (5-batch subagent fan-out
over the built/discoverable docs) and resolved the remaining open
questions. See
[completeness-audit-triage.md](./completeness-audit-triage.md#stage-b5-content-verify-results-2026-06-09)
for the full method, per-doc disposition, and the `exclude_docs`
113-built/107-repo-only split.

### Q4 — Blog content-verify: archive, fix, or defer?

**Decision:** **Archive the content-historical version-announcement
posts; defer the rest as dated artifacts.** B6's git-date rule kept
all 55 blog posts in-scope, so the content read (Q1's deferred
half) makes the call. `attune-ai-v4-agent-sdk.md` (v4.0) and
`discord-v6-release.md` (v6.0) are record-keeping for superseded
releases → moved to `docs/archive/blog/2026/`. The remaining blog
tutorial/essay/social posts carry point-in-time counts (e.g. "557
templates", "18 workflows", "38 MCP tools"); they are treated as
dated content-marketing artifacts (the same convention applied to
the dated-historical CLEAN docs in the triage) and a blog-copy
count refresh is **out of scope** for the completeness audit.

**Rationale:** A version-announcement post IS record-keeping for a
specific past release (the Q1 "not fiction, record-keeping"
category). A tutorial/social post written at vX stating the count
at that time is a dated artifact, not a current-state claim — and
rewriting marketing copy is not what a fiction audit is for.

### Q5 — Feature-doc quad fiction: hand-fix or fix the generator?

**Decision:** **Fix the attune-author generator + regenerate; do
NOT hand-patch the ~30 generated docs.** The quad
(`how-to/`/`reference/`/`tutorials/` per feature) shares identical
*generated* failure modes (wrong import paths, async-as-sync,
fabricated CLI binaries, fictional `WorkflowResult.content/.sources`)
— the docs even ship fact-check footers documenting their own
unresolved imports. Hand-fixing would regress on the next regen.
→ spawned follow-up spec **`attune-author-generator-fidelity`**.

### Q6 — Legacy "Empathy framework" docs: spot-fix or rewrite/retire?

**Decision:** **Rewrite/retire as a product-framing editorial pass
— not spot-fixes.** `index.md`, `reference/{core,empathy-os,
glossary,llm-toolkit,configuration,config,pattern-library,
TROUBLESHOOTING,cli-reference}.md`, and
`getting-started/choose-your-path.md` describe a superseded product
(5-level empathy maturity model, `EmpathyOS` as "main entry
point", healthcare/HIPAA) with dead/fabricated APIs. Spot-fixing a
version string in a doc slated for rewrite is wasted; the framing
itself is the problem. → spawned follow-up spec
**`legacy-empathy-framework-doc-retirement`**.

### B5 fixes landed this PR

The cheap, unambiguous MECHANICAL fixes + the one high-impact
onboarding REWRITE (`getting-started/first-steps.md`) — full list
in the triage's "FIXED this PR" table. The pitch-doc count/inventory
fiction (Tier 1) and the 2 blog archives also landed here.

---

## Spec closure (2026-06-09)

Stage A (triage artefact) and Stage B (B2 version sweep #715, B3.1
ORCHESTRATION_API #717, B3.2 ORCHESTRATION_USER_GUIDE #718, B4
archive records #716, B6 blog date-classification #719, B5
content-verify + this PR) are complete. The PENDING content-verify
queue is **worked-through and routed**: built docs verified and
either fixed here, confirmed CLEAN, or routed to the two follow-up
specs above; repo-only excluded docs and blog-copy counts formally
deferred (Q4). `mkdocs build --strict` passes. The
docs-completeness-audit spec is therefore **complete** — its job
was to find and triage fiction, which it did; the remaining
remediation is owned by the two spawned follow-up specs, not by
this audit.

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
