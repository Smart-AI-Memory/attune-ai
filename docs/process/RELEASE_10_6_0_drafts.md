# Release 10.6.0 drafts — notes + post (pre-tag working copy)

**Written:** 2026-07-20 (rulings-sitting session). **Refreshed:**
2026-07-21 evening-2 (checklist verified against `gh` + the
CHANGELOG; Draft-A confirm-markers resolved). **Tag day:**
2026-07-27 per the Monday runbook (tag-only; prep done in #1526).
Derived from the CHANGELOG `[Unreleased]` section at write time.

**Refresh before tagging** — strike or keep each bracketed line
against what actually merged, and confirm each landing added its
own `[Unreleased]` entry:

- [x] #1529 LessonsFilePublisher — MERGED 2026-07-21. **No
  `[Unreleased]` entry yet — OWED** (see Monday additions below).
- [x] sdk-teardown-exit-guard — #1534 MERGED 2026-07-20; entry
  present (Fixed: "SDK teardown-exit guard now covers every SDK
  workflow").
- [x] post-commit help hook dry-run flip — merged 2026-07-20;
  entry present (Fixed: "Post-commit help hook is now
  check-only").
- [x] #1531 coverage-bar alignment — MERGED 2026-07-20. **No
  `[Unreleased]` entry yet — OWED** (see Monday additions below).
- [x] Overnight four (2026-07-21 antigravity-review arc):
  #1551 friction matrix + gate, #1552 AST context budgeting,
  #1553 ghost simulator, #1554 self-healing traps — `[Unreleased]`
  entries added same-day (this checklist's own confirm pass).
  Draft-A candidate line: **10.6.0 activates two new plugin hooks**
  (`friction_gate`, `trap_stash`) on plugin update — the traps
  spec's D5 caveat names the post-publish organic-fire check.
- [x] Anything else merged into `[Unreleased]` this week — audited
  2026-07-21 evening-2: every post-#1560 merge is internal spec
  bookkeeping (#1564, #1570, #1572), lessons appends (#1565,
  #1573, #1579–#1583), or test-only (#1566, #1575, #1577) — none
  owe standalone entries. #1563's T5 docs repoints fold into the
  consolidation entry held PR #1574 already carries.

**Monday changelog additions — write in the release PR, AFTER the
queue lift.** Held #1574 inserts its own entry at the top of
`### Added`, so any `[Unreleased]` edit before the lift re-dirties
the queue (verified 2026-07-21 evening-2; CHANGELOG.md is
queue-locked until then):

- #1529 graduation clause — append to the self-healing diagnosis
  engine bullet: verified diagnoses graduate into the lessons
  corpus with provenance (`LessonsFilePublisher`, chair-ruled).
- #1531 — one Changed line: codecov patch gate raised 50→80,
  enforcing the documented 80% changed-code floor.
- #1562 (at lift) — weekly freshness report now says 0 stale, not
  27 false positives.
- #1571 (at lift) — tooltip unification complete + CI grep-gate.
- #1576 — only if the chair approves the /memory page revival.

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
than the last.

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
the subprocess crashes during teardown after a successful result;
report-shaped workflows now emit run records; the post-commit help
hook is check-only — it warns about stale docs but never spends
LLM budget on your commits; roundtable citation/convergence
contracts are taught by worked example.

Plus: usage-signals measurement tooling, memory feedback scoring
(step 2), an opt-in auto-merge CI class, platform-neutral
managed-Redis naming, and the codecov patch gate now enforcing the
documented 80% changed-code floor.

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

---

## Draft B-v2 — LinkedIn post, multi-LLM rework (2026-07-22)

Reworked per the launch plan
(`.claude/plans/launch-10-6-0-multi-llm.md`): the release is
**10.6.0** (chair briefly renumbered it 10.7.0 on 07-22, then
reverted to 10.6.0 as originally proposed — chair, 07-22 EOD), the centerpiece is the
multi-LLM story, and the post fires TUESDAY 07-28 with the launch
article (it is the short-form companion; the article carries the
receipts). **Draft B-v1's structural problem is solved by
replacement, not softening:** the new hook is the
roundtable-picked-features story, which is ALREADY receipted (the
promoted report `docs/reports/roundtable/q-multi-llm-obvious-win-001.md`
is on main). The v1 self-healing anecdote is DROPPED from this
post — that story publishes on its own day, when a real diagnosis
receipt exists (v1 gate option (b), preserved below as its own
backlog item).

> Last week I asked three AI models a question: given everything
> this project already has, what's the obviously-best next
> feature?
>
> Claude, Codex, and Google's Antigravity answered independently —
> they can't see each other's replies. Two of the three converged
> on the same feature with nearly identical designs: a real
> handoff between AI coding agents. The full deliberation, every
> seat's position, and my rulings are a tracked report in the
> repo.
>
> So that's what shipped this week in attune-ai 10.6.0:
>
> — Shared memory: a finding captured in one agent is recallable
> in the next (Claude Code, Codex, Antigravity — same tools, no
> sidecar)
> — Handoffs that verify: the receiving agent re-checks the packet
> against the actual git tree before continuing. Context, not
> authority.
> — Second opinions: your real diff, reviewed adversarially by a
> different vendor's model. Advisory by spec — a public dogfood
> ledger is the only thing that can ever promote it.
>
> Every boundary claim above carries a dated transcript in the
> repo. The ones we couldn't prove yet are marked UNPROBED — in
> public. That discipline already caught a real bug this week:
> a PII scrubber that a thousand mocked tests swore was on, and
> one live canary proved was off.
>
> The models deliberate; I decide. Free and open source,
> Apache 2.0: `pip install attune-ai`
>
> Full story with the transcripts: https://www.linkedin.com/posts/patrick-roebuck-attune-ai_this-article-talk-about-the-multi-llm-memory-activity-7487899197329993729-pGPN

### Honesty checklist on Draft B-v2 (chair rules at post time)

- [x] Roundtable-convergence hook — TRUE and receipted now
      (report merged to main 2026-07-22; thread
      `q-multi-llm-obvious-win-001`).
- [x] PII-scrubber story — TRUE and receipted (transport spec
      decisions.md + receipts.md, CR-2 live canary; ~1,600 mocked
      tests figure verified against the T2 session record — say
      "a thousand" only if the exact count stays unverified at
      post time).
- [x] "Shared memory … recallable in the next" — CLEARED
      2026-07-28. Transport receipt 4 PASSED live 2026-07-27
      (interactive Codex, plugin 10.6.0): capture → recall of the
      stored representation → forget `deleted:1` → empty re-recall.
- [x] "Handoffs that verify" — **CLEARED 2026-07-28 09:47 EDT.** Closed
      for real per the chair ruling; the reword fallback was not
      needed. Live Antigravity session returned `ok:true` with
      `head_moved` + `files_diverged` — the receiving agent re-checked
      the packet against the real tree and reported drift before doing
      any work. Receiving agent is Antigravity rather than Codex
      (headless approval auto-cancels); both are different vendors, so
      the post's "Claude Code, Codex, Antigravity — same tools" line
      still holds on its own receipts. Full transcript + the stale-
      instruction correction: handoff spec `receipts.md`, R6.
      Superseded detail: The
      Claude side is a live PASS (`handoff_create` through the real MCP
      server at 10.6.1, git-derived `head_sha`), and Codex dispatch
      is PROVEN (`handoff_resume` in its tool list, dispatch
      started) — but codex's headless approval policy auto-cancelled
      the call, so **no receiving-agent drift report exists**. Take
      this line's pre-authorized reword-to-per-agent-truth path, or
      close it with one interactive Codex run. Same ruling as the
      article's 4th receipt slot — decide both together.
- [x] "10.6.0 … shipped this week" — CLEARED 2026-07-28. Tags
      `v10.6.0` and `v10.6.1` exist; both return PyPI 200; latest
      = 10.6.1.
- [x] Antigravity named as a memory participant — CLEARED
      2026-07-28. Transport receipt 6 PASSED live 2026-07-27 against
      PyPI 10.6.1 (`agy --print`, four legs clean, PII redacted at
      rest from the Antigravity seat). No reword needed.
- [x] [LINK: launch article] filled with the published URL
      (2026-07-28). Article is LIVE; the post body above now carries
      the real link. **Every item on this checklist is now closed.**
- [x] v1 anecdote removed — nothing in v2 claims a self-healing
      diagnosis occurred.

### Backlogged from v1 (do not lose)

The self-healing-loop story (v1's hook) publishes as its OWN post
when a real operational failure has been diagnosed end-to-end —
v1 gate option (b). Candidate trigger: the first real failed run
around Monday's live fire. The v1 text above stays as its draft.
