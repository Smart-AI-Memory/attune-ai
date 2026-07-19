1. **MI-1 — Missing Surfacing Discovery & Query Logic**
   MI-1 specifies that the Stop hook must generate a verdict for every surfaced item in the session, but it fails to define how `session_stash.py` discovers and reads those surfacing records at session end. Without explicit logic to query `~/.attune/telemetry/memory_events.jsonl` filtered by the current `session_id`, the hook has no input dataset of surfaced items to evaluate.
   *Resolution:* Update MI-1 to explicitly require `session_stash.py` to filter `memory_events.jsonl` for events matching `session_id` (`lesson_recall`, `jit_recall`, `session_recall`), handling file read errors or missing logs by emitting zero verdicts without failing the hook (per `session_stash.py` facts and pack item 2: `surfacing_id` join key).

2. **MI-2 — Undefined Fallback for Malformed Ollama Responses**
   MI-2 specifies that `unscored` is emitted when Ollama is unavailable (returning `None`), but it does not specify how the hook handles malformed model output, schema mismatches, or unexpected strings returned by Ollama. If malformed output bypasses fallback handling and emits a invalid label, it will trigger schema validation failures downstream in `ops/data.py` (MI-5).
   *Resolution:* Require that any label parsing error, JSON decoding failure, or out-of-spec string returned by Ollama must immediately fall back to emitting an `unscored` verdict for that item (per `session_stash.py` `_extract_via_ollama` contract in pack item 4 and pack item 3: "a garbage label is worse than none").

3. **MISSING — Unbounded Execution Latency & Call Budget in Stop Hook**
   The draft contains no performance or batching constraints for verdict scoring inside `session_stash.py`. Executing sequential Ollama HTTP calls for sessions with multiple surfaced items will introduce noticeable user-facing delay during session teardown, violating the non-blocking hook contract.
   *Resolution:* Add a requirement to MI-3 mandating a single batched Ollama prompt pass per session for all surfaced items with an aggregate wall-clock timeout (e.g., 3.0 seconds max); if the timeout is exceeded, all surfaced items for that session must degrade to `unscored` (per `session_stash.py` facts in pack item 4: "hook must never block session end").

4. **MI-5 — Noise Ratio Conflates `wrong` (False Positives) and `ignored` (Passive Adherence)**
   MI-5 defines the noise ratio numerator as `(wrong + ignored)`, treating unreferenced injections identically to invalid/stale injections. This conflation penalizes passive adherence where a user follows injected guidance without explicitly commenting on it in the transcript tail, distorting the metric.
   *Resolution:* Redefine the noise ratio in `ops/data.py` to isolate hard noise as `wrong / (acted_on + wrong)`, while tracking `ignored` as a separate unreferenced injection rate (per pack item 1: ratified frame of tail-prevention net of noise, and pack item 6: 2026-07-08 stale findings datum representing true `wrong` noise).

5. **MISSING — Log Rotation Vulnerability (`_rotate_if_huge()`)**
   The draft does not specify how `ops/data.py` handles log rotation. If `_rotate_if_huge()` rotates `memory_events.jsonl` between the surfacing event write and verdict emission or reader aggregation, surfacings and verdicts may end up split across active and rotated files (`memory_events.jsonl.1`).
   *Resolution:* Require the `ops/data.py` reader to parse self-contained metadata (`surfacing_id`, `session_id`, source event type, item ID) directly from `memory_signal` records, or iterate across rotated `memory_events.jsonl*` files so orphaned verdicts do not break aggregation (per pack item 2: `log_memory_event` writer with `_rotate_if_huge()`).

6. **MI-6 — Incomplete CI Verification Coverage for Scored Verdict Labels**
   MI-6 demands a non-mocked round-trip receipt and notes it may run in `unscored` mode when Ollama is absent. However, in headless/keyless CI environments where Ollama is unavailable, this receipt will only ever test the `unscored` degradation path, leaving the `acted_on`, `ignored`, and `wrong` parsing logic unverified in automated testing.
   *Resolution:* Split the receipt criteria in MI-6 into two distinct verification requirements: (1) a non-mocked disk integration test asserting `unscored` fallback when Ollama is offline, and (2) a hermetic test using a local HTTP server fixture simulating the Ollama API response to verify `acted_on`, `ignored`, and `wrong` label paths in CI (per pack item 5: non-mocked round-trip receipt required for hook pipelines, and CI notes).

VERDICT: ready-with-edits

Single most important item: Item 3 (Batched single-pass Ollama call with strict timeout in `session_stash.py`), because sequential per-item local model calls will cause user-visible latency at session teardown and risk violating the non-blocking hook constraint (per pack item 4).
