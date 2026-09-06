# Codex native-host round-trip receipt (Task 4b observation, held)

**Taken:** 2026-09-06 01:41Z · **Chair observation:** "card painted" · **Held**
until Task 1B creates `receipts.md`; this file is the R4b block's source.

## Setup

- Codex desktop app restarted after its launcher pin was lifted from
  `attune-forms[mcp]==0.12.3` to `>=0.13.0` (`~/.codex/config.toml`, chair-
  approved edit, backup `config.toml.bak-20260906`).
- Codex-launched forms servers resolved to uv archive `fOEMMlR7RrT36Khn-V7pb`
  = `attune_forms-0.13.0` (verified from the live process argv + dist-info).
- The chair pasted one prompt asking Codex to call `elicitation_render_widget`
  with a fixed one-question decision form (`form_id e1cfd8b31260`, precomputed
  with `form_from_dict` so the rows are findable regardless of Codex's report).

## Telemetry join (`~/.attune/telemetry/form_events.jsonl`)

| ts (UTC) | event | form_id | instance_id |
| --- | --- | --- | --- |
| 01:41:28.127612 | form_surface (chosen `widget`, reason `default`) | e1cfd8b31260 | — |
| 01:41:28.127872 | form_rendered (17,873 html bytes) | e1cfd8b31260 | fb05442cfee34605b4bf2bbc34a7976c |
| 01:41:51.111595 | form_submitted | e1cfd8b31260 | fb05442cfee34605b4bf2bbc34a7976c |

Excluded: a `form_build` for the same form_id at 01:28:46Z, written by the
lead's local precompute in the forms venv (no render, no submit).

## Verdict

- **Falsifier passed:** the submit carries the render's `instance_id`, so the
  answer came through the widget's post-back — the widget's JS is the only
  writer of that field; a typed answer relayed by Codex would arrive without it.
- **Paint:** observed by the chair ("card painted"); no machine paint trace
  exists (the 09-05 preflight's `cua.getApp('Codex')` refusal still stands).
- **Attribution basis:** the events file carries no pid; the rows are
  attributed to the Codex-launched server because this Claude session never
  rendered the form and the timestamps match the chair's run — inferred from
  timing, not read from a process id.
- **Codex host profile (R1):** RICH tier via the MCP Apps `ui://` surface,
  round-trip verified; 23 s render→submit for a one-question card.
