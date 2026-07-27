# Feature Lead Governance — Decisions

**Status:** DRAFT decision register (2026-07-26)

No design decision in this file is ratified until Patrick rules on it.

## Proposed D1 — feature lead, not permanent model owner

Recommend `feature lead` as the canonical role. It communicates
temporary, feature-scoped authority and avoids implying that Claude,
Codex, or another provider permanently owns a directory.

**State:** proposed; resolves OPEN-1 if approved.

## Proposed D2 — coherence authority with hard limits

Recommend that the lead resolve requirement-satisfying implementation
choices, while repository rules, required probes, security constraints,
and the human chair remain above the lead.

**State:** proposed.

## Proposed D3 — immutable review, appended disposition

Recommend preserving the reviewer's exact finding and allowing only an
appended lead disposition. This makes disagreement inspectable and
prevents either model from rewriting the other's position.

**State:** proposed.

## Proposed D4 — tracked branch-scoped assignment

Recommend `docs/assignments/<branch-slug>.yaml` as canonical state, with
handoff and board entries carrying references/digests. This survives
provider boundaries and keeps the board from becoming a second source
of truth.

**State:** proposed; resolves OPEN-3 if approved.

## Proposed D5 — integrate before adding a conversational skill

Recommend a pure governance core plus MCP tools, then integration with
handoff and cross-review. Add `/feature-lead` only after dogfood shows
the lifecycle and vocabulary are stable.

**State:** proposed; resolves OPEN-2 if approved.

## Proposed D6 — advisory rollout

Recommend opt-in dogfood. Measure accepted/rejected/preference-only
findings, chair escalations, transfers, and repeated rewrites. Do not
make assignment mandatory until the data shows less churn without
slower delivery.

**State:** proposed.
