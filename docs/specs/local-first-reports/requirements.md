# Local-First Reports — Requirements

**Status:** parked (2026-08-08 triage — Phase 1 shipped in #1823:
roundtable transcripts machine-local, curated stubs in-repo;
Phase 2 is a design question set with no authority granted.)
Resume-Trigger: a chair gate on a named Phase 2 item
(lessons-corpus localization, cross-review ledger trim, or an
`attune reports` surface).
**Slug:** `local-first-reports`
**Provenance:** chair-initiated 2026-07-31 ("some of the reports
should be only on my machine and not distributed as part of
attune-ai"), refined through a lead pushback round in the same
session. Chair ratified the pushback-adjusted carve verbatim.

## Problem

The attune-ai plugin installs by cloning this repository, and the
repository is public. Every tracked report therefore distributes
two ways: public GitHub visibility, and a full copy on every
plugin user's machine. Three consequences:

1. **The chair's development data travels.** Roundtable
   deliberation transcripts, operational run records, and workflow
   narratives are the maintainer's working data, not product
   content. Users need the *generators*, not the maintainer's
   *output*.
2. **Repository size grows without bound.** Reports accrue per
   deliberation and per routine run; each one ships to every
   clone forever.
3. **The boundary was implicit.** Nothing distinguished "this
   file is product documentation" from "this file is the
   maintainer's session output," so every new report defaulted to
   tracked-and-distributed.

## Hypotheses

- **H1 — capability/content split.** Users should be able to
  GENERATE every report type (roundtable, cross-review,
  routine digests); the maintainer's own generated content should
  stay machine-local. Shipping the machinery and localizing the
  data are separable, and the split costs users nothing.
- **H2 — local-first + promote.** Defaulting report writers to
  `~/.attune/reports/` with deliberate, curated promotion into the
  repo preserves everything the repo actually needs (provenance,
  rulings, evidence) at a fraction of the bytes.

## The carve (chair-ratified 2026-07-31)

| Class | Disposition |
|---|---|
| Roundtable full transcripts (`docs/reports/roundtable/`) | **Phase 1: machine-local.** Full reports live at `~/.attune/reports/roundtable/`; the repo keeps curated stubs (chair-promoted sections + pointer) so spec citations resolve. |
| Future generated reports (all types) | **Phase 1: local-first by default.** Writers target `~/.attune/reports/`; repo promotion is a deliberate curated step. |
| Cross-review ledger (`docs/specs/cross-review/receipts.md`) | **Stays tracked (Phase 2 question).** Chair-ratified standing evidence surface, format-enforced by `tests/unit/gates/test_ledger_rejection_format.py`, read by cross-provider seats. Trimming it is a governance change requiring its own ruling. |
| Spec decision logs (`docs/specs/*/decisions.md`) | **Stays tracked, full stop.** Small, CI-enforced, and the only governance state cross-provider seats can see (they consume the repo through distribution channels). |
| Lessons corpus (`.claude/lessons.md`) | **Stays tracked for now (Phase 2 question).** It contains maintainer data AND is load-bearing: `test_core_mirror.py`, JIT-recall hooks, and Redis hydration read it. Localizing it is a migration (local corpus + hydration + repointed consumers), not a deletion. |

## Non-goals and honest boundaries

- **No retroactive privacy.** Phase 1 buys FUTURE privacy and
  repository size, nothing else. Every report migrated on
  2026-07-31 remains permanently in public git history, in forks,
  and in the `.git` of every existing clone. This migration is
  not a scrub, must never be described as one, and no phase of
  this spec will claim otherwise. Content that must actually be
  removed from history is a different operation (history rewrite +
  force-push + revocation semantics) with costs this spec does
  not authorize.
- **No new storage subsystem.** `~/.attune/` is the existing
  machine-local precedent (memory corpus, telemetry, health
  snapshots); reports join it. No new index, lifecycle, or
  sync layer.
- **No change to promotion authority.** The chair promotes (R8);
  local-first changes WHERE unpromoted content lives, not who
  decides what becomes durable.
- **No cross-provider blinding.** Anything a cross-provider seat
  needs to see (decisions, ledgers, contracts) stays in the repo —
  seats consume attune through distribution channels and cannot
  read `~/.attune/`.

## Counter-case (recorded from the lead's pushback, chair-accepted)

Localizing too much breaks the collaboration model: the shared
truth IS the repo (worktree, Git state, tests — never hidden
context), so every artifact that other agents, other machines, or
CI must read has to stay tracked. The original four-class proposal
(roundtable reports, cross-review receipts, decision logs, lessons)
was cut to one class plus a default for exactly this reason —
decision logs and the ledger are enforcement-wired and
seat-visible, and the lessons corpus has CI and hydration
consumers. The counter-case bounds every future phase: before
localizing a class, enumerate its in-repo consumers (grep tests,
hooks, hydration paths, seat-facing references) and either keep it
tracked or migrate the consumers in the same change.

## Phase 1 (executed 2026-07-31, this session)

1. Migrated 14 roundtable reports: full copies to
   `~/.attune/reports/roundtable/`, curated stubs in
   `docs/reports/roundtable/` (title + preamble + sections whose
   headings match ruling/promotion/synthesis/outcome/decision,
   plus a local-first pointer). Cited-provenance content verified
   preserved (e.g. the `q-outcome-first-attune-ux-001` ruling
   synthesis cited by `docs/specs/outcome-first-fix/`).
2. Roundtable skill D2 destination updated: full transcript →
   machine-local always; promoted content → owning spec's
   `decisions.md` or a curated stub. `.agents/skills/` mirror
   re-synced.
3. `docs/reports/roundtable/README.md` states the policy and the
   no-retroactive-privacy boundary.

## Phase 2 (design questions only — no authority granted)

- Lessons corpus localization: local corpus + hydration with only
  the core mirrored in-repo; requires repointing
  `test_core_mirror.py`, JIT-recall, and hydration consumers.
- Cross-review ledger: whether verbose per-run sections can move
  local with the format-enforced summary rows staying tracked —
  needs a chair ruling because the ledger is the P1 standing
  evidence surface.
- Whether `attune` should grow a `reports` surface (list/open
  local reports) so localized content stays discoverable.

Each Phase 2 item is authored and executed only behind its own
chair gate.
