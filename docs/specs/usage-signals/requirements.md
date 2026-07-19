# Usage Signals (table-refreshed) — Requirements

**Status: requirements chair-ruled per item** — authored by the
round table (thread `us-refresh-001`); compiled deterministically by
`attune.roundtable.compiler` (V2-P2). Approved items only;
declined: none;
unruled: none.

Chair rulings 2026-07-19: all seven items approved. Third spec-authoring loop, FIRST under armed rotation (interactive): codex drafted per next_owed, claude + antigravity critiqued (12 + 6 cited items); dissent register attested empty, moderator-verified against all 18 critique points. Replaces the 2026-06-11 approved requirements, most of which shipped (D1-D13); prior text preserved in git history.

## Requirements

**US-1 — Phase 0 reach baseline is complete**
The zero-instrumentation inventory and baseline shipped on 2026-06-11 and are closed. Their interpretation must preserve the later evidence caveats: per-package PyPI observations are the usable baseline, mirror traffic is reported separately, and pepy badge totals, aggregate vanity counts, and the attune-rag figure are not evidence of real users.

- Mark the original Phase 0 inventory and baseline DONE, citing D1 and the attune-rag noise decision after its D11b annotation.
- Preserve the package-level observations and mirror-split addendum without presenting known-noise figures as adoption evidence.
- Treat further reach-source discovery as new scope requiring new evidence and a chair-approved decision.
(table: agreed; chair: approved)

**US-2 — Privacy-preserving opt-in usage signaling is complete**
The opt-in pipeline shipped end-to-end and was verified live on 2026-06-20. It defaults OFF, honors `DO_NOT_TRACK` and `ATTUNE_USAGE_PING`, enumerates its payload, validates and rate-limits ingestion, and provides first-run consent prompts through CLI and plugin/MCP channels.

- Mark the original privacy, payload-auditability, ingestion, and consent requirements DONE, citing D4–D9, the 8.6.1 two-channel consent receipt, D11a, and D12.
- Retain default-OFF behavior and the documented environment-variable overrides in `src/attune/telemetry/usage_ping.py`.
- Pin the current default, override precedence, and enumerated payload with regression tests that fail if those contracts drift.
- Treat approximately zero opt-in events as a valid observation, not proof of either zero usage or a broken pipeline.
- Any future default, payload, or consent-flow change requires separately approved scope and a new decision entry.
(table: agreed; chair: approved)

**US-3 — Resolve external usage through bounded direct outreach**
Passive signals have not established whether or how external users use Attune workflows. The remaining discovery task is a privacy-preserving, timeboxed outreach round conducted within this spec.

- Build a candidate set of up to ten qualifying users: people with prior direct Attune contact, a public Attune issue or contribution, or a self-reported installation or use. Stars, downloads, telemetry identifiers, and marketplace counts alone do not qualify.
- Seek approximately five substantive responses about whether Attune is used and, when applicable, which workflows are used.
- Close the outreach round when five substantive responses are received or when ten delivered contacts have had fourteen calendar days to respond, whichever occurs first.
- Record coded respondent identifiers, contact date, channel category, response status, and a minimal finding in `docs/specs/usage-signals/decisions.md`; do not record names, addresses, message transcripts, telemetry identifiers, or unnecessary personal data.
- Report responses and non-responses separately. If the timebox ends without enough evidence, record the external-usage question as unresolved rather than inferring adoption or non-adoption.
(table: agreed; chair: approved)

**US-4 — Make reach capture reliable and incomplete snapshots unmistakable**
The 10.5.0 probe demonstrated that tag-time retries against pypistats can remain rate-limited for more than 50 minutes. The release receipt therefore needs both a capture strategy and an explicit completeness contract.

- Maintain an explicit allowlist of the five expected packages; a complete snapshot contains valid observations for every listed package.
- Capture the before snapshot 24–72 hours before the planned tag and persist it before release activity begins.
- Issue one package batch per attempt, honor server-provided retry guidance, and permit at most two additional attempts separated by at least 60 minutes; reuse already captured package results instead of requesting them again.
- Produce a manifest containing the expected, captured, and missing package names, source, observation timestamp, and completeness status.
- Return non-success for any snapshot missing an expected package. The release may continue only with an unmistakable incomplete-receipt warning; snapshot failure must not silently report completion or indefinitely block tagging.
- Add regression coverage for complete, partial, and zero-package captures, including a simulated 429 boundary.
- A different data source may be introduced only through a chair-approved decision defining its provenance and comparability with the existing baseline.
(table: agreed; chair: approved)

