# Product Direction Review — Follow-up Assessment

**Status:** assessment (2026-07-11) — decisions pending Patrick
**Owner:** Patrick (+ agent)
**Type:** strategic assessment / decision record (not a build spec)
**Trigger:** Patrick asked for a second critical review, 24 days after
[assessment.md](assessment.md) (2026-06-17).
**Method:** identical to the first — every number re-measured from the
repo itself; same sources where possible, noted where not.

---

## Verdict

The June report was executed selectively — and the selection is the
finding. Every recommendation a solo engineer could satisfy *inside
the repo* got real, high-quality follow-through: ~30k LOC of dead
subsystems deleted, a working value-gate process, CI firefighting cut
from ~18% to ~4% of commits, a spend alarm built. The one
recommendation that required *leaving* the repo — DEC-2, talk to five
users — produced zero commits, zero memory entries, zero recorded
decisions. All five DECs still read "(pending)" in a file last touched
2026-07-10. Meanwhile commit velocity **doubled** to ~20/day and two
more major versions shipped. Finding 1 is not just unresolved; the
repo has gotten better at absorbing the energy that was supposed to
resolve it.

---

## Evidence (ground truth, 2026-07-11 vs 2026-06-17)

| Metric | 2026-06-17 | 2026-07-11 | Δ | Source |
|--------|-----------|-----------|---|--------|
| Product code (`.py`) | 183,768 LOC / 712 files | 169,169 LOC / 652 files | **−14.6k** | `find src/attune -name "*.py" \| xargs cat \| wc -l` |
| Test code (`.py`) | 349,399 LOC / 968 files | 327,136 LOC / 980 files | −22.3k | same, `tests/` |
| `test_` functions | ~20,160 | 20,393 | +233 | `grep -rE "def test_"` |
| Test-to-product ratio | 1.9 : 1 | 1.93 : 1 | flat | derived |
| Commit rate | 9.8/day (90d) | **20.3/day** (487 in 24d) | ×2.1 | `git log --since=2026-06-17` |
| Last 200: `feat` | 27 (13.5%) | 38 (19%) | +5.5pt | `git log -200 --format=%s` |
| Last 200: chore+docs+test+ci | 148 (74%) | 129 (64.5%) | −9.5pt | same |
| CI/hang/flake/runner commits | ~18% of 300 | **~4%** (20 of 487) | −14pt | `grep -cE "^ci\|hang\|flake\|runner"` |
| Open spec directories | 49 | **60** | +11 | `ls docs/specs` |
| `lessons.md` | 9,356 lines | **14,560 lines** | +56% | `wc -l` |
| CI workflows | 22 | 26 | +4 | `ls .github/workflows` |
| Docs `.md` files | ~500 | 693 | +39% | `find docs -name "*.md"` |
| Scripts | 108 | 120 | +12 | `ls scripts` |
| Dependency lines (pyproject) | 311 | ~402 (36 core + 366 optional) | +29% | `awk` over dep sections |
| Version | 8.5.0 | **10.3.0** | +2 majors | pyproject |
| Releases since 6/17 | — | **16 tags** (9.0.0 → 10.3.0) | 1 per 1.5 days | `git tag` |
| Human authors, last 200 | 1 | 1 (162 Patrick, 38 bots) | — | `git log %an` |
| Downloads/week | 636 | 2,316 | ×3.6 | usage-signals snapshot 07-08 |
| Real behavioral signal | ~0 | ~0 | — | see Finding F1 |
| User conversations (DEC-2) | 0 | **1 of 5** | +1 | [user-conversations.md](user-conversations.md) |

---

## Prior findings — status audit

### F1 — Demand hypothesis untested *(existential)* → **FIRST SIGNAL (1 of 5)**

> **Correction (2026-07-11, same day):** this section originally
> reported zero conversations. Patrick had in fact held one on
> 2026-07-09 — it was simply recorded nowhere in the repo, which is
> N1's point made empirically: the repo's measurement systems see
> commits, not calls. Now logged in
> [user-conversations.md](user-conversations.md).

