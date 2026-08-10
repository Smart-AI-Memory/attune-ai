# memory-claim-verification

**Status:** active (2026-08-10) — the ref-binding fork is RULED:
the table sat 2026-08-10 and D7 adopts per-finding matching with
three riders (unbound first-class; session provenance as a
derivable weaker view; measure-first probe). Requirements authored
2026-07-26; OQ1 measured at n=18: 28.1% of model-authored refs
grounded, 10.1% heuristic-backfillable — R3-as-written retired by
D6. Next gate: the D7 rider-(c) probe runs before the P1 matcher
build.
**Owner:** Patrick (chair)
**Origin:** 2026-07-25 session — 2 of 4 auto-stashed findings were wrong
enough that Patrick had to ask for them to be deleted.

---

## Problem

`plugin/hooks/session_stash.py` runs a local `llama3.1:8b` over the
transcript tail on every Stop, extracts ≤5 findings, and writes them to a
30-day store as free prose. `SessionStashEntry` carries `id`,
`session_id`, `cwd`, `timestamp`, `type`, `content`, `tags` — and **no
link to the evidence the claim came from, and no verification of any
kind.**

Measured failure, 2026-07-25 (4 findings written, 2 deleted as wrong):

| Finding | Reality |
|---|---|
| `9e140a08` — "PR #1666 is open for reviewing the changes" | #1666 was merged the same session |
| `203a128d` — "the baseline … led to mistakes in the last two days" | the noisy baseline was found and fixed *before* causing any mistake |

Both survived because nothing checks. `"PR #1666 is open"` and
`"PR #1666 is merged"` are indistinguishable as strings; only one is
checkable, and no code checks it.

**Why this is worse than storing nothing.** A wrong memory is recalled
later wearing the authority of a recorded fact, at a moment when the
originating context is gone. The existing lesson *"a memory's
`description:` is the RECALL SURFACE"* documents the same failure class
in the curated tier: a stale line drove a confident, wrong
recommendation. This spec addresses the raw tier, where the error rate is
higher and there is no human author.

### The prompt is not the lever

The extraction prompt already has a PROVENANCE rule telling the model to
record only what the session concluded. Both bad findings violated it
anyway. **Making an 8B model more careful is not a control** — it is the
thing that failed. This spec adds verification *outside* the model.

---

## The principle: derive, don't store

This repo already solved this problem twice, in the same week:

- **The claim-drift gate** (`tests/unit/gates/test_claim_drift.py`)
  refuses to trust a tool count written in a README. It derives the count
  from the live registry and fails when the written one disagrees.
- **The capability projector** (`scripts/project_capabilities.py`) owns
  the claim sites outright, so the number is never hand-authored.

