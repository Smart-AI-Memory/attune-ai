# Phase 4 Findings — attune ops dashboard review

**Status:** Draft (2026-05-23)
**Cycle:** Spec's Phase 4 reflection cycle (target 2026-05-25; written 2 days early)
**Reviewer:** Live-driven walk-through by an AI assistant via the Cowork preview pane (attune-gui worktree, port 8775)
**Predecessor:** [tasks.md](tasks.md) — Phases 1–3 shipped via PRs [#236](https://github.com/Smart-AI-Memory/attune-ai/pull/236), [#239](https://github.com/Smart-AI-Memory/attune-ai/pull/239), [#249](https://github.com/Smart-AI-Memory/attune-ai/pull/249)

---

## 0. Critical issue surfaced during the review

⚠️ **Spec status files were mutated without explicit user confirmation during the review session.** Nine `PUT /api/specs/{slug}/{phase}/status` requests fired while driving the dashboard via the preview MCP tool, modifying six spec files. All mutations were reverted via `git checkout HEAD -- docs/specs/<paths>` before any commit; no data was lost.

This is Finding 0 — high-priority either way:

- If the page itself fires PUTs on certain navigation patterns, it's a real and serious bug that puts user spec history at risk.
- If the trigger is an interaction artifact between an automated browser-control tool and the page's event handlers, it's a robustness signal worth understanding (and a real risk for any future agent-driven review).

### Observable trace

The dashboard server logs (uvicorn access log) show two clear batches:

**Batch 1 — three PUTs to `complete`** (matched `/api/specs/completion-candidates` response):

```
PUT /api/specs/multi-actor-bulletin/decisions/status        → 200 OK
PUT /api/specs/ops-specs-completion-candidates/decisions/status → 200 OK
PUT /api/specs/coverage-exclusion-policy/decisions/status   → 200 OK
```

Fired after `GET /specs` + `GET /api/specs/completion-candidates`, before any deliberate Confirm button click. The JS at `src/attune/ops/static/js/completion_candidates.js:159` (`onConfirm`) only PUTs on a click event. No auto-confirm path is visible in the source.

**Batch 2 — six PUTs to specs *not* in the candidates list**:

```
PUT /api/specs/telemetry-rethink/decisions/status           → 200 OK
PUT /api/specs/larger-runners/decisions/status              → 200 OK
PUT /api/specs/ops-security-hardening/decisions/status      → 200 OK
PUT /api/specs/ops-security-hardening/requirements/status   → 200 OK
PUT /api/specs/ops-security-hardening/design/status         → 200 OK
PUT /api/specs/ops-security-hardening/tasks/status          → 200 OK
```

These were *not* completion-candidates. They mutated to varied statuses (not all `complete`). Mechanism unclear — likely the `.status-pill[role="button"]` flip path in the main table.

### Hypotheses (none verified)

1. **Preview-tool interaction artifact**: the MCP tool's `click(selector)` or `snapshot` (accessibility tree) actions may activate `role="button"` elements via keyboard/focus events that fall outside the source-visible click listener. Worth instrumenting.
2. **Hidden auto-confirm path**: a code path in the candidates or status-pill logic fires PUT without an explicit click. Source review of `completion_candidates.js` showed `onConfirm` is only wired to `addEventListener("click", ...)`. Worth a deeper audit of the status-pill flip code (not read in full during this session).
3. **Race in optimistic-UI rollback**: if the optimistic UI rolls forward and the rollback path fires a "re-save" PUT, that could explain the pattern. Speculative.

### Recommended follow-up

- **Investigate-trigger spec or chip.** Repro with `--read-only` (per [tasks.md](tasks.md) task 2.3, the flag blocks status mutations). If PUTs still appear in server logs under `--read-only`, prove the page is firing them; if they 403/blocked, the trigger source is provable from the request pattern.
- **Add server-side defense**: the PUT endpoint could require an `Origin` header check or a CSRF-style token (like attune-gui's `X-Attune-Client` pattern, see attune-gui's `routes/cowork_specs.py`). attune-gui's PUT route is guarded by `Depends(require_client_token)`; attune-ops' isn't, per the audit.

This finding alone justifies a dedicated investigation spec before Phase 5 is considered.

---

## 1. What was reviewed

| Tab | Coverage |
|---|---|
| **Home** (`/`) | Full DOM snapshot; layout + tiles read |
| **Workflows** (`/workflows`) | Full DOM snapshot; 20 workflows visible, no runs triggered |
| **Specs** (`/specs`) | Full DOM snapshot; "Ready to close?" section explored; one drill-in (`ci-debt`) read |
| **Sessions** (`/sessions`) | Brief HTML check, returns 200; not driven |
| **Telemetry** (`/telemetry`) | Not driven (paused after Finding 0) |
| **Health** (`/health`) | Not driven (paused after Finding 0) |

Walk-through paused at Sessions when the spec-file mutations were discovered. The Telemetry and Health tabs warrant a separate session under safer conditions.

---

## 2. Findings — Specs page (subject of the spec)

### 2.1 Status-pill truncation impairs at-a-glance scanning (severity: friction)

The main spec table's status pills truncate at ~8 characters with ellipsis. Custom-status phrases like:

- `paused 2026-05-12 — premise invalidated, see decisions.md` → renders as `paused 2…`
- `complete (2026-05-10) — Phase A 68f19b90, Phase B 28441852, Phase C 463df6a5` → `complete…`
- `retired (2026-05-12, see [decisions.md](decisions.md))` → `retired …`
- `draft (2026-05-16) — no decisions resolved yet` → `draft (2…`

The `data-tooltip` attribute carries the full text, so hover recovers it — but the pill itself is the primary signal in the table view. Result: users have to hover-test each pill to know what state things are in.

The drill-in page (`/specs/<slug>`) renders status verbatim with no truncation — a sharp inconsistency between the two views.

**Suggested direction**: either (a) expand pill min-width on rows where status doesn't fit, (b) extract just the leading status keyword for the pill (matching attune-gui's `\*\*Status...\*\*\s*(\S+)` capture pattern) and show the rest in a popover, or (c) show the full status in a wrappable cell at desktop widths.

