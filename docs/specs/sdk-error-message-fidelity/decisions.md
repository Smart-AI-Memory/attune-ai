# Spec: SDK Error Message Fidelity — Decisions

> Pre-committed decisions per the existing lesson "Pre-committed
> decision matrices survive contact with data." Edits to this file
> after Phase 1 ships require a follow-up PR with rationale.
**Status:** approved (2026-05-24)
---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Implementation path | **Path A — wrap the SDK call site** | No SDK fork, no monkey-patch fragility. Path B (monkey-patch `subprocess_cli`) is rejected: brittle across SDK upgrades, hard to test, smell. The double-spend on Path A only fires on failure paths and the second `subprocess.run` exits in sub-second for quota/auth failures (which dominate the failure modes). |
| Classifier shape | **Hard-coded `(regex, kind, message)` tuples in `agent_sdk_adapter.py`** | Five-ish known shapes is well below the table-driven threshold. Hard-coded reads fine, tests fine, ships fine. Revisit only if the list grows past ~8 shapes or a project-specific override becomes a real ask. |
| Stderr redaction | **Yes — route through `session_redaction.redact()` before persistence + render** | Captured stderr from a `claude` failure could carry API keys (esp. on auth failures where the SDK logs the literal env value). Reusing the existing redactor matches the lesson on "all-paths-touched-by-secrets get redacted" without adding a new code path. Cost: one O(stderr-length) pass per failed run. Acceptable. |
| Chip-classifier defense-in-depth (PR #366) | **Keep for now, simplify in Phase 4** | The log-scan chip classifier solved the same surface from a different angle. Once Phase 1–3 ship, Phase 4 reads the typed `kind` from the persisted run record and stops scanning the log text. Defense-in-depth stays until the new typed channel proves itself in production. |
| Exception type | **`SdkSubprocessError(message, stderr, kind, original_exc)`** | Single dataclass-style exception in `agent_sdk_adapter.py`. `kind` is an enum (`Literal["api_quota","auth","rate_limit","not_found","schema_rejected","unknown"]`). `original_exc` retains the SDK's wrapped Exception so callers / tests can chain. |
| Persistence surface | **Add `sdk_stderr: str \| None` + `sdk_error_kind: str \| None` to `Run.to_record()`** | Two new fields, both nullable. No schema migration needed — older run records read them as missing → None → render falls back to the legacy "What Went Wrong" block. |
| Render placement | **Collapsible `<details>` on `/runs/<id>/view`, below "What Went Wrong"** | Default-collapsed so the page stays scannable; one click to expand the raw stderr. Matches the existing run-view info hierarchy. |
| Scope of v1 rollout | **Six workflows: `code-review`, `security-audit`, `bug-predict`, `perf-audit`, `refactor-plan`, `dependency-check`** | The high-traffic SDK workflows Patrick exercised during the 2026-05-24 dashboard run. Hits the most common surfaces fast. Other SDK workflows (`test-audit`, `doc-audit`, `doc-gen`, `discovery-sweep`, `secure-release` pipeline, `deep-review`) get the same treatment in Phase 5 once the API stabilizes. |

---

## Open questions (resolved)

1. **Should the classifier be table-driven (config file) or hard-coded?**
   **Hard-coded** for v1; table-driven if the list grows past ~8 shapes. See matrix.

2. **Should the captured stderr be redacted before persisting?**
   **Yes**, reuse the existing `session_redaction.redact()`. See matrix.

3. **Does PR #366's chip-classifier get simplified once this lands?**
   **Yes, in Phase 4**, not earlier. Defense-in-depth holds until typed channel proves out. See matrix.

---

## Carryover

- 2026-05-24 — Initial decisions captured during spec build-out, triggered by the morning's firefight on the same surface (PR #452 was a separate symptom of the same root cause). Patrick.

- 2026-05-31 — **Phase 3 split + side-channel architecture decided.** Implementation revealed the runner spawns the CLI as a subprocess (`asyncio.create_subprocess_exec`) and doesn't directly hold `WorkflowResult` objects. The original Phase 3.2 ("`RunnerService._execute()` pulls fields off `WorkflowResult.metadata`") needs an architectural mechanism the spec didn't specify. **Decision: env-gated stdout side-channel** mirroring the existing `ATTUNE_DS` pattern (`src/attune/workflows/discovery_sweep/ds_stdout.py`). New module `src/attune/ops/run_meta_stdout.py` defines `ATTUNE_RUN_META key=value` line grammar gated by `ATTUNE_RUN_META_EMIT=1`. CLI emits one line per metadata field after the formatted output; runner sets the env var when spawning the subprocess and parses these lines from the stdout it's already reading. Env-gated (not non-TTY-gated) so legitimate users piping `attune workflow run X > out.md` don't see the marker lines in their file — per the existing CLAUDE.md lesson on `ATTUNE_DS_EMIT`. **Phase 3 splits into 3a** (schema + render, independent, ~45 min) **and 3b** (CLI emit + runner consumer, wires the data flow, ~1 hr). 3a renders no-op until 3b lands. Patrick.
