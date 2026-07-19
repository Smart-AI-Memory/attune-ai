## Requirements

**MI-1 — The Stop hook plugin/hooks/session_stash.py correlates the session's surfacing records against the transcript tail and emits one memory_signal verdict record per surfaced item.**
- Given a session with N surfacing events in ~/.attune/telemetry/memory_events.jsonl (lesson_recall, jit_recall, session_recall), running the Stop hook against that session's transcript produces verdict records keyed on (surfacing_id, lesson_id|rule_id|finding_id) for every surfaced item; a missing key pair for any surfaced item fails the probe.
- Verdict records are written via the existing attune.telemetry.memory_events.log_memory_event(event="memory_signal", ...) writer (respecting _enabled(), _events_path(), _rotate_if_huge()), not a parallel writer; a grep showing a second jsonl write path fails the probe.
- Each verdict record carries the session_id and the source event type, so a reader can join verdicts back to their surfacing without re-parsing transcripts.

**MI-2 — The verdict label set is exactly acted_on / ignored / wrong / unscored, and unscored is emitted — never a heuristic guess — when Ollama is unavailable.**
- With Ollama stopped (or _extract_via_ollama returning None per its existing unavailable/timeout contract), every verdict emitted for that session is unscored; any acted_on/ignored/wrong label produced without an Ollama round-trip fails the probe. The _extract_heuristic fallback path is NOT used for verdicts (per the decisions.md rationale: "a garbage label is worse than none").
- A record with any label outside the four-value set fails schema validation in the reader (MI-5).
- The wrong label is reachable in practice: a test fixture modeled on the 2026-07-08 stale /recall findings (surfaced items whose referenced bugs were already fixed, and the transcript shows the session identifying them as stale/incorrect) is scored wrong, not ignored.

**MI-3 — Verdict scoring uses only the transcript tail already read by the hook and a LOCAL Ollama call; no network egress, no paid-API calls.**
- Input to the scorer is bounded by _read_transcript_tail(transcript_path, max_chars); the scorer accepts the tail text plus the session's surfacing records and nothing else.
- A network-capture (or code-audit) probe shows the only model call is the local Ollama endpoint already used by _extract_via_ollama-style calls; any anthropic-SDK or remote-HTTP call in the verdict path fails the probe (telemetry is local-only, no phone-home).

**MI-4 — The Stop hook never blocks or breaks session end, regardless of scorer failure.**
- With a corrupt memory_events.jsonl, an unreadable transcript, an Ollama timeout, or an unwritable telemetry dir, the hook still exits successfully and completes its existing stash duties; a nonzero exit or raised exception in any of these injected-failure probes fails the requirement.
- All failure handling catches specific exceptions (no bare except:) and degrades silently per repo hook policy.

**MI-5 — An ops/data.py reader aggregates memory_signal verdicts into the noise denominator that estimate_intervention_signal's caption declares missing.**
- The reader returns, at minimum: counts per verdict label, the noise ratio (wrong + ignored relative to scored surfacings), and the unscored count reported separately (unscored surfacings are excluded from the denominator, not silently folded into either side); a fixture jsonl with known verdicts yields exactly the expected counts.
- estimate_intervention_signal (ops/data.py:1069) and/or its rendered caption is updated so callers can present the measured denominator alongside the upper-bound count; the caption no longer claims the denominator is missing when verdict data exists, and it degrades to the current upper-bound-only caption when no verdicts exist.
- No output anywhere in the reader or caption is a "savings percentage" — a grep of the new surface for percent-savings framing fails the probe if found (ratified frame: premium efficiency + tail-prevention net of noise, never savings %).

**MI-6 — At least one NON-MOCKED round-trip receipt proves the pipeline: real surfacing write → real Stop-hook scoring run → real reader aggregation.**
- A test (or receipt script) writes a real surfacing event via log_memory_event, runs the actual hook code path against a real transcript file on disk, and reads the resulting verdict back through the ops/data.py reader — no mocked Ollama client in this one path (it may run in unscored mode if Ollama is absent, which itself exercises the real degradation contract).
- Changed code ships with type hints, docstrings on public APIs, and >=80% coverage; no eval/exec.

## Non-goals

- Task-shape routing taxonomy. Routing decisions FALL OUT of measured noise later; this step only produces the measurements. No routing logic, no up-front task-shape enum.
- Any savings-percentage metric or dashboard. Explicitly barred by the ratified frame.
- Changes to the STEP 1 writers or event schemas (lesson_recall, jit_recall, session_recall records shipped in PR #1366) beyond adding the new memory_signal event type.
- Heuristic verdict labeling. No _extract_heuristic-style fallback verdicts; unavailability yields unscored only.
- Phone-home or remote scoring. Telemetry stays local-only.
- Retroactive scoring of historical sessions. The hook scores the session it fires for; a backfill tool is out of scope.

## Open questions

1. Verdict granularity vs. cost: a jit_recall event can carry multiple rules per surfacing. Is one Ollama call per surfacing (batched items in one prompt) acceptable, or one per item? The pack fixes the join key but not the call budget, and Stop-hook latency is user-visible at session end.
2. ignored in the denominator: the pack says tail-prevention is "NET of false surfacings." Is ignored noise (counts against), neutral (excluded like unscored), or a separate reported class? MI-5 currently treats it as noise; chair should ratify.
3. Rotation vs. join integrity: _rotate_if_huge() can rotate surfacing events away before or after their verdicts land. Should the reader tolerate orphaned verdicts (count them on verdict fields alone), or must rotation keep surfacing+verdict pairs together?
4. Unscored-event emission: when Ollama is down for a whole session, do we write N unscored records (denominator completeness, more jsonl volume) or one session-level marker? MI-2 assumes per-item records; cheaper alternatives exist.
5. Which Ollama model and prompt contract: the pack establishes the mechanism (_extract_via_ollama-style local call) but not the model tag, prompt shape, or how label parsing failures (malformed model output) map to unscored.
