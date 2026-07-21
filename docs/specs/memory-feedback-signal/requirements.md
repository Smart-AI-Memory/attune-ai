# Memory Feedback Signal (STEP 2) — Requirements

**Status:** shipped (2026-07-19 — chair approved all seven items
per-REQ AND implemented same day in #1459; MI-6a/b/c receipts in
[decisions.md](decisions.md)) — authored by the round table in its first
V2-P1 spec-authoring loop (thread `mem-signal-001`, three rounds:
draft → adversarial critique ×2 → revision; full record in
[decisions.md](decisions.md)). Implements the memory-as-insurance
frame's owed design pass: the Stop-hook verdict scorer and the
noise-denominator reader (STEP 1 shipped in PR #1366; scoping in
`docs/specs/memory-recall-eval/decisions.md`, which remains the
benchmark spec).

Chair ruling on OQ-1 folded into MI-5: **`wrong_rate =
wrong / (acted_on + wrong)` is the headline hard-noise metric**;
`ignored_rate` is co-reported, not noise (an ignored surfacing on a
quiet day is expected premium under the insurance frame); the
combined candidate-noise rate stays available as a reversible field.

## Requirements

**MI-1 — The Stop hook (`plugin/hooks/session_stash.py`) snapshots the session's surfacing set BEFORE rotation can disturb it, and emits one `memory_signal` verdict per *recoverable* surfaced item.**
- At hook entry, filter `~/.attune/telemetry/memory_events.jsonl` (and any rotated `memory_events.jsonl*` siblings) for the current `session_id` across `lesson_recall`/`jit_recall`/`session_recall`, and snapshot that set BEFORE any `_rotate_if_huge()` call can run — so surfacing→verdict correlation cannot be split mid-run.
- Emit exactly one verdict keyed on `(surfacing_id, lesson_id|rule_id|finding_id)` for every item in the snapshot. Completeness is defined over RECOVERABLE surfacings: an already-rotated-away surfacing is not a probe failure; a missing key pair for a snapshot item is.
- Idempotent: re-running the Stop hook against the same JSONL for the same session produces no duplicate verdicts (dedup on the full join identity). Absent or reused `session_id` is handled by treating `(session_id, join key)` as the unit.
- A missing/unreadable `memory_events.jsonl` yields zero verdicts and the hook still succeeds.
- Verdicts are written only via `attune.telemetry.memory_events.log_memory_event(event="memory_signal", ...)` (respecting `_enabled()`, `_events_path()`, `_rotate_if_huge()`); a grep showing a second jsonl write path fails the probe. The new `memory_signal` record MAY carry `source_event` and `session_id`; STEP 1 event schemas (`lesson_recall`/`jit_recall`/`session_recall`) stay immutable.
(table: agreed 3-0)

**MI-2 — The label set is exactly `acted_on` / `ignored` / `wrong` / `unscored`, and `unscored` is the ONLY output whenever a trustworthy label cannot be produced — never a heuristic guess.**
- `unscored` is emitted (never `_extract_heuristic`) when ANY of: Ollama unavailable/timeout (`_extract_via_ollama`-style `None`); malformed, partial, or non-schema model output; JSON/parse failure; OR the bounded transcript tail contains insufficient evidence about that item.
- Insufficient-evidence→`unscored` is explicit and probed: an item surfaced early in a long session whose subsequent use falls outside `_read_transcript_tail(transcript_path, max_chars)` is `unscored`, NOT `ignored` (bounded tail ≠ "ignored").
- Any label outside the four-value set fails reader schema validation (MI-5).
- `wrong` is reachable: a **controlled-scorer** unit fixture modeled on the 2026-07-08 stale `/recall` datum (surfaced items whose referenced bugs were already fixed; transcript identifies them as stale) scores `wrong`. The real-Ollama path is exercised only in the integration receipt (MI-6) — no unit test asserts an exact label from a live nondeterministic call.
(table: agreed 3-0)

**MI-3 — Scoring uses only the bounded tail plus a single batched LOCAL Ollama pass, under a hard latency ceiling, with no remote egress.**
- Scorer input is `_read_transcript_tail(...)` plus the snapshot's surfacing records and nothing else.
- One batched Ollama call per session (chunked into bounded sub-batches only if item/token count exceeds a threshold), governed by a single aggregate wall-clock timeout (default ~3.0s). Any item not scored at timeout → `unscored`; the hook still exits success.
- Transport is restricted to loopback/local Ollama; a configured non-loopback endpoint is rejected. A network-capture or code-audit probe shows no remote host contacted and no anthropic-SDK / remote-HTTP call anywhere in the verdict path (telemetry stays local-only).
- The prompt and model tag are pinned/versioned with deterministic inference settings where the Ollama API supports them.
(table: agreed 3-0)

**MI-4 — The hook never blocks or breaks session end; failure is isolated to verdict scoring.**
- Invariant: successful hook exit PLUS preservation of every duty whose inputs remain available. An unreadable transcript disables ONLY transcript-derived verdict work (its items degrade to `unscored`/skipped) and must not fail the independent stash duties.
- Injected-failure probes — corrupt `memory_events.jsonl`, unreadable transcript, Ollama timeout, unwritable telemetry dir — each still exit success; any nonzero exit or raised exception fails the requirement.
- Specific exceptions only (no bare `except:`), logged before degrading.
(table: agreed 3-0)

