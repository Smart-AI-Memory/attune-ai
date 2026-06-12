# Lessons Corpus via RAG — Decisions

## D1 — Phase 0 go/no-go matrix (PRE-COMMITTED 2026-06-11)

Committed BEFORE the benchmark runs, per the "pre-committed decision
matrices survive contact with data" discipline. The commit timestamp
is the arbiter.

**Benchmark shape:** ~25 golden queries, each phrased as a realistic
*trap moment* (the situation an agent is in when the lesson should
fire), mapped to the governing lesson. Corpus = one document per
lesson from the `.claude/CLAUDE.md` Lessons section, summary = the
lesson's bold title. Retriever = attune-rag keyword retrieval
(shipped default), no tuning beyond wiring summaries correctly
(the metadata-reaches-the-retriever check runs first).

**Metrics:** P@1 and P@3 over the full set; P@3 reported separately
for the high-severity subset (queries whose miss would cause secret
exposure, data loss, broken main, or wasted money).

| Result (P@3, full set) | Decision |
|---|---|
| ≥ 80% AND high-severity P@3 = 100% | **GO** — proceed to design (tiered split per R2) |
| 60–79%, or high-severity miss | **ITERATE ONCE** — fix corpus summaries/keywords only (no retriever changes), re-run; then GO/NO-GO on the re-run against the same thresholds |
| < 60% after the iterate pass | **NO-GO** — keyword retrieval insufficient; record numbers, evaluate the fastembed arm as a SEPARATE pre-committed decision, or close |

**Context-cost number is motivational, not a gate** — it sizes the
prize but cannot rescue a failed retrieval gate (R4 dominates).

High-severity queries are tagged in the fixture before the first
run, not after.

## D2 — Phase 0 results (2026-06-11) — **GO**

Harness: `scripts/phase0/lessons_rag_benchmark.py` (in-tree,
re-runnable). Fixture: `golden_queries.json` (frozen; authored before
the first run). Matrix commit `17c81199` predates this result.

**Context cost (R1a):** the Lessons section is **417,252 chars
(~116k tokens) — 58% of a 200k window, every session**, across
**375 top-level lessons**. CLAUDE.md total is 422,645 chars; Lessons
is 99% of it.

**Retrieval quality (R1b):** keyword retriever, summaries verified
reaching all 375 entries before scoring.

| Metric | Result | Gate |
|---|---|---|
| P@3 (full set, 25 queries) | **84%** | ≥ 80% ✓ |
| High-severity P@3 (7 queries) | **7/7 = 100%** | 100% ✓ |
| P@1 | 68% | informational |

**Matrix verdict: GO** — proceed to design (tiered split per R2).
No iterate pass needed; the misses below inform design rather than
blocking.

**The 4 misses, read honestly:**

- `windows-crlf` and `dispatch-table-mock` — both targets are
  **consolidated mega-lessons** ("Cross-platform … has many Windows
  surfaces", "Mocking & patching — get the target right, then the
  pitfalls") whose specific sub-item didn't outweigh smaller sibling
  docs. **Design implication:** at ingest, split consolidated
  multi-bullet lessons into atomic sub-documents (one per sub-bullet,
  parent title prefixed). The consolidation that helps a human reader
  hurts retrieval granularity.
- `subscription-sdk-fail` — the #1 hit was
  `diagnosing-sdk-workflow-failures…`, which genuinely covers the
  trap (exit-1 diagnosis incl. the subscription case). The fixture's
  expected set was arguably too narrow; recorded as a miss anyway
  (no post-hoc fixture edits), but the practical answer retrieved
  was useful.
- `merge-errored-but-merged` — keyword collision inside the
  branch-protection lesson family; the family surfaced, the exact
  member didn't. Same atomic-split fix likely helps (the target is
  itself a 3-bullet consolidated lesson).

**Carry-forward into design:** (1) atomic sub-document splitting at
ingest; (2) summaries-as-titles is sufficient signal — no LLM polish
pass needed for v1; (3) the splitter must be wrap-aware (titles span
lines at the 72-char wrap — first naive split captured 69/375 docs;
the harness's `split_lessons` handles it).

## D6 — 8.4.0 live receipts (2026-06-12, first post-restart session)

The three receipts the cutover (T5) is gated on, captured in the
first session running the 8.4.0 plugin hooks — with one load-bearing
root-cause find along the way.

**Root cause first: ALL hooks were dark at session start.** Plugin
hooks run under the pyenv shim, whose editable install resolves
`attune` from the MAIN `~/attune-ai` checkout — which was still
parked on `docs/decisions-backlog-catchup` (late May). That checkout
predates `attune.lessons` (#771) and `backend_status` (#769), so the
SessionStart health line swallowed an ImportError and
`lesson_recall.py` was silent on every prompt — while AMS +
redis-stack (launchd-managed) were healthy the whole time. Unparked
the checkout (stale branch's unique commit verified `-` in
`git cherry`; dirty edits snapshotted to a patch), and every hook
went live immediately — hooks are fresh subprocesses per fire, so no
session restart was needed.

**Receipt 1 — SessionStart health line.** Silence is the HEALTHY
state: the shipped line is warn-only (prints only when
`unreachable_upgrade` is set). Verified directly:
`backend_status()` → `{"backend": "AMSMemoryBackend",
"fallback": false, "unreachable_upgrade": null}`. Caveat recorded:
warn-only silence is ambiguous with import-failure silence (exactly
how the parked-checkout outage hid) — an info-level one-liner naming
the backend would disambiguate; left as a possible tweak, not a
blocker.

**Receipt 2 — recall hooks fire live in-session.** `jit_recall.py`
(PreToolUse) fired organically on an `AskUserQuestion` call in the
live session, injecting the question-shape rule. `lesson_recall.py`
(UserPromptSubmit) probed via the real plugin-cache hook against the
real corpus: the squash-merge-tag trap prompt injected the
Tag-mechanics lesson as `additionalContext`, exit 0; "Auto run 4"
(below the 20-char floor) correctly stayed silent. Organic
injection on a substantive user prompt is expected from the next
prompt onward (pre-unpark prompts were silent for the import
reason above).

**Receipt 3 — `/recall` two-store search.** Query "tagging a release
after a squash merge": lessons store returned the exact child
sub-lesson *"Don't tag before a squash-merge"* plus the
post-squash-local-main and AFK-pull lessons, labeled `[lesson]` with
scores; session-findings store answered via AMSMemoryBackend
(fallback: false) with recent stashed notes — none tag-specific yet
(young soak), reported honestly as such.

**Outstanding for the T5 gate:** the Stop-hook stash receipt
(`~/.attune` stash.log + a new finding written at a real session
end on the fixed code) — the soak is now running on current code.
