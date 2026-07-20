# Decisions: SDK teardown-exit-1 guard

**Status:** EXECUTED (2026-07-20) — design approved as drafted and
execution armed by the chair 2026-07-20; see the execution log below
**Requirements:** [requirements.md](requirements.md) ·
**Design:** [design.md](design.md)

---

## D1 — Success signal is `subtype == "success"`, not `not is_error`

The guard recognizes a successful run by
`ResultMessage.subtype == "success"`.

**Why:** SDK 0.2.102 / bundled CLI 2.1.178 emitted `is_error=True`
*together with* `subtype="success"` on successful runs (fixed in CLI
2.1.183 / SDK 0.2.105 — see the bundled-CLI lessons). `subtype` was
correct throughout that window, so it is the trustworthy success marker
across version pins. `collect_agent_output` already records `subtype`, so
no new capture is needed.

**Rejected:** `not is_error` (false during the 2.1.178 window);
"any ResultMessage" (would treat error/timeout results as success).

---

## D2 — A pass-through async generator, not a loop-owning helper

`iter_agent_messages(query)` wraps the SDK async iterator and re-yields
every message; workflows adopt it by wrapping their existing
`claude_agent_sdk.query(...)` in one line.

**Why:** one-line adoption across eight workflows with zero change to
their bodies (`collect_agent_output` / `build_result_text` / scoring
stay put). A higher-order `run_agent_query(...)` that owned the whole
loop would have to thread each workflow's distinct `options`/`agents`
config through a shared signature — more surface, more churn, more risk —
for no extra benefit. The generator centralizes exactly the teardown
guard and nothing else.

---

## D3 — Swallow ONLY after success; never mask a real failure (false-green constraint)

The teardown exception is swallowed **iff** a `subtype="success"`
`ResultMessage` was already yielded AND the exception matches the benign
teardown shape (`"command failed"`). Anything before success, any
non-success ResultMessage, and any `BaseException`
(KeyboardInterrupt/SystemExit/CancelledError) propagate unchanged.

**Why:** the mirror-image bug already exists — `attune workflow run`
exits 0 even when `WorkflowResult.success` is False (dispatcher swallows
SDK exceptions → false **green**). A blanket "swallow Command-failed"
guard would convert our false **red** into that false **green**, hiding
genuine auth/quota/startup/runtime failures. The `saw_success` gate is
the load-bearing safety; the message match is a conservative second gate.
Genuine pre-success failures still reach `capture_subprocess_failure` /
the error-translation path unchanged.

---

## Resolved open questions

- **OQ1 → D1.** Success signal: `subtype == "success"`.
- **OQ2 → D2.** Wrapper shape: pass-through async generator.
- **OQ3 → D3.** Teardown matching: `saw_success` gate (primary) +
  `"command failed"` substring (secondary); `Exception` only, never
  `BaseException`.

---

## Execution log — 2026-07-20

Design approved as drafted; execution armed by the chair 2026-07-20.

**Already landed before this session (PR #1099):** T1 — the
`iter_agent_messages` + `_is_benign_teardown_exit` wrapper in
`agent_sdk_adapter.py`, its unit tests
(`tests/unit/workflows/test_iter_agent_messages.py`: R1 recover,
R2 pre-success propagates, R3 non-success propagates, D1
`is_error=True`-with-`subtype="success"` still recovers,
message-mismatch post-success propagates, `BaseException`
propagates, clean stream passes through), and T2 adoption in the
eight spec-named workflows.

**This session — scope drift corrected + T2 completed + guards:**

- Grepping the actual `async for … in claude_agent_sdk.query(`
  instances (per the spec-scope-drift lesson) found SEVEN more
  consumption loops the spec's list predated: `refactor_plan`,
  `release_prep`, `deep_review`, `test_gen/workflow`,
  `test_audit/workflow`, `doc_audit/workflow`,
  `document_gen/workflow`. All seven now wrap the query in
  `iter_agent_messages(...)` — the same one-line adoption, no other
  body changes. No `claude_agent_sdk.query(` call sites exist
  outside `src/attune/workflows/`.
- Regression guard added
  (`test_every_workflow_query_loop_is_wrapped`): scans
  `src/attune/workflows/**/*.py` and fails on any bare
  `async for … in claude_agent_sdk.query(` loop, so a new workflow
  or a revert cannot silently reintroduce the discarded-success bug.
- `CHANGELOG.md` `### Fixed` entry added.

**Receipts (probes actually run):**

- `pytest tests/unit/workflows/test_iter_agent_messages.py`
  (serial, `-o addopts=`): 8 passed.
- Existing unit tests for the seven newly wrapped workflows
  (doc_audit, document_gen, test_audit, test_gen dirs +
  deep_review / refactor_plan / release_prep / parallel_test_gen
  execute+behavioral files, serial): 531 passed.
- Coverage on the seven modified modules (coverage-from-/tmp
  worktree dance): 98% total — deep_review 91%, test_audit 99%,
  test_gen 99%, doc_audit / document_gen / refactor_plan /
  release_prep 100%.
- Pinned pre-commit `black` + `ruff` pre-flighted on all touched
  files: Passed.
- D3 false-green constraint unchanged: the wrapper still re-raises
  everything pre-success (R2/R3 tests), so genuine failures reach
  `capture_subprocess_failure` / error translation as before; the
  dispatcher's exit-0-on-`success=False` behavior was not touched.

**T3 dogfood receipt (2026-07-20, chair-authorized spend):** a real
`CodeReviewWorkflow` run at quick depth over a planted-issue temp
file, executed nested inside a live Claude Code session (the repro
condition), returned `success=True`, `subtype="success"`,
`is_error=False`, cost $0.60, 7 turns, with genuine findings (the
planted command injection and path traversal). The teardown exit did
NOT fire on this particular run (adapter guard warning absent — the
stream ended cleanly), so the recovery branch was not exercised
live; the design's T3 validation (success + findings + cost > 0
while nested) is met, and the guard-fire path remains proven by the
unit suite.

---

## Cross-references

- `docs/specs/archive/sdk-error-message-fidelity/` — flagged this case;
  this spec finishes its deferred note.
- `~/.claude/projects/.../memory/project_sdk_workflows_blocked_nested.md`
  — nested-SDK investigation; confirms `ResultMessage(subtype="success")`
  arrives before the teardown exit; env-scrub workaround stays dev-only.
- The false-green dispatcher behavior (`attune workflow run` exits 0 on
  `success=False`) — the constraint D3 must not worsen.
- Seam: `src/attune/workflows/agent_sdk_adapter.py`
  (`collect_agent_output`); `code_review.py:396-400` (representative
  consumption loop).

---

## 2026-07-20 — Design approved + execution armed (chair: Patrick)

Ruled in the chair-rulings sitting (stepped-through review). The
design stands as drafted with the already-resolved D1–D3 (success
signal `subtype == "success"`; pass-through async generator at the
`collect_agent_output` seam; `saw_success` gate primary +
`"command failed"` substring secondary, `Exception` only).
Implementation may proceed — one seam, regression-guarded, with
the named constraint that the false-green dispatcher behavior
(`attune workflow run` exits 0 on `success=False`) must not
worsen.
