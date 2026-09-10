# Session-hook reliability review

Original review: 2026-09-09 against commit `c15c92103d9ff00c984f7429cf22b47694a1262e`.
Scope: `help_freshness_nudge.py`, `starter_prompt_nudge.py`, and
`starter_reconciler.py`, their tests, and their SessionStart registrations.
The original review below made no production changes. Patrick subsequently
authorized local remediation, recorded in the follow-up section at the end.

The hooks remain useful safeguards. The current design has explicit branch
handoff precedence, shared artifact selection, labeled legacy fallback, and
unverified results for many failed checks. A fresh run passed all 181 focused
tests. Existing tests exercise real script imports, local Git discovery and
slow subprocesses. The previous coverage run on this same code measured 98.01%
across the three hooks.

**Recommendation: retain all three, but do not ship this branch yet.** One
repository gate fails, and controlled probes found incorrect-repository
verdicts, a process deadline overrun, and silent monitoring gaps. High coverage
does not establish reliability at those boundaries. These are reproducible
failure modes, not claims that all of them have occurred in production.

## Findings in priority order

### R1 — High: PR queries are not bound to the verified repository

`starter_reconciler.py:369–374` runs `gh pr view <number>` without `--repo`.
`_run()` inherits the environment. The installed CLI's `gh help environment`
documents that `GH_REPO` chooses the repository for such commands.

**Receipt:** a starter stamped `repo: local/project` and containing
`local/project#49` passed provenance and extraction. A controlled `gh`
subprocess honoring `GH_REPO=foreign/project` received arguments without a
repository selector and returned the foreign PR's simulated `MERGED` state.
The hook printed `PRs: #49 MERGED` under the local starter. This establishes
the command-wiring defect; no real remote PR state was queried.

**Improve:** carry verified repository identity through to the actual query,
including host where applicable. Pass an explicit repository selector; when
identity cannot be established, report unverified. Test with an ambient
`GH_REPO` that conflicts with provenance and a control fixture where local and
foreign states differ. Assert the selected repository, not just the state.

### R2 — High: the deadline bounds reconciliation, not process termination

`starter_reconciler.py:476–490` reads the whole PyPI response using urllib's
socket timeout. At `579–597`, executor waiting is bounded, but
`shutdown(wait=False)` leaves running worker threads alive. A responder that
keeps sending bytes can keep the HTTP read active beyond the total budget;
the Python process then waits for its worker during shutdown.

**Receipt:** a real loopback HTTP server streamed a small JSON response one byte
every 0.55 seconds. Only the destination URL was redirected to the fixture;
urllib response reading and the executor were real. Reconciliation returned
after **6.005 seconds**, but the interpreter exited after **15.107 seconds**.
The registered hook timeout is **12 seconds**. The existing slow-git test does
not cover this slow-response-body case. No external HTTP service was contacted.

**Improve:** enforce an absolute deadline at a boundary that can actually be
terminated, such as a bounded worker process for network work. Preserve and
flush partial results, mark unfinished work unverified, and test interpreter
exit time as well as function return time. A smaller socket idle timeout alone
does not solve a continuously progressing response.

### R3 — Medium: foreign spec paths become local spec verdicts

`starter_reconciler.py:452–470` extracts a slug from any matching
`docs/specs/<slug>` substring and reconstructs the path under the current repo.
It discards the prefix that can identify another repository.

**Receipt:** an actual temporary
`../foreign/docs/specs/shared-feature/tasks.md` contained `Status: active`.
A different local spec with the same slug contained `Status: shipped`.
The hook returned `terminal:shipped` and generated a CLOSED-spec warning for
the foreign reference, using real filesystem reads.

**Improve:** accept explicitly repo-relative references or resolve the named
path against its context and verify containment. Leave foreign or ambiguous
paths unverified. A regression should put opposite states in the two real
files so using the wrong file cannot pass.

### R4 — Medium: failed checks can look identical to having nothing to report

Two independently reproduced cases remain:

- At `starter_reconciler.py:487–490`, PyPI failure becomes `None`; at
  `650–657`, that can suppress the entire banner. A correctly stamped,
  version-only starter attempted PyPI once under a controlled `URLError`, then
  returned `False` with **empty stdout**. It did not report unverified.
- At `help_freshness_nudge.py:111`, staleness scanning occurs before structural
  findings are printed. The catch at `142–143` silently exits. An unchanged
  script copy executed through its real entry point received an unsupported
  absolute glob and a separately missing feature. It returned **exit 0, empty
  stdout, empty stderr**, erasing the already-computable missing-feature notice.

**Improve:** distinguish not applicable, completed, failed, and skipped checks.
Preserve completed findings when another check fails. Emit one concise
degradation notice while keeping SessionStart nonblocking. Add entry-point
tests with mixed success and failure; a test that merely reconstructs a catch
block does not establish the behavior of the installed script.

