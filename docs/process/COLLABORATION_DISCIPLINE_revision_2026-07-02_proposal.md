# Discipline Article — Revision Proposal (progress through 2026-07-02)

**Status:** APPROVED & APPLIED — Patrick approved C1–C9 item-by-item
on 2026-07-02 (F2 resolved as option 1: 134, retrospective-UTC
convention). All nine changes applied to the article source and
`index.html` rebuilt (Draft v5) in the same-day PR. Publishing to
smartaimemory.com/discipline remains Patrick's step. C4 placed as
the closing beat of C3's block (editorial call, flagged at apply
time).

**Target file:**
`~/attune-ai/attune-ai-dev/discipline/COLLABORATION_DISCIPLINE.md`
(9,869 words today; rebuild via `attune-ai-dev/build_discipline.py`
after approved edits land).

**Standing refinements honored** (per
`project_discipline_article_revisions`): autonomous contract stays
inside §2 (already there — untouched); the generative frame stays
frame-not-section (C6 sharpens the existing closing paragraph, adds
no section); every new line is taught tool-agnostic —
pattern + why + one example — with attune-ai as the receipt, not the
gate. Each change carries a transferability note.

**Receipt legend:**

- **[R-A]** Communication grammar live — decision / pushback /
  progress constructs shipped (`communication-grammar.md`); pushback
  form changed the hook-interpreter pin
  (curated-memory-productionization D5, 2026-07-02); review form
  carried the first human memory review, 6 keep / 1 sharper / 0 wrong
  (requirements.md:15).
- **[R-B]** Memory loop closed — two-layer protocol ratified (D6);
  git-versioned curated graph with provenance; SessionStart Redis
  hydration live (D5 receipts: hook registered, 7 nodes, warm FCALL
  128µs, exit 0).
- **[R-C]** Recursion receipt — the D6 protocol decision recorded as
  a memory node governed by that protocol; the pushback construct
  (D5) fixed the hydration infrastructure that loads the memory the
  constructs render from. Patrick's frame: "synergies tied to the
  discipline."
- **[R-D]** Velocity re-measured 2026-07-02 (verification commands
  in Appendix): **277 merged PRs in the 14 calendar days 2026-06-19 →
  2026-07-02 (~19.8/day)**; composition: docs 128, feat 49, chore 30,
  fix 25, test 17, ci 8, release 7, spec 7, refactor 3, build 1,
  other 2 → **feat+fix = 74 (~5.3/day)**.
- **[R-E]** The 9.3.0 → 9.4.0 recall story — 9.3.0 shipped with the
  personal-memory round-trip broken (capture ok, recall empty;
  `RagPipeline.run()` result-shape misread) while all unit tests were
  green; caught by the three-ring audit's clean-venv + fake-HOME
  probe of the SHIPPED wheel; fixed in #1208, shipped as 9.4.0
  (tag `v9.4.0`, wheel uploaded 2026-07-02T16:09:51Z, publish run
  28604412725); closure receipted the same way (fresh 9.4.0 install,
  recall returns the captured content). Source: `release_state`
  memory + PyPI + git tag.

---

## Verification flags — resolutions (updated after Patrick's review)

