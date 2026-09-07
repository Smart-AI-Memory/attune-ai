# Live host conversation trials

Follow-up: https://github.com/Smart-AI-Memory/attune-ai/issues/2455

## Protocol frozen before collection

The [case matrix](live-trials/2026-09-07/cases.json) contains eleven scripted user
turns per host, including fresh sessions and continuing replies. Its SHA-256 and
the tested source hashes are recorded in the
[manifest](live-trials/2026-09-07/manifest.json). The tested source is merged main
at `705004a8a`; the policy and hook came from PR #2454. These are real model/CLI
conversations driven by a scripted operator, not human usability trials or a
comparison of task outcomes.

The assistant responses are judged against each case's prewritten expectations.
Report conversation behavior separately from policy delivery and preference
state. An answer that happens to look polished cannot establish that the host
checked the library's policy. Failure, unavailable surfaces, and harness setup
errors remain in the evidence record; they are not silently retried into passes.

## Host setup and evidence boundaries

- Claude Code 2.1.260, existing Max subscription, API credential variables
  removed from the child. A session-only hook registration invokes the actual
  merged `plugin/hooks/prompt_refinement.py`, with its existing SDK guard. This
  is a host-loaded hook trial, not a claim that the installed cached plugin was
  upgraded or that every hook in the plugin was exercised.
- Codex CLI 0.153.4 from the existing AF-3 runtime, existing ChatGPT login,
  GPT-6 Astra, medium reasoning, read-only workspace. The PATH CLI 0.144.6
  rejected the configured model before producing an answer; that attempt is
  retained separately.
- The real attune-ai MCP server runs from the merged `src` directory using the
  existing project Python. Each host's server receives a separate temporary
  HOME/USERPROFILE and Redis mock mode. No normal preference is changed.
- Host prompts do not tell the model to call the refinement tool. MCP
  initialization delivers the production instructions. A transparent stdio
  capture records requests and responses without rewriting them. The first
  clear cases preceded transport instrumentation; do not claim transport
  observations for those cases.
- The child host retains normal account authentication. Codex still loaded
  personal instructions despite `--ignore-user-config` and
  `project_doc_max_bytes=0`; it read the global memory index during the vague
  task. Personal polishing instructions are a confound and are not attributed
  to the library. Private tool outputs remain in local raw logs, not published
  transcript excerpts.
