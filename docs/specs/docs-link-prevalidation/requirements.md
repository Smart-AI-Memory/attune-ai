# Spec: Catch hallucinated docs cross-references before mkdocs --strict fails

> Every `attune-author generate <feat> --all-kinds` regen produces
> docs files whose body contains LLM-hallucinated cross-reference
> links to non-existent targets. mkdocs `--strict` catches them
> downstream and aborts the docs build, blocking PR CI. The fix
> shouldn't be "tighten the polish prompt" alone — by the time a
> hallucinated link reaches `docs/`, the failure cost is amortized
> across CI runs and contributor confusion. This spec proposes
> catching them at the boundary between attune-author and the
> attune-ai repo BEFORE they land.

**Status:** approved
**Created:** 2026-06-02
**Owner:** —
**Related:**
- CLAUDE.md lesson "attune-author polish-pass hallucinations have
  six distinct shapes" — names the family. Broken cross-references
  are shape #3 (four "See also" cross-references to non-existent
  docs).
- attune-author#27 (upstream umbrella spec) — addresses the
  polish-pass fact-check mechanism at its source. This spec is
  the *consumer-side* defense in attune-ai.
- PR #564 (.help regen 2026-06-02) — surfaced this. Five
  hallucinated links blocked mkdocs `--strict`; required a tactical
  inline fix PR.

---

## Phase 1: Requirements

**Status:** approved

### Problem statement

Each `attune-author generate <feat> --all-kinds` regen produces up
to 4 `docs/<dir>/<feat>.md` files (architecture, how-to, reference,
tutorials). The polish pass tries to make these "well-connected"
by inserting cross-reference links in `## See also` and `## Next
steps` sections. Many of those links point at non-existent docs.

