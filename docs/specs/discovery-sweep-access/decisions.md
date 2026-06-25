# Discovery-Sweep Access — Decisions

Decisions recorded during scoping. Agent recommendations marked; Patrick
to confirm/edit in spec review.

---

## D1 — Surface scope: MCP tool + thin skill

**Decided (Patrick, 2026-06-25).** Add a `discovery_sweep` MCP tool plus a
thin skill. Not full first-class (no dedicated CLI command, no
`features.ts`); not MCP-only (would stay undiscoverable); not skill-only
(inconsistent with the other 21 workflows). This is the smallest change
that closes the access gap and matches the sibling pattern.

## D2 — Response format: force `output_format="json"`

**Agent recommendation.** The handler forces `output_format="json"` so
the MCP response carries `queue` / `questions` / `rejected` as structured
data Claude can act on, rather than pre-rendered markdown. The CLI keeps
its markdown default; only the MCP surface forces json. Rejected
alternative: return markdown (simpler, but Claude would have to parse
prose to act on findings).

## D3 — Input surface: `path` + `budget_usd` + `no_llm` only

**Agent recommendation.** Expose only kwargs `execute()` actually accepts
and that a caller reasonably sets: `path` (required), `budget_usd`,
`no_llm`. Deliberately omitted: `min_severity` (not an `execute()` kwarg —
the threshold is in `verification.py`); `source` filter and `sweep_id`
(power-user / correlation knobs, not needed for the interactive surface);
`event_sink` (daemon-only, out of scope). Keep the tool surface minimal;
widen later only if a use case demands it.

## D4 — Auto-trigger disambiguation

**Agent recommendation.** The skill auto-triggers on aggregate-intent
phrasing only — "run all audits / full sweep / audit everything / what
should I fix / triage findings" — and explicitly does **not** claim the
single-audit phrases owned by `security-audit`, `bug-predict`,
`code-quality`/`deep-review`, or the multi-workflow phrase owned by the
explicit-only `workflow-orchestration`. Follows the #1068 lesson
(disambiguate auto-trigger phrases so the right skill fires). Fallback if
phrasing proves greedy in practice: make the skill explicit-only.

## D5 — No engine changes

**Decided.** This spec is surface-only. `workflow.py`,
`verification.py`, and `sources/` are untouched. If the json return path
turns out to need a shape tweak for clean bucket extraction, that is a
separate, explicitly-flagged change — not folded in silently.

## D6 — Out-of-scope boundary with the ops daemon

**Decided.** The `event_sink` / scheduled-daemon use case stays in its own
`discovery-sweep-ops-integration` Phase-2 track. This spec does not touch
it; the interactive MCP surface and the daemon surface are independent.

---

## Open for review

- **OQ1:** Confirm D2 (force json) vs. returning markdown — does any
  expected caller want the rendered report instead of structured buckets?
- **OQ2:** Confirm D4's trigger phrasing, or start explicit-only and add
  auto-triggers after observing real shadowing behavior.
