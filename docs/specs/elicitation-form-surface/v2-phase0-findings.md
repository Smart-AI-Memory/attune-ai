# Elicitation v2 — Phase 0 findings (V2.0 tasks 1–2)

Grounded inventory of the three candidate surfaces against the
[V2.0 rubric](v2-phase0-requirements.md) (C1–C5), plus the D4
return-path re-validation. Every claim is sourced (verify-first, D1).

## Headline finding — D4's elicitation rejection is now STALE

v1 rejected MCP native elicitation because it lacked multi-select (D4).
**The MCP spec 2025-11-25 adds multi-select**, and its return path is
**structured and keyed by field** — the cleanest C2 of all three
surfaces. The surface v1 ruled out is now arguably the *leading*
candidate. This is the kind of premise-drift the Phase 0 spike exists
to catch.

## Surface × criteria

| | S1 show_widget / Cowork | S2 MCP elicitation | S3 standalone web |
|---|---|---|---|
| **C1 controls** | Best — arbitrary HTML (any control) | Good — string/number/bool/enum + **multi-select**; date/email via string `format`; no true slider/color | Best — arbitrary web UI |
| **C2 return path** | Free-text postback (`sendPrompt`) carrying JSON the agent parses | **Best — structured `{field: value}`, accept/decline/cancel** | Structured, but out-of-band (POSTs to a backend, not the chat loop) |
| **C3 portability** | Widget-capable clients (Cowork/claude.ai); CSP/CDN-sandboxed | Native; Claude Code/Desktop/web support form+url; needs runtime capability negotiation | Heavy — needs hosting; client just opens a URL |
| **C4 reuse** | Render HTML from artifact; parse postback → `collect_form_response` | Map artifact → elicitation JSON schema; keyed response → `collect_form_response` (clean) | New web infra; backend owns the response |
| **C5 north-star fit** | HTML can host a designer later | Flat-primitives only — caps rich/designer ambitions | Closest to the Florence horizon (user-designed, data-bound) |

## Evidence

### S2 — MCP elicitation (spec 2025-11-25)

- **Multi-select supported:** `{"type":"array","items":{"type":"string",
  "enum":[...]},"minItems":1,"maxItems":2}` (spec example). Single-select
  via `enum` / `oneOf`+`const`+`title`.
- **Types:** flat object of primitives only — string (formats: email,
  uri, date, date-time; pattern, min/maxLength), number/integer
  (min/max), boolean, enum (single+multi). No nested objects; no native
  slider/color.
- **Return path (structured):** client returns `{"action":"accept"|
  "decline"|"cancel","content":{<field>:<value>}}` — keyed by schema
  property, NOT free text.
- **Client support:** Claude Code / Desktop / web support form+url modes;
  server must check `capabilities.elicitation` at init and not send
  unsupported modes.
- Source: <https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation.md>

### S1 — show_widget / Cowork preview

- Renders arbitrary HTML fragments inline (full control palette possible),
  but sandboxed: CSP/CDN allowlist, no `position:fixed`, scripts run
  post-stream.
- **Return path:** the only postback is the global `sendPrompt(text)` —
  "sends a message to chat as if the user typed it." So answers come back
  as a **free-text chat message** (the widget would serialize a JSON
  string into it) that the agent then parses — not a structured callback.
- Source: `mcp__visualize__read_me` (interactive module) — `sendPrompt`
  section.

### S3 — standalone web (Florence-style)

- Arbitrary web UI → best control coverage and the closest fit to the
  North-star (user-designed, data-bound) horizon.
- **Return path:** form POSTs to a web backend — structured, but the
  submission lands in a server, out of the chat agent's loop; needs
  hosting + new infra. Reference: `Deep-Study-AI/ai-nurse-florence-v3.1`
  (~20 clinical web forms on the same declarative model).

## D4 re-validation verdict (task v2.0-2)

**D4 is partially OVERTURNED.** D4 deferred the rich surface on two
premises: (a) MCP elicitation lacks multi-select, and (b) a widget's
return path is fragile posted-JSON.

- **(a) OVERTURNED** — elicitation now supports multi-select with a
  *structured, keyed* return. The disqualifier is gone.
- **(b) CONFIRMED for the HTML-widget surface (S1)** — its only postback
  is a free-text `sendPrompt`, i.e. exactly the "round-trip via posted
  JSON" D4 named; workable but the weakest return path. NOT confirmed for
  elicitation (S2), whose return is structured.

**Net:** the return-path objection that drove v1 to `AskUserQuestion`
does not apply to MCP elicitation. S2 leads on C2/C3/C4; S1 leads on
C1/C5 (rich controls, designer headroom); S3 is the heavy North-star
surface.

## Recommendation (pre-D8)

Lead with **S2 (MCP elicitation)** for v2's general form surface — best
return path, native/portable, reuses `collect_form_response` with only a
schema-mapping transform. Keep **S1 (show_widget)** as the escape hatch
for controls elicitation can't express (true slider, color, rich
layout). **S3** stays the North-star horizon (V2.3), not a v2 build
target. Final pick is **D8** after the task v2.0-3 PoC.
