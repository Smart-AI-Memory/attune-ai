# Round table — the round table as a pre-release audit stage (ratified)

**Thread:** `q-release-audit-roundtable-stage-001` · 2026-08-22 ·
3/3 seats (Claude, Antigravity, Codex), 1 round, halted on
convergence. Chair-promoted sections only; full transcript is
machine-local (`~/.attune/reports/roundtable/`).

Adapts the class-first review model
(`~/.attune/reports/attune-ai-review/CLASS-REGISTER.md`) into a
per-release stage. The register's central measured finding is the
premise the whole design rests on:

> Review is the right tool for FINDING A CLASS and the wrong tool for
> ENUMERATING ITS INSTANCES. Only the gate is permanent.

Two measurements behind it: the attune-forms review, where a 3-seat
table designed the funnel and a SINGLE reviewer found all 23 confirmed
defects; and attune-ai batch 2, where 3 reviewers and ~450k tokens
yielded 8 instances of one class, while mechanizing that class took
~20 minutes and found 84 more at zero false positives.

## Chair rulings

- **RULED A** — the audit is a stage inside `/release`, not a separate
  command or a headless routine.
- **RULED B** — the table sits on EVERY release, not gated on residual
  size. (The register makes an empty residual nearly impossible: 15 of
  26 classes are ungated or open.)
- **RULED C, seat roles** — (a) advise ship/hold per residual item and
  (c) rank which ungated/open classes need a gate before this release
  are IN. (d) detect defects in the diff is OUT; the two measurements
  above settle it.
- **RULED D, teeth** — `gate-before-ship` HAS TEETH. The stage may hold
  a release until a fixed-but-ungated class re-exposed by the diff gets
  its gate. Advisory-only rejected: with 7 classes already
  fixed-but-ungated, an advisory stage reports a growing set every
  release while nothing forces it to shrink.
- **RULED E, trigger** — a calibrated rule HIT blocks; surface EXPOSURE
  warns. Exposure remains the §3 boolean matrix (below), not a
  warning-severity row competing with hits for the packet's cap.
- **RULED F, escape** — `DEFER` with owner and expiry. An accepted
  release risk is recorded and cannot quietly become permanent.
  (The moderator recommended a lighter one-line record and was
  overruled toward more rigor.)

## The stage

```text
0  baseline    git diff <last-tag>..HEAD --name-only
1  reconcile   every CLOSED class's gate green in CI (receipt: run id)
2  diff sweep  mechanized rules over CHANGED FILES ONLY, weighted
               toward the 7 fixed-but-ungated classes
3  residual    sweep hits + ungated exposure + new-boundary inventory
4  sitting     one round, three seats, no rebuttal loop
5  chair       rules per item; manifest row per changed package
```

**Early aborts, no sitting:** reconcile red at step 1 stops the stage —
never sit on a red baseline. A packet over caps means the chair splits
the release, not that the packet is reformatted.

**Explicit non-stop:** an empty residual does NOT skip the sitting. It
produces a one-page packet and three one-line ships in minutes. The
near-zero cost floor is what makes RULED B payable.

## The residual packet (3/3 convergent; caps are Claude's)

Hard budget: ≤1500 words, ≤12 residual items, ≤20 sweep rows, zero diff
hunks, no file contents. All three seats independently demanded a
structured manifest and forbade a raw diff.

| § | Content |
|---|---|
| 0 | Header: tag range, files changed, packages touched, public symbols added/removed |
| 1 | Reconcile receipt: CI run id, closed-class gates green |
| 2 | Sweep hits: class id, `file:line`, one-line excerpt, **and the rule's recall/precision** so seats can weight it |
| 3 | **Ungated exposure** — per fixed-but-ungated class, a boolean over the changed surface, plus the file |
| 4 | New-boundary inventory, two program points each |
| 5 | Open-class exposure of the changed surface |
| 6 | Explicit NULL section — what the diff does NOT introduce |
| 7 | **A pre-filled default disposition per item** |

§3 is the reason the stage exists: nothing prevents a fixed-but-ungated
class from walking back in on a new diff, and that risk is both certain
and invisible.

§7 is the anti-mush mechanism. A seat asked to COMPOSE from a dump
produces prose; a seat asked to AMEND a pre-filled disposition produces
a delta. Seats reply per item number, one closing paragraph maximum.

## Class M — not a table question (unanimous)

All three seats routed class M ("the mock defined the contract")
mechanical-detector → single reviewer with tree access → table only on
the unresolved residue, and all three independently reached the same
zero-cost enforcement:

> A fix for a boundary class whose DECLARED receipt type is `suite`
> rather than `live-fire`/`behavioral` is class M **by declaration**.

That is a PR metadata check against the repo's existing
receipt-declared delegation rule. No AST required, and it catches the
case the AST rules will miss. Codex adds that the reviewer attestation
must carry an evidence pointer and receipt type, never a bare "yes",
or it becomes checkbox theater.

Three AST shapes seed the detector's worklist (a worklist, never a
verdict): a patched call site whose only assertions are on the mock; a
test-local literal passed to a deserializer whose paired writer exists
in the package (I-4 mirrored into tests); a "cannot write" test that
induces failure by patching `open`/`write_text` rather than by a real
chmod or read-only directory.

## The status column should not exist (unanimous)

All three seats concluded the register's hand-maintained status column
is the wrong artifact, and refused to let a fresh repo inherit `CLOSED`
without a local scan receipt. It is a cache of a value that is
mechanically derivable per repo:

| gate test present? | current sweep hits | derived status |
|---|---|---|
| yes | 0 | CLOSED |
| no | 0 | FIXED BUT UNGATED |
| no | >0 | OPEN |
| yes | >0 | **broken gate — loud** |

The fourth quadrant is the one a hand-maintained column cannot report
at all.

Portability follows from this: what the three-day review bought was the
**class vocabulary**, and vocabulary is the portable artifact. Rules
port; status is derived per repo; calibration is per-corpus and a rule
runs advisory and labeled `uncalibrated-here` in a new repo until that
repo has its own calibration receipt (~20 min/rule of hand triage,
versus three days of review).

## Held, not promoted

**Role (b) — name a new class from a diff summary.** 2 NO, 1 qualified
yes, and the split is narrower than the vote: Codex's NO already
contains the fallback "candidate hypotheses labeled unconfirmed leads,
with no hold or register effect", which is nearly verbatim the
re-scoped (b) Claude defended. Antigravity is the only unqualified no,
on the sharpest argument in the thread — asked to invent classes from
static summaries, models predictably emit generic anti-patterns that
pollute the residual.

Not promoted this session. If it returns, the only defensible form is
the instrumented one: a candidate carries its confirm recipe, never
blocks, and the manifest tallies candidates-named against
candidates-later-confirmed so the role retires itself by evidence.

## Prerequisite (why this is not yet buildable)

The sweep suite (`sweep_suite_v2_r7.py`, 157 lines) and the class
register are machine-local scratch artifacts under
`~/.attune/reports/attune-ai-review/`. Steps 1–3 read both. Promoting
them into tracked code — a rule pack under `src/attune/classes/` with
`{id, invariant, calibration, fixtures}` per rule, a `scan` verb over
changed paths, and a `register` verb that DERIVES the table above — is
Phase 0 of the build, not a follow-on.

## Provenance

Board thread `q-release-audit-roundtable-stage-001`, messages 2, 3, 4
(positions), 7 (synthesis), 8 (chair ruling) promoted 2026-08-22.
Seat receipts: Codex ~39s (gpt-5.6-sol); Antigravity ~63s (plan mode);
Claude 87,126 tokens (~135s, agent seat).