### R5 — Medium: help freshness does not cover the current authored sources

`help_freshness_nudge.py:69–85` scans only manifest `files` patterns. Reading the
actual YAML with both the hook and a YAML parser found **31 features, all
manual, and zero source patterns**. The manifest deliberately omits these
globs for authored projections. This hook's freshness calculation consequently
has no sources in this repository; directory completeness still works.

**Receipt:** a fixture used the current manual-feature convention, complete
but old help templates, and a newer canonical `content/features` master.
The hook printed nothing. This establishes a monitoring gap, not that the
actual committed templates are stale. A separate fixture also showed that
a valid quoted YAML glob stays quoted in the regex parser and misses its file.

**Improve:** use the existing authored-projection drift mechanism or its source
metadata. `attune.authoring.projector.check_projection_drift` is already used
by `tests/unit/authoring/test_projection_drift.py`, including mutation tests.
Do not restore generation globs that the manifest intentionally removed.
Until freshness is checked, describe this hook as a completeness check or
make the unavailable freshness coverage explicit. If legacy YAML parsing
remains, use a schema-aware parser or reject unsupported forms visibly.

### R6 — Medium: handoff scope labels overstate provenance

`starter_prompt_nudge.py:116–139` describes the selected handoff as tracked,
but checks file existence and size, not Git tracking or resolved containment.

**Receipt:** a real temporary Git repository contained an untracked,
branch-named symlink to another project's file. `find_handoff()` selected it
as `handoff:branch`; `git ls-files` returned no tracked entry and the resolved
path was outside the repository.

**Improve:** reject or visibly distinguish outside-repository targets. Decide
explicitly whether untracked local drafts are usable; if they are, label them
as drafts rather than granting tracked provenance. Test both ordinary files
and symlinks. Also test equal mtimes after a fresh checkout before treating
the newest-mtime fallback as reliable recency evidence.

### G1 — Release blocker: the last change fails the complexity gate

Preflight now fails
`tests/unit/quality/test_complexity_ratchet.py::test_no_new_d_or_worse_blocks`.
Radon measured `starter_reconciler.format_banner` at **17 before the last
commit and 21 now**, crossing the gate's D-grade threshold. Preflight results
were **86 passed, 1 failed**; the focused suite still passed all 181 tests.

This is a verified repository-policy failure, not an observed runtime crash.
The last implementation ran preflight before editing, but did not rerun this
broader gate after editing; the focused tests and commit hooks did not catch it.

**Improve:** simplify the formatter below the existing threshold and rerun
post-edit preflight. Do not widen the allowlist to accommodate this change.
This is the smallest immediate repair; R1 and R2 are the most urgent runtime
reliability improvements.

## Verification and limits

All imports used for probes were checked against this worktree's actual files.
The lead reran both delegated probe scripts centrally. Evidence types were
real filesystem reads, real local subprocesses, controlled failure injection,
installed CLI help, and one real loopback HTTP response. Git remained at the
reviewed commit during all probes.

Reproducers are saved as local review artifacts:

- [Repository/spec/offline probes](/Users/patrickroebuck/.codex/visualizations/2026/09/09/01a08772-e7fb-7900-974d-4fcb9e59f737/probe_reconciler_correctness.py)
- [Help and handoff probes](/Users/patrickroebuck/.codex/visualizations/2026/09/09/01a08772-e7fb-7900-974d-4fcb9e59f737/probe_help_handoff.py)
- [HTTP deadline probe](/Users/patrickroebuck/.codex/visualizations/2026/09/09/01a08772-e7fb-7900-974d-4fcb9e59f737/probe_hook_deadline.py)

The first two run directly with Python. The deadline probe takes the repo
root as its sole argument and requires loopback socket access. Its test
endpoint substitutes for PyPI; the result is not a measurement of PyPI.

Windows, Linux, the actual Claude SessionStart harness, and live GitHub/PyPI
services were not exercised in this review. No production occurrence rates
or cross-platform guarantees are inferred from these tests.

## Original recommended next work

Keep the approved three-hook structure. Clear G1, then address R1 and R2 with
failure-sensitive boundary tests. Follow with explicit failed/skipped states
(R4), context-preserving spec references (R3), and truthful help/handoff
provenance (R5/R6). These changes improve correctness and detectability without
adding another gate or a broader orchestration layer.

## Local remediation — 2026-09-09

**All three hooks are retained. The reported defects were corrected and
verified locally before publication.** This section supersedes the
original implementation status above while preserving the failure evidence.
Corrections follow `c15c92103`, on `codex/session-hook-targeted-fixes`.
The local work was initially held from shipping; Patrick's subsequent "go"
authorized committing, opening the PR, and checking required CI. Inspect the
PR for current remote checks; the receipts below describe the local review.