### 2.2 Status abbreviations lack a legend (severity: friction)

For canonical statuses the pill renders a 3-letter code:

- `rvw` for `in-review`
- `apv` for `approved`
- `drf` for `draft`
- `cpl` for `complete` / `completed` / `done`

These work once you know them but are not obvious. A hover-tooltip presumably exists (not verified in this session). Worth a one-line legend somewhere on the page, or a discoverable hover affordance.

### 2.3 "Ready to close?" feature design is strong (severity: positive)

The candidacy detection is thoughtful: signal-based (task rows complete, PRs merged, no open issues, last edit age), evidence cards displaying each signal, `snapshot_hash` to prevent stale-confirm races, and a 14-day dismiss with auto-resurface on new signal. The UI affordance (Confirm complete / Dismiss) is clear.

The implementation is in `src/attune/ops/completion_candidates.py` + `static/js/completion_candidates.js`. The CACHE_TTL_SECONDS = 300s and in-process caching are appropriately scoped.

### 2.4 Status capture grabs entire status line (severity: by-design, with consequence)

attune-ai's `_STATUS_VALUE_RE` (in `src/attune/ops/routes/specs.py` — based on Phase 2 task 2.2 which mirrored attune-gui) captures more than the leading keyword. attune-gui's version captures `\S+` (first non-whitespace token); attune-ai's captures the rest of the line.

This is consistent within attune-ai but produces the long-string truncation problem above. A future alignment between the two implementations is worth considering — see attune-gui's recent PR [#57](https://github.com/Smart-AI-Memory/attune-gui/pull/57) for the regex evolution.

### 2.5 Drill-in page renders all phases on one scroll (severity: design choice)

The drill-in (`/specs/<slug>`) shows decisions, requirements, design, tasks as stacked sections — no tabs. For long specs this is a lot of scrolling, but the simplicity is honest. No finding here, just noting the design.

### 2.6 Spec count: 42 across 1 root

The dashboard reports 42 specs in `/Users/patrickroebuck/attune-ai/docs/specs`. Federated multi-root listing exists per spec task 1.2 (`--specs-root` flag) but is not configured by default. Compare with attune-gui's federated config which surfaces ~75 specs.

If "test the federated workflow" is part of Phase 4, that wasn't exercised in this session.

---

## 3. Findings — Home page

### 3.1 Layout is clean at desktop width; narrow viewports overflow horizontally (severity: friction)

At ~640px width (Cowork preview pane default), the nav tabs scroll horizontally and only "Home" + partial "Wor" are visible without manual horizontal scroll. At 1280×800 the nav fits comfortably.

Worth a media query that wraps the nav or shows a hamburger below some threshold.

### 3.2 Family snapshot shows version data that may be stale (severity: verify-then-decide)

The "Family snapshot" tile reports:

