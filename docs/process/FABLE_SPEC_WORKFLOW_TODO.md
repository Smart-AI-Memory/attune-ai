# TODO — Reliable Fable Spec Authoring Workflow

**Status:** done (2026-07-22 — this line rides the PR that makes it
true: item 1 merged as #1590 [benchmark + ratified decision matrix];
items 2–5 are this PR, #1591 [`spec_runner.py` + `spec_workflow.py`];
dogfood receipt green end-to-end, posted on #1591)
**Priority:** high — collaboration workflow failure
**Scope:** spec-authoring orchestration, not the cross-provider Redis-memory implementation
**Created:** 2026-07-22

## Problem

The first Fable 5 spec call remained silent for more than 150 seconds and
had to be interrupted. A context-free Fable probe returned in about seven
seconds, proving the model/auth path was healthy. A bounded retry eventually
completed, but only after another long interval with no progress signal.

The surrounding workflow compounded the failure:

- External-data authorization was requested after drafting had already begun,
  rather than being front-loaded once with the scope.
- Native elicitation failed without a useful recovery surface.
- Prompt packets temporarily appeared as workspace edits, confusing the
  promotion/review surface.
- The lifecycle gate failed once because its ledger path under `~/.attune`
  was not writable from the sandbox, then had to be rerun host-side.
- The user experienced multiple stop/retry cycles before receiving the
  requested artifact.

## Outcome

Fable-authored specs run through a bounded, observable workflow that either
produces the artifact or fails quickly with an actionable reason. External
authorization, scoping, scratch storage, generation, validation, and lifecycle
gates form one coherent path rather than a sequence of reactive retries.

## Work

### 1. Measure before setting the generation budget

- Benchmark Fable 5 with representative one-file, four-file, and five-file
  spec packets.
- Record time to first event, total duration, input/output size, and failure
  mode using streaming JSON output where available.
- Commit the decision matrix before selecting the default whole-spec versus
  per-document strategy. Patrick ratifies the latency budget from measured
  data; do not invent an arbitrary acceptable threshold.

### 2. Add a bounded Fable drafting runner

- Stream progress instead of waiting for one final stdout block.
- Enforce separate time-to-first-event and total-run limits.
- On a first-event timeout, stop once and switch to the preselected
  per-document strategy; never repeat the same silent whole-spec call.
- Capture the exact provider/model/auth/CLI failure without exposing secrets.
- Validate required file markers and output-size limits before materializing.

### 3. Front-load the workflow contract

- Present one informed external-data authorization before any external model
  invocation; treat the approval as session-durable for the same packet class
  when the host policy permits.
- Gather only genuinely missing scope. If rich elicitation is unavailable,
  fall back immediately to one plain question or explicit documented defaults.
- Select whole-spec versus split-document generation before launch using the
  measured decision matrix.

### 4. Keep scratch artifacts out of the review surface

- Store prompt/reply packets in an isolated temporary directory, not the
  repository working tree.
- Guarantee cleanup on success, timeout, rejection, and interruption.
- Assert `git status --short` shows only intended spec artifacts before review.

### 5. Make gates sandbox-aware

- Run lifecycle gates with a writable, isolated `ATTUNE_HOME`, or through the
  trusted host boundary when the real ledger receipt is required.
- Detect an unwritable ledger path before running the gate and report the
  selected execution boundary.
- Do not spend a failed attempt rediscovering the same sandbox restriction.

## Acceptance criteria

- A benchmark report and pre-committed routing matrix select whole-spec or
  split-document generation from evidence.
- Every Fable run emits an observable first event or terminates at the bounded
  first-event gate with one actionable error.
- The same failed generation strategy is never attempted twice in one run.
- One informed authorization covers the scoped external drafting sequence when
  platform policy allows it; unavoidable platform re-prompts are surfaced
  before generation begins.
- No prompt/reply scratch file appears in the repository review surface.
- Native elicitation failure takes one deterministic fallback path.
- Lifecycle gates produce their real receipts without a preliminary
  permission failure.
- A dogfood receipt creates a five-file draft spec, validates its XML plan,
  runs lifecycle gates, and leaves only the five intended artifacts in Git.

## Done when

Patrick can request “use Fable 5 to write the spec” and receive either a
validated review-ready draft or one early, legible failure—without silent
multi-minute waits, repeated strategy attempts, or temporary-file confusion.