One conversation held (2026-07-09). Its primary finding: **setup
issues** — the first behavioral datum ever collected, and it
implicates the platform's width (F4: ~402 dependency lines,
multi-package surface) at the front door, before any pillar is
reached. Four calls remain, with the uncaptured questions listed in
the log. Beyond that single datum the picture stands: nothing else
in 487 commits, `memory/`, or 5,200 new lessons lines. Worse, the downloads number now *looks* like traction —
636/wk → 2,316/wk — and no interpretation of the surge is recorded
anywhere in usage-signals. The surge correlates exactly with the
release cadence (16 releases in 24 days; snapshots jump on tag
dates: 921 on 07-03 → 1,500 on 07-04, the v9.5–9.7 window). The
project's own D1 finding — "our CI is the biggest user" — predicts
precisely this artifact, yet the README now carries three download
badges. The risk has evolved from *no signal* to *self-generated
signal mistaken for demand*.

### F2 — Test suite guards the wrong thing → **PARTIAL**

Real movement: test LOC down 22k, growth nearly stopped (+233
functions vs thousands prior), and deletions came with receipts
(`memorygraph-value-gate`). But the structure is intact: 20,393
tests, ratio flat at 1.93:1, codecov gate still ratcheting (80%
project / 50% patch), and the SDK 0.2 migration — the original proof
that mocked-green ≠ working — is *still* an open spec
(`claude-agent-sdk-0-2-migration`, created since 6/17).

### F3 — Scaffolding outweighs product → **WORSE, with one honest offset**

