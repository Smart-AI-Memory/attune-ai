# Spec: Ops Help Page

> A first-class help-browsing surface in the attune ops
> dashboard. Lets users search, browse, and read the
> `.help/templates/` corpus directly from the browser —
> independent of any chat / CLI flow.

**Status:** complete — shipped (`ops/routes/help.py` + `ops/help_data.py`); Phase 3–4 polish optional — verified 2026-06-08 spec triage
**Created:** 2026-05-26
**Owner:** TBD
**Related:**
- [`bulletin-curator`](../bulletin-curator/requirements.md) — sibling consumer of the help corpus; same retrieval primitives
- `attune-help` package — provides the corpus + reader primitives
- `attune-rag` package — provides the search/retrieval relevance
- Future spec: `attune-help-client` — extracts the live Q&A surface (current MCP `help_lookup`) into a reusable library; the dashboard help page deliberately does NOT bundle this in v1

---

## Problem statement

The `.help/` system is a substantial body of work — 11 template
kinds per feature, polished prose, freshness-tracked, queryable
via `attune-rag`. Today there are only three ways to consume it:

1. The MCP `help_lookup` tool — agent-facing, invoked through
   Claude Code only
2. The CLI `/coach` skill — terminal-bound, transient
3. Reading the raw `.help/templates/<feature>/*.md` files —
   no search, no cross-references, no rendering

A human user who wants to **browse** the help — see what's there,
search across it, follow cross-references, surface gaps — has no
good surface. The dashboard is the natural home for that.

Patrick's framing on the help system: *"a point of pride for me"*.
The page should reflect that — not a minimum-viable search box,
but a well-built reading and browsing surface that does justice
to the corpus.

---

## Goals

1. **Browse the corpus** — sidebar tree of features; expand to
   see all 11 template kinds per feature; click any to open.
2. **Search the corpus** — top-bar search backed by attune-rag's
   semantic retrieval; results ranked by relevance with snippets
   and click-through.
3. **Read templates beautifully** — markdown rendered with
   headings (auto-anchored), code highlighting, working
   cross-references, math/diagrams if present.
4. **Surface freshness signals** — the existing
   "10 stale, 2 incomplete" signal visible in the UI; stale
   templates get a marker, missing kinds get a gap indicator.
5. **Surface coverage gaps** — a dedicated tab listing features
   with incomplete template sets (fewer than the 11 kinds, or
   stale beyond N days), to support pride-of-craftsmanship in
   the corpus itself.
6. **Deep-link friendly** — URLs like
   `/help/security-audit/task#section-name` work; users can
   bookmark and share them.
7. **Power-user affordances** — recent views + pinned templates
   (local-storage only; no server state needed).

## Non-goals (v1)

- **Live Q&A from the page.** A "type a question, get a synthesized
  answer" surface — that's the future `attune-help-client` library
  + a separate dashboard widget. v1 is browse + search only.
- **Editing.** Templates are read-only in v1. Patrick edits via
  `attune-author` from the CLI.
- **Authentication / multi-user.** Same as the rest of the
  dashboard — single-user, localhost-bound.
- **Generation / regeneration triggers.** v1 only displays. Buttons
  to regenerate stale templates can land in v2 if the friction
  warrants it.
- **Telemetry on browse patterns.** Don't track what users read
  in v1. If recommendation-quality tuning needs that signal later,
  add it deliberately.

---

## Acceptance criteria

1. **Browse the full corpus** — `/help` renders a sidebar with
   every feature in the corpus and every kind under each feature.
   No feature missing; no template silently dropped.
2. **Search returns ranked semantic results** — a query like
   "how do I detect injection" returns the `security-audit/task`
   and `security-audit/concept` templates in the top 3 results,
   not just lexical keyword matches.
3. **Read renders correctly** — opening a template shows the
   markdown with proper headings, code highlighting, lists, and
   tables. Cross-references to other templates are live links.
4. **Freshness signals visible** — at least one stale template
   in the corpus renders with a "stale" chip; at least one
   feature with incomplete kinds shows a gap indicator.
