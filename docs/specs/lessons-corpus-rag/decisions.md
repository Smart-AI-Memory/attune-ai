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

## D2 — Phase 0 results

*(pending — filled after the benchmark runs)*
