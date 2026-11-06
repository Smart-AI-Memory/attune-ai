# Security audit SDK JSON integration

## Goal

Distinguish a completed SDK security audit from failed or missing output, and
make incomplete execution fail the existing security gate.

## Acceptance criteria

- Strict SDK JSON validates completion, terminal state and structured findings.
- Missing, partial, malformed and unauthenticated audits remain failures.
- Existing critical-only blocking, bypass and spending criteria remain intact.
- Real-source controls and installed-package evidence support the change.
- Exact-head hosted checks and a genuine authenticated audit remain separate.
- Completion review: complete for the offline source/package handoff; hosted
  qualification and a genuinely authenticated audit remain pending.

## Scope and assumptions

- Owned local branch: `codex/integrate-security-audit-json`.
- Parents prepared locally: main `25e2a3b3288f56763be06c4141aacfc72820f469`
  and existing PR #2553 head `03f82e323394fa4431647fb12d14a354da442fd9`.
- This integrates the existing two-commit failure-containment PR; no duplicate
  PR or other creator's remote update has occurred.
- The earlier `fix-security-scan-fail-closed.md` records the original containment
  phase. This handoff adds the reviewed SDK producer/consumer compatibility work.
- No dependency, credentials, permissions, provider budget or deployment change.

## Current state

The JSON-only exporter accepts one successful, completed own-prompt SDK result,
checks raw terminal fields before the shared collector discards them, validates
the structured schema and emits `security-audit/v1` with explicit completion.
Human mode and the shared collector retain their original behavior. HIGH findings
are retained and displayed without changing the existing critical-only blocker.
The analyzer bounds and encodes displayed model text while retaining full findings.

Different-model review: configured Claude Opus 5.5 reviewed the original proposal
and five successive narrow deltas. Final V6 SOURCE_ACCEPT covers full patch
`0b8520681558dba22d0444f2ac0af912f84e53b3512ce8db999e2d1f36dac0b2` and
V5-to-V6 delta `842ccd83040ff32d9896003f5071d0d8f1a86b028a9ddbb5aa818f6faa08fe32`.
Final V7 SOURCE_ACCEPT covers full patch
`46ecd7686f70e3992943fc7b7dbec8459c3050dcb102f25ebb45285734b008b5` and delta
`e7d35b347e30cf754f7d4921a67fcb05d7f8362cff687f80a169b7f44c8f1440`.
It adds only pinned formatter output and direct bindings to the original fixture
objects. All116 assertion source segments and the production AST are preserved.
The first hook failure is retained. This new copy was made from the full frozen
V7 candidate; the earlier V6 copy and Black-mutated publication copy remain intact.
V7 pinned hooks completed0 with no source changes. Its fresh first focused run
completed0:308 passed, zero failures/errors/skips; allfive complexity cases also
passed. Both runtime origin/hash preconditions and source/environment guards
were satisfied. These are offline controls, not a genuine SDK audit.

The author independently verified packet hashes and reconstructed V5 exactly
from V6's extracted validator blocks. Review is source evidence, not a live audit.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Strict JSON guards and existing workflow behavior | Eight existing control files through actual CLI/analyzer/check bodies with offline SDK/API stubs | 308 passed on V7; zero failures, errors or skips |
| Refactor satisfies existing ratchet | All five original complexity tests; unchanged threshold and allowlist | Five passed on V7; exporter15, findings14, suggestions9 |
| Tests execute the new module | Actual module origin and SHA before both runtime checks | New V6 path and `49715ac6ae0336b7e78ae91f6249ee4817c9dd9a0979573a90e8b90cfea3297f` verified |
| Human behavior preserved | Four original/candidate CLI processes on V5 | Byte-equal stdout/stderr/exit/schema; separate V6 human controls also passed |
| Tests expose old defects | Original producer, old terminal guard and old renderer substitutions | 24 retained cases: 16 expected failures and eight companion positives on V5 |
| Package build and installed boundary | New wheel with payload/origin checks and offline CLI controls | Wheel built; all895 RECORD entries,797 Python/source joins and894 installed payloads checked. Fresh80-distribution noneditable install and pip check passed. All14 finite installed producer cases passed; actual exits, seven critical origins, findings and refusals independently checked |
| Full source/coverage/platform qualification | Normal exact-head hosted CI, including unchanged 94% coverage gate | Pending; no local full pass claimed |
| Genuine authenticated audit | Actual supported SDK output from an approved authenticated route | Not run; no live SDK/model calls |

The installed check uses the actual console-declared main function under an
isolated startup and the unchanged finite offline SDK runner. All14 cases passed
in62.369 seconds. Root read each raw process, stdout, counters and module-origin
record; all5805 installed entries including bytecode and6863 source bindings
stayed unchanged. There were zero observed Python network/process attempts.
Native capability discovery, enabled TaskBudget, ordinary console startup,
platform qualification and a genuine authenticated audit remain unqualified.

Both first installed attempts remain failed. The external harness initially
misattributed a documented attune-forms module alias and blocked a capability
probe/public OS metadata. A cache workaround did not cover the remaining read.
The separate same-Astra-reviewed final bootstrap validates the exact dependency
alias and selects the already-observed unsupported capability cache for this
child. It admits one literal canonical non-symlink public OS metadata file
readonly, checks its bytes before/after, and keeps all other file/process/network
refusals. The wheel, environment, product source and original14 predicates were
not changed. Python audit hooks are bounded controls, not an OS sandbox.

The first local full run was interrupted protectively after a legacy Redis ping
failure and the original complexity failure. Collection-time Redis probes precede
per-test scrubbing, and a legacy fixture cleans broad key prefixes. No claim about
earlier fixture effects is supported. No post-stop Redis inspection occurred.
The first log, interruption and source/environment readbacks are retained. No
local full rerun, new skip, sandbox experiment or assertion relaxation follows.
Use hosted PR CI to isolate full execution from the developer's local service.

The configured workflow remains keyless. JSON compatibility cannot authenticate
a runner. An incomplete scan must fail even when this correctly blocks rollout;
do not add credentials, waive the gate or describe empty output as a clean audit.
Website dependency PR #2568 is separate; its successful checks do not qualify this
SDK source. The separately triaged Python dependency alerts remain outside scope.

## Next action

The local reviewed integration is ready for signed handoff. With Patrick's
explicit approval, update existing PR #2553's branch by normal fast-forward and
record the prepared review/evidence body before that push. No duplicate PR,
force push, merge or deployment is approved. Inspect actual exact-head hosted
results and retain authentication failures separately from source regressions.
