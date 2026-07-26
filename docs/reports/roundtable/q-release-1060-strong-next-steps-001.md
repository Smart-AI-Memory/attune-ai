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

## #1 — question (chair)

> What are the best next steps between now (Wed 2026-07-23) and Monday
> 2026-07-27 to make the attune-ai 10.6.0 release VERY STRONG — and what
> should deliberately NOT be done in that window?
>
> Grounding (verified today):
> - A held queue of 16 PRs (zero DIRTY) lifts Monday in a ratified order:
>   flat lifts (#1562 #1571 #1574 #1578 #1591 #1605 #1607) -> memory-transport
>   stack (#1593->#1594->#1596->#1598) -> ops stack (#1576->#1615->#1616) ->
>   capability-projector --write sync -> release PR -> tag v10.6.0 -> PyPI
>   publish. Windows CI lanes (~13 min) must be waited on every src-diff PR.
> - The Monday 06:00 scheduled roundtable clean-run fire is the ship receipt
>   that flips agent-round-table to shipped/living. Dry-run rehearsal was
>   green (exit 0, 18,260-test keyless suite); only LIVE seat auth is
>   unproven.
> - Launch materials are all staged: article draft with [RECEIPT] slots,
>   LinkedIn Draft B-v2 with an honesty gate, two feature-page branches,
>   website multi-llm pillar branch. Publication fires TUESDAY 07-28, after
>   receipts. Policy: no claim without a receipt.
> - US-5 usage snapshot fires Fri/Sat via launchd; usage reads (DEC-7,
>   PersonalMemory) happen at the Monday sitting.
> - Post-lift blocked items: Codex MCP canary (needs marketplace re-sync),
>   Antigravity probe (needs the PyPI 10.6.0 publish), handoff T3/T4,
>   cross-review OPEN-1..3 rulings.
>
> "Very strong" means: the lift lands clean, the fire is green, published
> claims all carry receipts, and nothing regresses main. Answer with
> concrete, ordered actions for the Wed->Sun window specifically.

## #2 — position, round 1 (claude, 47s)

POSITION

The window's job is to protect Monday, not to add to it. In order:

Wed: (1) De-risk the one unproven link: LIVE seat auth — a minimal
manual live-auth smoke per seat, FROM THE SAME launchd environment the
06:00 fire will use (env-parity; a manual-shell success proves nothing
about the scheduled context). This does not consume the ship receipt —
the receipt is still the scheduled clean run. (2) Start a daily
queue-health sweep (mergeStateStatus across all 16); any drift to
BEHIND/DIRTY gets rebased now, not mid-lift. Zero-DIRTY is a snapshot,
not a property.

Thu: (3) Write the Monday lift runbook as an executable checklist:
ratified order, per-PR receipts (Windows-lane wait per src-diff,
git log -1 + mergeStateStatus verify after each merge, stacked-PR
re-target check before any --delete-branch). (4) Pre-author the
release PR content on a branch (7+ file version bumps, changelog,
README refs) so Monday is execution, not authoring — keep rebased,
don't merge. (5) Pre-map every [RECEIPT] slot in the drafts to the
specific Monday artifact that fills it — Tuesday becomes
paste-and-verify, not hunt.

Fri/Sat: (6) Verify the US-5 launchd snapshot actually fired (file
exists, non-empty) — "scheduled" is not a receipt. (7) Sat: re-run
the identical dry-run rehearsal unchanged — cheap, catches
environment drift; red buys two days of runway.

Sun: (8) Final queue sweep, confirm gh auth / PyPI workflow readiness
(read-only), then stop. Nothing merges after Sunday.

Deliberately do NOT: lift any PR early "to lighten Monday"; touch the
roundtable fire path (hard code freeze — the dry-run green is only
evidence for the code that ran); attempt the blocked post-lift items
(the T5' attempt already proved the sequencing); publish or tease
launch content before Tuesday; add new PRs/features/scope. Idle
capacity is a feature here.

RISK

The Wed live-auth smoke is the sharpest call and biggest exposure:
(a) it could be read as pre-spending the receipt, and (b) a green
manual smoke creates false confidence without true env-parity with
the scheduled run — the "worked in my shell, failed under launchd"
trap. If parity can't be established cleanly, the honest answer is
to let Monday's fire carry the full unknown. Secondary: freeze
discipline leaves four days under-utilized if the queue stays clean.

QUESTION

Does the honesty gate permit a pre-fire live-auth smoke as pure
de-risking, or does the ratified policy require LIVE auth to stay
untouched until the 06:00 fire so the receipt is uncontaminated?

## #3 — position, round 1 (antigravity, 42s)

### 1. Position on the Question

To guarantee a **VERY STRONG** `attune-ai 10.6.0` release on Monday 2026-07-27, the Wednesday-to-Sunday window must be dedicated exclusively to operational rehearsal, auth pre-flighting, telemetry monitoring, and absolute code stabilization.

#### **Concrete Actions (Wed 2026-07-23 → Sun 2026-07-26)**

* **Wed 07-23 — Live-Seat Auth & Credential Pre-flight:**
  * Validate live seat auth tokens/API keys out-of-band for the Monday 06:00 roundtable fire. The 18,260-test dry-run was keyless; live seat auth is the single remaining unproven point of failure.
  * Verify token scoping, rate limits, and failure fallback behaviors across all three model providers without committing changes to main.

* **Thu 07-24 — Queue Lift Execution Dry-Run & Scripting:**
  * Perform a non-push local rebase/merge dry run of the 16 PRs against `origin/main` in the exact ratified sequence: Flat lifts (`#1562` `#1571` `#1574` `#1578` `#1591` `#1605` `#1607`) $\rightarrow$ Memory-transport stack (`#1593` $\rightarrow$ `#1594` $\rightarrow$ `#1596` $\rightarrow$ `#1598`) $\rightarrow$ Ops stack (`#1576` $\rightarrow$ `#1615` $\rightarrow$ `#1616`) $\rightarrow$ `capability-projector --write` sync.
  * Verify that pre-commit auto-fix hooks run cleanly on each intermediate commit to avoid unstaged drift during Monday's fast-follow pushes.

* **Fri 07-25 & Sat 07-26 — Telemetry Monitoring & Snapshot Guarding:**
  * Verify the automated `launchd` execution of the US-5 usage snapshot on Fri/Sat. Confirm snapshot artifact integrity so DEC-7 and PersonalMemory reads land cleanly at the Monday sitting.

* **Sun 07-27 — Pre-Release Freeze & Runbook Lock:**
  * Enforce an absolute repository code freeze. Lock all PR branches and draft materials.
  * Ensure the PyPI release automation and post-publish verification scripts (e.g., Antigravity probe trigger) are ready to execute immediately following tag creation.

#### **What Deliberately NOT To Do in This Window**

* **DO NOT touch post-lift blocked items early:** Strictly refrain from initiating the Codex MCP canary, Antigravity probe, T3/T4 handoffs, or resolving OPEN-1..3 cross-review rulings before the 10.6.0 PyPI tag lands.
* **DO NOT add or re-order PRs:** Do not merge "small cleanups" or insert new PRs into the 16-PR queue, regardless of perceived low risk.
* **DO NOT force-push or mutate queued PR branches:** Keep all 16 PR branch tips pristine to preserve verified test baselines.
* **DO NOT modify launch copy or pre-populate `[RECEIPT]` slots:** Maintain strict adherence to policy—no receipts filled prior to live execution output on Monday.

---

### 2. Main Risk of My Position

**Risk:** *False-sense-of-security idle drift.* By locking code changes and strictly waiting for Monday, we risk discovering a live runtime edge case (e.g., an unexpected live API model response structure change or a rate-limit constraint during the 06:00 fire) during the active lift window rather than during the pre-lift window.

---

### 3. Follow-up Question for the Table

"Given that Windows CI lanes take ~13 minutes per `src-diff` PR, how should we structure the execution of the 16-PR queue on Monday morning—should we run strict sequential CI waits per PR on main, or pre-stage verified stack-rebased branches locally to parallelize CI triggers without risking lane failures?"

## #4 — position, round 1 (codex, 24s)

(1) POSITION

Treat Wed–Sun as a release-hardening window, not an implementation window.

1. Wed: Freeze scope and publish one authoritative Monday runbook containing the ratified PR order, dependency checkpoints, Windows-CI wait points, projector sync, release/tag/PyPI commands, owners, rollback/stop conditions, and required receipt locations.

2. Thu: Validate every queued PR against its expected base and Monday ordering. Reconfirm zero DIRTY, required approvals, mergeability, CI expectations, and overlapping files. Run the strongest practical keyless preflight on the final projected integration state without changing the held queue.

3. Fri: Verify the first US-5 launchd snapshot fired and produced readable, timestamped evidence. Perform a live-auth readiness check for each roundtable seat—credential presence, permissions, model availability, quotas, and a minimal non-publishing connectivity probe. LIVE seat auth is the largest remaining release risk.

4. Sat: Verify the second usage snapshot and rehearse Monday’s operational sequence from the runbook: merge checkpoints, failure ownership, rerun policy, receipt capture, article/LinkedIn honesty gates, feature-page publication gates, and explicit abort criteria.

5. Sun: Establish a quiet baseline: fresh main status, queue/CI/approval audit, PyPI and tag preconditions, secrets/auth availability, disk/runtime health, and Monday staffing. Pre-fill receipt templates with identifiers and commands, but leave outcomes blank. Then freeze all release surfaces.

6. Monday execution rule: lift strictly in ratified order; after each src-diff, wait for Windows CI and stop on unexplained failure. Run projector `--write`, verify no drift, merge the release PR, tag, publish, verify the installed PyPI artifact, then run the 06:00 clean fire and capture receipts. Only afterward run post-lift canaries/probes and unlock Tuesday claims.

Deliberately do NOT:

- Add features, refactor, upgrade dependencies, reorganize stacks, or “clean up” adjacent code.
- Rebase or refresh all 16 PRs merely for freshness; touch only demonstrably stale or conflicting branches.
- Parallelize dependent merges or waive the Windows lanes.
- Treat the dry run as proof of live-seat authentication.
- Run the marketplace-dependent Codex canary or PyPI-dependent Antigravity probe prematurely.
- Fill `[RECEIPT]` slots, remove honesty gates, schedule claims as unconditional, or publish anything before evidence exists.
- Resolve OPEN-1..3, T3/T4, or unrelated cross-review work unless it becomes a direct release blocker.
- Diagnose flaky infrastructure indefinitely: after two equivalent failures, stop, classify, and choose rollback, deferment, or abort.

(2) MAIN RISK

A strict freeze can preserve a latent integration defect that only appears when the stacked queue is assembled. Mitigate this with a non-mutating final-state integration preflight and explicit Monday stop/rollback criteria—not late code churn.

(3) FOLLOW-UP QUESTION

What exact live-auth probe can be run before Sunday that exercises all three seats without consuming the one scheduled clean-run ship receipt?

## #8 — position, round 2 (claude, 67s)

(A) PROBE: A safe, meaningful probe exists. Mechanics: throwaway
one-shot probe PLIST — copy the fire plist, change only Label +
ProgramArguments (10-line probe script: one minimal live completion
per seat — claude -p / codex exec / agy one-shot; success = exit 0 +
non-empty completion in ~/.attune/ops/authprobe-<date>.log). Run via
launchctl bootstrap gui/$UID + kickstart, then bootout + delete.
True parity: same gui domain, session type, env block, keychain
context — env -i approximations leak. WHEN: Wednesday — four days to
remediate an auth failure; re-run Sunday ONLY if Wed failed and was
fixed. Green proves credentials round-trip live under launchd; does
NOT prove Monday-06:00 state, concurrency, or orchestration (already
dry-run-receipted). CONTAMINATION: NO — the receipt's claim is "the
scheduled fire ran live, unattended, via the frozen path"; caveat:
a probe may refresh a token that would otherwise expire, making the
receipt "fires on a maintained machine" — which is the actual product
claim; note it in the receipt's conditions line.

(B) SLOTS: Pre-fill identifiers-only. Monday morning is the
highest-pressure window; hand-transcribing 16 PR numbers/SHAs under
pressure is the most probable source of a WRONG receipt. Defeat the
anchoring concern structurally: every outcome slot pre-populated
with the literal "PENDING — no evidence yet".

(C) PREFLIGHT: Yes — Thursday, sequential-assembly, NOT octopus.
Per-PR CI proved each branch alone; never the 16-branch assembled
state. Invisible failure classes: positional textual conflicts;
semantic conflicts (rename + new caller, both green alone). Fresh
scratch worktree off origin/main, git merge the 16 in ratified
order (sequential names the first bad position), then keyless suite
ANTHROPIC_API_KEY="" (empty, never unset). Conflict at N = the
demonstrated DIRTY drift the ruling requires → rebase that branch
only. Assembled-red/green-alone → prepare reconciling commit to land
right after the second PR, or hold the later PR. Honest limit:
macOS-local — Windows behavior stays unproven until Monday's lanes;
preflight shrinks mid-queue-break risk, does not replace lane waits.

## #9 — position, round 2 (antigravity, 43s)

### (A) PROBE DESIGN

* **launchd Environment Parity**: Execute the probe inside a clean environment matching the launchd daemon context using `env -i` combined with the explicit `PATH` and environment file sourced by the plist:
  ```bash
  env -i PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$(pyenv root)/shims" \
    $(cat /Users/patrickroebuck/.config/attune/anthropic.env | xargs) \
    <probe-command>
  ```

* **Invocation Shape per Seat**:
  * **Claude seat**: `env -i ... claude auth status` (or a 1-token live ping to `https://api.anthropic.com/v1/messages` verifying HTTP 200).
  * **Antigravity seat**: `env -i ... agy auth check` (verifying Google Cloud ADC / API credential validity).
  * **Codex seat**: `env -i ... codex auth status` (verifying OpenAI API key authorization).

* **What a Green Result Proves**: Proves that launchd environment variables correctly hydrate active, non-expired credentials and establish outbound network reachability to all three provider APIs without depending on interactive shell profiles (`.zshrc` / `.bashrc`).
* **What a Green Result Does NOT Prove**: Does not prove that multi-turn agent interaction, prompt template rendering, or payload output parsing inside the scheduled orchestration script will succeed under load on Monday.
* **Timing**: Run on **Sunday at 18:00 UTC** (12 hours prior to the Monday 06:00 fire) to allow sufficient lead time for credential rotation or network remediation without touching the code-frozen fire path.
* **Contamination Ruling**: **No.** An out-of-band auth probe validates credential plumbing without touching repository state, altering the frozen script, or generating the timestamped execution receipt reserved for the scheduled launchd fire.

---

### (B) RECEIPT SLOTS

* **Selection**: **Leave slots untouched until evidence exists.**
* **Strongest Reason**: Pre-filling receipt fields with identifiers creates a deceptive risk of unverified placeholder acceptance or partial commit pollution if execution fails mid-sequence, whereas untouched slots guarantee that every populated entry strictly represents verified, post-execution empirical log output.

---

### (C) INTEGRATION PREFLIGHT

* **Ruling**: **Yes.**
* **Mechanics**:
  1. Create a throwaway, detached local scratch branch on Friday: `git checkout -b scratch/preflight-16pr main`.
  2. Sequentially merge all 16 held PR branches in their exact ratified sequence into the scratch branch.
  3. Execute the full keyless unit/integration test suite (`uv run pytest tests/unit -q`) and pre-commit checks (`uv run --with pre-commit pre-commit run --all-files`).
  4. Delete the scratch branch immediately upon completion (`git checkout main && git branch -D scratch/preflight-16pr`).
* **Failure Trigger**: Any merge conflict, interface mismatch between dependent PRs, or test failure on the assembled tree triggers an immediate halt and isolates the offending PR before Monday's sequential lift begins.

## #10 — position, round 2 (codex, 30s)

(A) Run one minimal, read-only inference per seat on Sunday at 06:00—the same weekday-adjacent time and host state as Monday’s fire—after the final queue-health sweep.

Use a temporary launchd job whose environment is copied from the production plist, including its exact `PATH`, working directory, user, and the same `anthropic.env` sourcing step. Change only the program arguments from the roundtable fire to these seat probes:

```text
claude -p "Reply with exactly: AUTH_OK"
agy    -p "Reply with exactly: AUTH_OK"
codex exec --ephemeral "Reply with exactly: AUTH_OK"
```

If the installed `agy` version uses a different non-interactive flag, substitute its documented equivalent; do not add fallback providers or interactive login. Capture exit status, stdout, stderr, resolved executable path, model/provider identity where exposed, and timestamp. Require exit 0 and exact `AUTH_OK`; redact credentials.

Green proves that, from a launchd-equivalent environment, each resolved seat CLI can find its credentials, reach its provider, authenticate, and complete one inference. It does not prove Monday’s scheduler will fire, the roundtable orchestration will route correctly, all three responses will be persisted, or the downstream receipt/publish path will work.

No: a green probe does not contaminate the scheduled-fire receipt because it validates only independent seat authentication, while Monday remains the first execution receipt for the frozen scheduled orchestration path.

(B) Pre-map identifiers only: receipt key, scheduled timestamp, seat, expected artifact location, PR/commit identifiers, and required evidence fields; leave all outcomes, statuses, timestamps of observation, and evidence links blank.

The strongest reason is attribution integrity: deterministic identifiers prepared before execution prevent Monday responders from inventing or mismatching receipt targets under pressure without asserting that any evidence already exists.

(C) Yes—provided it remains disposable and cannot update held branches.

Create a scratch worktree from the exact Monday base, then sequentially merge the 16 exact held PR head SHAs in the ratified lift order using `git merge --no-commit --no-ff <sha>`. After each merge, record conflicts and abort only the scratch assembly if necessary; after the sixteenth, run the same keyless required suite with `ANTHROPIC_API_KEY=""`, including projection/drift guards, unit tests, lint/type checks, packaging checks, and any Windows-sensitive tests available locally. Record the base SHA, all 16 head SHAs, merge order, and test results; delete the scratch assembly afterward.

A merge conflict, projection drift, collection/import failure, packaging failure, or deterministic keyless test failure triggers a Monday hold and targeted investigation. It triggers branch refresh only if the failure demonstrates actual DIRTY/BEHIND drift; otherwise fix or revalidate the responsible PR without blanket rebasing.

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