**US-5 — Produce one comparable release reach pair or obtain an explicit waiver**
The failed 10.5.0 tag-time capture cannot be reconstructed retroactively and does not satisfy the original before/after condition. The next planned release using the US-4 strategy is the bounded opportunity to produce the receipt.

- For the next planned release after US-4 ships, capture a complete before snapshot 24–72 hours before tagging and a complete after snapshot 24–72 hours after tagging.
- Both observations must use the same package allowlist, source, field definitions, and completeness threshold.
- Record the pair, computed deltas, and interpretation in `docs/specs/usage-signals/decisions.md`; do not substitute vanity totals, partial captures, or the uninterpreted attune-rag figure.
- Record the scheduled 2026-07-27 read separately as historical evidence about 10.5.0 and outreach; it is not a replacement for a tag-moment snapshot and is not itself this requirement.
- If the next planned release still cannot produce a comparable pair after the bounded strategy is followed, stop retrying and obtain an explicit chair decision to waive or replace this condition.
(table: agreed; chair: approved)

**US-6 — Complete the reach, freshness, and spend dashboard receipt**
The current evidence establishes that dashboard templates and the spend alarm exist, but it does not establish the original R3 done-when across all three panels. Residual scope is limited to making the existing ops dashboard expose and test these exact behaviors; no new dashboard framework is required.

- The reach panel must render the latest complete package snapshot, its observation timestamp, and per-package values; incomplete snapshots must be labeled incomplete and must not replace the latest complete snapshot.
- The freshness panel must display the last-write age of `usage.jsonl` and visibly flag an age greater than 48 hours.
- The spend panel must display the current spend status and the shipped D13 anomaly-alarm state, including the flat-history rule.
- Add or retain regression tests proving all three panels render their source data and proving the freshness flag changes at the 48-hour boundary.
- Verification must exercise the dashboard through its real file-to-render boundary using representative persisted artifacts, not only mocked helper functions.
- Record R3 as DONE only after one receipt demonstrates reach, freshness, and spend together; existing implementation may satisfy any acceptance criterion once that receipt is produced.
(table: agreed; chair: approved)

**US-7 — Close spend work, disambiguate the ledger, and apply the refreshed done-when**
The spend alarm is complete, while duplicate D11 identifiers make consent and attune-rag citations ambiguous. Closure requires a non-destructive ledger annotation and a single refreshed termination condition.

- Mark the original spend-alarm requirement DONE, citing D13, and open no additional spend-monitoring scope absent a demonstrated defect.
- Rename the first D11 entry to D11a and the second D11 entry to D11b without renumbering later decisions or changing their dates, text, or historical order.
- Preserve existing `DEC-*` identifiers; do not convert the ledger wholesale between naming schemes.
- Audit and update references within `docs/specs/usage-signals/`, tracked handoffs, and the tracked memory corpus so consent cites D11a and the attune-rag noise verdict cites D11b.
- The refreshed spec is DONE when US-1 and US-2 remain regression-protected, US-3’s bounded outreach outcome is recorded, US-4 has complete/partial/zero capture receipts, US-5 has either a comparable pair or an explicit chair waiver, US-6 has the three-panel receipt, and the ledger audit is complete.
- Closure evidence must be recorded in `docs/specs/usage-signals/decisions.md` with the commands, artifacts, and observed results used to support each claim.
(table: agreed; chair: approved)

## Non-goals

- Changing usage signaling from default OFF or expanding its payload or consent scope.
- Treating PyPI totals, pepy badges, marketplace counts, mirror traffic, or the attune-rag figure as proof of real users.
- Building a second telemetry pipeline, new growth tooling, or additional analytics providers.
- Repeated tag-time retries or any unbounded attempt to outwait pypistats rate limits.
- Retroactively reconstructing a nonexistent 10.5.0 tag-moment snapshot.
- Rebuilding the existing ops dashboard framework.
- Expanding the shipped spend alarm beyond the three-panel integration receipt.
- Collecting outreach transcripts, telemetry identities, or unnecessary personal data.
- The bounded repairs to the already-shipped reach snapshot and dashboard artifacts in US-4 through US-6 are explicitly permitted and are not new instrumentation.

## Dissent register

Empty — attested: all critique items absorbed.