Each affected file has a `## Unresolved references` audit table at
the bottom (attune-author's own fact-check) that *already flags*
the broken links by line number. So the signal is fully present
in the generated file — but nothing in the attune-ai pipeline
reads it. We discover the breakage only when mkdocs `--strict`
fails on CI.

Per PR #564 evidence: 11 features × 4 docs each = up to 44 generated
docs files in a single regen pass. Five had broken body links;
all five were flagged by the audit blocks. The cost of catching
each one at CI: a follow-up commit, a rebase across siblings, and
contributor confusion ("is this PR really broken?"). Multiply by
the regen cadence (~weekly) and the cost compounds.

The right place to catch it is at the boundary between the
attune-author generation step and the commit landing in attune-ai —
before the file lands.

### Scope

**In scope:**

- A validator running as a **pre-commit hook** on `docs/**/*.md`
  (chosen over post-generate runner: catches manual edits too,
  reuses existing pre-commit infrastructure, low integration cost)
  that either:
  - **Reads the `## Unresolved references` audit block** at the
    bottom of each generated file and surfaces the failures
    (preferred — the work is already done; we just need to
    consume it).
  - **OR**: re-runs a lightweight link check independently
    (`mkdocs build --strict` or a stdlib-only equivalent).
- Two modes: **block** (fail commit / fail PR) or **warn**
  (annotate, don't block). v1 ships in **warn** mode for one
  release cycle so we can characterize false positives without
  blocking real work.
- Clear remediation messages: name the file, the broken link,
  the line number, and the suggested fix (remove the link, point
  it elsewhere, or override).

**Out of scope for v1:**

- Other hallucination shapes from the CLAUDE.md lesson (invented
  CLI flags, invented private-module imports, wrong route paths,
  wrong numeric claims, insecure security examples). Each has its
  own detection mechanism; bundling them all into one spec creates
  scope sprawl.
- Fixing the attune-author polish prompt itself — that's
  attune-author#27 territory. This spec is the consumer-side
  defense; both layers should ideally exist.
- AST-based fact-check of code fences (existing attune-author
  feature; we trust it).
- Retroactively fixing already-merged docs with hallucinated
  links — separate housekeeping pass if needed.

### User stories

1. **As Patrick running an `attune-author generate` pass on a PR
   branch**, I want the broken-link failures surfaced AT THE
   GENERATE / COMMIT MOMENT, not after a full CI matrix run, so
   the cost of the LLM hallucination is bounded to the local cycle.
2. **As a contributor opening a PR with regen'd docs**, I want the
   broken-link issues either pre-fixed or pre-flagged with clear
   remediation guidance, so I'm equipped to fix them efficiently —
   even if I didn't introduce them. The contributor on the PR is
   often in the optimum position to fix the problem with full
   context; the validator's job is to surface what to fix, not
   hide it.
3. **As CI on a docs-only PR**, I shouldn't fail on something that
   was preventable at commit time. mkdocs `--strict` becomes the
   safety net, not the primary detection layer.
4. **As a future agent rebasing a stale branch**, I want validation
   that's idempotent and doesn't surprise me on rebase.

### Current behavior (grounded in code)

After `attune-author generate <feat> --all-kinds`:

- `.help/templates/<feat>/*.md` files are written (11 kinds).
- `docs/{architecture,how-to,reference,tutorials}/<feat>.md` files
  are written (up to 4, depending on whether the feature has all
  4 kinds defined).
- Each generated `docs/*.md` file includes a `## Unresolved
  references` audit block at the bottom listing fact-check
  failures: broken links, undefined names in code fences,
  unimportable modules, etc.

No commit-time, no pre-CI, no pre-mkdocs validation reads that
audit block. The signal exists; the consumer is missing.

PR #564 evidence:
- 11 features regen'd × 4 docs each ≈ 44 generated files.
- 5 had broken body links (all flagged by their audit blocks).
- Plus one additional file (`docs/architecture/deep-review.md`)
  with a 6th broken link not surfaced by CI because mkdocs's
  nav-restricted strict check didn't reach it.
- The audit blocks correctly flagged all 6 — including the one
  CI missed.

### Proposed mechanism

Three reasonable shapes to validate at the boundary:

1. **Audit-block consumer** (cheapest):
   - Stdlib-only Python script: `scripts/check_doc_audit_blocks.py`
   - For each `docs/**/*.md`, extract the `## Unresolved references`
     table if present, count `error` rows that flag broken
     markdown links (severity == "error", issue contains
     "target does not exist").
   - If non-zero, print remediation message and exit non-zero (block)
     or exit zero with annotation (warn).
   - Wire into pre-commit hook on the `docs/**/*.md` glob.
   - Wire into a new CI job (`docs-audit-check`) for belt-and-
     suspenders.

2. **Mkdocs pre-flight job**:
   - Add a fast CI job that runs `mkdocs build --strict` BEFORE
     the full test matrix. Cheap (~15s); fails early.
   - Doesn't help local; you only see it once CI runs.

3. **Generate-time validator** (most upstream):
   - Wrap `attune-author generate` so that after it writes the
     files, it scans the audit blocks AND verifies their
     resolvability against the actual docs tree. Refuses to
     write a file with unresolvable links unless `--allow-broken`
     is passed.
   - Requires changes to either attune-author OR a wrapper
     script in attune-ai (`scripts/regen_with_validation.py`).

Recommendation: **(1) + (2) together.** (1) catches the issue
locally at commit time using the existing audit-block signal.
(2) is the safety net at PR time. (3) is the most upstream but
also the most invasive; defer until evidence shows (1)+(2) aren't
enough.

**Locked decision (2026-06-02 approval):** ship (1) + (2) together.
Defer (3) until evidence shows the consumer-side defense alone
isn't catching cases the polish-prompt fix would.

### Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | PR #564 surfaced concrete evidence: 5+1 broken links, all already self-flagged by attune-author audit blocks. |
| **Interfaces** | partial | The audit-block reader needs a precise regex / parser for the table format. Phase 2 design.md locks it. |
| **User-facing behavior** | addressed | Local pre-commit blocks/warns with concrete remediation; CI safety net via mkdocs job. |
| **Edge cases** | partial | What if the audit block is malformed? What about overrides? See below. |
| **Compatibility** | addressed | Additive — pre-commit hook + new CI job. Existing mkdocs builds keep working. |
| **Error handling** | addressed | Pre-commit hook degrades gracefully on parse failure (warn, don't block). |
| **Tradeoffs & alternatives** | addressed | See below. |
| **Rollback** | addressed | Remove the pre-commit hook + CI job. No persisted state. |

### Edge cases & open questions

| Case | Expected |
|------|----------|
| Generated file has no audit block | No-op; the file passes the consumer-side check. mkdocs strict is still the catch-all. |
| Audit block is malformed (corrupt table) | Warn, don't block; fall back to mkdocs |
| Audit block flags a link that resolves (false positive) | Override mechanism — Phase 2 to design |
| Manual edit creates a broken link in a non-generated file | mkdocs strict catches; out of scope for v1 of this spec |
| File has audit block flagging non-link issues only | Pass through (we only fail on link errors) |

**DECIDE-1** — Block vs. warn for v1.
*Recommend:* **warn for one release cycle.** We don't yet know
the false-positive rate of the audit blocks. Ship warn, observe
~2 weeks of real usage, promote to block once confident.

**DECIDE-2** — Override mechanism for known-OK broken links.
*Recommend:* **inline comment override.** A file containing
`<!-- attune-skip-link-check: <reason> -->` near the audit block
gets skipped. Phase 2 specifies the exact format.

**DECIDE-3** — Pre-commit hook vs CI-only.
*Recommend:* **both.** Pre-commit catches it locally before the
PR opens. CI job is the safety net (also catches PRs from
contributors without the hook installed).

### Tradeoffs & alternatives

The polish-prompt fix at attune-author#27 is the root-cause path
and is **necessary but not sufficient** on its own: LLM
hallucination floor is non-zero, attune-author already generates
the audit block (the signal is sitting there unused), and the
consumer verifier is extensible to the other 5 hallucination
shapes from the same family. The right shape is **defense in
depth**: polish-prompt fix reduces the hallucination rate at
source; consumer verifier catches what slips through.

| Option | Pros | Cons | Pick |
|--------|------|------|------|
| **Consumer-side audit-block reader** (this spec) | Cheap; leverages existing fact-check signal; extensible to other hallucination shapes | New script + hook + CI job to maintain | ✅ ship now |
| **Fix the polish prompt at the source** (attune-author#27) | Reduces hallucination rate at root | Slow; LLM hallucination floor is non-zero; doesn't consume the existing audit-block signal | ✅ keep in flight upstream — defense in depth |
| **Make mkdocs --strict run in a faster pre-flight job** | Minimal new code | Doesn't help local; just shifts the failure earlier in CI | △ — already option 2 from "Proposed mechanism" |
| **Accept the status quo** | Zero work | Every regen pass blocks PRs; contributor confusion compounds | ✗ |

### Rollback strategy

Single PR for v1 (after Phase 2 + 3). Rollback = `git revert <merge-commit>`. No persisted state, no migration. Pre-commit hook is opt-in (existing hooks don't enforce); removing the hook removes the local behavior. Removing the CI job removes the PR-level enforcement.

### Testing strategy

- **Unit tests** for the audit-block reader: malformed table,
  empty table, all-resolvable, mix of resolvable + broken, override
  comment.
- **Integration test**: run the script against the actual
  `docs/architecture/deep-review.md` fixture (currently has a
  broken link flagged in its audit block) and assert it reports
  the expected issue.
- **Regression guard**: a fixture file with a known broken link
  + audit block. CI assertion: script catches it; script PASSES
  on the cleaned-up version after manual fix.

### Gaps

None blocking Phase 1 approval. Three DECIDEs have recommended
defaults. Phase 2 (design) locks the exact audit-block parser,
the override comment format, the pre-commit hook config, and the
CI job YAML.

---

## Phase 2: Design — *(not started; awaiting requirements approval)*

## Phase 3: Tasks — *(not started)*
