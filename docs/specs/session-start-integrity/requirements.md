# Session-Start Integrity — Requirements

**Status:** approved (chair, 2026-08-18) — implementation active
same-day; D1–D3 ratified, OQ1 deferred.
**Slug:** `session-start-integrity`
**Provenance:** roundtable `q-context-mgmt-review-001` (2026-08-18,
unanimous 3/3, round-1 convergence halt) over the same-day
session-start context test. Chair directed implementation of all
three table recommendations; this spec is the gate.

## Problem (motivating evidence, all observed 2026-08-18)

Session-start surfaces degrade silently instead of failing loudly:

- The global orientation script's status regex expects
  `**Status**:` while 53/55 specs write `**Status:**` — nearly
  every spec rendered "(unknown)" (alarm-fatigue trainer).
- `starter_reconciler.py` resolved the starter's PR references
  (#1–#8, written about a DIFFERENT repo) against attune-ai and
  printed plausible MERGED/CLOSED verdicts — a cross-repo false
  verification, injected at the moment of highest trust.
- The single global starter mixed two projects and was 5 days
  stale, with no staleness signal.
- `spec_orient.py` sibling copies are hand-synced twins and have
  ALREADY diverged (help+author hash `7736748…` vs rag+canonical
  `b3ee32f…`); attune-forms and attune-lite have no session-start
  hooks at all.

## Goal

Every session-start surface is correct or loudly refusing — never
plausibly wrong — with the writer side automated so the refusing
path stays rare. Mechanical enforcement over manual discipline.

## Requirements

### R1 — Starter provenance, machine-written

Starter files (`~/.attune/next_session_starter.md` and the
project-local `.attune/next_session_starter.md`) carry frontmatter:

```text
---
repo: <owner/name slug>
branch: <branch>
head_sha: <sha>
written_at: <ISO-8601 UTC>
---
```

A `--stamp <file>` mode on the reconciler script derives every
field from live git state — no hand-authoring. Acceptance: stamping
a file twice is idempotent; stamped fields match `git` output.

### R2 — Fail-closed reconciler (verification claims only)

- Provenance `repo` present and ≠ current repo identity → the
  reconciler REFUSES named-thread verification (PRs, branches,
  specs, versions) and prints an explicit skip notice naming both
  repos. No verdicts are emitted. The session still starts.
- `written_at` older than the TTL (48 h) → a loud `⚠ STALE` banner
  line (age in days) prepends the banner; verification still runs
  when the repo matches.
- No provenance block → verification runs (existing starters keep
  working) but the banner carries an explicit
  `⚠ no provenance — verdicts assume this starter is about THIS
  repo` warning plus the stamp pointer. Hard refusal is reserved
  for PROVEN mismatch (Claude seat's refusal-becomes-common-path
  risk; Codex's degrade-with-warning rule).

Acceptance: unit tests cover all three paths; a cross-repo starter
fixture produces zero PR verdicts.

### R3 — Repo identity anchoring

Identity = normalized `origin` remote slug (`owner/name`, scheme/
`.git`-suffix stripped, case-insensitive); fallback when no remote:
repo directory name. No committed UUIDs (D1).

### R4 — Corpus-tested status parsing

A drift-guard test runs the REAL parsers — the canonical
`attune.ops.specs_data` status regexes and the reconciler's
`STATUS_RE` — over every `docs/specs/*/requirements.md` in the
tree. Unparseable-status count is a shrink-only ratchet seeded at
the actual post-fix count (target 0); failure output names the
offending files. The corpus is the fixture.

### R5 — Personal orientation-script fix (out-of-repo)

`~/.claude/hooks/session_start_orientation.sh` accepts both
`**Status:**` and `**Status**:`. Personal infra — not CI-gated;
the receipt is a live re-run showing real statuses instead of
"(unknown)". Recorded here so the fleet audit (R7) and this spec
carry the claim.

### R6 — Single-source session-hook fleet projection

A registry file names each sibling repo and the hook file-set it
receives (canonical source: `plugin/hooks/`). A projector
(`scripts/sync_session_hooks.py`, `sync_agents_skills.py`
convention) supports `--check` (exit non-zero on drift/missing)
and `--write` (idempotent projection incl. the `SessionStart`
settings entry). Registry: attune-help, attune-author, attune-rag,
attune-forms, attune-lite. attune-gui excluded (parked, chair
2026-07-30).

### R7 — Fleet audit at session time

`collaboration_preflight.py` gains a fleet-audit check: WARN when
a registry sibling is missing a hook file or hash-diverges from
canonical; SKIP silently when the sibling directory does not exist
(CI-safe, other-machine-safe). Cross-repo state cannot be CI-gated
from attune-ai; the preflight line is the standing local gate, the
projector's `--check` the on-demand one.

### R8 — Live remediation (one-time, receipts required)

- Run the projector `--write` across the registry: attune-forms and
  attune-lite gain hooks; help/author/rag converge to the canonical
  hash. Receipt: `--check` clean + one live `spec_orient` run per
  newly-covered repo.
- Split the live global starter: archive the concluded
  IndianRailroadTicketing content (rename, reversible — no
  deletion), leave a stamped attune-ai starter. Receipt: reconciler
  re-run shows provenance-scoped output, no cross-repo verdicts.

### R9 — Retire the global starter (OQ1 ruled RETIRE, chair 2026-08-18)

`starter_prompt_nudge.py` surfaces the best tracked handoff first
(current branch's `docs/handoffs/<branch-slug>.md`, else the newest
tracked handoff) and MAY co-surface the project-local stamped
starter (`<repo>/.attune/next_session_starter.md`) — the two are
complementary (branch context vs repo-scoped queue), not
alternatives (wording amended 2026-08-18 after cross-review F1
flagged spec-code drift in the original "else"-chain phrasing). The
global file surfaces ONLY when no repo-scoped surface emitted, and
always explicitly labeled legacy. The live global file is archived
(rename, reversible); its still-live attune-ai queue migrates to
the project-local starter, stamped. Acceptance: a live hook run
surfaces the branch handoff first and never advertises the global
path unlabeled.

## Non-goals / open questions
- User-facing `attune hooks install` CLI — separate candidate spec
  (`docs/specs/hooks-install/`), not this scope.
- attune-gui (parked) and non-attune repos.

## Acceptance (spec-level)

All R1–R7 enforcers green in CI or receipted locally; R8 receipts
recorded in `decisions.md`; no session-start surface emits a
verdict about a repo it did not verify against.
