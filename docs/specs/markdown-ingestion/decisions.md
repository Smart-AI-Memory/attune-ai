# Tolerant Markdown Ingestion — decisions

Decision log for [requirements.md](requirements.md). Append-only;
newest at the bottom.

## D1 — Intake rulings (form-collected, 2026-08-14)

**Date:** 2026-08-14 · **Status:** decided (Patrick, via decision-card
intake form; validated receipt `resp-20260814-213951`).

Provenance chain: round table `q-forms-grammar-expansion-001` — the
Claude seat's follow-up ("is the parser code or model-assisted, and
where does the validation truth live?") and the Antigravity seat's
follow-up (inline response template vs extraction schema) posed the
central fork; the Codex seat demanded a deterministic round-trip
protocol. Chair ruled the lane "spec next" (receipt
`resp-20260814-211025`, board msg 9).

1. **Normalization owner = hybrid**: deterministic library parser
   (`markdown_to_answers`) for the shorthand grammar; the host agent
   owns the free-text lane as a skill-taught proposal. Validation
   truth stays `collect_form_response` for both — this answers the
   seats' follow-up questions directly.
2. **Shorthand scope = minimal**: `field_id: value`, `N: value`
   (1-based), dotted triage ids, filled JSON block; EXACT option
   matching. Prefix/case-insensitive matching deferred to a v2 ruling
   backed by real transcripts.
3. **Slug = `markdown-ingestion`**; done-when recorded verbatim in
   requirements.

## D2 — AC-4 live receipt: both lanes fired (chair via typed reply, 2026-08-14)

**Date:** 2026-08-14 · **Status:** decided.

The ship gate rendered on the markdown surface itself (a `confirm`
form via `form_to_markdown` — no widget, the exact Codex/Antigravity
experience). The chair typed the free-text reply "approve". The
deterministic lane behaved per D1: `markdown_to_answers` returned
`unparseable line: 'approve'` — not shorthand, not the exact option,
NO guess. The host-agent lane then proposed the mapping
`{pr_gate: "Approve"}`, validated through `collect_form_response` —
receipt `resp-20260814-214817`. AC-4 satisfied with BOTH ruled lanes
demonstrated in one exchange, including the parser's refusal — the
honesty half of the design — observed live.
