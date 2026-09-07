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