| Finding | Correction | Failure-sensitive receipt |
| --- | --- | --- |
| R1 — repository identity | `gh pr view` receives an explicit host/owner/repository selector. New stamps include `repo_host`; host changes and legacy hostless stamps cannot silently receive repository verdicts. The verified target reaches the query without rediscovery. | Opposite local/foreign PR states with conflicting GH_REPO/GH_HOST; real Git stamp under host A, change origin to host B with the same owner/name, assert no PR query. |
| R2 — process deadline | PyPI runs in a subprocess killed and reaped by the remaining deadline. Executor workers finish before the shared deadline is reset. | Owned loopback HTTP fixture, real urllib response parsing and worker entrypoint: successful response prints latest; slow body prints unverified and the whole process exits in 4.338s. Registered timeout remains 12s. |
| R3 — spec paths | Preserve path context, reject foreign paths and outside symlinks, isolate resolution/read failures per spec. | Real opposite-state local/foreign files, symlinked directory/phase files, and a symlink loop alongside another spec and a successful PyPI result. |
| R4 — failed monitoring | PyPI failures and exhausted budgets are visible; help structural findings are flushed independently and feature failures are summarized. | Version-only failed lookup, no-process-on-expired-budget assertion, and real help entrypoints combining missing/incomplete/stale/invalid inputs. |
| R5 — authored help | Parse actual YAML and compare canonical dry-run help projections, including their planned kind set. Validate template/source containment before trusting content or mtimes. | Real projector round trips; actual help-system prose change invisible to the old hash; removed section/all sections; direct template edit; legacy outside-template/source cases; standalone checkout-local projector import. |
| R6 — handoff provenance | Reject outside-resolving files; distinguish indexed, draft, and unverified handoffs; use an explicitly labeled deterministic mtime fallback. Git discovery and index lookup share two seconds. | Real Git indexes and script entrypoints; branch/fallback selection, internal/external symlinks, equal mtimes, and a slow-Git nudge that preserves both notices and exits in 2.033s, below its 3s registration. |
| G1 — complexity | Simplify banner construction without changing the ratchet. | `format_banner` is now 15, below the existing 21 threshold; post-change preflight passes all 87 governance tests. |

The different-model review (gpt-5.6-sol) found five further defects during
implementation: hostless provenance, lossy authored hashes, legacy template
containment, spec-directory resolution failure, and incomplete projection sets.
All five were accepted, corrected, and independently rechecked. The reviewer
reported no remaining actionable blocker within R1–R6/G1. The lead reran the
behavioral receipts centrally rather than relying on the reviewer's report.

### Final local receipts

- **260 focused tests passed**, with **96.16% combined statement/branch coverage**:
  help 91.53%, nudge 96.92%, reconciler 97.58%. These are tested-boundary results,
  not a substitute for the real subprocess/filesystem/HTTP receipts above.
- **87 governance tests passed** in post-change collaboration preflight,
  with zero failures. Three expected Git-state warnings remain: this working
  tree has local changes, and the separate main checkout is dirty and behind
  cached origin/main. That checkout was not modified.
- **77 integration and projection guards passed**: SDK subprocess gating,
  path validation, hook-fleet wiring, and authored projection drift.
- **28 review-ledger checks passed** after recording the delegation and review.
- Pinned Black 24.10.0 and Ruff 0.8.4 passed on all ten changed Python files;
  `git diff --check` passed.
- The actual help script, with empty inherited PYTHONPATH and import tracing,
  loaded this checkout's projector and returned no findings in **0.592s**,
  below its unchanged five-second timeout. All 31 manifest features have
  authored masters. No generated help or docs outputs were edited.

Combined test command (keyless; the HTTP fixtures use owned loopback sockets):

```sh
PYTHONPATH=src ANTHROPIC_API_KEY='' python -m pytest \
  tests/unit/hooks/test_help_freshness_nudge.py \
  tests/unit/hooks/test_help_freshness_reliability.py \
  tests/unit/hooks/test_starter_prompt_nudge.py \
  tests/unit/hooks/test_starter_reconciler.py \
  tests/unit/hooks/test_starter_hook_alignment.py \
  tests/unit/hooks/test_starter_reference_scope.py \
  tests/unit/hooks/test_spec_status_corpus.py \
  tests/unit/hooks/test_starter_reliability_boundaries.py \
  -q -o addopts='' -n 0 \
  --cov=attune.hooks.scripts.help_freshness_nudge \
  --cov=attune.hooks.scripts.starter_prompt_nudge \
  --cov=attune.hooks.scripts.starter_reconciler \
  --cov-branch --cov-report=term-missing
PYTHONPATH=src ANTHROPIC_API_KEY='' python scripts/collaboration_preflight.py
```

