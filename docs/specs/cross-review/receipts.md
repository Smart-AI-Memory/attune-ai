# Cross Review — Receipts

## R5 dogfood ledger (T3 — five real runs, 2026-07-28/29 session)

D5/D7-honest: every row below is a real run executed 2026-07-29 UTC
(2026-07-28 ET evening session); no synthetic entries. Board thread
ids recorded per T3's live-fire check. Dispositions ruled by Patrick
(chair) in-session, 2026-07-28 ET.

Rejection rows (D11a, 2026-07-29): a disposition in a rejection
class (`dismissed` / `noise` / `rejected`) must read
`<class> — claim: "<seat's words verbatim>" — reason: <lead's
reason>` — enforced by
`tests/unit/gates/test_ledger_rejection_format.py`; pre-D11 rows
are allowlisted there explicitly.

Principle tags (D12, 2026-07-29): where a finding maps to a
contract principle, append `[P<n>]` to the disposition (e.g.
`real — accepted and fixed [P1]`). Convention, not gated — the
tags let the ledger passively accumulate evidence of which
principles the review lanes actually exercise (the aspirational
principles are measurable nowhere else).

Countersign tokens (D11c, 2026-07-29): a row claiming the lead's
central receipt re-run was skeptic-countersigned carries the full
citable token `countersign: <seat> :: <label> :: sha256:<16+ hex>`
(dissents: same grammar, `dissent:` prefix), produced only by
`attune.roundtable.countersign` from an executor-written,
digest-verified artifact. Enforced by
`tests/unit/gates/test_ledger_countersign_format.py`, which imports
the grammar from the module — a bare "countersign:" claim without
the artifact digest is exactly the lead-narrated form D11c rejects,
and it fails the gate.

