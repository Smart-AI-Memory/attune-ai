# Spec: Ops Dashboard — Spec Completion Candidates

> Surface specs that look complete (all tasks checked, referenced
> PRs merged, no open follow-ups) as one-click confirmation
> candidates on the Specs page — without ever writing the status
> field automatically.

---

## Phase 1: Requirements

**Status**: complete (shipped — completion_candidates.js + dismiss route)

### Problem statement

The Specs page lets Patrick flip a spec's `**Status**:` line
between `draft / in-review / approved / complete`. In practice,
specs accumulate as `approved` long after the work has shipped:
the in-flight spec list at session start frequently shows entries
in `(unknown)` or stale `approved` state when the underlying
work is already on `main`. Patrick currently catches these on
manual review.

Patrick floated an opt-in feature where Claude marks `approved`
specs `complete` once the work appears done. The honest pushback
(brainstorm transcript, 2026-05-15) was:

- **Asymmetric cost.** A false negative costs ~10 seconds of
  manual marking. A false positive costs trust in the panel and
  possibly forgotten work. The existing `(unknown)` drift already
  shows automated tracking degrades silently — direct writes
  would make it worse.
- **"Complete" has nuance.** The current corpus uses `partial`,
  `paused`, `retired (premise invalidated)` — judgment calls
  about whether remaining work matters. An auto-marker collapses
  that to a boolean.

Patrick agreed: instead of auto-writing, surface **completion
candidates** with evidence inline, and let him click confirm or
dismiss. The detector does the scanning; the human keeps the
authority over the field.

### Scope

**In scope:**

- Detector module that scans specs and emits "looks complete"
  candidates with evidence. Lives in
  `src/attune/ops/completion_candidates.py`.
- `GET /api/specs/completion-candidates` endpoint returning the
  list of candidates with their evidence bullets.
- `POST /api/specs/{slug}/completion-candidates/dismiss` to
  suppress a candidate for a TTL (default 14 days). Dismiss
  state persisted to
  `~/.attune/ops/spec_completion_dismissed.json`.
