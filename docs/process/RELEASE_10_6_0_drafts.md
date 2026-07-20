# Release 10.6.0 drafts — notes + post (pre-tag working copy)

**Written:** 2026-07-20 (rulings-sitting session). **Tag day:**
2026-07-27 per the Monday runbook (tag-only; prep done in #1526).
Derived from the CHANGELOG `[Unreleased]` section at write time.

**Refresh before tagging** — strike or keep each bracketed line
against what actually merged, and confirm each landing added its
own `[Unreleased]` entry:

- [ ] #1529 LessonsFilePublisher (chip session; graduation writes)
- [ ] sdk-teardown-exit-guard implementation (chip session)
- [ ] post-commit help hook dry-run flip (chip session)
- [ ] #1531 coverage-bar alignment (patch gate 50→80)
- [ ] Anything else merged into `[Unreleased]` this week

---

## Draft A — GitHub release notes

### attune-ai 10.6.0 — the self-healing loop closes

When a workflow fails, attune can now tell you **why** — and what
it learned.

`attune diagnose <run_id>` convenes a multi-model panel (Claude,
Antigravity, Codex) over the failed run's evidence — recalled
priors, a bounded evidence pack — and hands you ranked root-cause
hypotheses. On the ops dashboard it's one click: **"Why did this
fail?"** on any failed run. A propose-only fix loop and a manual
triage command close the loop, and every fix is chair-ruled —
nothing auto-applies. Verified diagnoses can graduate into the
lessons corpus with provenance, so the next failure starts smarter
than the last. *[graduation publisher: confirm #1529 merged]*

The loop stands on three new foundations shipped in the same
window:

- **Multi-LLM round table** — `/roundtable` convenes three models
  to deliberate a question on a Redis-backed board with receipts;
  you chair what gets promoted. V2 adds the artifact compiler,
  proposal ledger, solution materializer, seat rotation, and
  headless routines.
- **Cross-provider collaboration contract** — a projector-owned
  contract (`AGENTS.md` + `.agents/` mirrors, read-only preflight,
  shared Redis memory index) teaches any agent — Claude Code,
  Codex, Antigravity — to work this repo safely.
- **Canonical run-record corpus** — every workflow run lands one
  provenance-stamped record; the readiness-gated pipeline learner
  mines it for suggestions and never touches an unready corpus.

**Honesty infrastructure, applied to ourselves:** three
claim-drift CI gates (count-and-claim, advertised-command
validation, brand drift) each landed red on real drift before
turning green; spec-lifecycle statuses come from one enforced
vocabulary; a starter-lint hook flags stale session handoffs.

**Reliability:** SDK workflow results are no longer discarded when
the subprocess crashes during teardown after a successful result
*[confirm guard PR merged]*; report-shaped workflows now emit run
records; the post-commit help hook is check-only — it warns about
stale docs but never spends LLM budget on your commits *[confirm
flip PR merged]*; roundtable citation/convergence contracts are
taught by worked example.

Plus: usage-signals measurement tooling, memory feedback scoring
(step 2), an opt-in auto-merge CI class, platform-neutral
managed-Redis naming, and the codecov patch gate now enforcing the
documented 80% changed-code floor *[confirm #1531]*.

Full details in the [CHANGELOG](../../CHANGELOG.md).

---

## Draft B — LinkedIn post

> A workflow failed in my project this morning. Instead of me
> spelunking through logs, I clicked "Why did this fail?"
>
> Three different AI models — Claude, Codex, and Google's
> Antigravity — independently read the run's evidence and came
> back with ranked root-cause hypotheses. They agreed on the
> cause. The fix was proposed, I approved it, and the diagnosis
> became a permanent lesson in the project's memory — so the
> *next* failure starts from what this one taught.
>
> That's the headline of attune-ai 10.6.0: the self-healing loop
> is closed. Failed run → multi-model diagnosis → chair-approved
> fix → verified lesson → corpus. No step auto-applies; I rule on
> everything. The models deliberate; I decide.
>
> Under it: a round table where three LLMs debate with receipts, a
> collaboration contract that lets any provider's agent work the
> repo safely, and a run-record corpus the whole loop learns from.
>
> Free and open source, Apache 2.0: `pip install attune-ai`

### Honesty gate on Draft B (chair-flagged 2026-07-20, unresolved)

The opening anecdote is **plausible but not yet true** — as of
2026-07-20 the diagnosis stream holds only ship-day artifacts; no
real operational failure has been diagnosed. Options:

- (a) soften the opening to "Here's what happens when a workflow
  fails now" — publishable immediately;
- (b) **hold the post until a real diagnosis exists** (this week's
  first real failed run, or one surfaced around Monday's live
  fire), making the anecdote literally true with a receipt.

Lean (b): the claim-grounding memory
(`memory_cost_claim_grounding`) and the receipts-over-claims
discipline both argue for waiting until the story is a receipt.
Chair decides at post time; do not publish Draft B as-is without
resolving this gate.