- Codex's first disable attempt was blocked by the headless approval policy.
  The successor launch explicitly permits only the isolated preference tool
  via `mcp_servers.attune_trial.tools.prompt_refinement.approval_mode="approve"`.
  This follows the documented [per-tool configuration](https://developers.openai.com/codex/config-reference/).
  Other tool permissions and the read-only sandbox remain in force. This is
  test configuration, not a proposed change to normal user approval policy.
- Desktop widget presentation, keyboard focus, screen reader behavior, and
  actual human preference are not established by headless transcripts. The
  active desktop MCP inventory lacked `prompt_refinement` at collection start;
  source/transport trials cannot establish that desktop installation is updated.


## Completed collection and refinements

The collection contains **41 launch attempts and 40 assistant-response records**:
22 baseline turns (11 per host), two preserved Codex setup attempts, two rejected
Codex metadata experiments, three Claude policy follow-ups, one narrower Claude
polish-only follow-up, and eleven Codex native-hook turns. These are different
conditions and repeated scenarios; they are not 41 independent experimental
units. No aggregate success rate or causal improvement estimate is appropriate.

| Condition | Observed receipt | Limitation / disposition |
| --- | --- | --- |
| Codex MCP-only baseline | Initialization delivered policy on instrumented turns; explicit enable/disable worked after isolated tool approval was configured | Ordinary turns did not call status. Output alone cannot establish policy observation, restart opt-out, or one-turn skip adherence |
| Claude hook baseline | All eleven turns received hook state; disabled restart, skip, re-enable, and quoted-text protection were observed | Several responses were verbose; the polish-only answer invented approval timing. Headline length violations were general instruction-following errors |
| Stronger Codex tool description | Neither of two follow-ups called status | Reverted metadata change; planned third follow-up was not run after repeated failure |
| Shared policy follow-ups | Claude asked three initial question groups and returned only an editable prompt in the polish-only follow-up | Initial candidate still invented approval timing; narrowed wording preserves unspecified approval wording and permits labeled proposed scope |
| Narrower Claude policy | Polish-only output kept “Approver: Ryan” without an invented pre-build gate | Known lineup status was awkwardly placed under assumptions; this is not perfect quality or outcome evidence |
| Codex native hook, eleven turns | Every turn had a successful UserPromptSubmit receipt. Restart observed disabled state; skip was inactive without saving; next turn was active; quoted text did not mutate preferences | Headless lifecycle receipt only; does not validate interactive hook trust setup or desktop UI |

Codex native-hook conversation retained the corrected October 17 date, budget,
launch date, and approver. It left approval timing unresolved and produced only
an editable prompt for the polish-only request. Both hosts used conversational
questions in the keyboard-oriented cases; no form-selection or rendering claim
is made. Models can still ignore delivered guidance or make factual mistakes.

The retained production change is confined to shared guidance: start terse
keyboard conversations with at most three material questions, respect requested
output format, avoid invented budget exclusions and approval gates, and stop
at the editable prompt when requested. Proposed scope remains allowed when
labeled. The existing hook and MCP adapter are unchanged.

A final wording compression preserves the same rules while satisfying the
existing 2,200-character hook-context gate. That exact compressed text was
validated locally, not re-collected through the live models. Collected and final
source hashes are separate in the supplemental manifest.

## Native Codex hook setup boundary

Codex CLI 0.153.4 executed the same production hook through its native
UserPromptSubmit lifecycle. This uses the documented
[Codex hook output contract](https://learn.chatgpt.com/docs/hooks), including
`hookSpecificOutput.additionalContext`. The temporary launch explicitly
registered only the reviewed trial hook and used the documented
`--dangerously-bypass-hook-trust` automation option. It did **not** disable the
workspace sandbox or change normal installed configuration. Consequently, these
runs establish hook execution after trust was supplied, not the normal human
review/trust flow. Normal setup must review and trust the configured hook through
`/hooks`; installing or listing a plugin is not that receipt.

The native trial ran cases in this order: vague, terse, correction, clear,
disable, off_restart, enable, skip, after_skip, polish_only, quoted. The original
fresh/continuation boundaries were retained. Claude reported model
`claude-opus-5[1m]` in initialization; Codex used GPT-6 Astra at medium reasoning.
Subscription authentication was retained, with API credential variables removed;
Claude's reported list-price accounting is not evidence of a billed API charge.

## Durable evidence, privacy, and reproducibility

- [Observations](live-trials/2026-09-07/observations.json) preserve synthetic
  responses and state observations, including unsuccessful attempts.
- [Event ledger](live-trials/2026-09-07/events.json) preserves ordered per-stream
  hook/MCP control events, tool arguments and state results, and raw-source
  hashes. Missing timestamps are null; cross-stream ordering is not inferred.
- [Refinement manifest](live-trials/2026-09-07/refinement-manifest.json) records
  candidate hashes and the rejected metadata experiment.
- [Supplemental manifest](live-trials/2026-09-07/supplemental-manifest.json)
  records final hashes and native launch recipes retrospectively. It is not a
  pre-registered protocol. Frozen case inputs remain unchanged.

Private command outputs, reasoning, account identifiers, and private transcript
paths are excluded from the durable ledger. Raw originals remain locally under
`/private/tmp/prompt-refinement-live-trials`: directory modes 0700, file modes
0600, and new captures use umask 0077. Initial permissive modes were corrected
following review. Retain private originals only through review of this phase's
PR, then delete that trial directory after the review is resolved. The sanitized
records remain tracked. Hashes bind retained originals but do not independently
prove capture completeness or transparency after originals are removed.

Only explicitly isolated trial preference files were written. Their final state
is recorded before cleanup; no normal user setting or cached plugin was updated.

## Remaining acceptance work

Issue #2455 remains open for a fresh installed desktop session: verify normal
hook trust/configuration, ordinary requests, keyboard focus and form presentation
where selected, opt-out across restart, and fallback when the form surface is
unavailable. A human must then assess interruption, effort, and usefulness.
Separate controlled outcome work is still required to establish whether forms
or refinement improve completed tasks.

## Review and local checks

A real Codex advisory review covered eight initial files and found three
issues: raw capture permissions/retention, insufficient durable control evidence,
and an overly broad scope restriction. All three were accepted and corrected as
recorded above. The reviewer inspected private file metadata, not private raw
contents. A follow-up reviewed all twelve changed files and found no remaining actionable
issue; it independently ran 86 tests. Reviewer self-description did not establish
a different deployment identity, so a separate explicitly configured GPT-5.6 Sol
review (`/root/host_trial_final_review`) covered the same twelve-file scope for
the cross-model requirement. It verified counts, hashes, transitions, and claim
boundaries. Its one documentation finding requested reviewer-identity clarity;
separate ledger rows now distinguish the earlier identity-unverified lane from
this explicitly configured lane. No code or evidence defect was reported.

Central checks: 130 tests passed across prompt-refinement, MCP schemas, SDK hook
guards, and generated-help drift. Evidence validation checked 41 records,
eleven hook states for each hook host, opt-out/skip/resume transitions, frozen
case hashes, and raw capture permissions. Isolated preference files were removed
after their final state was recorded in the supplemental manifest.

Additional central ledger and brand gates: 12 passed. Pinned pre-commit checks
passed. The strict documentation build could not run because the existing
project interpreter has no MkDocs installation; no docs-build pass is claimed.