- New "Ready to close?" section on the Specs page (above the
  main table), rendered only when the feature is enabled AND
  candidates exist. Each row shows:
  - Spec slug + current status
  - Evidence bullets (e.g. "all 8 tasks.md rows checked",
    "PR #324 merged 2026-05-14", "no open issues referencing
    this spec")
  - "Confirm complete" button → calls existing
    `PUT /api/specs/{slug}/{phase}/status` with `complete`
  - "Dismiss" button → calls the dismiss endpoint
- Opt-in setting via `--specs-candidates` CLI flag on
  `attune ops` (default OFF). Also readable from
  `~/.attune/ops/config.json` so the toggle persists across
  restarts.
- Read-only mode (`--read-only`) hides the section entirely —
  the section presupposes the user can flip statuses, which
  read-only mode forbids.

**Out of scope:**

- Auto-writing status fields. Confirmed explicitly out.
- Detecting `paused / partial / retired` nuance. Detector only
  proposes `complete`. The other statuses remain manual.
- Cross-repo PR detection. We only check PRs on the host repo
  of the spec root (i.e. the repo containing `docs/specs/`).
- Anything for `draft` or `in-review` specs. Candidates are
  only drawn from `approved`.

### User journey

1. Patrick opens the Specs page.
2. If `--specs-candidates` is enabled and the detector finds
   ≥1 candidate, a "Ready to close?" callout appears above the
   table with N rows.
3. Each row shows the spec slug, current status pill, and a
   2–4 line evidence summary.
4. Patrick clicks **Confirm complete** → row disappears, table
   row's status pill flips to `complete`.
5. Or clicks **Dismiss** → row disappears, suppressed for
   14 days. Reappears if new signal lands (PR merge, new
   tasks.md row checked) after dismissal.
6. If `--specs-candidates` is off, no section appears, no
   detector runs, no API calls happen — zero overhead.

### Detector signals

A spec is a completion candidate when **all** of the following
hold:

1. Current status (from any phase file: prefer `decisions.md` →
   `tasks.md` → `design.md` → `requirements.md`) is `approved`.
2. If `tasks.md` exists: every checklist row matches
   `- [x] ` or has a `**done**` / `**complete**` status marker.
   Zero unchecked `- [ ]` rows.
3. If the spec references PRs in `decisions.md` / `tasks.md`
   (regex: `#(\d+)` or `PR (\d+)`), all referenced PRs on the
   host repo are merged. Open or closed-without-merge → not a
   candidate.
4. No open issues on the host repo reference the spec slug in
   title or body.
5. `last_modified` (newest `.md` mtime in spec dir) is ≥ 24 h
   ago. Specs touched in the last day are likely still active
   — guard against marking work-in-progress as done.

The evidence shown in the UI is the bullet list of which checks
passed (e.g. "✓ 8 of 8 tasks.md rows checked", "✓ PR #324
merged 2026-05-14", "✓ last edit 3 days ago"). Failed checks
suppress the candidate entirely — the user never sees "almost
complete" rows. We want zero false positives, accept many
false negatives.

### Dismiss semantics

- Dismiss persists `{slug, dismissed_at, snapshot_hash}` to
  `~/.attune/ops/spec_completion_dismissed.json`.
- `snapshot_hash` = SHA256 of sorted (PR numbers + tasks.md
  mtime + last_modified). When the detector runs, it computes
  the current snapshot hash; if it differs from the dismissed
  hash, the candidate re-surfaces immediately (new signal
  landed). If it matches and `dismissed_at + 14 days > now`,
  the candidate stays suppressed.
- Manual flip-back-to-`approved` (via the existing status PUT)
  clears any dismiss entry for that slug, so a re-completion
  cycle can re-surface naturally.

### Open questions

- **Q1.** What's the host-repo discovery rule? Cheapest:
  `git remote get-url origin` from the spec root. Acceptable
  if the spec root sits inside the repo; less clean for
  multi-root setups. Alternative: a `--specs-host-repo
  owner/name` flag per root. Defer to design phase.
- **Q2.** Should the detector run on every page load, or on
  a cron? Page load is simpler; cost is ~1 `gh api` call per
  candidate-eligible spec per load. For the typical 5–15
  approved specs that's fine. If it becomes a perceptible
  delay, cache results for 5 minutes in-memory.
- **Q3.** What's the UI affordance when a confirmation fails
  (e.g. status PUT 403 because read-only mode flipped on
  between page load and click)? Standard inline error banner
  on the row, matching how the existing status pills handle
  PUT failures.
- **Q4.** Should `partial` / `paused` specs ever be candidates
  for *any* state change? Probably not in V1 — they're already
  explicit signals that "this isn't done and we know it." If
  the user wants to revisit one, they'll do it manually.
  Revisit in V2 if usage shows a pattern.

### Non-goals

- A general-purpose "review my project state" surface.
  Candidates only addresses `approved → complete`.
- Predicting *when* a spec will be complete from in-progress
  state.
- Replacing the manual status flip. The PUT endpoint stays
  the canonical write path.

### Success criteria

- Patrick can enable the feature with one CLI flag.
- Section appears only when ≥1 candidate is detected AND the
  feature is on AND read-only is off.
- Zero false-positive completion suggestions across the
  current spec corpus during a 1-week trial run (manually
  audited by Patrick). False negatives are acceptable and
  expected.
- Dismissing a candidate suppresses it until either 14 days
  pass or new signal lands.
- Disabling the feature removes the section and zero
  detector work runs.

---

## Phase 2: Design

**Status**: draft

### Resolved open questions (from requirements Phase 1)

- **Q1 — Host-repo discovery.** `git remote get-url origin`
  from the spec root's enclosing repo. Per-root override flag
  deferred until a real cross-repo case appears.
- **Q2 — Detector cadence.** Page load with a 5-minute
  in-memory cache keyed by the spec-roots tuple.
- **Q3 — Confirm-failure UX.** Inline error banner on the
  row, manual retry, row stays visible. Matches existing
  status-pill PUT-failure pattern.
- **Q4 — `partial` / `paused` candidates.** Out of scope.
  Detector only considers `approved`.
- **Q5 — PR-ref scope.** Extract from `decisions.md` and
  `tasks.md` only. Discursive files (`_sequencing.md`,
  audit notes) are excluded — they reference PRs for
  context more often than for closure.
- **Q6 — Persist the `--specs-candidates` toggle.** Yes,
  to `~/.attune/ops/config.json`. `--no-specs-candidates`
  clears the persisted state.

### Module layout

```text
src/attune/ops/
├── completion_candidates.py        # detector (new)
│   ├── Candidate (dataclass)
│   ├── detect_candidates(roots, config) → list[Candidate]
│   ├── _resolve_host_repo(root) → "owner/name" | None  [cached]
│   ├── _check_status_is_approved(spec) → bool
│   ├── _check_tasks_all_done(spec_dir) → (ok, evidence_str)
│   ├── _check_referenced_prs_merged(spec_dir, repo)
│   │       → (ok, evidence_str)
│   ├── _check_no_open_issues(slug, repo)
│   │       → (ok, evidence_str)
│   ├── _check_last_edit_age(spec) → (ok, evidence_str)
│   ├── _snapshot_hash(spec_dir, pr_numbers) → str
│   └── _cache  (module-level dict, 5-min TTL)
├── dismiss_store.py                # persistence (new)
│   ├── DismissEntry (dataclass)
│   ├── load() → dict[str, DismissEntry]
│   ├── save(slug, snapshot_hash) → None
│   ├── clear(slug) → None
│   └── is_active(slug, current_hash, ttl_days=14) → bool
├── routes/specs.py                 # add 2 endpoints
│   ├── GET  /api/specs/completion-candidates
│   └── POST /api/specs/{slug}/completion-candidates/dismiss
├── config.py                       # add field
│   └── specs_candidates_enabled: bool = False
├── static/js/completion_candidates.js  # frontend (new)
└── templates/specs.html            # add "Ready to close?" section
```

Existing files modified:

- `src/attune/cli_minimal.py` (or wherever `attune ops`
  args are defined) — add `--specs-candidates` flag.
- `src/attune/ops/server.py` — wire flag into config.
- Existing status-PUT endpoint — on successful flip away
  from `complete`, call `dismiss_store.clear(slug)` so a
  re-completion cycle can re-surface.

### Detector algorithm

Pseudocode for `detect_candidates(roots, config)`:

```python
cache_key = tuple(sorted(str(r) for r in roots))
cached = _cache.get(cache_key)
if cached and time.time() - cached.timestamp < 300:
    return cached.candidates

dismissed = dismiss_store.load()
candidates: list[Candidate] = []

for root in roots:
    repo = _resolve_host_repo(root)  # None if no git remote
    for spec in _list_specs_in_root(root):
        # Cheapest checks first; short-circuit on first fail.
        if not _check_status_is_approved(spec):
            continue
        ok_edit, edit_ev = _check_last_edit_age(spec)
        if not ok_edit:
            continue
        ok_tasks, tasks_ev = _check_tasks_all_done(spec.path)
        if not ok_tasks:
            continue

        # PR + issue checks gated on repo discovery.
        pr_numbers = _extract_pr_refs(spec.path)
        if repo is None and pr_numbers:
            # Can't verify PRs without a repo. Conservative:
            # treat as "not a candidate" rather than guess.
            continue
        if repo is not None:
            ok_prs, prs_ev = _check_referenced_prs_merged(
                pr_numbers, repo
            )
            if not ok_prs:
                continue
            ok_iss, iss_ev = _check_no_open_issues(spec.slug, repo)
            if not ok_iss:
                continue
        else:
            prs_ev = iss_ev = None  # nothing to show

        # Apply dismiss filter LAST so dismissed candidates
        # still benefit from the short-circuiting above.
        snap = _snapshot_hash(spec.path, pr_numbers)
        if dismissed.get(spec.slug):
            if dismiss_store.is_active(
                spec.slug, snap, ttl_days=14
            ):
                continue

        candidates.append(Candidate(
            slug=spec.slug,
            path=spec.path,
            current_status="approved",
            evidence=[e for e in (
                tasks_ev, prs_ev, iss_ev, edit_ev
            ) if e],
            snapshot_hash=snap,
        ))

_cache[cache_key] = CacheEntry(time.time(), candidates)
return candidates
```

Ordering rationale: status check is a file read; edit-age
is one stat call; tasks parse is one file read; PR/issue
checks are network. The cheapest local checks short-circuit
network calls for ~80% of specs.

### Signal-check specifics

**`_check_tasks_all_done(spec_dir)`** — parses `tasks.md` if
present. Returns `(True, "✓ 12 of 12 tasks complete")` when
zero `- [ ]` rows AND zero rows whose status field reads
anything other than `done` / `complete` / `**done**` /
`**complete**`. Returns `(True, "✓ no tasks.md (decisions-only spec)")`
when tasks.md is absent — many specs in the corpus skip
the tasks phase. Empty tasks.md (only the header) →
`(False, ...)` to avoid auto-completing skeletons.

**`_check_referenced_prs_merged(pr_numbers, repo)`** —
PR refs extracted via regex `(?:PR\s+|#)(\d+)` from
`decisions.md` and `tasks.md` only (not `_sequencing.md`,
audit files, or other discursive content — those frequently
mention PRs for context rather than closure). If a real
shipping claim lives only in a non-canonical file, the
candidate doesn't surface and the user does a manual flip
— the cheap failure mode. Calls `gh api repos/{repo}/pulls/{n}`
per PR (parallelized with a thread pool, cap at 4 concurrent).
Each PR must have `state == "closed"` AND `merged_at != null`.
Evidence string: `"✓ PRs merged: #324, #344, #358"`
(comma-separated, truncated to first 5 with `…+N more`).
On any `gh` non-zero exit or malformed JSON, treats as
"check failed" (conservative — not a candidate).

**`_check_no_open_issues(slug, repo)`** — `gh search issues
"{slug}" repo:{repo} state:open --json number`. Returns
`(True, "✓ no open issues reference this spec")` on empty
result. Slug-text matching is loose (substring), so a slug
like `ops-path-picker` would match issue titled "fix
ops-path-picker memory leak" — that's the desired behavior.
Evidence on the absence side; we never *show* the issue
numbers because their existence is what's being asserted
absent.

**`_check_last_edit_age(spec)`** — uses `spec.last_modified`
already computed by `_list_specs_in_root` in `specs.py`.
Returns `(True, "✓ last edit N days ago")` when
`now - last_modified >= 24h`. The 24h floor is the cheap
guard against marking work-in-progress as done.

**`_resolve_host_repo(root)`** — `subprocess.run(["git",
"remote", "get-url", "origin"], cwd=root.parent, ...)`.
Parses three URL shapes:

- `git@github.com:owner/name.git` → `owner/name`
- `https://github.com/owner/name.git` → `owner/name`
- `https://github.com/owner/name` → `owner/name`

Memoized per-root for the process lifetime — remotes
don't change inside a single dashboard session.
Non-zero exit (not a git repo, no origin) → `None`.

### Dismiss-store schema

File: `~/.attune/ops/spec_completion_dismissed.json`

```json
{
  "version": 1,
  "dismissed": {
    "ops-sessions-page": {
      "dismissed_at": "2026-05-15T18:30:00+00:00",
      "snapshot_hash": "a3f1c8d9...",
      "ttl_days": 14
    }
  }
}
```

Writes are atomic: write to `<file>.tmp` then `Path.replace`
to the real path (per the existing Windows-cross-platform
lesson). Reads are lazy (per request) — no in-memory cache,
the file is small enough that re-reading per call is cheaper
than coordinating cache invalidation across requests.

`is_active(slug, current_hash, ttl_days=14)` returns `True`
iff:

1. `slug` exists in the store, AND
2. `entry.snapshot_hash == current_hash` (no new signal
   landed since dismissal), AND
3. `now < entry.dismissed_at + entry.ttl_days`

Any failure → `False` (re-surface the candidate). When
condition 2 fails, the entry is also evicted on the next
write — dismissed-then-resurfaced is a one-shot.

### Snapshot hash

```python
def _snapshot_hash(spec_dir, pr_numbers):
    payload = json.dumps({
        "prs": sorted(pr_numbers),
        "tasks_mtime": _mtime_or_none(spec_dir / "tasks.md"),
        "last_modified": _newest_md_mtime(spec_dir),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
```

Deliberately excludes PR merge state from the hash. If a
referenced PR transitions open → merged, the candidate
should re-surface even though the local snapshot inputs
haven't changed. The detector's PR check sees the new
state; the dismiss-hash matches the old state; condition 2
fails; re-surface. Correct.

### API endpoints

**`GET /api/specs/completion-candidates`**

```json
{
  "enabled": true,
  "candidates": [
    {
      "slug": "ops-sessions-page",
      "path": "/abs/path/docs/specs/ops-sessions-page",
      "current_status": "approved",
      "evidence": [
        "✓ 8 of 8 tasks complete",
        "✓ PRs merged: #379, #382, #384",
        "✓ no open issues reference this spec",
        "✓ last edit 3 days ago"
      ],
      "snapshot_hash": "a3f1c8d9..."
    }
  ]
}
```

When `config.specs_candidates_enabled is False` or
`config.allow_run is False`: returns
`{"enabled": false, "candidates": []}` immediately without
invoking the detector. Frontend uses `enabled` to decide
whether to render the section header at all.

**`POST /api/specs/{slug}/completion-candidates/dismiss`**

Body: `{"snapshot_hash": "..."}`

Persists `(slug, snapshot_hash, dismissed_at=now, ttl_days=14)`
to the dismiss store. Returns `{"ok": true}` on success. The
client passes back the hash from the GET response so we can
guarantee dismiss-state aligns with what the user actually
saw — defends against the race where new signal lands between
GET and POST.

Gated by `config.allow_run` (read-only mode → 403), same as
the existing status-flip endpoint.

### Frontend component

`templates/specs.html` — server-rendered shell, hidden
initially:

```html
{% if config.specs_candidates_enabled and config.allow_run %}
<section id="completion-candidates"
         class="candidates-section"
         hidden
         data-tooltip="…"
         aria-label="Specs that look complete">
  <header>
    <h2>Ready to close? <span id="cc-count">0</span></h2>
    <p class="muted">
      Specs where all signals indicate the work is done.
      Confirm to flip status to <code>complete</code>,
      or dismiss for 14 days.
    </p>
  </header>
  <div id="cc-list"></div>
  <div id="cc-empty" hidden>
    <p>No completion candidates right now.</p>
  </div>
</section>
{% endif %}
```

`static/js/completion_candidates.js`:

```javascript
async function loadCompletionCandidates() {
  const sec = document.getElementById('completion-candidates');
  if (!sec) return;  // feature disabled — server didn't render shell
  const res = await fetch('/api/specs/completion-candidates');
  const data = await res.json();
  if (!data.enabled) return;
  renderCandidates(data.candidates);
  sec.hidden = false;
}

function renderCandidates(candidates) {
  // builds row markup per candidate, attaches confirm/dismiss
  // handlers, updates #cc-count
}

async function onConfirm(slug, snapshotHash) {
  // PUT /api/specs/{slug}/decisions/status  body={"status":"complete"}
  // on 200: remove row, refresh main specs table row's pill
  // on error: render inline banner on row, leave row visible
}

async function onDismiss(slug, snapshotHash) {
  // POST /api/specs/{slug}/completion-candidates/dismiss
  // body={"snapshot_hash": snapshotHash}
  // on 200: remove row
  // on error: inline banner
}

// Run on page load AND when main specs table refreshes
document.addEventListener('DOMContentLoaded', loadCompletionCandidates);
```

Row markup follows the existing dashboard card pattern.
Two action buttons:

- **Confirm complete** — primary button, requires no
  confirmation dialog (the evidence list IS the confirmation
  surface).
- **Dismiss** — secondary button, with tooltip explaining
  the 14-day TTL and the "resurfaces on new signal" semantics.

Per the existing tooltip lesson (`overflow: hidden` on parent
clips `::after`), the section uses `overflow: visible` on the
card container; clipping happens on inner spans only.

### Config + CLI

`config.py`:

```python
@dataclass
class OpsConfig:
    # ... existing fields ...
    specs_candidates_enabled: bool = False
```

CLI flag (per the existing `attune ops` argparse):

```python
parser.add_argument(
    "--specs-candidates",
    action="store_true",
    help="Surface 'Ready to close?' candidates on the Specs page",
)
```

Persisted toggle: when the user passes `--specs-candidates`,
also write `{"specs_candidates_enabled": true}` to
`~/.attune/ops/config.json` so the next `attune ops` launch
(without the flag) keeps it enabled. Symmetric
`--no-specs-candidates` flag clears the persisted state.

### Test plan

Unit tests for each signal check (`tests/unit/ops/
test_completion_candidates.py`):

- Status filter rejects non-approved specs
- Tasks check: all-checked, some-unchecked, missing
  tasks.md (passes), empty tasks.md (rejects)
- PR check: all merged, one open, one closed-not-merged,
  gh non-zero exit
- Issue check: empty result, non-empty result
- Edit-age check: 23h ago (rejects), 25h ago (passes)
- Snapshot hash determinism (same inputs → same hash;
  PR list order doesn't matter)

Dismiss-store tests:

- Roundtrip: save → load → entry matches
- TTL boundary: 13d 23h still active; 14d 1h not active
- Snapshot mismatch → not active even within TTL
- Atomic-write semantics (no partial writes visible
  mid-save)

API endpoint tests:

- GET when disabled → enabled=false
- GET when read-only → enabled=false
- GET happy path → candidates rendered
- POST dismiss happy path → store updated
- POST dismiss when read-only → 403

E2E "no false positives" check:

- One-shot script (`scripts/audit_completion_candidates.py`)
  that runs the detector against the live `docs/specs/`
  and prints results. Patrick runs this manually after
  implementation to verify zero false positives on the
  current corpus before flipping the feature on.

### Risks

- **gh CLI not installed.** Detector degrades to "no
  candidates" rather than failing. Document in the CLI
  flag's help text.
- **gh rate limits.** With 60 unauthenticated req/hr and
  ~15 specs × ~5 PRs each, the cache makes this comfortable.
  If a user disables `gh auth login`, they'll hit it
  on the first uncached load. Authentication is a
  prereq, document it.
- **Tasks-status parsing brittleness.** Tasks files vary
  in convention across the corpus (some use `- [x]`,
  some use `**done**` rows in tables). The parser handles
  both; future formats will need parser updates.
  Mitigation: when the parser can't make sense of a
  tasks.md file, treat as "check failed" not "passes" —
  err toward false negative.
- **Dismiss-store growth.** Bounded by number of approved
  specs that get dismissed; ~30 entries is a realistic
  upper bound. No eviction needed for V1.
- **Detector cache staleness across requests.** 5-min
  TTL means a user who clicks confirm could see the same
  candidate on a sibling tab for up to 5 minutes. Acceptable
  — confirming flips the underlying status to `complete`,
  so the next detector run filters it out by the status
  check. The stale UI is only the display, not the data.

---

## Phase 3: Tasks

**Status**: draft

### Shipping plan

One PR. The feature is opt-in default-off, surface is
bounded (~1.2k LoC including tests), and the cost of
splitting outweighs the benefit at solo-dev pace. Tasks
ordered by dependency; intermediate states compile and
pass tests.

### Task list

#### T1. Dismiss-store module + tests

**Files (new):**

- `src/attune/ops/dismiss_store.py` (~120 LoC)
- `tests/unit/ops/test_dismiss_store.py` (~200 LoC)

**What:**

- `DismissEntry` dataclass with `dismissed_at: datetime`,
  `snapshot_hash: str`, `ttl_days: int`.
- `load()` returns `dict[str, DismissEntry]`; missing file
  returns `{}`; corrupt file logs warning and returns `{}`.
- `save(slug, snapshot_hash, ttl_days=14)` atomic write via
  temp file + `Path.replace()` (cross-platform per existing
  lesson).
- `clear(slug)` removes the entry; no-op if absent.
- `is_active(slug, current_hash, ttl_days=14)` per the
  three-condition rule in Phase 2.

**Validation:**

- Roundtrip: save → load → entry matches.
- TTL boundary tests: 13d23h active, 14d1h inactive
  (use `freezegun` or `monkeypatch` on `datetime.now`).
- Snapshot mismatch → inactive even within TTL.
- Concurrent-write smoke test (two save() calls back-to-back
  produce the latest entry, no partial writes).
- Corrupt JSON: write `{"version": "bad"}` to the path,
  assert `load()` returns `{}` and logs at WARN.

**Risk notes:**

- Use timezone-aware datetimes per the existing
  `datetime.now(timezone.utc).isoformat()` lesson. Do NOT
  append `+ "Z"`.

---

#### T2. Detector module + per-signal tests

**Files (new):**

- `src/attune/ops/completion_candidates.py` (~280 LoC)
- `tests/unit/ops/test_completion_candidates.py` (~350 LoC)
- `tests/unit/ops/fixtures/completion_candidates/` (test
  spec dirs — minimal trees with known signal states)

**What:**

- `Candidate` dataclass per the GET endpoint schema.
- `detect_candidates(roots, config)` per the Phase 2
  pseudocode, including 5-min in-memory cache keyed by
  the spec-roots tuple.
- Five `_check_*` helpers per Phase 2 signal-check specs.
- `_resolve_host_repo(root)` with three URL-shape parsers.
- `_extract_pr_refs(spec_dir)` reading only `decisions.md`
  and `tasks.md` per Q5.
- `_snapshot_hash(spec_dir, pr_numbers)` per Phase 2.

**Validation per signal:**

- Status filter: 4 fixture specs (approved / draft /
  in-review / complete) — only approved passes.
- Tasks check:
  - all `- [x]` rows → pass
  - one `- [ ]` row → fail
  - missing tasks.md → pass with "no tasks.md" evidence
  - empty tasks.md → fail
  - mixed `**done**` / `**complete**` markers in tables
    → pass
- PR check:
  - all merged → pass
  - one open → fail
  - one closed-not-merged → fail
  - gh non-zero exit → fail (mocked subprocess)
  - 5+ PRs → evidence truncated to first 5 + "…+N more"
- Issue check:
  - empty result → pass
  - non-empty → fail (mock gh search output)
- Edit-age check: 23h ago fails, 25h ago passes.
- Snapshot hash:
  - deterministic across runs (same inputs → same hash)
  - PR list order doesn't matter (sort before hashing)
  - tasks.md mtime change → hash changes
- Host-repo resolver:
  - parses git@github.com:owner/name.git
  - parses https://github.com/owner/name.git
  - parses https://github.com/owner/name (no .git)
  - returns None when `git remote get-url origin` fails
  - memoized per-root (one subprocess call across N calls)

**Cache validation:**

- Two calls within 300s return same `id()` (cached).
- Call after manually advancing the cache timestamp
  re-runs the detector.

**Risk notes:**

- Mock `subprocess.run` and `gh` invocations — never hit
  real network in unit tests.
- Per the existing lesson on `subprocess.run(text=True)`
  on Windows, always pass `encoding="utf-8",
  errors="replace"`.

---

#### T3. Config field + CLI flag plumbing

**Files (modified):**

- `src/attune/ops/config.py` — add
  `specs_candidates_enabled: bool = False`.
- `src/attune/cli_minimal.py` (or actual ops arg site)
  — add `--specs-candidates` / `--no-specs-candidates`
  flags.
- `src/attune/ops/server.py` — read persisted config from
  `~/.attune/ops/config.json` at startup, overlay CLI
  flag, write back if flag changed the value.

**What:**

- `--specs-candidates` sets enabled True and persists.
- `--no-specs-candidates` sets enabled False and persists.
- Neither flag: load persisted value (default False).
- Help text mentions `gh auth login` is a prereq for
  PR / issue checks.

**Validation:**

- `tests/unit/ops/test_config_persistence.py` — write,
  read, overlay precedence.
- Manual smoke: `attune ops --specs-candidates` then
  `attune ops` (no flag) — feature stays on.

**Risk notes:**

- Config-file write is new surface. Atomic via temp file
  + replace. Permission errors → log + degrade to
  in-memory-only for the session.

---

#### T4. API endpoints + status-PUT modification

**Files (modified):**

- `src/attune/ops/routes/specs.py`:
  - Add `GET /api/specs/completion-candidates`
  - Add `POST /api/specs/{slug}/completion-candidates/dismiss`
  - Modify existing `PUT /api/specs/{slug}/{phase}/status`
    to call `dismiss_store.clear(slug)` on successful
    flip AWAY from `complete` (re-completion cycle support).

**Files (new):**

- `tests/unit/ops/test_completion_candidates_routes.py`
  (~250 LoC)

**What per Phase 2:**

- GET respects `enabled` (config flag) AND `allow_run`
  (read-only mode); either off → `enabled: false,
  candidates: []`.
- POST body: `{"snapshot_hash": "..."}`; validates slug,
  validates hash format (hex), persists, returns
  `{"ok": true}`.
- POST gated by `allow_run` → 403 when read-only.
- Status-PUT modification: idempotent — clearing an
  already-absent entry is a no-op.

**Validation:**

- GET when disabled → `enabled: false`.
- GET when read-only → `enabled: false`.
- GET happy path → candidates present with expected shape.
- GET caches across two calls (mock detector, assert
  called once).
- POST happy path → store updated, GET no longer shows
  the candidate.
- POST when read-only → 403.
- POST with non-matching hash → still persists (the hash
  comes from the client, we trust it; server-side
  recompute would race).
- PUT status `approved → complete` → dismiss NOT cleared.
- PUT status `complete → approved` → dismiss cleared.

**Risk notes:**

- Use the existing test client / fixture pattern from
  `test_specs_routes.py` if present; same shape.

---

#### T5. Frontend section + JS

**Files (modified):**

- `src/attune/ops/templates/specs.html` — server-render
  the section shell behind the
  `config.specs_candidates_enabled and config.allow_run`
  gate.

**Files (new):**

- `src/attune/ops/static/js/completion_candidates.js`
  (~180 LoC)
- CSS additions to `src/attune/ops/static/css/main.css`
  for the candidates section (~60 LoC).

**What:**

- Per the Phase 2 component spec.
- Row markup uses existing card pattern; tooltip on the
  Dismiss button explains 14-day TTL + signal-aware
  re-surface.
- `onConfirm` → existing PUT status endpoint with
  `complete` → on success remove row + flip the main
  table row's status pill (DOM update; no page reload).
- `onDismiss` → new POST endpoint → on success remove row.
- Failures render inline error banner on the row; row
  stays visible.
- Page-load fetch; no polling.

**Validation:**

- `tests/unit/ops/test_specs_page_candidates_section.py`
  — section renders when enabled, hidden when disabled,
  hidden when read-only.
- Manual browser check via the worktree-venv launch
  recipe (per existing lesson): no JS errors in console,
  confirm/dismiss buttons functional, error path shows
  banner.

**Risk notes:**

- Cache-buster on `completion_candidates.js` per the
  existing `?v={{ attune.__version__ }}` lesson — avoids
  stale JS after release.
- Tooltip on Dismiss button must use `overflow: visible`
  on its container per the existing `::after` clipping
  lesson.
- Use `os.path.join("docs", "specs")` (or POSIX
  `.as_posix()` on display strings) for any test
  asserting on paths — Windows separators.

---

#### T6. E2E audit script

**Files (new):**

- `scripts/audit_completion_candidates.py` (~80 LoC)

**What:**

- Runs `detect_candidates` against the live `docs/specs/`
  and prints each candidate with full evidence.
- No writes; no dismiss-store interaction. Read-only
  audit.
- Prints a one-line summary at the end: N candidates
  surfaced, N skipped (with reasons grouped: status,
  tasks, prs, issues, age).
- Exit 0 always (audit, not a gate).

**Validation:**

- Manually run on the current attune-ai
  `docs/specs/` corpus.
- Patrick reviews output: zero false positives required
  before flipping the feature on by default for himself.
- The script lives in `scripts/` rather than
  `src/attune/`; keep it out of the package surface.

**Risk notes:**

- Document in the script's docstring: "this hits the
  GitHub API and requires `gh auth login`. Expect ~30s
  on a ~30-spec corpus."

---

#### T7. Documentation

**Files (modified):**

- `src/attune/ops/cli.py` (or wherever) — CLI help text.
- `CHANGELOG.md` — `### Added` entry under `## [Unreleased]`.
- `docs/specs/ops-specs-completion-candidates/decisions.md`
  (new, short) — captures the four Q1–Q6 decisions for
  archival, mirrors the convention in `ops-path-picker`
  and `ops-sessions-page`.

**What:**

- One-line CHANGELOG entry.
- decisions.md is the durable record once the spec ships;
  this requirements.md becomes the historical draft.

**Validation:**

- CHANGELOG renders correctly on PyPI (per existing
  lesson on relative links).

---

### Pre-merge gates

1. All new unit tests pass on all OS lanes.
2. `coverage report` for `src/attune/ops/completion_candidates.py`
   and `src/attune/ops/dismiss_store.py` ≥ 85%.
3. E2E audit script run by Patrick against live
   `docs/specs/` — zero false positives.
4. Worktree-venv manual smoke check of the UI per the
   existing recipe (confirm, dismiss, and error-path
   each exercised once).
5. `gh pr checks --watch` clean on all required platforms.

### Post-merge follow-ups (deferred)

- Watch the dismiss-store size over a few weeks. If it
  grows past ~50 entries, add an eviction policy (drop
  entries older than 90 days).
- If users (or Patrick) report wanting `partial → complete`
  flow, revisit Q4.
- If multi-repo specs roots become a real case, add the
  per-root `--specs-host-repo` flag deferred in Q1.

---

## Phase 3: Tasks

**Status**: not started

(To be drafted after design approval. Anticipated phases:
detector module + unit tests; API endpoints (candidates GET,
dismiss POST); dismiss-store persistence; frontend section
+ JS wiring; CLI flag plumbing; opt-in config persistence;
end-to-end test on the live spec corpus.)
