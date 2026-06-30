# Master Fact-Check — Tasks

**Status:** draft (2026-06-30) · implements [design.md](design.md).

## T1 — Extract the authoritative resolver (R1/R2)

- Lift `audit_doc_imports.py`'s repo-`src`-on-`sys.path` import resolver
  into a small importable helper (keep the script as a thin caller).
- Point `project_features.py`'s pre-projection check at that helper for
  import lines; stop importing against the editable mapping.
- **Acceptance:** the multi-line `from attune.elicitation import (…)`
  regression yields zero "not importable" findings; the projector's
  import verdict equals `audit_doc_imports.py`'s on a fixture set.

## T2 — Measure the incremental coverage (R3)

- Run `check_python_refs` and `audit_doc_imports.py` across all 27
  masters; compute the delta; hand-classify each delta finding
  (true / false / import-redundant).
- Write `incremental-findings.md` in this spec dir with the table.
- **Acceptance:** the measurement exists and classifies every delta
  finding; T3's direction is chosen from it, not assumed.

## T3 — Gate the reliable subset OR retire the duplicate (R4/D4)

- If a near-zero-false-positive check exists: fold it into the
  authoritative resolver and put it on the advisory→required promotion
  path; add a fires-on-bad / silent-on-good test.
- Else: remove the redundant/flaky import check from the projector
  (imports already moved to the authoritative path in T1).
- **Acceptance:** either a new advisory check with a passing promotion
  guard, or a net deletion — and in both cases the projector emits one
  authoritative verdict (R5).

## T4 — Author-facing message + docs (R5)

- Ensure the projector prints the authoritative findings located at the
  master (file + line); update the single-source playbook lesson to note
  the projector's verdict now matches the required gate.
- **Acceptance:** a wrong master gives one actionable message at
  authoring time; no contradictory pair of warnings.

## Sequencing

T1 first (the trust fix, valuable alone). T2 is the pivot; T3 follows its
result. T4 closes. None depends on the scaffolder spec or the
drift-propose Open item.