5. **Coverage gaps surface** — a `/help/gaps` view (or tab)
   lists features with incomplete sets, sorted by completeness.
6. **Deep-link works** — opening
   `/help/security-audit/task#run-the-scan` (or whichever
   section anchor exists) scrolls to the right section, not
   the top of the page.
7. **Performance** — the home page loads in <500ms cold (corpus
   browse is server-rendered, no JS round-trip). Search responds
   in <1s for any single query.
8. **Read-only safety** — no API endpoint exposed under `/api/help/`
   accepts writes. GET-only.

---

## Wireframes (low-fi, ASCII)

### Home — `/help`

```text
┌─────────────────────────────────────────────────────────────┐
│  attune ops    Home  Workflows  Specs  Sessions  Help …    │
├──────────────────┬──────────────────────────────────────────┤
│                  │                                          │
│  Search help…    │   Help                                   │
│  [_____________] │                                          │
│                  │   26 features · 286 templates ·          │
│  ─ Browse ─      │   10 stale · 2 incomplete   [refresh]   │
│                  │                                          │
│  ▾ Features      │   ─ Recent ─                             │
│    ▸ bug-predict │     • security-audit / task              │
│    ▾ code-review │     • bulletin / concept                 │
│      • concept   │     • discovery-sweep / reference        │
│      • task      │                                          │
│      • reference │   ─ Pinned ─                             │
│      • error     │     (none yet — pin from any template)   │
│      • faq       │                                          │
│      ⋮ (11 kinds)│   ─ Coverage gaps ─                      │
│    ▸ discovery-… │     ⚠ 2 features with incomplete sets   │
│    ⋮ (26 feats)  │     [view all →]                         │
│                  │                                          │
│  ─ Browse by kind│   ─ Recently regenerated ─              │
│    • concept (26)│     • ops-dashboard / concept (today)   │
│    • task (24)   │     • plugin / reference (today)        │
│    • reference … │     ⋮                                    │
│                  │                                          │
└──────────────────┴──────────────────────────────────────────┘
```

### Search results — `/help?q=injection`

```text
┌─────────────────────────────────────────────────────────────┐
│  Search help…  [injection_____]                             │
├──────────────────┬──────────────────────────────────────────┤
│                  │   Results for "injection" — 7 matches    │
│  Browse sidebar  │                                          │
│  (collapsed)     │   ★ security-audit / task                │
│                  │     "…detects SQL injection patterns,    │
│                  │     command injection, path traversal…"  │
│                  │     score 0.92 · 200 chars               │
│                  │                                          │
│                  │   ★ security-audit / concept             │
│                  │     "…OWASP top-10 coverage including    │
│                  │     injection, XSS, broken auth…"        │
│                  │     score 0.88                           │
│                  │                                          │
│                  │   bug-predict / reference                │
│                  │     "…the `dangerous_eval` scanner flags │
│                  │     potential injection via eval()…"     │
│                  │     score 0.61                           │
│                  │                                          │
│                  │   …4 more                                │
│                  │                                          │
└──────────────────┴──────────────────────────────────────────┘
```

### Template view — `/help/security-audit/task`

```text
┌─────────────────────────────────────────────────────────────┐
│  Search help…    │                                          │
├──────────────────┤   security-audit                         │
│                  │   ──────────────                         │
│  ▾ security-audit│   task · ⊕ pin · last updated 4d ago    │
│    • concept     │                                          │
│   ★ task ◀       │   On this page                           │
│    • reference   │   • Run the scan                         │
│    • error       │   • Interpreting results                 │
│    • faq         │   • Acting on findings                   │
│    • troublesh…  │   • Related features                     │
│    ⋮             │                                          │
│                  │   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│  See also        │                                          │
│  • bug-predict   │   ## Run the scan                        │
│  • code-quality  │                                          │
│  • deep-review   │   ```bash                                │
│                  │   attune workflow run security-audit \   │
│                  │     --path src/                          │
│                  │   ```                                    │
│                  │                                          │
│                  │   ## Interpreting results                │
│                  │   …                                      │
└──────────────────┴──────────────────────────────────────────┘
```

### Coverage gaps — `/help/gaps`