The offset first: the subsystem-value-gate is real and it worked —
socratic (~16k LOC, #1060) and the memory-graph API (10.0.0) are
gone, with documented verdicts. That is the pruning muscle the June
report asked for. Everything else grew: specs 49→60 (43 spec dirs
received new files in 24 days), lessons +56%, docs +39%, workflows
+4, scripts +12, and three new *gate* specs (`claim-drift-gates`,
`master-factcheck-gate`, `spec-gate-real-review`) — governance built
to govern the governance. DEC-1 (two-week freeze on new surface) was
not adopted: 11 net-new spec directories, and 43 spec dirs received
new files, in the 24 days after it was proposed.

### F4 — Identity blurred across packages → **WORSE**

June counted six packages. The root directory now also contains
`attune-verify` (a new `packages/` stub alongside attune-author,
-help, and -rag), `attune-healthcare-fork`,
`attune-software`, `attune-ai-dev`, `mcp-publisher`,
`vscode-extension`, and `website`. Nothing was consolidated
(`attune-author-consolidation` is another open spec, not a done one).
The platform got wider while the user count stayed unobservable.

### F5 — Major-version inflation → **WORSE**

Two majors in 24 days: 9.0.0 (06-26) and 10.0.0 (07-05), nine days
apart, inside a run of 16 releases — one every 1.5 days. 10.0.0's own
changelog admits the breaking change affected nobody ("telemetry says
nobody did"). Breaking-change ceremony for an audience of zero is
pure cost: it churns CI, inflates the download badge (see F1), and
spends the credibility a real 2.0 moment would need.

### F6 — CI firefighting tar-pit → **RESOLVED (genuinely)**

~18% → ~4% of commits. The tar-pit trip-wire worked. This is what
closing a finding looks like; it is cited here as the standard the
other five are measured against.

### DEC-1 … DEC-5 — **none recorded**

The June file instructed: "Record the call inline with a date when
made." Twenty-four days and 487 commits later, all five still read
"(pending)". Not declined — *unanswered*. The repo executed the parts
of the assessment that could become commits and silently dropped the
parts that could only become decisions.

---

## New findings

### N1 — The review loop doesn't close (meta, most important)

This document's predecessor was high-quality, evidence-based — and
functionally shelfware: zero decisions recorded, its existential
finding untouched, its freeze ignored. The failure mode is specific:
**recommendations get translated into build work** (gates, alarms,
pruning specs — all shipped) **because build work is the comfortable
dialect here; decisions and outreach have no pipeline to land in.**
Prediction: absent a forcing mechanism, this assessment meets the
same fate. The forcing mechanism must be non-repo-shaped — a calendar
entry, an email, a call — or it will be converted into a spec.

### N2 — The machine outspends its observable value ~∞

`usage-signals/decisions.md` records a **$1,200/month API burn on
CI** against a $350/month ceiling (`user_monthly_spend_budget`),
while local (human) usage ran ~$126/month. The response was
characteristic: a well-engineered spend *alarm* (18 tests, z-score
anomaly detection, source-precedence design). The alarm is good
engineering. But the finding isn't that spend was invisible — it's
that ~$1,200/month of LLM calls validate a product with zero
confirmed users. That's ~$14k/year buying green checkmarks. DEC-5's
logic applies: time-box it, cap CI model spend hard, spend the
difference on anything that touches a human.

### N3 — Release cadence is manufacturing its own evidence

16 releases in 24 days is a treadmill: each tag triggers CI, mirrors,
and scanners, which inflate the download badges, which are the only
"adoption" number on the README. The project is now measurably
generating the metric it is in danger of believing. Freeze releases
for two weeks and watch the download curve — that is a free,
zero-code experiment that would settle F1's data question.

### N4 — Repo-root hygiene has slipped below the project's own bar

The root holds ~80 entries, including: a stray `MagicMock/` directory
(a mock that escaped to disk — ironic given F2), `scratchpad_pushback.html`,
six loose `test_*.py` files (tracked), untracked `build/`, `dist/`,
`htmlcov/`, `site/`, `coverage.json`, and both `ACKNOWLEDGEMENTS.md`
*and* `ACKNOWLEDGMENTS.md`. Also 2.4 GB across nine
`.claude/worktrees/`. None of this is expensive individually; together
it signals that the hygiene systems watch everything except the front
door. An afternoon fixes it.

---

## Decisions to make (pending Patrick)

DEC-2 through DEC-5 from June carry forward unchanged. New:

- **DEC-6 — Answer DEC-1…5 in writing, this week,** even if every
  answer is "no". An explicit "no" is a decision; silence is drift.
  **Resolved 2026-07-12:** self-fulfilling — answered by recording
  DEC-1…5 above, in writing, with dates, this week.
- **DEC-7 — Release freeze, 14 days.** No tags. Observe the download
  badge. Publishes the F1/N3 experiment at zero cost. **Decided
  2026-07-12:** yes, starting 2026-07-13 after one more release
  already in flight. No tags through 2026-07-27; watch the download
  badge over that window.
- **DEC-8 — Hard-cap CI LLM spend at $100/month.** The alarm exists;
  add enforcement. Redirect the ~$1,100/month delta toward anything
  user-facing. **Decided 2026-07-12 (modified amount):** cap at
  $350/month — the existing documented ceiling
  (`user_monthly_spend_budget`) — rather than a new $100 figure.
  Still a ~70% cut from the $1,200 actual. Enforcement mechanism
  (provider-side cap vs. CI gate) is a follow-up implementation task,
  not yet built.
- **DEC-9 — One root-hygiene pass** (N4), time-boxed to half a day.
  **Done 2026-07-12:** PR #1322 — merged ACKNOWLEDGEMENTS files,
  removed six stale root test scripts, cleared MagicMock/ and other
  local artifacts, pruned ~93MB of stale worktree bloat.

DEC-2 remains the only decision that matters. One of five
conversations is done (2026-07-09, logged in
[user-conversations.md](user-conversations.md)); its finding —
setup friction — is already the most valuable product input of the
quarter. Four remain. The June bar stands: if the other four users
cannot be found, *that is the finding* — and it is worth more than
the next 487 commits.

---

## Counterweight (kept honest)

The pruning was real: ~30k LOC of well-tested dead weight deleted
with documented verdicts, which most engineers never manage. F6 was
closed properly. The consent-surface tests pin privacy promises in
CI. Feature share of commits rose. The discipline critiqued here is
the same discipline that, pointed at five phone calls instead of the
next gate spec, would resolve F1 in a week.

---

## Related

- [assessment.md](assessment.md) — the 2026-06-17 review this
  follows up; DEC-1…5 defined there, all still pending.
- [usage-signals](../usage-signals/) — snapshots (download surge
  data), spend-alarm decision record ($1,200 CI burn).
- [memorygraph-value-gate](../memorygraph-value-gate/) — receipts for
  the 10.0.0 deletion; the pruning pattern working as designed.
- [subsystem-value-gate](../subsystem-value-gate/) — the gate
  process itself (BEP, hot_reload receipts).