Both caught real drift on 2026-07-25 (#1605, #1607). The memory store is
the one remaining place that trusts written prose about mutable state.

**Requirement: a claim about a mutable entity must be resolvable to that
entity's live state, at write time and again at read time.**

---

## Requirements

### R1 — Findings carry typed entity references

`SessionStashEntry` gains `refs: list[str]` — typed references to the
entities a finding is about:

```
pr:1666   sha:1f6553edc   file:scripts/check_platform_compat.py
spec:memory-recall-eval   branch:claude/foo   issue:1612
```

The extractor emits refs alongside content. Refs are cheap to resolve and
are the join key between a prose claim and ground truth.

### R2 — Write-time verification rejects contradicted claims

Before storage, each ref resolves to live state. Where the finding also
carries a **structured claim** about that entity (R3), a contradiction
rejects the finding rather than storing it. Rejections increment the
existing rejection counter (`_record_rejection`) so the rate is visible.

Resolution must be cheap and offline-tolerant: `gh` for PR/issue state,
`git` for sha/branch, filesystem for paths. **Unreachable ≠ contradicted**
— if resolution fails, the finding is stored ungrounded (R4), never
rejected. The memory layer must never block a session.

### R3 — Verifiable claims are structured, prose is not

The extractor emits an optional `claim` object for the narrow set of
mechanically checkable assertions:

```json
{"type":"reference","content":"PR #1666 fixed the scanner",
 "refs":["pr:1666"],
 "claim":{"kind":"pr_state","ref":"pr:1666","value":"open"}}
```

Only `claim` is verified. `content` stays prose and is never
NL-parsed — that would reintroduce the model as the checker.

Initial `claim.kind` set (deliberately small): `pr_state`, `file_exists`,
`count`. Extending it is a decision, not a default.

### R4 — Grounded vs. interpretation is a first-class distinction

Entries gain `grounding: "grounded" | "interpretation"`:

- **grounded** — has ≥1 ref that resolved.
- **interpretation** — no resolvable ref. `"the baseline led to mistakes"`
  is an interpretation and must never carry the same authority as
  `"baseline went 22→4 at sha 1f6553e"`.

Recall labels and ranks by this. Interpretations are not banned — they
are demoted and marked.

### R5 — Read-time re-resolution

`recall_entries` / `recent_entries` re-resolve refs and annotate:

```
[reference] PR #1666 fixed the scanner  ⟨pr:1666 → MERGED 2026-07-25⟩
```

This is the highest-value, lowest-cost half: it makes the 07-25 failure
visible **without needing to understand the sentence**. A reader sees
"open for reviewing" next to `MERGED` and discards it. Ships even if R2/R3
are deferred.

### R6 — The recall scan cap must not read as absence

`recent_entries` currently logs `request cap (40) hit scanning attune;
older records skipped`. A capped scan returning nothing is reported as
"no hits", which is indistinguishable from "not stored" — the same
absence-as-success failure the CI gates were rebuilt to remove. Recall
must distinguish *no matches* from *scan truncated*.

---

## Acceptance — the golden-set receipt

The regression test replays the four real findings from 2026-07-25:

| Finding | Required outcome |
|---|---|
| `9e140a08` "PR #1666 is open for reviewing" | **rejected** at write (R2/R3), or flagged `MERGED` at read (R5) |
| `203a128d` "…led to mistakes in the last two days" | stored as **interpretation**, demoted in recall (R4) |
| `[decision]` "fix the script, not the code" | **survives, grounded** |
| `[pattern]` "false positives from comment/docstring sensitivity" | **survives** |

A change that rejects all four is as wrong as one that accepts all four.
The test must pin both directions — this is the same discipline used in
`tests/unit/ci/test_platform_compat_scanner.py`, where every
false-positive class is paired with its true positive so a later
re-broadening fails loudly.

Additional receipts:

- **Non-mocked round trip** — real extraction → real verification → real
  write → real recall, per the "registered ≠ working" lesson. Mocked
  tests will pass precisely because they mock the resolver.
- **Offline degradation** — with `gh`/network unavailable, findings still
  store (ungrounded) and no session is blocked.

---

## Non-goals

- **Improving the extraction model or prompt.** Explicitly out of scope;
  see "the prompt is not the lever".
- **Verifying prose.** Only structured claims are checked.
- **Touching the curated `/remember` tier.** That layer is
  human-authored; its staleness problem is separate and already has a
  lesson.
- **Blocking on the memory layer.** Degrading silently stays mandatory.

---

## Phases

**P1 — read-time annotation (R1 refs, R5, R6).** Highest value per unit
work: catches the 07-25 failure with no model changes and no write-path
risk. Refs can be back-filled heuristically from `content` for existing
entries (`#\d+`, sha-like tokens, paths).

**P2 — write-time verification (R2, R3).** Extractor emits `claim`;
resolver rejects contradictions.

**P3 — grounding tier (R4).** Ranking and labelling in recall.

P1 is independently shippable and worth shipping alone.

---

## Open questions

1. **Does the 8B model reliably emit refs?** If not, P1's heuristic
   back-fill from `content` may be the permanent mechanism rather than a
   migration step. Measure before building P2 — this determines whether
   R3 is viable at all.
2. **Rejection vs. demotion on contradiction.** Rejecting loses the
   observation entirely; a contradicted claim may still indicate
   something happened. Proposal: demote to `interpretation` with the
   contradiction recorded, rather than drop.
3. **TTL interaction.** Should a grounded finding whose entity still
   resolves outlive the 30-day TTL? Probably yes, but it changes the
   store from working-memory to something more durable — a chair call.
