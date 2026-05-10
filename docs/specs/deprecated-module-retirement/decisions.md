# Per-module retirement decisions

Append-only log. One section per module as it's retired. See
`requirements.md`, `design.md`, `tasks.md` for the framework.

---

## Pre-execution decisions (recorded 2026-05-09)

### D1 — `examples/orchestration/basic_usage.py`: **rewrite**

Decision: rewrite the example against `ReleasePrepTeamWorkflow` from
`attune.agents.release` rather than delete it. The example carries
narrative value beyond the deprecated symbol it imports; orchestration
basics deserve a live, working demo using the current API.

Action at execution time: replace the import on line 23 and update
the body of the example to call `ReleasePrepTeamWorkflow` with its
current constructor signature. Verify the example runs end-to-end
before commit.

### D2 — CHANGELOG version bucket: **v7.0.0**

Decision: hold the removal until the v7.0.0 release. Rationale: v7.0.0
will also publish the 100% test coverage milestone — coupling the
breaking removal with the coverage announcement gives a single, clean
release narrative ("we hit 100% coverage; in the process we cleaned
out two long-deprecated modules") rather than two unrelated
breaking-change discussions in adjacent minor releases.

Implication for sequencing: the spec still executes when ready — the
file deletions and pyproject edits don't have to wait — but the
CHANGELOG entry slots under v7.0.0 and the release isn't cut until
the coverage push completes. If the coverage work surfaces additional
retirement candidates, those can land in the same v7.0.0 bucket.

### G1 — Formal deprecation date for `attune.scaffolding`: **2026-02-21**

Established via git history:

- **Module first introduced**: 2026-02-01 in commit `fafd4321`
  ("feat: Migrate empathy-framework to attune-ai") — at this point
  it was an active CLI surface, not deprecated.
- **Deprecation notice added**: 2026-02-21 in commit `3833d5d6`
  ("refactor: config decoupling, CLI deprecation, /plan brainstorm
  (#60)"). This is the commit that introduced the
  `_emit_cli_deprecation("attune.scaffolding", "attune workflow run")`
  call in `__main__.py`.

So `attune.scaffolding` will have been formally deprecated for
**~10 months by an estimated v7.0.0 release** (Feb 2026 → est. late
2026). That's a defensibly long warn period for a CLI-only surface
that already prints the deprecation notice on every invocation.

CHANGELOG entry should read approximately:

> **Removed** — `attune.scaffolding` package and its CLI surface
> (`python -m attune.scaffolding`). Deprecated since v… (2026-02-21,
> commit 3833d5d6); replaced by `attune workflow run`. Migration:
> use `attune workflow run <workflow-name>`.

(Fill in the version number from the v6.x history that contained
commit 3833d5d6 when writing the final entry.)

---

(per-module execution sections appended below as commits land)
