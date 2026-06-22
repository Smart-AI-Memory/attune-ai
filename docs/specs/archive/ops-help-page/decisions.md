# Decisions: Ops Help Page

> Resolutions to the open questions in
> [`requirements.md`](requirements.md). Each entry locks an
> ambiguity so Phase 1 implementation can proceed without
> re-litigating.

**Last updated:** 2026-05-27

---

## 1. Search backend — `attune-rag` with lexical fallback

**Decided:** Use `attune-rag` semantic retrieval as the
primary search backend. If `attune_rag` is not importable
at runtime, degrade to a lexical fallback (filename match +
first 500 chars of body match, ranked by hit count).

**Why:** attune-rag already carries the benchmark + faithfulness
investment for this corpus; the help page inherits that quality
for free. The fallback keeps the page useful in minimal installs
without making attune-rag a hard dependency of `attune.ops`.

**How to apply:** `attune.ops.help_data` exposes a single
`search(query: str, limit: int = 10)` entry point that
internally branches on `importlib.util.find_spec("attune_rag")`.
The API contract (`GET /api/help/search?q=...`) is identical in
both modes — only the ranking quality differs. Surface the
active mode in the response payload (`"backend": "rag" | "lexical"`)
so the UI can show a subtle indicator when lexical-only.

---

## 2. Markdown renderer — `markdown-it-py`

**Decided:** Use `markdown-it-py` for template rendering, the
same renderer already used by the spec viewer in `attune.ops`.

**Why:** Consistent sanitization story (XSS-safe by default
with `html: False`), consistent code-block + table styling
across the dashboard, no new dependency. The spec viewer's
render path is the proven pattern.

**How to apply:** Reuse the spec viewer's render helper
rather than instantiate a second `MarkdownIt` configuration.
Add a `help`-scoped CSS class to the rendered container so
typography rules can diverge from the spec viewer if Patrick
wants different prose styling without affecting specs.

---

## 3. Pinned scope — localStorage only (v1)

**Decided:** Pinned templates and recent views are stored in
the browser's localStorage. No server-side persistence.

**Why:** Simplest path that satisfies the v1 acceptance
criteria; no new file under `<attune_home>/`, no migration
story, no cross-browser sync expectation to maintain. The
v2 escape hatch (persist to `<attune_home>/help/pins.json`)
stays open if a user reports losing pins on browser cache
clears.

**How to apply:** All pin/recent state lives in
`runner.js`-style frontend code. The server is read-only
for help — no `POST /api/help/pin` endpoint in v1. Keep the
localStorage key namespaced (`attune.ops.help.pins.v1`,
`attune.ops.help.recent.v1`) so a future v2 migration can
detect and import legacy state.

---

## 4. Coverage-gap thresholds — adopt v1 defaults

**Decided:** v1 defaults are **11 kinds per feature** for
completeness and **>7d source_hash drift** for staleness.
Both values are constants in `help_data`; not user-configurable
in v1.

**Why:** These match the values already in use by
`attune-author check_staleness` and the polish-pass kind list.
Surfacing them as config in v1 would invite tuning without
data; if real usage shows the thresholds wrong, adjust the
constants in code or promote to config in v2.

**How to apply:** Define `_COMPLETENESS_TARGET = 11` and
`_STALENESS_DAYS = 7` as module-level constants in
`attune.ops.help_data`. Reference them by name in the
`/api/help/gaps` payload so the UI can display the active
thresholds without hard-coding them in the template.

---

## 5. Curator help-indexing — out of scope for this spec

**Decided:** The curator's source reader for "feature X has
documentation drift Patrick might want to fix" is **not** part
of the ops-help-page spec. It belongs in
[`bulletin-curator`](../bulletin-curator/requirements.md)
as one of the curator's source-list entries.

**Why:** ops-help-page is a read-only browsing surface;
the curator is a separate spec that builds the bulletin from
many sources, of which "help-corpus drift" is one. Keeping
the surfaces decoupled lets each spec ship independently.

**How to apply:** No work in this spec. When the curator
spec advances, the help-corpus drift reader can re-use the
freshness + gap helpers built in Phase 1 of this spec via
the public `attune.ops.help_data` API — the same way any
other consumer would.

---

## Status of open questions

| # | Question | Status |
|---|----------|--------|
| 1 | Search backend choice | Resolved — attune-rag with lexical fallback |
| 2 | Markdown renderer choice | Resolved — markdown-it-py |
| 3 | Pinned scope | Resolved — localStorage only (v1) |
| 4 | Coverage-gap thresholds | Resolved — 11 kinds / 7 days |
| 5 | Help-page indexing for curator | Resolved — out of scope, lives in bulletin-curator |

All five questions resolved. Phase 1 implementation
(read primitives + read-only API) is unblocked.
