# Requirements: Help-Serving Bridge

**Status:** complete — bridge shipped (help/templates.py resolves .help/templates first; verified 2026-07-14); reconciled at 2026-07-14 triage (was: approved)
**Created:** 2026-06-24
**Owner:** Patrick + agent
**Related:** [help-docs-single-source](../help-docs-single-source/)
(now complete — every feature single-sourced)

---

## Problem

The help-docs-single-source rollout is complete: every feature has a
hand-authored, adversarially-verified master in `content/features/<F>.md`
projected to `.help/templates/<F>/<kind>.md`, `docs/`, and the website.

But the surface real users hit does **not** serve that content. The
in-conversation `.help` lookup (MCP `help_lookup` → `attune.help.engine`
→ `populate()`) reads a **different** bundle:
`plugin/help/generated/<type>/<name>.md` — a type-organized corpus built
by `scripts/generate_all.py` from `.claude/CLAUDE.md` lessons +
`plugin/skills/*/SKILL.md`. It never reads the single-source content.

Consequence: the grounded, fiction-free help reaches the **ops dashboard
help tab** (`ops.help_data` reads `.help/templates/`) and the
**website/mkdocs** (`docs/`), but **not** MCP / the Claude Code plugin's
in-conversation help. Those still serve the older, separately-sourced
bundle (~800 templates stale at last check).

### Evidence (verified 2026-06-24)

- `attune.help.templates._DEFAULT_GENERATED_DIR` =
  `<root>/plugin/help/generated`; `populate()` resolves IDs there.
- MCP `_handle_help_lookup_impl` (`src/attune/mcp/server.py`) calls
  `populate_progressive` / `get_workflow_help` etc. from
  `attune.help.engine` — all using that default dir.
- `populate("con-help-system")` → `None` (no single-source content in
  the bundle); `populate("con-progressive-depth")` → a hand-curated
  *system* concept that lives only in the bundle.
- `generate_all.py` and the per-type generators read lessons + skills,
  never `content/features/` or `.help/templates/`.
- The bundle parser (`_parse_template_file`) reads a single-source
  `.help/templates/<F>/<kind>.md` file cleanly.
- The wheel packages **neither** `.help/templates` nor
  `plugin/help/generated` (both live outside `src/attune`; not grafted
  in `MANIFEST.in`). attune-ai is consumed primarily as a **Claude Code
  plugin**, which *does* ship `.help/templates` (286 tracked files) and
  `plugin/help/generated` (905 tracked files).

---

## Goal

Make the in-conversation help surface (MCP `help_lookup` / the plugin)
serve the single-source content for every feature, without losing the
hand-curated system concepts (`progressive-depth`, `audience-adaptation`,
…) that live only in the bundle.

---

## Functional requirements

- **FR1** — `populate("<prefix>-<feature>")` returns the single-source
  body from `.help/templates/<feature>/<kind>.md` for every projected
  feature and every projected kind (concept, task, reference,
  quickstart, comparison, error, troubleshooting, warning, note, tip,
  faq).
- **FR2** — Existing bundle-only templates (system concepts, lessons/
  skill-derived `tool-<skill>` and `err-*` entries) continue to resolve
  unchanged. No regression for any ID currently served.
- **FR3** — MCP `help_lookup` (all modes that resolve a template) serves
  the single-source content for single-sourced features, verified by a
  live call returning the grounded body (not the old bundle body).
- **FR4** — The change ships to the channel users consume (the Claude
  Code plugin) via a version bump + changelog + release.

## Non-functional / constraints

- **NFR1** — Smallest viable change; no duplication of content into a
  second on-disk copy unless a decision explicitly chooses emission.
- **NFR2** — No new LLM spend (this is wiring, not regeneration).
- **NFR3** — `mkdocs build --strict` and the full `tests/unit/help/`
  suite stay green; add coverage for the new resolution path.

## Out of scope (this spec)

- **Pip-wheel help packaging.** Making `pip install attune-ai` ship the
  in-tool help bundle is a separate packaging task (both dirs are
  outside `src/attune`). Deferred unless explicitly pulled in — see
  decisions D2.
- **Retiring the lessons/skills bundle** or the `tool-<skill>` concepts.
- **Rewriting `generate_all.py`.**

## Acceptance criteria

- `populate("con-<feature>")` and the other ten kinds return the
  single-source body for a sampled set of features (incl. help-system,
  ops-dashboard, security-audit).
- A live MCP `help_lookup` call for a single-sourced feature returns the
  grounded content.
- All previously-resolving IDs still resolve (regression test).
- Full `tests/unit/help/` green; `mkdocs build --strict` exit 0.
- Released to the plugin channel (version bump + changelog).