| Date | Seat | Target | Files | Findings | Disposition |
|---|---|---|---|---|---|
| 2026-07-29 | codex | branch vs merge-base 94e8459c5 (origin/main) — #1559 skeptic diff | 3 sent / 0 omitted | 5 (findings) | ruled at the #1559 lift (row closed 2026-07-30, chair-directed; fixes verified in merged tree) — 4 real, accepted and fixed in the lift commit (worktree-from-HEAD blind spot surfaced via `uncommitted_paths`; uncited COUNTERSIGN parses malformed; CITE validated against executed labels; git failures raise `SkepticError`) + 1 dismissed — claim: "caller-provided `scratch_root` is not created before `git worktree add`; nonexistent roots fail" — reason: `git worktree add` creates missing parents (probed live, 3-level nonexistent root, exit 0); `test_isolated_pass_and_fail_receipts` stays as the regression guard [P1] |
| 2026-07-29 | antigravity | branch vs merge-base 94e8459c5 (origin/main) — #1559 skeptic diff | 3 sent / 0 omitted | 0 (clean) | clean |
| 2026-07-29 | codex | branch vs merge-base cd55f3839 (origin/main) — lessons docs diff | 1 sent / 0 omitted | 1 (findings) | dismissed — dated context by design |
| 2026-07-29 | antigravity | branch vs merge-base cd55f3839 (origin/main) — lessons docs diff | 1 sent / 0 omitted | 0 (clean) | clean |
| 2026-07-29 | codex | branch vs merge-base e7fa7e088 (origin/main) — feature-page docs branch | 23 sent / 7 omitted | 3 (findings) | stale-branch — carry only if revived |
| 2026-07-29 | codex | branch vs merge-base 51bc7550f (origin/main) — feature-lead PILOT diff (contract lead rule + base.py QA) | 6 sent / 0 omitted | 1 (findings) | real — accepted and fixed in-branch (single-provider lead fallback) |
| 2026-07-29 | codex | branch vs merge-base db48a3bf2 (origin/main) — pilot lane 3: principles draft + citations guard | 2 sent / 0 omitted | 2 (findings) | real — both accepted and fixed in-branch (path-scope widened; def/class-anchored name check); verify-it-fires receipts re-run |
| 2026-07-30 | codex | branch vs merge-base ace35630b (origin/main) — 11.1.0 release-prep diff (#1761, D11b release-class lane) | 11 sent / 0 omitted | 0 (clean) | clean |
| 2026-07-30 | codex | branch vs merge-base 53b62da04 (origin/main) — G5 workflow-OS hard tier + straggler sweep (D11b governance lane) | 7 sent / 0 omitted | 0 (clean) | clean |
| 2026-07-30 | codex | staged changes — D11b refinement: authored contract/spec/rule text named explicit risk class (D11b contract-text lane; row 10, D8 count bar closed) | 5 sent / 0 omitted | 1 (findings) | real — accepted and fixed in-branch (decisions entry cited this row before it existed; row landed in the same commit) [P1] |
| 2026-07-30 | codex | staged changes — D11b default-on RULED: risk-triggered permanent (contract master + decisions transcription; D11b contract-text lane) | 5 sent / 0 omitted | 1 (findings) | dismissed — claim: "The ruling is dated 2026-07-30 even though the current date is 2026-07-29, creating a future-dated governance record and unreliable audit chronology." — reason: this ledger records UTC dates by documented convention (header: "executed 2026-07-29 UTC (2026-07-28 ET evening session)"); it is 2026-07-30 UTC and the module-generated rows this session carry the same stamp — the chronology is consistent, not future-dated |
| 2026-07-30 | codex | staged changes — P1 FULL ACTIVATION ruled: pilot exits to standing mode, spec status active, execution un-gated (D11b contract-text lane; row 12) | 7 sent / 0 omitted | 0 (clean) | clean |
| 2026-07-30 | codex | staged changes — P1 entry amendment: finding-level precision (3 parked under stale-branch) + codex-deep evidence caveat (D11b contract-text lane; row 13) | 1 sent / 0 omitted | 0 (clean) | clean |
| 2026-07-30 | codex | staged changes — D11d lead-conduct guards, lane round 1 (D11b contract-text lane) | 6 sent / 0 omitted | 2 (findings) | real — both accepted and fixed in-branch (contract bullet omitted D11d.4 while decisions claimed it encoded; label-drop carve-out wording authorized undoing chair actions) [P3][P1] |
| 2026-07-30 | codex | staged changes — D11d round 2 after fixes | 6 sent / 0 omitted | 1 (findings) | real — accepted and fixed in-branch (FEEDBACK-ASK bound all seats but mechanics were Claude-only; contract now carries the agent-agnostic shape with structured-text degradation) [P3] |
| 2026-07-30 | codex | staged changes — D11d round 3 after fixes | 6 sent / 0 omitted | 2 (findings) | real — both accepted and fixed in-branch (decisions record lagged its own projections on the own-actions limit; chair-reliance clause added to the carve-out) [P3] |
| 2026-07-30 | codex | staged changes — D11d round 4 after fixes | 6 sent / 0 omitted | 2 (findings) | real — both accepted and fixed in-branch (protect-then-ask contract text missed the endorsed/relied clause; CHAIR-ARMS read-receipt was UNBOUND — now SHA-bound, the round's standout mechanism catch) [P3][P1] |
| 2026-07-30 | codex | staged changes — D11d round 5 after fixes (loop capped this round) | 6 sent / 0 omitted | 1 (findings) | real — accepted with a scope-preserving fix (mandated constructs unsatisfiable for open-ended asks; resolved: constructs fire when content exists, open asks render as free-text form fields — independently reprises the lead's overruled disposition-only edge; the chair's full-scope ruling stands) [P13] |
| 2026-07-30 | codex (implements) | delegated implementation lane — audit_logger behavioral suite (first post-P1-activation lane; receipt-declared: suite + metric) | draft: 1 test file + un-omit | 2 lead amendments | lead-integrated with recorded amendments (unused import; event-shape assertions corrected to the nested violation dict). Central receipts re-run by the lead: 12 passed serially; 95% module coverage (bar 85%). countersign: antigravity :: audit-suite :: sha256:077f4d766ea674b6 (first live D11c token — executor artifact at the lane HEAD, re-minted after the review fix) [P1][P11] |
| 2026-07-30 | antigravity | branch vs merge-base e2de7f2c8 (origin/main) — audit_logger lane diff (P1-caveat commitment: first post-activation review via antigravity) | 2 sent / 0 omitted | 1 (findings) | real — accepted and fixed in-branch (builtins.open monkeypatch risked pytest/coverage interference; seam narrowed to json.dump). Antigravity's first-ever finding across all lanes — yields on TEST code [P1] |
| 2026-07-30 | codex (implements) | delegated implementation lane 2 — tokens.py coverage gap (overnight, chair-authorized scope; receipt-declared: suite + metric) | draft: 1 test file + un-omit | 0 lead amendments | lead-integrated clean. Omit entry was masking an already-88%-covered module (QA-6 illusion class); now 96%, remainder is the untestable tiktoken-ImportError guard. Central receipts: 37 passed serially; 96% module coverage. countersign: antigravity :: tokens-suite :: sha256:318f137ab96371f0 (minted at final HEAD per the countersign-last rule) [P1][P11] |
| 2026-07-30 | antigravity | branch vs merge-base d5a625ca2 (origin/main) — tokens lane diff | 2 sent / 0 omitted | 2 (findings) | 1 real — accepted as hardening (mock lambda gains default args; TypeError from a mock is a confusing failure mode) + 1 dismissed — claim: "Monkeypatching attune.models.registry.get_pricing_for_model will not affect tokens.py if get_pricing_for_model was imported directly." — reason: estimate_cost imports the symbol INSIDE the function body, re-binding from the registry module on every call; the patch demonstrably works — the test's ValueError assertion passes, which is the receipt [P1] |
| 2026-07-30 | codex | staged changes — chair-arm paved-path script, round 1 (D11b governance lane; queue item 1 of the 07-30 close-out) | 2 sent / 0 omitted | 2 (findings) | real — both accepted and fixed in-branch (arm-without-label now refused with the enabling actor named — receipt laundering closed; governance surface map gains AGENTS.md + content/collaboration/) [P1] |
| 2026-07-30 | codex | staged changes — chair-arm round 2 after fixes | 2 sent / 0 omitted | 1 (findings) | real — accepted and fixed in-branch (label presence now gates the `armed` verdict; a lingering autoMergeRequest after a half-failed guard disarm no longer counts as armed) [P1] |
| 2026-07-30 | codex | staged changes — chair-arm round 3 after fixes | 2 sent / 0 omitted | 4 (findings) | real — 3 accepted and fixed in-branch (receipt reworded to assert THIS chair-run rather than label history; a head move during verify now disarms + unlabels fail-closed; receipt dedup author-scoped so an arbitrary commenter cannot suppress the real receipt) + 1 dismissed — claim: "An existing autoMergeRequest plus label is accepted without proving the current chair applied or re-applied that label, allowing a pre-existing or independently created arm to be laundered into a chair read-receipt." — reason: lead and chair share one gh identity in this repo (the script runs under the chair's auth and the when-green workflow arms via the owner's PAT), so label-application attribution is API-unknowable; the conduct guard is procedural (D11d binds the lead), and the script is chair-run by definition [P1] |
| 2026-07-30 | codex | staged changes — chair-arm round 4 after fixes (loop capped this round) | 2 sent / 0 omitted | 1 (findings) | dismissed — claim: "A head push after the final polled SHA check but before receipt lookup/comment posting leaves auto-merge armed on an unread head while publishing a stale SHA receipt; refetch and validate the head immediately before posting, and disarm on mismatch." — reason: the receipt is SHA-bound and self-invalidating by design (a later push makes receipt-SHA differ from the visible head, which is D11d's own invalidation rule), the round-3 fix already disarms on any head move observed during verify, and a pre-post refetch narrows but cannot close a check-then-post race — the residual window is about a second and irreducible client-side [P1] |
| 2026-07-30 | codex (implements) | delegated implementation lane 3 — attune.mcp.server handler + protocol-adapter suite (first HARDER-target lane: 60-tool dispatch, async handlers, module-global adapter singleton; receipt-declared: suite + metric; brief carried live-captured runtime envelopes) | draft: 1 test file | 0 lead amendments | lead-integrated clean — zero guessed shapes; the seat flagged its one uncertainty (60 tools split 49 `_tool_handlers` / 11 `_plugin_handlers`) instead of papering over it, then pinned it as a contract test. Central receipts re-run by the lead: 70 passed serially; module coverage 34%→60% (elicitation + help blocks reserved for later lanes; omit entry stays until the 85% bar). countersign: antigravity :: mcp-server-suite :: sha256:2aedba2d24eef605 (executor artifact at final HEAD f9648144b per the countersign-last rule) [P1][P11] |
| 2026-07-30 | antigravity | staged changes — mcp/server lane 3 diff (thread review-claude-weekly-role-changes-review-070ee6-20260730-1742) | 1 sent / 0 omitted | 1 (findings) | real — accepted and fixed in-branch (unconditional `len(app.tools) == 60` pin was environment-brittle AND duplicated the conditional pin `test_mcp_memory_tools.py:49` already owns; the set-equality registration contract stays). Third real antigravity finding — all three on TEST code, the role-shaped-yield pattern holding [P1] |
| 2026-07-30 | codex (implements) | delegated implementation lane 4 — attune.mcp.server elicitation block (receipt-declared: suite + metric; brief carried live-captured envelopes incl. three non-determinism traps: timestamped response_id, content-hashed widget form id, wrapper-added voice_summary) | draft: 1 test file | 0 lead amendments | lead-integrated clean — seat covered every in-scope executable line, then correctly REFUSED to cross the scope boundary to reach the lead's ≥80% metric target (the target arithmetic was a lead brief defect: set from estimate, not measured region stmt counts). Central receipts re-run by the lead: 94 passed serially at draft; 138 passed at final HEAD after review fixes + counting the pre-existing help suite; module un-omitted at 97% (13 residual stmts). countersign: antigravity :: mcp-elicitation-suite :: sha256:1ae5953ff71b0732 (executor artifact at final HEAD fde412814 per the countersign-last rule) [P1][P11] |
| 2026-07-30 | antigravity | staged changes — mcp/server lane 4 diff (thread review-claude-lane4-elicitation-mcp-20260730-1806) | 1 sent / 0 omitted | 2 (findings) | both real — accepted and fixed in-branch (side_effect sat on log_submission only, leaving maybe_keyboard_hint's own swallow path untested — now seam-parametrized; positional await_args[0]/[2] indexing fails as IndexError under a kwargs switch — now arg-style-robust). Fifth antigravity finding, all five on TEST code. Lane 5 (help handlers) cancelled pre-launch the same hour: measuring WITH tests/unit/mcp/test_help_handlers.py showed the block already covered — file-subset coverage illusion, no seat spend [P1] |
| 2026-07-30 | codex | staged changes — D13/D14 delegation-rulings transcription (D11b contract-text lane; thread review-claude-d13-d14-delegation-rulings-20260730-1857) | 1 sent / 0 omitted | 1 (findings) | real — accepted and fixed in-branch (D13a guard transcribed as "criteria the chair has seen" — passive visibility, not approval; hardened to STATED-or-EXPLICITLY-APPROVED with launch blocked otherwise. The lead softening its own authority guard in transcription — the recurring D11b class, caught again by the different-model lane) [P3][P1] |
| 2026-07-31 | codex | branch vs merge-base e6ad569bc — outcome-first-fix narrow spec draft, PR #1805 (D11 spec-text lane; thread review-claude-q-outcome-first-attune-ux-review-0bf640-20260731-0136) | 3 sent / 0 omitted | 2 (findings) | both real — accepted and fixed in-branch (high: Phase 0's "traceable through existing interfaces" acceptance was verified only by a prose inventory doc — a claim, not a probe; added a dry-trace introspection check so every seam-map interface must import with its documented signature, live-execution proof staying Phase 2's acceptance by the ruling's design. medium: D3 listed false-confident-route rate in the Phase 2 metric set while deferring routing metrics to Phase 4 — it IS a routing metric; moved to Phase 4, compatibility regressions swapped in). The spec-text risk class earning its permanent-lane status again [P1] |
| 2026-07-31 | codex | branch vs merge-base e6ad569bc — outcome-first-fix Task 1 authoring + Phase 0 deliverables (D11 spec-text lane; thread review-claude-outcome-first-fix-task1-20260731-0203) | 10 sent / 0 omitted | 4 (findings) | all real — accepted and fixed in-branch (high: the dry-trace signature probe filtered out `args` AND carried an `expected == "args"` escape, making the cmd_workflow_run/cmd_diagnose pins vacuous — the VERIFIER itself wasn't verifying; now strict, only `self` filtered, no escape. high: inventory overclaimed "every row mechanically checked" while Phase 1/2-design and out-of-repo rows had no check — rows now split checked vs † design-commitment, with RoutingDecision and _auth_preflight promoted to checked entries. medium×2: requirements status header still said Task 0 awaited a chair go after it executed; compat constraint still cited the already-fixed exit-0 divergence as current). A verifier-checking-the-verifier catch — exactly the yield profile that keeps the spec-text lane permanent [P1] |

Board threads (live-fire check): `review-detached-20260729-0036`,
`review-detached-20260729-0037`,
`review-claude-test-11-0-0-release-08e6c3-20260729-0037`,
`review-claude-test-11-0-0-release-08e6c3-20260729-0038`,
`review-detached-20260729-0039`. All five posted (`board: posted`);
zero absent seats; all replies format-compliant (no
`format_noncompliant` rows).

## Carried findings — #1559 (run 1, codex, all carry-to-#1559)

For the #1559 lift review; anchors are the draft's
`src/attune/roundtable/skeptic.py`:

1. [high] :193 — detached worktree is created from committed HEAD,
   so staged closure changes are absent from what receipts validate.
2. [medium] :186 — caller-provided `scratch_root` is not created
   before `git worktree add`; nonexistent roots fail.
3. [medium] :267 — COUNTERSIGN accepted with no CITE despite the
   every-verdict-cites contract (uncited rubber stamp).
4. [medium] :267 — CITEs never validated against executed receipt
   labels/argv; an invented CITE records as valid.
5. [low] :151 — nonzero git exit in `staged_closure_text` silently
   returns empty closure ("nothing to review" masks failures).

## Evidence notes for T4 (OPEN-1 / OPEN-3 re-rule)

- **Seat behavior (OPEN-1):** codex produced findings on all three
  diffs (5, 1, 3); antigravity returned NO FINDINGS on both diffs it
  reviewed, including the 821-line skeptic diff where codex found
  five. Consistent with the appendix-triage divergence recorded on
  #1602 (2026-07-28). Supports keeping the fixed `codex` default.
- **Diff-size distribution (OPEN-3):** 3 files / 821 insertions
  (fit, 0 omitted); 1 file / 44 insertions (fit); 30 files / 3,679
  insertions (truncated: 23 sent / 7 omitted). The 60,000-char cap
  fit both code-review targets whole and degraded visibly (manifest
  named every omitted file) on the bulk docs target. No run needed a
  larger cap for its code content.
- **Finding quality:** run 1's findings 3–5 are substantive contract
  gaps a same-model review missed; run 3's single finding was
  pedantic (dismissed); run 5 correctly flagged a stale doc claim.
  Quality supports continuing advisory posture; no gate-upgrade
  claim from five runs.

## Carried findings — #1559 dispositions (lift, 2026-07-29)

Ruled at the #1559 lift (branch rebased onto main; fixes land in
the lift commit on the PR):

1. [high] worktree-from-HEAD — FIXED by surfacing, not re-design:
   receipts still validate committed state (isolation is the
   point), but `uncommitted_paths()` now records the blind spot
   and the brief + chair digest name every uncommitted path the
   receipts could not see (TAC-4 honesty over silent omission).
2. [medium] scratch_root not created — DISMISSED, false positive:
   `git worktree add` creates missing parents (probed live with a
   3-level-deep nonexistent root, exit 0), and
   `test_isolated_pass_and_fail_receipts` already passes a
   nonexistent root — it stays as the regression guard.
3. [medium] uncited COUNTERSIGN — FIXED: every verdict now
   requires a CITE; an uncited countersign parses as malformed
   (rubber-stamp decay is the ruling's named failure mode #1).
4. [medium] CITE never validated — FIXED: `parse_skeptic_verdict`
   accepts `valid_labels`; a CITE whose label names no executed
   receipt records as malformed, never as a valid verdict.
5. [low] silent git failure — FIXED: `staged_closure_text` and
   `uncommitted_paths` raise `SkepticError` on nonzero git exit;
   an empty result can only mean "no staged closure".

Copilot's PR review independently flagged findings 3 and 5 plus two
CLI gaps (unvalidated `spec_dir` pathspec; `--dry-run` crashing on a
bad declaration) — both CLI gaps fixed in the same lift commit.
Regression tests for all fixes in
`tests/unit/roundtable/test_skeptic.py` (48 tests, serial pass).