| Package | Reported | (as of session date) |
|---|---|---|
| `attune-ai` | v7.0.0 | matches pyproject |
| `attune-author` | v0.11.1 | (worth verifying) |
| `attune-rag` | v0.1.5 | attune-gui's pin is `>=0.1.22,<0.2`; 0.1.23 is on PyPI |
| `attune-help` | v0.7.0 | attune-gui's pin is `>=0.10.0,<1.0` |
| `attune-gui` | not installed | actually installed in the workspace this session ran from |

This isn't necessarily wrong (attune-ai's venv may not have these packages or may pin older versions), but the labels suggest "is the latest known good?" not "what does my venv have?" — worth clarifying the source of truth.

### 3.3 7-day spend sparkline renders correctly (severity: positive)

Sparkline drawn cleanly. Cost tiles ($136.47 7D, $471.21 MTD) match the daily-activity table below.

---

## 4. Findings — Workflows page

### 4.1 Recent-runs list shows worktree paths (severity: friction)

Each workflow row's "Recent runs" column shows the scope path of each historical run. For runs from worktrees, this surfaces paths like:

```
2026-05-17T15:09:31.491418+00:00, id 5e506b33,
scope: /Users/patrickroebuck/attune-ai/.claude/worktrees/reverent-sammet-ca2f0a/src/attune/ops/data.py
```

The worktree slug doesn't necessarily map to anything memorable. Suggestion: collapse worktree paths to their relative-from-repo-root form, or label them with branch name if recoverable. Doesn't affect correctness — just readability.

### 4.2 "Run" buttons are exposed without confirmation (severity: noted)

Each workflow row has a `Run` button. Clicking would trigger an Anthropic-billed workflow run. There's no confirmation modal. This is consistent with the dashboard's "dev tool" framing but worth noting.

---

## 5. Findings deferred (not exercised)

- **Sessions tab** — only the HTTP 200 response was verified.
- **Telemetry tab** — not exercised.
- **Health tab** — not exercised.
- **`--read-only` flag behavior** — not exercised.
- **Federated multi-root spec listing** — not exercised (would require a second `--specs-root` pointing at attune-gui's specs, for example).
- **Status-flip UI from the main spec table** — not directly tested in a controlled way (probably exercised inadvertently per Finding 0, but not as a deliberate check).

A second review session under safer conditions (read-only mode or a throwaway specs copy) should cover these.

---

## 6. Phase 4 task status

Mapping back to [tasks.md](tasks.md):

- **4.1** — *log which features are actually used (telemetry: spec listing views, status flips, drill-ins)*

  Not addressed by this review. This requires actual usage telemetry over time, not a single-session walk-through. Recommend keeping 4.1 open and building lightweight usage logging if it doesn't already exist (e.g., counting GET /specs hits and PUT /api/specs/* per day).

- **4.2** — *decide whether Phase 1's read-side is enough or whether to expand toward attune-gui's create/bootstrap flows*

  Defer until Finding 0 is resolved. Expanding the write surface while there's an open question about unintended writes would be premature.

- **4.3** — *if usage warrants, file a follow-up spec for Phase 5*

  Not yet. The strongest follow-up candidate from this review is **a spec for the unintended-PUT investigation** (Finding 0) — that's higher-priority than any feature expansion.

---

## 7. Recommendations

In rough priority order:

1. **Investigate Finding 0.** File a spec or a chip. Repro with `--read-only`. Confirm whether the trigger is a real bug or a preview-tool artifact.
2. **Add server-side auth to mutating endpoints.** Port the `X-Attune-Client` pattern from attune-gui's `routes/cowork_specs.py`. Even if Finding 0 turns out to be benign, defense-in-depth against accidental writes from any client (including automation) is cheap and valuable.
3. **Address the status-pill truncation.** Pick one of the three options in §2.1.
4. **Add a status-abbreviation legend** or hover affordance on the Specs page.
5. **Verify the family-snapshot version source.** Either explain "this is my venv's pin" in the UI, or read from PyPI to show "latest available."
6. **Run a second review session covering Sessions / Telemetry / Health / `--read-only` / federated multi-root.**

## 8. Open questions for Patrick to triage

- Is the Finding 0 investigation worth a fresh spec, or fold it into the existing `ops-specs-features` Phase 4?
- Should the second review session wait for Finding 0 to be understood (safer) or proceed with a throwaway specs copy (faster but less informative)?
- Is the "family snapshot" tile's source of truth documented anywhere? (Curious how attune-gui ended up as "not installed" when it's clearly installed in the workspace this session ran from.)