The HTTP fixture adapts only worker launch and URL routing so the worker owns
its server and the repository's inference guard remains active. It runs the
real worker entrypoint and urllib parser. This is a controlled process-lifetime
receipt, not a live PyPI availability measurement. A separate fast response
completed in 0.653s and emitted the expected version.

### Compatibility and remaining limits

Retaining the hooks adds startup work and makes formerly silent failures
visible; the measured local budgets remain below their registrations. Legacy
hostless stamps now require checking their intended repository and explicitly
re-stamping to add `repo_host`. Existing user starters were not rewritten.
Untracked local handoffs stay usable as drafts. Mtime fallback is evidence of
filesystem modification time, not last authored or committed content.

Windows, Linux, live GitHub/PyPI, and the actual Claude SessionStart harness
remain untested here. Local filesystem stalls have no new hard deadline.
The help hook checks help outputs; projected docs pages retain their existing
drift gate. The subsequent shipping go-ahead does not replace validation:
required CI, including Windows, must pass before proceeding toward merge.

### CI portability follow-up — PR #2499

The initial published head `d868dee78` failed four hook jobs: both Windows
lanes exposed the test wrapper's missing UTF-8 bootstrap, and both macOS lanes
failed to reach the owned HTTP fixture. Head `26be85a5c` restored the real
bootstrap and isolated fixture proxy routing. Both Windows and both Linux
hook jobs passed; macOS still failed. Proxy isolation alone was not its fix.

A guarded real-worker probe with an injected DNS stall reproduced the macOS
failure signature: standard HTTPServer construction spent 4.004s in its
unbounded reverse lookup and returned no version; numeric socket binding
returned 1.2.3 in 0.117s with the same stall active. The fixture now skips that
irrelevant lookup, asserts hostname resolution is never used, and preserves
actual subprocess exception details. The production deadline is unchanged.
This proves the fixture dependency; the runner's actual DNS behavior remains
unverified until CI supplies the final platform receipt.

The broader initial matrix exposed two stale baselines and one Python-version
semantic difference. The broad-catch debt decreased from 4 to 3, now recorded
in the shrink-only ratchet. The surface inventory and its subject/digest now
include the PyPI worker's module-level stdout anchor; existing pending runtime
obligations remain pending. Strict spec-directory resolution exposes loops on
Python 3.13+, while containment is checked first so dangling foreign symlinks
remain unverified. Real directory/phase-file symlinks and missing/active/empty
siblings are covered. Central checks: 671 repository gates and 35 boundary
tests passed; filesystem probes agree on Python 3.12, 3.13 and 3.14. Required
CI on the final PR head remains the acceptance condition.

Final combined hooks/gates: 1,796 passed. A full keyless unit run exposed the
packaged inventory copy requiring regeneration (22,662 passed, one failed,
116 skipped, 3 xfailed). The existing runtime projector updated both packaged
JSON files; 278 bootstrap/parity/ledger checks then passed. No existing receipt
or pending runtime obligation changed. Pinned pre-commit passed on all changes.

## Merged remediation and 16.4.0 artifact checks — 2026-09-09

The final CI obligation above is discharged. PR [#2499](https://github.com/Smart-AI-Memory/attune-ai/pull/2499)
merged as `b79a4701fb53f6988adbd5f3f2ef6e9997237c56`. Its final head,
`f9cc99dde328172d5d230b7038eacd5f46693c07`, passed all 15 platform/Python
suites, both timezone suites, coverage and the final build in
[Tests run 34398921719](https://github.com/Smart-AI-Memory/attune-ai/actions/runs/34398921719).
The original failures and local retest measurements remain historical evidence.

Release preparation [#2501](https://github.com/Smart-AI-Memory/attune-ai/pull/2501)
merged as `bb120c62cfe2a596014923433030d925e923801f`; a tree comparison and
whole-branch patch-id comparison confirmed the reviewed diff survived the squash.
Wheel and source archive rebuilt from that merge passed metadata checks and
separate clean-install smokes outside the checkout with isolated user state.
All three installed hook scripts match the merged source byte for byte. The
exact wheel passed the capture/recall gate from an empty directory: hit@3 3/3.
These are built-artifact receipts, not claims of PyPI publication.

Prompt refinement does not depend on the deferred host-question adapter in
[#2496](https://github.com/Smart-AI-Memory/attune-ai/pull/2496). Its 34 focused
tests passed without that module. Both rebuilt artifacts also passed a real MCP
stdio probe for host instructions, default-on status, persistent disable/enable
and a one-turn skip, with the adapter module confirmed absent. This establishes
policy delivery and preference behavior, not automatic invocation on every
message, the quality of a model's rewrite, or a human interaction receipt.

Live Claude SessionStart acceptance remains unverified. The earlier filesystem
stall, filesystem-time fallback and legacy-stamp limits still apply. Repository
state reconciliation does not establish the correctness of decision content.
