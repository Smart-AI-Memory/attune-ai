# Master Fact-Check — Design

**Status:** superseded (2026-06-30) — by attune-author-consolidation (#1192 D4, fact-check absorbed #1193); reconciled at 2026-07-14 triage (was: draft)
[requirements.md](requirements.md).

## The shape of the fix: make the projector agree with the gate

The required gate (`audit_doc_imports.py`) is already the authority on
master imports. The projector's warn-only check is the unreliable
duplicate. So the design is *subtraction toward a single source of
truth*, not a new gate bolted on top.

```text
project_features.py
  ├─ import resolution  → DEFER to the authoritative resolver
  │                        (repo src on sys.path), not the editable map
  └─ non-import refs     → keep advisory, with the SAME resolver,
                           until R3 measures whether any is gate-worthy
```

## Step 1 — Authoritative resolution (R1/R2)

`audit_doc_imports.py` already owns the correct mechanism: it adds the
in-repo `src/` to `sys.path` and resolves `attune` imports there, immune
to the editable-install mapping. Extract that resolver into a small
importable helper (it is currently script-internal) and have
`project_features.py` call it for the master's import lines — instead of
`attune_author.validate_master_file`'s editable-mapping import.

Result: the projector's import verdict is byte-for-byte the gate's
verdict. The line-115-style false positive disappears because the same
authoritative path is used. Single source of truth on imports (R2).

The change is attune-ai-side (the driver + a helper extraction); no
`attune_author` change is needed for the import half (D1).

## Step 2 — Characterize the incremental checks (R3)

Before touching `check_python_refs`'s *non-import* behavior, measure it:

1. Run the current `check_python_refs` across all 27 masters; collect
   every finding.
2. Run `audit_doc_imports.py` across the same; collect findings.
3. The **delta** (in `check_python_refs` but not the gate) is the
   incremental coverage — symbol references in prose, bare names,
   method-ish refs.
4. For each delta finding, hand-classify: *true positive* (a real stale
   ref), *false positive* (resolves fine / not actually a code ref), or
   *import-redundant* (already the gate's job).

This is an investigation task with a written output
(`incremental-findings.md`), not an assumption. It decides Step 3.

## Step 3 — Gate the reliable subset, or retire the duplicate (R4)

Two honest outcomes, chosen by the Step 2 measurement:

- **If the delta contains a near-zero-false-positive check** (e.g. "a
  bare `attune.X.Y` symbol reference in prose resolves"): fold it into the
  authoritative resolver / `audit_doc_imports.py` and ride the
  advisory→required promotion path (advisory on main until a green
  streak, then added to branch protection — the exact play `doc-import`
  and `wiring` already followed).
- **If the delta is empty or all high-false-positive:** the correct result
  is *removal*, not addition — drop the redundant/flaky import check from
  the projector (Step 1 already moved imports to the authoritative path),
  leaving the projector's advisory output trustworthy-by-subtraction.
  "Less verification machinery, more trust" is a legitimate, even
  preferred, outcome (D4).

Method-call accuracy and prose-claim accuracy are **out** either way
(non-goal; high false-positive; the doc-import-gate line).

## Step 4 — One author-facing message (R5)

After Steps 1–3 the projector prints the authoritative resolver's
findings only (no contradictory second opinion), located at the master
(file + line). The required gate remains the blocking authority in CI; the
projector surfaces the same verdict earlier, at authoring time, so the
error is caught before projection fans it to 14 outputs.

## Testing

- **Resolution (R1):** a master with a valid multi-line
  `from attune.elicitation import (…)` produces zero "not importable"
  findings from the projector (the exact regression that motivated this
  spec).
- **Agreement (R2):** a property/parametrized test that the projector's
  import verdict equals `audit_doc_imports.py`'s on a fixture set
  including resolvable, unresolvable, and skip-marked fences.
- **Promotion guard (R4):** if a delta check is gated, a test that it
  fires on a known-bad master and is silent on the 27 real ones.

## Sequencing note

Step 2 (measurement) is the pivot — Step 3's direction (gate vs. retire)
is unknown until the delta is measured. So this spec is **partly
investigative**: do not pre-commit to adding a gate; let the corpus
decide (D3).
