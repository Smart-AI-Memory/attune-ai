# Cross-Provider Session Handoff — Requirements

**Status:** complete (2026-07-28; approved by chair 2026-07-22) —
implementation finished 2026-07-28; R1–R6 all satisfied, R6 closed
live (receipts.md).
**Slug:** `cross-provider-session-handoff`
**Provenance:** roundtable `q-multi-llm-obvious-win-001` (chair
ruling + same-day amendment, 2026-07-22) — see
`docs/reports/roundtable/q-multi-llm-obvious-win-001.md` and
tracking issue #1601.

## Problem

Context degrades at the provider boundary. A task started in Claude
Code cannot be reliably continued in Codex or Antigravity: the
receiving session lacks the declared goal, acceptance criteria,
changed-file set, decisions, verification receipts, and next action.
The collaboration contract defines a handoff artifact
(`templates/agent-handoff.md`, `docs/handoffs/<branch-slug>.md`) and
a verification duty ("a handoff is context, not authority"), but
both ends are manual prose today — nothing assembles the packet from
real state, and nothing verifies it against the current tree on
resume. Two of three roundtable seats independently named this the
highest-value multi-LLM gap.

## Goal

Make the contract's handoff a first-class, validated tool call on
both ends: `handoff_create` assembles a packet from actual git and
session state; `handoff_resume` verifies that packet against the
current worktree before any work continues. Providers become
interchangeable seats on one task, using surfaces every client
already has (MCP tools + tracked files + `session_memory_*`).

## Requirements

### R1 — `handoff_create` assembles from real state, never from claims

An MCP tool `handoff_create` producing
`docs/handoffs/<branch-slug>.md` per the contract template.

- Git-derived fields (branch, changed files vs the merge base with
  origin/main, ahead/behind counts, HEAD sha) come from actual git
  reads at call time — never from caller-supplied text.
- Caller-supplied fields (goal, acceptance criteria, decisions,
  risks, next action) are recorded verbatim but clearly attributed.
- Verification-table rows record only probes actually run; a claim
  without a probe result is written as `not run` — the tool must
  not fabricate pass rows.
- Result is `{ok, path, packet}` with the written file path; a
  write failure returns `{ok: false, reason}` (no false success —
  transport spec R1 discipline).

### R2 — `handoff_resume` verifies before continuing

An MCP tool `handoff_resume` that reads a named packet (default:
the current branch's slug) and returns a structured verification
report, not a go signal.

- Verifies against the CURRENT tree: branch exists, packet HEAD sha
  vs current HEAD (drift), changed-file set vs actual diff,
  uncommitted-state summary.
- Every divergence is an explicit machine-readable warning
  (`head_moved`, `files_diverged`, `branch_missing`,
  `packet_stale_days`); warnings never auto-block and never
  auto-fix.
- The report separates VERIFIED (git-derived, re-checked) from
  ASSERTED (caller-supplied prose) so the receiving agent knows
  what is context and what is authority-free claim (contract:
  "a handoff is context, not authority").
- Resume performs no side effects: no checkout, no file writes, no
  test runs.

### R3 — memory linkage, degrade-silent

- `handoff_create` additionally captures a pointer entry via the
  `session_memory_capture` surface (topic `handoff`, body = slug +
  goal one-liner) so cross-session recall surfaces open handoffs.
- `handoff_resume` recalls topic-`handoff` entries for the slug and
  includes them in the report.
- When the memory backend is unreachable, both tools proceed and
  report `memory: skipped` — the memory layer never blocks a
  handoff (contract rule), and skipping is stated, not silent
  success.

### R4 — works from sandboxed providers

- Both tools are registered through the same plugin MCP
  registration path as `session_memory_*`, so any client that gets
  those tools gets these (Codex marketplace, Antigravity MCP
  config, Claude Code plugin).
- `handoff_resume` requires only read access (git reads + file
  read) and must work in a read-restricted sandbox.
- `handoff_create` requires workspace write for the packet file; a
  denied write surfaces as `{ok: false, reason: write_denied}`
  (truthful-fallback discipline).

### R5 — terse by default (anti-ceremony)

Codex's named risk — ceremonial context duplication — is a binding
constraint, not a style note.

- The packet contains only sections with content; empty template
  sections are omitted from the rendered file.
- No transcript dumps: caller-supplied fields are bounded (packet
  body capped; oversize input is rejected with the cap named, not
  truncated silently).
- One packet per branch (the contract's `<branch-slug>` rule);
  re-running `handoff_create` updates the existing file rather than
  accreting copies.

### R6 — receipts (D7 discipline: no synthetic provider passes)

- Unit: packet assembly from a fixture repo (git-derived fields
  match reality; fabricated-claim path impossible by construction);
  resume drift matrix (head_moved / files_diverged /
  branch_missing / clean).
- Integration: real MCP dispatch through the server (transport
  spec receipt-2 pattern).
- Live: one non-mocked cross-provider round trip — packet created
  in a Claude Code session, resumed in a live Codex session after
  the 07-27 lift + marketplace re-sync; receipt appended to this
  spec's receipts.md. Honest `UNPROBED` rows stay until the named
  client actually runs (receipts.md ledger, transport-spec R8
  pattern).

## Non-goals

- No automatic handoff on session end — lifecycle hooks are not
  promised on Codex/Antigravity (transport spec D2/R5); both tools
  are explicit calls.
- No provider routing or recommendation (deferred with the router
  candidate; recorded-not-committed).
- No second memory subsystem, no daemon, no board dependency — the
  packet file plus existing memory transport is the whole
  mechanism.
- No auto-continue: `handoff_resume` reports; the receiving agent
  (and its human) decide.

## Dependencies

- Held stack #1593→#1598 merged (07-27 lift) — `session_memory_*`
  surface on main.
- Distribution lag applies to live receipts: Codex sees new tools
  only after a marketplace re-sync against main; Antigravity after
  the 10.6.0 PyPI publish (proven 2026-07-22, transport receipts 4
  and 6).
