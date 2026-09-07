# Host-native interaction trials — 2026-09-07

These are bounded observations, not full host parity or statistical latency
claims. PR #2450 merged at 6934b177ece5e0eb8b80dee3ea0c4a11167c7b06.

## Controlled Codex Attune-route trial

The installed preview wheel hash matched its provenance record; 782 installed
Python/JSON files matched the wheel. The provenance record named PR head
2d0e3ad7327a9e83def5970bda958c74b2e601fd. Config and process inspection showed
the preview environment, with MCP 1.29.1 and attune-forms 0.14.0. This is
installation evidence, not an assertion that a process exposed its own digest.

The actual connected `elicitation_route_form` returned accepted
`server_observed_completion`, response ID
`resp-20260907-113835-50d1948e`, with one renderer and one presentation.
Patrick confirmed keyboard-only form completion; the mouse stopped recording.
The 55.28-second recording at 11:38:08 AM shows choice focus, retained text
through required-choice validation, and subsequent completion. Approximate
request-to-visible time was 6.5 seconds from half-second sampling, including
assistant dispatch. It is one controlled trial, not a distribution.

## Fresh Codex discovery trial

Task `01a07c89-a1c9-7590-8736-92be51d58d72`, titled
"Plan flower shop website", began with an ordinary planning request.
Its complete returned history showed the planning skill read, help lookup,
and prompt-refinement status, then three plain-text scoping questions.
There was no `elicitation_route_form` call. The 119.68-second recording at
11:42:59 AM corroborates the text interaction. This demonstrates a discovery
failure in that run, not universal failure or an unavailable tool.

Earlier built-in Codex question trials preserved submitted answers in task
history, but one user reported premature disappearance. Ending the assistant
turn was a plausible contributor, not a controlled root-cause finding.
The new guidance keeps needed asynchronous questions pending, handles partial
answers and corrections, and treats cancellation explicitly. Source review
and projection tests cannot certify the host's lifecycle behavior.

## Antigravity native-control trial

Roundtable receipt #15: desktop conversation
`c9d2a9ba-3e15-4f9d-a808-28f1359459bc` displayed built-in two-question controls
and echoed submitted choices correctly. During attempted free-text entry the
computer-use tool reported that the user changed the app; free-text correction
and full keyboard operation were not certified. This was explicitly prompted,
not an automatic-discovery trial. Visible model was Gemini 3.8 Flash High;
CLI 1.1.27 was inspected, not asserted as the desktop version.

Receipt #16: Patrick's 72.08-second recording at 12:08:23 PM showed native
single-choice and multi-select questions, mouse interaction, and completion.
Patrick reported problems with keyboard operations. No key-event overlay
identified the exact failing keys, and hover alone does not prove lost input.
Keyboard acceptance did not pass; successful submission did not override that
finding. Enhanced prompts remain the default; native forms are experimental.

## Remaining Codex acceptance

### Bakery recording: old-guidance control, not revised-branch acceptance

The 52.675-second recording at 12:29:12 PM shows a native question card
following an ordinary bakery-planning request. Task
`01a07cb3-f85f-7281-a4da-95eea7090130` ("Plan neighborhood bakery website")
used a separate checkout at 4a8bd9c0c. Read-only inspection found the old
"Codex: use the verified server route" heading in its elicit mirror; the
revised host-default text was absent. The returned history showed no skill
read and no submitted question reply. The assistant ended with a plan and
repeated the question in prose. This is evidence of native display under the
old setup, not acceptance of this branch or proof of answer loss. The lead
had not verified the receiving checkout before the user recorded the trial.
Do not request another recording until the receiving task's actual guidance
matches this branch.

On a fresh task loading the revised guidance: observe suitable built-in question
selection, keyboard entry/submission, partial replies and corrections without
duplicate intake, and explicit cancellation without automatic re-presentation.
Compare accepted answers with the continuation. Required-field checks are agent
validation against the question, not an Attune server receipt. Respect the host
tool's current question limits and the user's conversation preference.

Record tool returns separately from visible UI and user attestation. Repeated
timing, broad accessibility, and universal automatic discovery remain unproven.
Recordings and raw local receipts remain on the operator's machine; they are
not published as part of this repository.

## Claude host inspection — 2026-09-07

Recorded by the Claude lead from the desktop app's Code tab (Claude Code
2.1.260) in an autonomous session with no user present, so nothing below
is a rendering or keyboard observation.

Verified by inspection of the exposed tool definition: `AskUserQuestion`
accepts 1–4 questions per call, each with 2–4 options carrying a label
and description (optional preview), a `multiSelect` flag, a `header` of
at most 12 characters, and optional `metadata.source`; the host always
adds an "Other" free-text entry; the call is synchronous and its result
carries the answers keyed by question text. `show_widget`,
`elicitation_ask`, `elicitation_render_widget`, and
`elicitation_route_form` were also exposed; exposure is not a rendering
claim. The multi-question format guard that the elicit skill mentions is
operator-local infrastructure under `~/.claude/hooks/`, not a shipped
plugin hook.

Pending, not observed today: visible rendering of a one-question and a
multi-question call on the desktop app and on a terminal; keyboard-only
completion; whether a partially answered call can be submitted; what the
tool result reports when the user dismisses the card; and whether the
revised guidance is discovered on a fresh ordinary planning request.
Also pending after the D16 ruling: the Attune widget on Fable 5.1 for
the constructs the native control cannot express (ranking, triage over
four items, number, date, textarea) — render, submit, and keyboard
operation. When these are run, record tool returns separately from
visible UI and user attestation, as the Codex section above does.

