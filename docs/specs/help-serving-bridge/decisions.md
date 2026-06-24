# Decisions: Help-Serving Bridge

**Status:** approved (2026-06-24)
**Created:** 2026-06-24

Each decision lists the choice, the alternative(s), and the rationale.
D1–D4 RATIFIED 2026-06-24; OQ1/OQ2 resolved (see below).

---

## D1 — Resolver fallback, not bundle emission (RATIFIED)

**Choice:** Add a fallback to the engine's template resolver
(`attune.help.templates._find_template_file`): when an ID is not found
in `plugin/help/generated/<type>/<name>.md`, resolve it against
`.help/templates/<name>/<kind>.md` (mapping the ID prefix to the
singular kind filename). `populate()` and everything above it (MCP
`help_lookup`) then serve single-source content with no other change.

**Alternative (Design B):** Make the projector also emit a
type-organized copy into `plugin/help/generated/`, then rebuild
`cross_links.json` + `source_manifest`. Fuller integration but
duplicates content on disk, enlarges `generate_all.py`, and forces an
ID-naming convention.

**Rationale:** A is ~15 lines, introduces no second copy (NFR1), no LLM
spend (NFR2), and preserves all bundle-only IDs (FR2). The ID→file
mapping is already deterministic and the engine parser already reads the
single-source files. B's cross-link/progression integration is real but
can be layered on later (D3) without redoing A.

**Cost:** Under A, cross-links (`related`) and progressive-depth chains
are not wired for fallback content initially — see D3.

---

## D2 — Defer pip-wheel help packaging (RATIFIED)

**Choice:** Scope this spec to the **Claude Code plugin** channel (which
ships `.help/templates`). Do **not** package the help bundle into the
pip wheel in this spec.

**Alternative:** Also package `.help/templates` (or a generated bundle)
under `src/attune` so `pip install attune-ai` serves in-tool help, and
make the resolver find it there.

**Rationale:** attune-ai is consumed as a Claude Code plugin; the
in-conversation `.help` surface is a plugin feature. The plugin already
ships `.help/templates`, so the bridge reaches real users without
packaging work. Pip-wheel help is a distinct effort (packaging +
resolver path discovery in `site-packages`) with unclear demand. Record
it as a follow-up; pull in only if pip users are a target.

---

## D3 — Cross-links & progression for fallback content = follow-up (RATIFIED)

**Choice:** Ship D1 without cross-link/`related` resolution or
progressive-depth chaining for fallback-served content; track wiring
them as a follow-up.

**Alternative:** Build cross-links for `.help/templates` content as part
of this spec.

**Rationale:** The grounded body, title, tags, and per-kind lookup are
the core value and unblock the release. Cross-links/progression are
enhancements; bundling them expands scope and risks the release. The
projector already emits cross-reference-friendly content, so a later
pass can populate `related` without reworking D1.

---

## D4 — Release as a patch to the plugin channel (RATIFIED)

**Choice:** Ship the bridge as a **patch** bump (`8.9.0 → 8.9.1`) — no
runtime API change, a help-serving behavior fix — with a changelog entry
that is explicit: single-source help now served in-conversation (plugin/
MCP); website/ops already had it; pip-wheel help still out of scope.

**Alternative:** Minor bump (`8.10.0`) framing it as a feature.

**Rationale:** Behavior-fix/wiring with no public API change fits a
patch (consistent with 8.7.1's docs/distribution patch precedent). The
changelog carries the nuance so the scope is not over-claimed.

---

## Resolved questions

- **OQ1 (resolved 2026-06-24)** — The resolver prefers the **bundle
  first, `.help/templates` fallback second** — preserving current
  behavior for any colliding ID. Single-source IDs like `con-<feature>`
  don't collide with bundle `con-tool-<skill>`.
- **OQ2 (resolved 2026-06-24)** — Pip-wheel help is **not** wanted now;
  D2 stands (plugin channel only).