- **F1 — RESOLVED: 9.4.0 IS on PyPI.** My first check hit a stale
  cached response from PyPI's package-level JSON endpoint
  (`info.version` said 9.3.0). Authoritative re-checks confirm the
  release: `attune_ai-9.4.0-py3-none-any.whl` uploaded
  2026-07-02T16:09:51Z (version-specific endpoint + simple index),
  tag `v9.4.0` on origin at `3b345e01b`, publish run 28604412725
  success ("release: 9.4.0 — restore personal-memory recall
  (#1215)"). C5 now cites the release; C9 (new) tells its
  verification story. *Meta-lesson recorded: verify a release via
  the version-specific endpoint / simple index, not the cached
  package-level JSON.*
- **F2 — EXPLAINED; decision pending (see chat).** The original
  "130" was counted *on* 2026-06-02 while the window's final day was
  still running; four PRs (#575–#578) merged 17:52–19:57 UTC later
  that day, inside the window. A retrospective full-day UTC count is
  **134**. Recommendation: adopt the convention "windows are counted
  retrospectively in UTC calendar days," update the old figure to
  134. (An ET-boundary convention would give 139 old / 277 fresh —
  the fresh window is identical under both.)
- **F3 — RESOLVED by receipts; artifact regeneration spun off.**
  The "three-ring audit" is the 2026-07-02 **memory-system** audit
  (three rings: harness auto-memory / attune curated+personal
  memory / Redis short-term). The artifact file
  (`memory-three-rings`) did not persist, but the audit is
  receipted three ways: its backlog items live in
  `~/.attune/next_session_starter.md` (#4); its headline finding —
  clean-venv probe of the shipped wheel caught 9.3.0's broken
  personal-memory recall — is recorded in the `release_state`
  memory and became 9.4.0's headline fix; and the curated-graph
  feedback node of 2026-07-02 cites it. C5 cites the audit;
  regenerating the artifact itself is queued as a separate
  background task.
- **F4 — RESOLVED: expansion endorsed.** Patrick: the article is a
  core teaching artifact — for the agent and the user — and feeds a
  planned book on development with AI, with portions designed to be
  read by a developer and their AI together or separately. The
  9.5k target is lifted; the 12k hard cap stays as the readability
  guard. Net effect with C9 added ≈ **+700 words** → ~10.6k.
  (Book context persisted to the `project_discipline_article_revisions`
  memory.)

---

## C1 — §2: the decision-point surface has grown into a grammar

**Location:** §2, the "ask one question at a time" paragraph
(source lines ~180–189).
**Type:** replace (last ~2 sentences of the paragraph) + extend.
**Receipt:** [R-A]. **Net:** ≈ +150 words.

**Before (current tail of the paragraph):**

> …use a structured decision-point surface (AskUserQuestion in our
> tooling) as the default form. Number the options A/B/C, label A as
> Recommended where applicable, keep alternatives short. This is
> mechanical — not deep — but mechanical things compound.

**After (draft):**

> …use a structured decision-point surface as the default form.
> Number the options, label the recommendation, keep alternatives
> short. This is mechanical — not deep — but mechanical things
> compound.
>
> The surface for those questions matures with the collaboration. It
> starts as a numbered list in chat. It can grow into a small
> *grammar* of rendered forms, one shape per kind of fork: a
> **decision** form (the recommended option with its rationale and
> per-option tradeoffs — pick one), a **pushback** form (the human's
> stated approach and the agent's alternative side by side, under a
> "why I'd push back" — overrule or switch with one pick), a
> **progress** form (done, in-flight, and blocked items, with the
> blocked ones as the picker for "which do we tackle?"). The shapes
> matter less than the property they share: the fork is *rendered*,
> with the recommendation and tradeoffs visible at the moment of
> choice, and the answer collapses to one pick instead of a
> paragraph. Any tooling that can put a structured choice in front
> of a human can do this; ours renders them as forms in the chat
> surface. This is the contract's decision points getting a surface
> of their own.

**Transferability note:** pattern (render the fork) + why (answer
collapses to a pick; disagreement gets a first-class shape) + one
example each. No attune-specific API named; "ours renders them as
forms" is the receipt clause.

---

## C2 — §2: the pushback receipt (a form changed an infrastructure decision)

**Location:** §2, the pushback paragraph ("The contract above is
fully compatible with the agent disagreeing…", source lines
~244–252).
**Type:** additive (append to the paragraph).
**Receipt:** [R-A] (D5, 2026-07-02). **Net:** ≈ +85 words.

**After (draft, appended):**

> This stopped being hypothetical the day a pushback form changed a
> real infrastructure decision. The human had pinned a session-start
> hook to the development environment's interpreter; the agent's
> form showed why that pin would rot silently (the dev environment
> gets rebuilt routinely, and the dependency the hook needs isn't in
> its default set) and offered a dedicated, non-churning interpreter
> instead. The human read the rendered disagreement and switched.
> One form, one pick, one infrastructure decision corrected before
> it could fail silently.

**Transferability note:** the mechanism described (a pin to a
mutable environment rots) is a general ops lesson; no attune paths
named.

---

## C3 — §5: the two-layer memory protocol (the substantive upgrade)

**Location:** §5, insert after the "Anti-saves" paragraph (source
line ~606), before "Proactive persistence…".
**Type:** additive block.
**Receipt:** [R-B] (D6 ratified 2026-07-02; review verdicts
6/1/0). **Net:** ≈ +230 words.

**After (draft):**

> The three classes sort *what* to save. A second cut sorts *where*
> — and it earns its own rule because the two destinations fail in
> opposite ways. **Durable memory** holds only what passes a
> thirty-day test: will this still be true, and worth carrying, in a
> month? Preferences, validated approaches, decisions with their
> reasons. **Operational handoff** holds the short-term state one
> session leaves for the next: in-flight PRs, open threads, standing
> authorizations. Keep them separate, because they need opposite
> truth-maintenance regimes. Stale operational memory is *worse than
> none* — a stale "merge PR X" causes a wrong action — so its regime
> is machine verification against ground truth (the git log, the PR
> tracker, the package index) at load time, every time. Stale
> durable memory fails *softly* — a preference drifts out of date —
> so its regime is human review over time: periodic verdicts of
> keep, wrong, or needs-sharpening. Merge the two layers and you
> break both: the review loop drowns in expiring churn, and
> operational truth ends up policed by a mechanism too slow for it.
>
> In our setup this loop is now closed end-to-end: the durable layer
> is a git-versioned graph of curated nodes, each with provenance;
> sessions hydrate it into a fast store at startup; the handoff
> layer is machine-reconciled against git and the package index at
> session start; and the first human review pass returned its
> verdicts through a rendered form — six keeps, one sharpened, zero
> wrong.

**Transferability note:** the thirty-day test and the two-regime
argument are adoptable with plain files + any agent; the receipt
sentence is clearly marked "in our setup."

---

## C4 — §5: the continuity asymmetry, scaffolded not aspirational

**Location:** §5, append to the stale-memory discussion (after the
"memories that snapshot state" paragraph, source line ~660) or as
the new closing beat of C3 — your pick.
**Type:** additive.
**Receipt:** [R-B]. **Net:** ≈ +65 words.

**After (draft):**

> This layer is also the honest answer to the deepest asymmetry in
> §2 — one party cannot natively remember past sessions. The
> asymmetry doesn't disappear; it gets scaffolded. And the
> scaffolding has a property human memory never has: what the agent
> knows at minute zero of a session is a curated, reviewed,
> versioned artifact — inspectable, diffable, and correctable by
> the review loop above.

**Transferability note:** general claim about version-controlled
memory; no tooling named.

---

## C5 — §8: a one-day composition sentence (2026-07-02)

**Location:** §8, insert immediately before the velocity paragraph
("And that morning wasn't a one-off…", source line ~1103).
**Type:** additive.
**Receipt:** [R-A] + [R-B] + [R-E]; F1 and F3 resolved — the release
and the audit are now both receipted and cited.
**Net:** ≈ +75 words.

**After (draft, revised after F1/F3 resolution):**

> A single ordinary day near this revision (2026-07-02) shows the
> mix: a full human review pass over the durable memory layer,
> verdicts returned through a rendered form; a cross-layer memory
> protocol ratified and recorded the same day — as a memory node,
> governed by the protocol it records; an audit of the memory
> system's three rings that turned a vague "recall feels off" into
> a broken-round-trip receipt; and a release to PyPI carrying the
> fix that receipt demanded. None of it a crunch. That is what a
> compounding day looks like.

---

## C6 — §8: the velocity paragraph, re-measured

**Location:** §8, the "And that morning wasn't a one-off" paragraph
(source lines ~1103–1113).
**Type:** replace (whole paragraph).
**Receipt:** [R-D]. **Net:** ≈ +40 words.

**Before (current):**

> And that morning wasn't a one-off. Across the two weeks ending
> 2026-06-02, the same one-developer-plus-agent setup merged **130
> pull requests — roughly nine per calendar day** — into the
> attune-ai repository. The composition matters more than the
> headline: about fifty were feature and fix code; the rest were
> documentation, specs, and release work the discipline keeps moving
> in lockstep with the code. …

**After (draft):**

> And that morning wasn't a one-off — and the pace has *risen* as
> the disciplines compounded. Across the two weeks ending
> 2026-06-02, this one-developer-plus-agent setup merged 134
> pull requests into the attune-ai repository — roughly ten per
> calendar day. Across the two weeks ending 2026-07-02, the same
> setup merged **277 — roughly twenty per calendar day**. The
> composition matters more than the headline: 74 of the 277 were
> feature and fix code (about five a day); the rest were
> documentation, tests, specs, and release work the discipline keeps
> moving in lockstep with the code. That lockstep is the point —
> §5's memory and §4's artifacts mean the docs and specs *keep pace*
> rather than accruing as debt behind the shipping. These are dated
> snapshots of what the discipline produced here, not a multiplier
> anyone is promised — and they are re-measured every time this
> article is revised, because §7 applies to the article too.

**Notes:** honest-denominator rule kept (calendar days, composition
stated). Uses **134** per the F2 recommendation (retrospective UTC
calendar-day convention) — pending your F2 ruling; reverts to
"130-odd" if you prefer keeping the as-measured figure.

---

## C7 — §7: one cross-link sentence (verification now polices memory)

**Location:** §7, "What holds the four together" section, append
after "…where it belongs." (source line ~967).
**Type:** additive (one sentence). **Optional** — cut first if F4
(word budget) worries you.
**Receipt:** [R-B]. **Net:** ≈ +35 words.

**After (draft):**

> The same split now polices memory (§5): machine reconciliation
> verifies the operational layer against ground truth at every
> session start, and human review verdicts verify the durable layer
> over time — each layer checked by the mechanism matched to how it
> fails.

---

## C8 — closing: the recursion receipt (generative frame, sharpened)

**Location:** the closing "There is a tell…" paragraph (source
lines ~1124–1132).
**Type:** replace (whole paragraph).
**Receipt:** [R-C]. **Net:** ≈ +55 words.

**Before (current):**

> There is a tell in how this article got written. The attune-\*
> family is these disciplines turned into software — attune-ai
> builds and maintains the others — and the disciplines, once named,
> keep generating the next thing. Drafting this piece surfaced a
> friction none of the six quite covered; naming it produced a new
> spec by the end of the session. The discipline didn't only
> describe the work. It generated more of it. That is the synergy —
> tied to the discipline itself, not to any one tool.

**After (draft):**

> There is a tell in how this system evolves. The attune-\* family
> is these disciplines turned into software — attune-ai builds and
> maintains the others — and the loop has begun closing on itself.
> The rule that governs what durable memory may hold was itself
> recorded as a durable memory node, governed by the rule it states.
> The form that renders the agent's disagreement was used to fix the
> infrastructure that loads the memory the forms render from.
> Drafting an earlier revision of this piece surfaced a friction
> none of the six disciplines quite covered; naming it produced a
> new spec by the end of that session. The discipline doesn't only
> describe the work. It constrains and improves its own
> construction. That is the synergy — tied to the discipline itself,
> not to any one tool.

**Notes:** keeps Patrick's payoff phrase verbatim; upgrades the
2026-06-02 instance (article-generates-spec) with the two 2026-07-02
instances (protocol-node-governed-by-protocol;
pushback-fixes-pushback's-infrastructure) without adding a section —
frame, not volume, per refinement 2.

---

## C9 — §7: the shipped-wheel dogfood receipt (NEW, added after F1/F3 resolution)

**Location:** §7, "Verifying behavior" section, insert after "Both
are needed; neither replaces the other." (source line ~922), before
the regression-guard sentence.
**Type:** additive.
**Receipt:** [R-E]. **Net:** ≈ +140 words.

**After (draft):**

> The sharpest recent receipt of the gap: a release shipped with its
> memory-recall round-trip broken — capture succeeded, recall
> returned nothing — and every unit test was green, because the
> tests mocked the exact layer that was broken. What caught it was
> not a test run but a dogfood probe of the *shipped artifact* in a
> clean environment with a fresh home directory: install exactly
> what a user installs, run exactly what a user runs. The probe
> turned an opinion ("recall feels off") into a receipt (recall *is*
> broken, with the trace), the fix became the next release's
> headline, and the closure was verified the same way — fresh
> install of the fixed release, recall returns the captured content.
> Green CI never saw any of it, coming or going. Dogfood the
> artifact you actually ship, not the code you happen to have
> checked out.

**Transferability note:** pattern (probe the shipped artifact in a
clean environment) + why (tests share the code's mocks and
blind spots) + one example (the recall round-trip). Tool-agnostic —
no package names or versions in the article text; the receipt
metadata lives here in the proposal.

---

## Explicitly NOT proposed

- **No §1 changes.** The synergies frame is already in §1 (lines
  39–43); the roadmap bullets still describe their sections
  accurately. Touching §1 adds words without new truth.
- **No §3, §4, §6 changes.** No new receipts land there; the
  autonomous contract (refinement 1) already lives in §2.
- **No new section.** The recursion material goes into the existing
  closing paragraph (C8), per the frame-not-section decision.

## Application path (after your approvals — separate step, not done)

1. Apply approved items to
   `attune-ai-dev/discipline/COLLABORATION_DISCIPLINE.md` (lives in
   the MAIN checkout, not this worktree).
2. `python attune-ai-dev/build_discipline.py` to regenerate
   `index.html`.
3. You publish to smartaimemory.com/discipline (outside any repo,
   per the revision memory — your step).
4. Post-publish: update `project_discipline_article_revisions`
   memory with the new velocity snapshot and mark the 2026-06-02
   snapshot superseded.

## Appendix — verification commands (receipts for the receipts)

- PR windows: `gh pr list --state merged --limit 1000 --json
  number,title,mergedAt` filtered by `mergedAt` date; 2026-06-19 →
  2026-07-02 inclusive = 14 calendar days, 277 PRs; composition by
  conventional-commit prefix of PR titles (counts in [R-D] above).
- PyPI: `curl https://pypi.org/pypi/attune-ai/9.4.0/json` → 2 files,
  uploaded 2026-07-02T16:09:51Z; simple index lists
  `attune_ai-9.4.0-py3-none-any.whl`; `git ls-remote --tags origin`
  → `v9.4.0` at `3b345e01b`; publish run 28604412725 success. ✓
  (The package-level `/pypi/attune-ai/json` served a stale cached
  9.3.0 — do not trust it at release gates.) `attune-verify` 0.2.1 —
  the §7 claim that it ships stands. ✓
- Review verdicts:
  `docs/specs/curated-memory-productionization/requirements.md:15`
  ("6 keep / 1 sharper / 0 wrong"). ✓
- Pushback-changed-the-pin: same spec's `decisions.md` D5 ("decided
  2026-07-02, via pushback form"). ✓
- Hydration live: D5 R1 receipts (hook registered, 7 nodes, warm
  FCALL 128µs) + this very session's startup line: "hydrated 9
  nodes, 7 edges into attune:memory:*". ✓
