# Product Direction Review — Third Assessment (pulse check)

**Status:** delivered (2026-07-14) — decisions executed same night
**Owner:** Patrick (+ agent)
**Type:** strategic assessment / decision record (not a build spec)
**Trigger:** Patrick asked for a repeat of the critical review with
emphasis on project-health opportunities, ahead of a spec-backlog
triage session.
**Method:** identical to the first two — every number re-measured
from the repo 2026-07-14. Only 3 days after
[assessment-2026-07-11.md](assessment-2026-07-11.md), so this pass
is a pulse check on whether the July decisions held, not a full
re-audit.

---

## Verdict

The decisions are holding — and that's new. The release freeze is
real (zero tags since v10.4.1 on 07-13), the spend cap is live
($26.53 MTD against $350), the repo is operationally immaculate
(0 open PRs, 0 open issues, main CI green), and the download decay
predicted by N3 is already visible. N1 (reviews become shelfware) is
partially broken: DEC-6 through DEC-9 all got answered or done.

Two things did not hold. DEC-2 is still 1 of 5 conversations,
unchanged since 07-09, while ~18 commits/day continue. And the spec
backlog — cut to 23 on 2026-06-24 — grew back to 56 active
directories in 20 days (triaged back to ~20 the night of this
assessment; see
[matrix-2026-07-14](../archive/spec-backlog-triage-2026-06-24/matrix-2026-07-14.md)).

---

## Metrics (2026-07-11 → 2026-07-14)

| Metric | 07-11 | 07-14 | Read |
|---|---|---|---|
| Product LOC / files | 169,169 / 652 | 169,913 / 654 | flat |
| Test LOC / `test_` funcs | 327,136 / 20,393 | 329,851 / 20,597 | +204 tests in 3 days — F2 growth resumed |
| Commit rate | 20.3/day | ~18/day (55 in 3d) | freeze slowed tags, not commits |
| Last 200: feat / scaffolding | 38 / 129 | 34 / 134 | drifting back toward scaffolding |
| Active spec dirs | 60 | 56 (pre-triage) | triaged to ~20 this night |
| `lessons.md` lines | 14,560 | 14,972 | +137/day, unchanged pace |
| Docs / scripts / workflows | 693 / 120 / 26 | 700 / 119 / 26 | flat |
| Version / tags | 10.3.0 | 10.4.1, frozen since 07-13 | DEC-7 holding |
| Open PRs / issues | — | 0 / 0 | immaculate |
| attune-ai downloads/wk | 2,034 | 1,809 (07-13 snapshot) | −11% into freeze — N3 confirming |

**The download experiment has its smoking gun early:**
`attune-verify` — a 0.2.1 stub untouched on PyPI since 2026-06-23 —
shows 5,710 downloads/week and ~41k/month (07-13 snapshot), roughly
triple attune-ai's numbers. A near-empty package outdownloading the
flagship is conclusive: the download numbers are mirrors and CI, not
humans. The DEC-7 decay curve (window ends 07-27) will quantify it,
but the conclusion is no longer in doubt. The three README download
badges now measure noise the project has itself proven is noise.

---

## Prior findings — pulse

- **F1 / DEC-2 (existential): STALLED at 1 of 5.** The inbound
  channel (Discussion #1325, live 07-12) is good repo-shaped work,
  but passive. No conversation 2 scheduled. The only finding with
  zero movement across three assessments.
- **F2 (test suite): regressing quietly** — +204 test functions in
  3 days after July noted growth had "nearly stopped."
- **F3 (scaffolding): the spec backlog was the live instance** —
  triaged same night, 56 → ~20, with an R1 recurrence check
  approved so it stops regrowing silently.
- **F5 (version inflation): RESOLVED by the freeze**, for now. The
  real test is what ships after 07-27 — and why.
- **N1 (review loop doesn't close): PARTIALLY BROKEN — credit where
  due.** DEC-6 answered, DEC-7 running, DEC-8 decided + gate live,
  DEC-9 done (#1322). The pattern held only for DEC-2 — exactly the
  one that requires leaving the repo, exactly as N1 predicted.
- **N2 (spend): closable.** Gate live, $26.53 MTD vs the $350 cap.
  Unless the Anthropic refund dispute changes the facts, DEC-8/
  Block 0 can be closed out.

---

## Health opportunities (ranked, as delivered)

1. **Spec backlog triage** — executed same night (56 → ~20; 28
   archived, 2 merged, 3 killed, 4 recommitted, R1 approved).
2. **Schedule conversation 2 — non-repo work.** A calendar entry,
   not a spec. The 4 uncaptured questions are already written in
   [user-conversations.md](user-conversations.md).
3. **Point the freeze window at deletion** — through 07-27 the repo
   can't tag or open spec dirs; archiving, consolidating, and
   killing are the natural freeze work. (Started with this triage.)
4. **Remove or reframe the download badges** — the attune-verify
   datum makes keeping three of them self-deception with a UI.
5. **Family coherence (F4):** `attune-lite` stale on PyPI since
   March (1.0.1) — deprecate or fold; `attune-redis` is documented
   as `pip install attune-redis` but is NOT on PyPI — a broken
   promise to any reader who tries. Both one-decision items.
6. **Close DEC-8/Block 0 formally** — gate live and under cap;
   record it and stop carrying it.

---

## Decisions made this pass (2026-07-14, Patrick, in-session)

- **Triage executed:** all 30 archive/merge dispositions; kill
  discovery-sweep-access, pipeline-coordinator-error-fidelity,
  doc-stack-reference-subtypes (pipeline-learner spared); recommit
  memory-recall-eval, sdk-teardown-exit-guard,
  elicitation-form-surface v2, post-commit-help-check-only.
- **R1 approved:** extend the spec-status audit to flag
  terminal-status-but-top-level >7 days in the weekly report
  (follow-up PR).

Open from this pass: opportunities 2, 4, 5, 6 above — all
Patrick-decision or non-repo items, deliberately NOT converted into
specs (per N1).

---

## Counterweight (kept honest)

Three days of evidence says the July report worked: freeze held, cap
built, root cleaned, decisions written down, zero open PRs/issues
with CI green. The fable-premium-tier and trap-battery work shipped
through the freeze without breaking it. The critique isn't
discipline; it's still allocation — and DEC-2 remains the proof.

---

## Related

- [assessment-2026-07-11.md](assessment-2026-07-11.md) — the July
  review this pulses against.
- [assessment.md](assessment.md) — the June original; DEC-1…5.
- [user-conversations.md](user-conversations.md) — DEC-2 evidence
  log (1 of 5).
- [usage-signals](../usage-signals/) — snapshots feeding the DEC-7
  decay observation.