**MI-5 — An `ops/data.py` reader aggregates `memory_signal` verdicts into a scoped, deduped denominator, and updates the caption's missing-denominator claim — with no savings %.**
- Scope + dedup: aggregate over the SAME session/time-range population as the rendered estimate; dedup on the full verdict identity; iterate rotated `memory_events.jsonl*` and rely on self-contained record metadata so rotation-split or orphaned verdicts don't break aggregation.
- Returns counts per label; `wrong_rate = wrong / (acted_on + wrong)`; `ignored_rate` separately; and a combined candidate-noise rate — all reported separately so the interpretation stays reversible (see OQ-1). `unscored` is counted and EXCLUDED from every denominator (not folded into either side). A fixture jsonl with known verdicts yields exactly the expected counts.
- `estimate_intervention_signal` (`ops/data.py:1069`) / its caption presents the measured denominator alongside the upper-bound ONLY when ≥1 VALID SCORED verdict exists in the same aggregation scope; otherwise it retains the current missing-denominator / upper-bound-only caption. All-`unscored`, orphaned, or out-of-scope verdicts do NOT flip the caption.
- No savings-percentage framing anywhere in the reader or caption; a grep for percent-savings framing fails the probe.
(table: 2-1 — resolved by chair ruling OQ-1: wrong_rate is the headline; see decisions.md)

**MI-6 — Two non-mocked receipts prove the pipeline: a mandatory keyless `unscored` round-trip in CI, and an Ollama-available real-scoring receipt recorded before release.**
- Receipt 1 (CI-mandatory): real `log_memory_event` surfacing write → real Stop-hook code path against a real on-disk transcript → verdict read back through the `ops/data.py` reader; with Ollama absent, asserts the `unscored` degradation contract end-to-end.
- Receipt 2 (real-scoring, env-gated): with Ollama available, a real model round-trip produces `acted_on`/`ignored`/`wrong` through the actual path, recorded before release. A local HTTP-server fixture simulating the Ollama API MAY additionally exercise the `acted_on`/`ignored`/`wrong` parse paths hermetically in CI so those labels aren't left unverified in keyless lanes.
- Changed code ships type hints, docstrings on public APIs, ≥80% coverage on changed code, and no `eval`/`exec`.
(table: agreed 3-0)

**MI-7 — Untrusted transcript and surfaced-memory text are delimited and strictly output-validated so prompt injection cannot override the label contract.**
- The transcript tail and surfaced content are inserted as clearly delimited, non-authoritative prompt DATA; the scorer validates model output strictly against the four-label schema and maps any non-conforming or injected output to `unscored`.
- Adversarial fixtures (a transcript attempting to force `acted_on`, or to emit a non-schema label) yield only validated labels or `unscored`; a leaked non-schema label fails the probe.
(table: agreed 3-0)

## Non-goals

- Task-shape routing taxonomy. Routing falls out of measured noise later; this step only produces the measurements. No routing logic, no up-front task-shape enum.
- Any savings-percentage metric or dashboard. Barred by the ratified frame.
- Changes to STEP 1 writers or event schemas (PR #1366) beyond adding the `memory_signal` event type (which MAY carry `source_event`/`session_id`).
- Heuristic verdict labeling. No `_extract_heuristic`-style fallback verdicts; unavailability/malformed/insufficient-evidence yields `unscored` only.
- Phone-home or remote scoring. Loopback-only local Ollama; telemetry stays local.
- Retroactive scoring of historical sessions. The hook scores the session it fires for; a backfill tool is out of scope.

## Dissent register

- **MI-5 (Critique A, antigravity).** Minority position, verbatim-faithful: *"Redefine the noise ratio in `ops/data.py` to isolate hard noise as `wrong / (acted_on + wrong)`, while tracking `ignored` as a separate unreferenced injection rate."* A would commit to `wrong/(acted_on+wrong)` as THE noise ratio now. The resolution reports exactly that value as `wrong_rate` but declines to crown it the headline metric, keeping the combined interpretation reversible per Critique B (codex): *"report separate `wrong_rate`, `ignored_rate`, and combined candidate-noise rate so downstream interpretation remains reversible."* Both critics agree on isolating `wrong` from `ignored`; they diverge only on whether to fix the final formula now — deferred to OQ-1. No critique item was rejected; every other item from both critiques was integrated.

## Open questions (all resolved — chair rulings 2026-07-19)

1. **Does `ignored` count as noise in the FINAL health metric?** Pack item 1 says tail-prevention is measured "net of noise" but does not define whether a surfaced-but-unreferenced item (`ignored`) is noise, neutral, or its own class; both critics deferred/separated it rather than settling it. MI-5 reports `wrong_rate`, `ignored_rate`, and a combined candidate-noise rate as separate reversible fields — the chair ratifies which enters the headline health number.
   **RULED (Patrick, 2026-07-19): `wrong_rate` is the headline** —
   `ignored` is NOT noise (a surfaced-but-unreferenced item on a
   quiet day is expected premium under the insurance frame);
   `ignored_rate` is co-reported and the combined rate stays
   available as a reversible field.
