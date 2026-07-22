# Cross-Provider Session Handoff — Decisions

Dated chair rulings. Newest last.

## 2026-07-22 — Feature ratified (roundtable)

Roundtable `q-multi-llm-obvious-win-001`: 2/3 seats independently
converged on the tool-mediated cross-provider handoff. Chair ruling
promoted the report and RATIFIED `handoff_create`/`handoff_resume`
as the next multi-LLM feature. Same-day amendment: `cross_review`
also ratified, sequenced second. Report:
`docs/reports/roundtable/q-multi-llm-obvious-win-001.md` (#1600).
Tracking issue: #1601.

## 2026-07-22 — Scheduling amendment (chair)

Spec AUTHORING moved pre-07-27 ("staged for implementation the 27th
or near after" — chair, in-session); IMPLEMENTATION stays post-lift.
Authoring runs against the held transport stack's code
(#1593→#1598), which merges at the 07-27 sitting.

## 2026-07-22 — Requirements APPROVED (chair)

R1–R6 + non-goals as drafted. Binding highlights: no fabricated
verification rows (R1); resume is a report, not a go signal (R2);
degrade-silent memory linkage with stated skip (R3); terse-by-
default caps as a requirement, not style (R5); live cross-provider
receipt required, honest UNPROBED until the named client runs (R6).

## 2026-07-22 — Design RATIFIED (chair)

D1 frontmatter-over-template packet; D2 read-only subprocess git in
`src/attune/handoff/`; D3 five report-only drift codes,
verified-first report order; D4 caps 8 KB / 2 KB reject-with-reason,
one packet per branch with `superseded_at`; D5 memory linkage via
the session-stash helpers; D6 one structlog event per tool. CLI
wrapper, auto-invocation, and cross-repo packets explicitly out.

## 2026-07-22 — Tasks APPROVED (chair)

T1 core module → T2 MCP surface → T3 memory/telemetry (post-lift
only) → T4 docs + live receipt (post-distribution). T1/T2 have no
transport dependency and MAY build early as held drafts if a slot
opens; T3/T4 wait for the lift. Spec is now fully authored —
requirements APPROVED, design RATIFIED, tasks APPROVED, all
2026-07-22; implementation staged for the 07-27 sitting or after.

## 2026-07-22 — T1+T2 BUILT (held draft #1605); one scope deviation

Both tasks executed same-evening as held draft #1605
(`claude/handoff-t1-t2`, hold-until-07-27). Deviation from tasks.md
T2 wording: the real-dispatch integration tests live in a NEW file
(`tests/integration/test_mcp_dispatch_handoff.py`) instead of
extending `test_mcp_dispatch.py` — that module is modified by held
PR #1594, and extending it would create a held-queue collision at
the lift. Intent (real server, real dispatch table, real core)
preserved. Receipts on the PR: 22 handoff unit tests + 86-test
serial sweep (dispatch/counts/reference-validation) + quality
ratchet green. Also recorded there: tool counts 49 core / 55 with
redis; CHANGELOG entry owed at lift per the drafts-doc pattern.
