# Round table — very-strong 10.6.0 next steps (q-release-1060-strong-next-steps-001)

**Thread:** `q-release-1060-strong-next-steps-001` · **Date:**
2026-07-23 · **Roster:** claude, antigravity, codex · **Rounds:** 2
(halted on convergence, D3) · **Promoted items:** #2 #3 #4 #8 #9
#10 #11 (chair-approved; ruling #12).

Chair ruling (2026-07-23): promote this report; EXECUTE the
live-auth probe (A) and the assembled-queue preflight (C) in the
Wed window; DECLINE receipt-slot pre-mapping (B) — slots stay
untouched until evidence exists (the Antigravity position prevails
on that item).

## #11 — synthesis (moderator)

SYNTHESIS (moderator, after 2 rounds — halting on convergence).

UNANIMOUS (round 1, held through round 2): Wed-Sun is a hardening
window, not an implementation window. Freeze scope; no early lifts;
no early post-lift canaries; nothing publishes before Tuesday's
receipts; verify the US-5 launchd snapshot actually fired Fri AND
Sat; daily held-queue health sweeps (zero-DIRTY is a snapshot, not a
property). All three seats independently named LIVE seat auth for
the Monday 06:00 fire as THE remaining unproven link.

(A) PRE-FIRE LIVE-AUTH PROBE — 3/3 a safe probe exists; 3/3 it does
NOT contaminate the ship receipt (the receipt's claim is the
scheduled, unattended, frozen-path fire). Mechanics converge
(Claude + Codex): a THROWAWAY one-shot launchd job copied from the
production plist (Label + ProgramArguments changed only), one
minimal live completion per seat, capture exit/stdout/log, then
bootout + delete. Antigravity's env -i approximation is the weaker
variant (round-1 Claude explicitly flagged shell-approximation
leakage; auth-status subcommands don't prove a live round-trip).
SPLIT — timing only: Claude=Wednesday (4 days remediation runway,
don't re-poke on green); Codex=Sunday 06:00 (time/state parity);
Antigravity=Sunday 18:00. Moderator read: run it NOW (Wed/Thu) —
the known failure mode (401 -> chair runs `claude login`) costs
calendar time, and runway dominates time-parity; a Sunday re-check
is cheap insurance ONLY if anything changed. Claude's honest caveat
stands: a probe may refresh a token that would otherwise expire —
note "maintained machine" in the receipt's conditions line.

(B) RECEIPT SLOTS — 2/3 pre-map identifiers-only (Claude, Codex)
vs 1/3 leave untouched (Antigravity). The majority defeats the
minority's anchoring/deception concern STRUCTURALLY: identifiers
(PR numbers, SHAs, artifact paths) only, every outcome slot
pre-filled with the literal "PENDING — no evidence yet". Codex's
framing: attribution integrity — pre-mapped targets prevent
inventing/mismatching receipts under Monday pressure. Moderator
read: adopt the majority with the PENDING sentinel mandatory.

(C) ASSEMBLED-QUEUE INTEGRATION PREFLIGHT — 3/3 YES, converged
mechanics: disposable scratch worktree off origin/main (never
pushed, deleted after), merge the 16 held heads SEQUENTIALLY in the
ratified lift order (not octopus — sequential names the first bad
position), then the keyless suite with ANTHROPIC_API_KEY="" (empty,
never unset) + drift/projection guards. Failure semantics: textual
conflict at position N = the demonstrated drift the settled ruling
requires -> rebase THAT branch only; assembled-red/green-alone =
semantic conflict -> prepare a reconciling commit to land
immediately after the second PR, or hold the later PR out.
Honest limit (Claude): macOS-local — Windows stays unproven until
Monday's lanes; the preflight shrinks mid-queue-break risk, it does
not replace lane waits. Timing: Thursday (leaves Fri/Sat to
remediate).

NET-NEW ACTIONS the table added to the already-staged plan:
1. Wed/Thu: throwaway-plist live-auth probe (A).
2. Thu: assembled-queue preflight in a scratch worktree (C).
3. Thu/Fri: pre-map [RECEIPT] slots identifiers-only + PENDING
   sentinels (B).
4. Fri+Sat: verify US-5 snapshot artifacts exist and are non-empty.
5. Sat: optional identical dry-run re-run (environment-drift check).
6. Daily: held-queue mergeStateStatus sweep; rebase only on
   demonstrated drift.
DO-NOT list (unanimous): no early lifts, no fire-path changes, no
blocked post-lift items, no pre-Tuesday publication, no new scope.

## Executed receipts (2026-07-23, same session — chair ruling #12)

### (A) Live-auth probe — GREEN, all three seats

Throwaway launchd job `com.smartaimemory.attune.authprobe`
(ProgramArguments wrapper byte-identical to the fire plist: PATH
export, `anthropic.env` sourced, REDIS_URL, `cd ~/attune-ai`;
payload = one minimal live completion per seat). Bootstrapped,
kickstarted, booted out, plist deleted. Log kept:
`~/.attune/logs/authprobe.log` (09:38 EDT).

| Seat | rc | dur | reply |
|---|---|---|---|
| claude | 0 | 6s | `AUTH_OK` (API-key path per backlog-c ruling; the CLI's "claude.ai connectors disabled" notice IS that path, not an error) |
| antigravity | 0 | 38s | `AUTH_OK` |
| codex | 0 | 5s | `AUTH_OK` |

Monday's single unproven link (live seat auth under launchd) is
proven. Per the ruling, green does not get re-poked before Monday.
Fire-receipt condition to carry: the probe may have refreshed
tokens — the claim is "fires on a maintained machine".

### (C) Assembled-queue preflight — 2 real finds, both with prepared fixes

Scratch worktree off `origin/main` (`cb0c1cac2`), the 14 Monday
heads merged sequentially in the ratified lift order (head SHAs as
of 07-23; #1559/#1561 excluded — they are not Monday lifts).

**Find 1 — textual conflict at position 12 (#1576), predicted
DIRTY at the Monday ops-stack step.** `ops/memory-page` conflicts
with #1578 (`ops/a11y-fixes`, position 4) in
`docs/specs/ops-dashboard-polish/decisions.md` — an
append-collision (D3+D4+D6 audits section vs C1 re-validation
section). Invisible to per-PR `mergeStateStatus` (both clean vs
main alone). Monday consequence: after #1578 lands, #1576 flips
DIRTY. Prepared fix: `git merge origin/main` INTO
`ops/memory-page` resolving keep-both (strip the three conflict
marker lines — verified clean in scratch), then push and let CI
re-run. MERGE, not rebase: #1576 is the base of the #1615/#1616
stack; a rebase rewrites commits the stacked branches share.

**Find 2 — semantic conflict: #1594 ↔ #1605 tool-count updates,
each written against main + itself.** #1594 adds 5
`session_memory_*` tools (registered conditionally via the redis
plugin hook, `attune_redis/mcp_tools.py`); #1605 adds 2 handoff
tools and updated `tests/unit/test_mcp_memory_tools.py` to expect
55 with-redis. Assembled truth: **60 registered / 49 core-schema /
26 skills**. Both PRs are green alone; main goes red on
`test_tools_list_returns_at_least_core_count` the moment #1594
merges (after #1605). Prepared reconciling edit (verified green in
scratch — fold into the step-3b sync commit):

```python
        if redis_tools.issubset(tool_names):
            # attune-redis also registers 5 session_memory_* tools when the
            # core session stash is importable (conditional registration).
            expected = 60 if "session_memory_status" in tool_names else 55
            assert (
                len(tools) == expected
            ), f"Expected {expected} tools with redis plugin, got {len(tools)}"
```

**Step-3b confirmation + amendment.** On the synced assembled tree
`scripts/project_capabilities.py --write` repaired 6 files
(README, plugin/README, quickstart-plugin, mcp-integration,
marketplace.json, features.ts) to **26 skills / 60 registered /
49 core** and `--check` went green — these derived values
supersede the staged website branch's hand-bumps (which say 49
mcpTools; the projector's 49 CORE matches, but registered is 60).
Step 3b must run from the MAIN checkout: run from a worktree, the
projector silently imports main's `attune_redis` (script-dir
`sys.path[0]`, editable-install fallback) and derives the wrong
registered count (observed 55-vs-60 in scratch; hardening task
flagged).

**Suite receipt.** Keyless (`ANTHROPIC_API_KEY=""`) unit suite on
the assembled tree: first pass 13 failed / 18,854 passed in 93s —
ALL 13 were capability-count claim drift, the predicted step-3b
class. After projector `--write` + the reconciling test edit:
**18,867 passed / 65 skipped / 7 xfailed in 60s — zero failures.**

No other integration failure classes surfaced. The
complexity-ratchet and drift-guard lanes (tests/unit/quality,
gates) ran green in the assembled state.

---

*Curated stub (local-first reports, `docs/specs/local-first-reports/`): the sections above are the
chair-promoted content. The full deliberation transcript is
machine-local at `~/.attune/reports/roundtable/q-release-1060-strong-next-steps-001.md` and is
not distributed with the repository.*