## Claude desktop trial prep — 2026-09-07, second session

Recorded by the Claude lead from the desktop app's Code tab in an
autonomous session. Patrick was not at the keyboard, so nothing below is a
paint or keyboard observation. Every claim names its basis.

### Trial (a): the receiving plugin is stale — refresh before recording

- Desktop `plugin:attune-ai` resolves through
  `~/.claude/plugins/installed_plugins.json` to
  `~/.claude/plugins/cache/attune-ai/attune-ai/16.2.1`, git SHA f51a2dd6
  (#2422, merged 2026-09-05), last updated 2026-09-05T03:23Z. Verified by
  reading that file and by `git merge-base --is-ancestor`: the cache does
  not contain 7bdf4112e (#2459).
- Its `skills/elicit/SKILL.md` has no "Claude: native questions first"
  heading. Its `skills/planning/SKILL.md` still says to gather Subject and
  Scope "as one form via the elicit skill, preferring the rich widget
  surface" — the D21 default that #2459 replaced. A fresh flower-shop
  request on this desktop would therefore exercise the OLD guidance no
  matter which checkout the session opens in, because these two skills are
  plugin-sourced. The repository's own `.claude/skills/plan` and `attune`
  skills call `AskUserQuestion` but are not the skills #2459 changed. This
  session's own `attune-ai:elicit` listing came from the same stale cache;
  the lead followed the worktree's SKILL.md text instead.
- The marketplace clone at `~/.claude/plugins/marketplaces/attune-ai` is
  also at f51a2dd6. The plugin version on origin/main is still 16.2.1, so
  the cache path will not change on refresh.
- Precondition, NOT run this session because it changes the operator's
  global plugin install for every session on the machine:

```bash
claude plugin marketplace update attune-ai
claude plugin update attune-ai@attune-ai
```

Then restart the desktop app (the CLI states a restart is required), then
take the receipt:

```bash
grep -n "native questions first" ~/.claude/plugins/cache/attune-ai/attune-ai/16.2.1/skills/elicit/SKILL.md
```

A match on that path is the go signal for the recording. No match means do
not record — the bakery lesson above.

- Observation protocol once refreshed: a fresh desktop session, the
  ordinary request "Help me plan a website for a flower shop", no mention
  of forms. Record per item: which tool was called (`AskUserQuestion`,
  `elicitation_render_widget`, or prose only); card and question counts;
  keyboard-only completion (Tab, arrows, Space, Enter); whether a partial
  answer set can be submitted and what the tool result then carries; what
  the tool result carries on dismissal (Escape); and whether the
  continuation uses the accepted answers. Tool returns in one column,
  visible UI in a second, Patrick's attestation in a third.

### Trial (b): Fable 5.1 widget — rendered; submit and keyboard pending

Setup: one form built in this session with the five constructs the native
control cannot express. Ranking of the four starter threads with the
starter's order as the suggestion; triage over six items (the pending
observations above; dispositions observe today / defer / drop; discovery
suggested defer because of the stale cache); number (0–120 minutes); date;
textarea for the attestation (2000 characters). The content is real: the
answers are this thread's rulings.

Tool returns, verified from the returns and not from the screen:

| Step | Return |
| --- | --- |
| `elicitation_render_widget` | success; five field ids; 28,137 HTML bytes |
| Serving process | project `.mcp.json` server, pid 26830, this worktree's venv; attune 16.2.1 imported from this worktree's `src` at f10baa3e1; attune-forms 0.14.0 |
| Telemetry 19:06:19Z | `form_build` cf43dd900008; `form_surface` chose widget, reason `no_portable_control`; `form_rendered` instance `10404e263dd242a2b3e4e9b63466fcf8` |
| `show_widget` | "Content rendered and shown to the user" — a host tool claim, not a paint observation |

HTML inspection, from the returned string: number is
`<input type="number" min="0" max="120" step="any">`; date is
`<input type="date">`; the textarea has `rows="3" maxlength="2000"`; the
ranking renders four ranked rows with move-up, move-down and remove
buttons plus an empty unranked pool, headed "Ranked 4/4 proposed"; the
triage renders six radiogroups. Every control is a native element with a
`:focus-visible` outline, so Tab reach is plausible and unobserved.

Finding for the forms repo, stated as an observation and not a bug claim:
`suggested` on the ranking pre-fills the ranked list, and `suggested` on
the triage pre-checks one radio per row, so an untouched Submit posts the
proposals as the answer. The schema text calls a suggestion "a visible
proposal, never the answer". Whether the renderer should leave the answer
empty until the user acts is a forms-repo question (thread 4 territory).

Pending, needs Patrick at the keyboard: paint of all five controls;
keyboard-only operation of the ranking buttons, the radios, the number
spinner, the date picker and the textarea; Submit; the
`__elicitation_response__` post-back arriving in this session;
`elicitation_collect_response` with the instance id; the `form_submitted`
telemetry row (the falsifier from the Codex receipt: the submit carries
the render's instance id); and the attestation text itself. Until those
land, the D16 caveat on these constructs stands unchanged.

### Other state at write time

- #2461 open; its Tests workflow was still in progress (Windows lane and
  coverage pending, nothing failed).
- Codex Task 1B increment 2 exists as branch
  `codex/host-surface-parity-task1b-increment2` at 1efa08406 in worktree
  9c6c; no PR yet.
