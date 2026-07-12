# Product Direction Review — Third Assessment

**Status:** assessment (2026-07-12) — outstanding-work ledger current
**Owner:** Patrick (+ agent)
**Type:** strategic assessment / decision record (not a build spec)
**Trigger:** Patrick asked for an updated version of the report,
one day after [assessment-2026-07-11.md](assessment-2026-07-11.md)
and after the weekend-plan execution session closed all 9 DECs.
**Method:** identical to the first two — every number re-measured
from the repo itself (worktree at `origin/main`, 5b5c17cf6); same
sources where possible, noted where not. Scope extended one level:
the `attune` umbrella workspace (`~/attune`) is now measured too,
since the scaffolding findings span both repos.

---

## Verdict

For the first time in this review's history, the loop closed. The
July 11 report predicted it would meet the June report's fate —
"translated into build work, decisions silently dropped" — and that
prediction was falsified within 24 hours: all nine DECs are recorded
with dates, the five setup frictions found by conversation 1 are
fixed and shipped (v10.4.0), the inbound channel is live and linked
from every setup-error path, root hygiene is done, and the release
freeze starts tomorrow. N1 (the review loop doesn't close) is
**resolved as of this writing** — with the caveat that it closed
under a forcing mechanism (the weekend plan) and must survive
without one.

What remains is no longer a findings problem; it is an execution
ledger with a sharp shape: **every open item that matters is either
(a) an action only Patrick can take outside the repo, or (b) an
observation window that must be left undisturbed.** The repo itself
is, for the first time since June, not the bottleneck. The danger
inverts accordingly: the failure mode to watch for over the next two
weeks is not neglect but *relapse* — filling the freeze window with
new build work because waiting is uncomfortable.

---

## Evidence (ground truth, three measurements)

| Metric | 2026-06-17 | 2026-07-11 | 2026-07-12 | Source |
|--------|-----------|-----------|-----------|--------|
| Product code (`.py`) | 183,768 / 712 files | 169,169 / 652 | 169,355 / 652 | `find src/attune -name "*.py" \| xargs cat \| wc -l` |
| Test code (`.py`) | 349,399 / 968 files | 327,136 / 980 | 327,806 / 983 | same, `tests/` |
| `test_` functions | ~20,160 | 20,393 | 20,441 | `grep -rE "def test_"` |
| Test-to-product ratio | 1.9 : 1 | 1.93 : 1 | 1.94 : 1 | derived |
| Commits since 06-17 | — | 487 | 505 (+18 in 1 day) | `git log --since` |
| Last 200: `feat` | 27 (13.5%) | 38 (19%) | 35 (17.5%) | `git log -200 --format=%s` |
| Last 200: chore+docs+test+ci | 148 (74%) | 129 (64.5%) | 134 (67%) | same |
| CI/hang/flake/runner, last 200 | ~18% | ~4% | 4 (2%) | grep over subjects |
| Spec directories (incl. archive dir) | 49 | 60 | 57 | `ls -d docs/specs/*/` |
| Archived spec dirs | — | — | 71 | `ls docs/specs/archive/` |
| `lessons.md` | 9,356 | 14,560 | 14,577 | `wc -l` |
| CI workflows | 22 | 26 | 26 | `ls .github/workflows` |
| Docs `.md` files | ~500 | 693 | 694 | `find docs -name "*.md"` |
| Scripts | 108 | 120 | 119 | `ls scripts` |
| Dependency lines (pyproject) | 311 | ~402 | 339 (36 core + 303 opt) | `awk` over dep sections |
| Version | 8.5.0 | 10.3.0 | 10.4.0 | pyproject |
| Release tags since 06-17 | — | 16 | 29 (of 32 tags; 3 archive) | `git tag --sort=creatordate` |
| Root entries | ~80 | ~80 | 65 | `ls \| wc -l` |
| Worktree bloat | — | 2.4 GB | 780 MB | `du -sh .claude/worktrees` |
| attune-ai downloads/week | 636 | 2,316 | 2,063 | usage-signals snapshot 07-12 |
| attune-rag downloads/month | — | — | **27,410** | same (see N5) |
| User conversations (DEC-2) | 0 | 1 of 5 | 1 of 5 | user-conversations.md |
| DECs recorded | 0 of 5 | 0 of 5 | **9 of 9** | assessment files |
| umbrella `attune` spec dirs | — | — | 28 | `ls -d ~/attune/specs/*/` |
| umbrella commits, last 30d | — | — | 35 | `git log --since` |

One-day deltas are noise except where a PR landed; the table's value
is the three-point trend. Notable trend reversals since 07-11:
dependency lines **down** 402→339 (first contraction on record),
spec directories **down** 60→57 (archive absorbed more than were
created), root entries 80→65, worktrees 2.4 GB→780 MB.

---

## Prior findings — status audit

### F1 — Demand hypothesis untested *(existential)* → **OPEN, now instrumented**

Still 1 of 5 conversations. But the situation differs from both
prior reports: conversation 1's finding (setup friction) was acted
on end-to-end within 48 hours — five frictions fixed (#1318),
shipped live in v10.4.0, and the zero-contact inbound channel
(Discussion #1325) is linked from the README, the CLI welcome
screen, and all three setup-error paths (#1326). The demand question
is still unanswered, but for the first time there is a door users
can walk through unprompted, placed exactly where a frustrated user
stands. Four conversations remain. The June bar stands unchanged: if
they cannot be found, that is the finding.

### F2 — Test suite guards the wrong thing → **PARTIAL, proof-point closed**

The original proof — the SDK 0.2 migration stuck behind 17,857
mocked-green tests — is resolved: `claude-agent-sdk` 0.2.x shipped
in 8.7.0 (pin 0.2.105) and the spec directory is gone. Structure
remains: 20,441 tests, ratio 1.94:1 and still creeping. DEC-4's
gate-freeze is satisfied trivially — `codecov.yml` (80% project /
50% patch) hasn't changed since February; the ratchet was
behavioral, not config. Watch item: +48 test functions in 24 hours
of housekeeping PRs suggests the reflex persists even post-DEC-4.

### F3 — Scaffolding outweighs product → **IMPROVED, first contraction**

Spec dirs down net 3 (archive grew to 71 — pruning, not growth).
Dependencies down 63 lines. Root cleaned (DEC-9, #1322). Scripts
down 1. Lessons grew only +17 lines in the day. Against that: the
scaffolding metric now needs two repos — the umbrella workspace
holds 28 more spec directories and its own audit CI. Combined open
spec surface is ~85 directories for a product with one confirmed
user conversation. The freeze (DEC-1, through 07-26) is the test:
if spec count still contracts by 07-27, F3 downgrades to managed.

### F4 — Identity blurred across packages → **UNCHANGED**

`packages/` now holds four (attune-author, -help, -rag, and the
attune-verify stub); `attune-ai-dev` sits at root;
`attune-author-consolidation` remains a draft spec (2026-06-30),
not a done one. Nothing widened this day, nothing consolidated.
DEC-3 chose Memory as the pillar; the package surface has not yet
been made to reflect that choice.

### F5 — Major-version inflation → **FREEZE PENDING**

v10.4.0 (07-11) was the declared "one more release" before the
freeze. 29 release tags since 06-17 — one per 0.9 days. The freeze
(07-13 → 07-27) is the corrective and the experiment at once.

### F6 — CI firefighting → **RESOLVED (holding)**

2% of last-200 commits. Third consecutive measurement at or below
4%. Closed and holding.

### N1 — The review loop doesn't close → **RESOLVED (this cycle)**

The 07-11 report predicted this assessment would be converted into
a spec and shelved. Instead: 9 of 9 DECs dated and recorded
(#1323), the weekend plan's five required blocks all executed in
one session, and the scorecard filled the same night. The
prediction was wrong, and the reason is instructive — the weekend
plan was *non-repo-shaped work expressed as a repo artifact with a
scorecard*, which let the decision-and-outreach dialect compile to
something the repo's habits could execute. Keep that pattern: it is
the only forcing mechanism observed to work here.

### N2 — Machine outspends observable value → **DECIDED, not yet enforced**

DEC-8 set the cap ($350/mo) and #1331 shipped the gate — but the
gate **fails open today**: `ANTHROPIC_ADMIN_API_KEY` is not in the
repo's secrets (verified live via `gh api`; only
`ADMIN_MERGE_TOKEN`, `ANTHROPIC_API_KEY`, `CODECOV_TOKEN` exist).
Protection is zero until the secret lands. The refund dispute with
Anthropic (root cause of the ~$1,700 figure) remains unresolved;
N2's causal narrative stays provisional.

### N3 — Release cadence manufacturing evidence → **EXPERIMENT ARMED**

Freeze starts 2026-07-13. The observable: the download badges over
a 14-day no-tag window. The 07-12 snapshot (#1327) is the baseline.
This only produces data if (a) no tags ship, and (b) snapshots keep
being taken, and (c) someone writes the interpretation on 07-27.
See ledger item 4.

### N4 — Root hygiene → **RESOLVED**

#1322: ACKNOWLEDG(E)MENTS merged, MagicMock/ and six stale root
test scripts gone, worktrees pruned 2.4 GB→780 MB, root 80→65
entries. Done as specified, inside the half-day box.

---

## New findings

### N5 — attune-rag's download number is a louder version of F1's trap

The 07-12 snapshot shows attune-rag at **27,410 downloads/month** —
5× attune-ai's 5,501 — with no interpretation recorded anywhere in
usage-signals. attune-rag has no announcement, no README badge
prominence, and no known users; a 27k figure for a sub-package is
almost certainly mirror/bot amplification, and it is exactly the
kind of number that will get quoted as traction if it sits
uninterpreted. One paragraph in usage-signals' decisions.md — "this
number is noise until shown otherwise" — inoculates it. (The D1
finding predicted this artifact for attune-ai; the sub-packages
inherited the trap.)

### N6 — Decided-but-unenforced is the new pending

The failure mode has mutated. June's problem was decisions nobody
made; July 11's problem was decisions converted to build work. The
current residue is decisions made, tooling shipped, **last-mile
manual step missing**: the spend gate without its secret (N2), the
umbrella spec-audit CI that dies without `ATTUNE_WORKSPACE_RO_TOKEN`
(unset, carried since 07-10), the Console spend limit never
configured. All three are minutes of Patrick's time in a browser.
None can be committed. The ledger below exists so they stop hiding
between assessments.

---

## Outstanding-work ledger (the point of this report)

Ranked. Items 1–3 are Patrick-only actions; nothing in the repo
advances them. Items 4–5 are observation windows. Items 6–9 are
build work that is legitimate *during* the freeze.

1. **DEC-2 — four user conversations** *(existential; only item
   that resolves F1).* Channel is live (Discussion #1325). Work =
   monitor it, respond fast to any reply, and count every
   substantive async thread toward the 5. If the channel is silent
   by 07-27, that silence is data — record it.
2. **Set `ANTHROPIC_ADMIN_API_KEY`** in attune-ai repo secrets
   (Settings → Secrets → Actions). Until then DEC-8 enforcement is
   a no-op by design. ~5 minutes. Verified still unset 2026-07-12.
3. **Anthropic Console spend limit** (account setting) +
   **`ATTUNE_WORKSPACE_RO_TOKEN`** (fine-grained PAT for the
   umbrella spec-audit CI; pick 1-year expiry or calendar the
   renewal). Both browser-side, both carried for 2+ days.
4. **Run the DEC-7 freeze experiment properly** (07-13 → 07-27):
   no tags, keep the snapshot cadence, and on 07-27 write the
   interpretation into usage-signals — does the download curve
   track releases or users? Free, zero-code, settles N3.
5. **CI-spend refund dispute** — when Anthropic states the
   mechanism (billing error vs. goodwill), correct N2's narrative
   in the 07-11 assessment and #1330's doc. Until then, don't
   rewrite history.
6. **Record the N5 interpretation** — one paragraph in
   usage-signals declaring the attune-rag 27k/month figure
   uninterpreted noise pending evidence. Prevents the next
   marketing-accuracy incident before it happens.
7. **DEC-3 execution — make Memory visibly the pillar.** The
   decision exists; the README and package surface still present
   four pillars and six packages. Freeze-compatible version:
   reorder, don't build — memory first in the README, others
   demoted to a single "also ships" line. Full consolidation (F4,
   `attune-author-consolidation`) stays parked until DEC-2 data
   arrives.
8. **fable-premium-tier** (separate checkout `~/attune-ai-fable`,
   tasks 3–9 remaining, task 9 approval-gated). In-flight spec, so
   DEC-1-compatible; but task 9 is a release and the freeze says
   no tags through 07-27 — sequence accordingly.
9. **trap-battery** — requirements pending approval since 07-08,
   pilot scale already ratified. A decision (approve/park), not a
   design pass. Parking it until 07-27 is a valid answer; record
   whichever.

Explicitly *not* on the ledger: new gates, new specs, coverage
work, CI tuning, memory-layer audit (backlog note exists; it can
wait out the freeze). The freeze window's idle hours go to item 1
or to rest — not to inventing item 10.

---

## Counterweight (kept honest)

Twenty-four hours ago this review's central claim was that the
project converts self-knowledge into build work and drops the rest.
That claim is now falsified once — comprehensively, same-day, with
receipts (#1318, #1322, #1323, #1325, #1326, #1331, the filled
scorecard). The discipline was never in question; this is the first
evidence the *aim* can move too. The next two weeks require the
rarest skill in this repo's history: doing nothing, visibly, on
purpose, while watching one Discussion thread and one download
curve.

---

## Related

- [assessment.md](assessment.md) — 2026-06-17 original; F1–F6,
  DEC-1…5 defined.
- [assessment-2026-07-11.md](assessment-2026-07-11.md) — follow-up;
  N1–N4, DEC-6…9; all DECs recorded 2026-07-12.
- [weekend-plan-2026-07-12.md](weekend-plan-2026-07-12.md) — the
  forcing mechanism that closed N1; scorecard filled.
- [user-conversations.md](user-conversations.md) — DEC-2 log,
  1 of 5.
- [setup-friction-log.md](setup-friction-log.md) — conversation 1's
  friction findings, F1–F5 all fixed in #1318.
- [usage-signals](../usage-signals/) — snapshots incl. the 07-12
  baseline (#1327) for the freeze experiment; N5's attune-rag
  anomaly lives in its 07-12 snapshot.