```text
┌─────────────────────────────────────────────────────────────┐
│   Coverage gaps                                              │
│                                                              │
│   Features with incomplete template sets (target: 11 kinds): │
│                                                              │
│   ⚠ foo-feature           7/11   missing: error,            │
│                                  troubleshooting, faq, tip   │
│                                                              │
│   ⚠ bar-feature           9/11   missing: comparison,       │
│                                  warning                     │
│                                                              │
│   Stale templates (source_hash drift > 7d):                 │
│                                                              │
│   ⏰ workflow-x / task     14 days  [regenerate via         │
│                                     attune-author cli]      │
│                                                              │
│   ⏰ feature-y / concept   9 days   …                       │
│                                                              │
│   ─ Coverage metrics ─                                       │
│   Overall: 96% complete (286/297 templates)                 │
│   Fresh: 92% (264/286 within 7d)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Tasks (phased)

### Phase 1 — Read primitives + read-only API (~3h)

| # | Task | Effort |
|---|------|--------|
| 1 | `attune.ops.help_data` module — wrap attune-help + attune-rag for the corpus / template / search reads | 1h |
| 2 | Freshness + gap computation (reuse existing attune-author `check_staleness` + a small completeness helper) | 30m |
| 3 | API routes: `GET /api/help/`, `/api/help/feature/<slug>`, `/api/help/template/<feature>/<kind>`, `/api/help/search?q=`, `/api/help/gaps` | 1h |
| 4 | Route tests + API contract tests | 30m |

### Phase 2 — Browse + search UI (~4h)

| # | Task | Effort |
|---|------|--------|
| 5 | `/help` route + `help.html` template (home + sidebar) | 1.5h |
| 6 | Search results rendering (snippet highlighting, relevance score) | 1h |
| 7 | Template view route + render (markdown w/ anchors + code highlighting) | 1h |
| 8 | Cross-reference link resolution (`concepts/tool-X.md` → `/help/X/concept`) | 30m |

### Phase 3 — Polish + power-user (~2h)

| # | Task | Effort |
|---|------|--------|
| 9 | Freshness chips + coverage gaps tab | 45m |
| 10 | Recent + pinned (localStorage only) | 30m |
| 11 | Deep-link / anchor handling | 30m |
| 12 | CSS pass — match dashboard conventions, prose typography | 30m |

### Phase 4 — Verification (~1h)

| # | Task | Effort |
|---|------|--------|
| 13 | Live verification against the real attune-ai `.help/` corpus; eyeball search relevance + browse UX with Patrick | 1h |

**Total estimated:** 10h. Phases 1+2 are the MVP (browse + search work);
Phases 3+4 are the polish that earns "point of pride."

---

## Open questions

> **Status (2026-05-27):** all five resolved — see
> [`decisions.md`](decisions.md). The questions below are
> kept for context; the leans they propose were adopted as
> the v1 path.

1. **Search backend choice.** attune-rag's existing retrieval is the
   semantic option; a simple lexical fallback is the no-cost option.
   Lean: use attune-rag (you've already invested in benchmarks +
   faithfulness scoring; this surface inherits that quality). If
   attune-rag isn't installed, degrade to lexical (filename + first
   500 chars match).

2. **Markdown renderer choice.** `markdown-it-py` (used elsewhere in
   attune-ops for the spec viewer) is the obvious pick — same
   sanitization story, consistent code-block styling. Confirmed
   default: yes.

3. **Pinned scope.** localStorage-only (per-browser) vs persisted to
   `<attune_home>/help/pins.json` (per-machine). Lean: localStorage
   for v1 — simpler, no server state to migrate; users who want
   persistence can wait for v2.

4. **Coverage-gap thresholds.** Currently the corpus targets 11 kinds
   per feature; staleness is "> 7d source_hash drift" per
   attune-author. Confirm both as the v1 defaults, or surface as
   config.

5. **Help-page indexing for the curator.** Should the curator have
   a separate `help.py` source reader that surfaces "feature X
   has documentation drift Patrick might want to fix"? Probably
   yes, but separate task — falls under the curator spec's source
   list, not this one.
