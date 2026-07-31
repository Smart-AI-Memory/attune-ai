# Outcome-First Fix — Measurement (Phase 3)

**Measured:** 2026-07-31, keyless, on the Phase 3 branch.
**Metric set:** the four RATIFIED in decisions.md D3. The routing
metrics (contract-edit rate, route-correction rate,
false-confident-route rate, abstention rate) stay deferred to Phase 4,
where the labeled corpus they require exists.

**No new telemetry, store, or lifecycle** (H3): every number below is
read from an artifact the surface already produces — the receipt
itself, or the test suite.

---

## 1. Evidence-valid receipt completeness — 100%

**Definition:** the share of rendered receipts carrying every required
section, so a reader never has to infer an omitted fact.

**Required sections:** `🧾 Fix receipt`, `Changes made (attributed to
this run):`, `Probes (evaluated independently):`, `Safest next
action:`, and the independence trailer.

**Measured:** 3/3 outcome shapes complete — no-change with passing
probes, no-change with failing probes, changed with failing probes.
Conditional sections (pre-existing changes, scope violations, remaining
uncertainty) render when and only when they have content.

```bash
pytest tests/unit/cli_commands/test_fix_phase3.py::test_every_receipt_carries_every_required_section -q
```

**Instrument:** `_REQUIRED_SECTIONS` in the Phase 3 test module. Adding
a section to the receipt without adding it there would leave the metric
overstating completeness — the tuple is the definition of record.

## 2. Verification-failure honesty — 100%

**Definition:** the share of failed or unverifiable conditions that
produce an explicit row, rather than a silent omission that reads as
success.

**Measured:** every negative path emits its row and a non-zero exit —
probe failure (`[FAIL]`), unrunnable probe (`[SKIPPED]` + a reason
under remaining uncertainty), out-of-scope edit (a named violation),
workflow crash (a partial receipt, exit 2), and git-unavailable (an
explicit "SCOPE NOT VERIFIED" line, never a success claim).

The load-bearing case is `WorkflowResult.success=True` with failing
probes: exit 1. Workflow exit is never trusted (H2).

```bash
pytest tests/unit/cli_commands/test_fix_phase3.py tests/unit/cli_commands/test_fix_receipt.py -q
```

**Phase 3 correction:** two honesty defects were found and fixed while
measuring. A run that changed nothing rendered `(none detected)` and
advised "review the attributed diff and commit" — advice for a diff
that did not exist, and indistinguishable from a verified fix. And a
multi-probe partial success named only the FIRST failing probe,
under-reporting what still had to pass.

## 3. Time to verified outcome — 1.13s verification overhead

**Definition:** wall-clock from request to a receipt the user can act
on. Split, because the two halves have different cost drivers.

| Component | Measured | Source |
|---|---|---|
| Independent verification (both probes) | 1.128 s (561 ms + 567 ms) | D6 live-fire receipt |
| Baseline capture + attribution | below timing resolution | Phase 3 suite durations |
| Agent fix step | not recorded | — |

**Instrument:** the receipt. Every probe row already carries its argv,
return code, and duration in milliseconds — this metric needs no new
measurement path, which is why it survives H3.

**Honest limit:** the agent step's wall clock is NOT captured in the D6
record, so no end-to-end figure is reported here rather than an
estimated one. The next live-fire run should record it; until then this
metric covers the CLI's own contribution only.

## 4. Compatibility regressions — 0

**Definition:** documented `attune workflow run` behavior that changed
as a side effect of the Fix surface.

**Measured:** 0 regressions across 9 intentional characterization pins
(14 tests total), including the full exit contract — `success=True` → 0,
`success=False` → 1, uncaught exception → 2, and the documented legacy
loophole where a result with no `success` attribute exits 0.

```bash
pytest tests/unit/characterization/test_outcome_first_phase0.py -q
```

**Instrument:** `tests/unit/characterization/test_outcome_first_phase0.py`
— named here as the metric's source of record, and guarded by
`test_compatibility_pins_module_still_exists_and_is_named` so deleting
it cannot quietly turn "0 regressions" into "unmeasured".

---

## Reading these numbers

Three of the four read 100% / 0 because they measure properties the
suite enforces rather than samples of real-world use. That is what they
are for at this phase: they make a regression in receipt honesty fail
CI. They are NOT evidence that users succeed with the surface — no
Fix has been run by anyone but its authors. Adoption-shaped metrics
(abandonment, completion without internal knowledge) need real users
and are not claimed here.
