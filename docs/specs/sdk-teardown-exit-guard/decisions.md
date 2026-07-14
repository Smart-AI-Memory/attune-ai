# Decisions: SDK teardown-exit-1 guard

**Status:** DRAFT (2026-06-26) — recommitted at 2026-07-14 triage (failure class still live)
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
