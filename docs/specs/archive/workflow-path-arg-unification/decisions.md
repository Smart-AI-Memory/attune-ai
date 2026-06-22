# Decisions — Workflow `path` Kwarg Unification

Append-only log. Pre-flight findings and per-PR decisions appended as
work lands.

---

## Origin (2026-05-13)

This spec follows the [`ops-runner-tier2`](../ops-runner-tier2/) Phase 1
audit (PR #285), which found 5 of 19 workflows use a kwarg name other
than `path`. PR #294 shipped a three-way `PATH_ARG_REGISTRY` as a
bridge — workable, but a workaround.

Patrick raised this spec on 2026-05-13: "I still think a fix the
workflows spec would be worth it." The bridge is the practical
near-term, but the cleaner long-term fix is to make every workflow
accept `path` directly. This spec is that long-term fix.

---

## Approach decisions

### D1 — Add `path` as a kwarg, keep old kwargs as deprecated aliases

**Decision**: Accept both names for one major version (v6.8 → v7.0),
emit `DeprecationWarning` on the old name, prefer `path` when both
are set.

**Why**: We don't know how many direct API callers exist outside the
codebase. The bridge maintains backward compat while signaling the
migration. After v7.0, the old kwargs become hard errors.

**Rejected alternatives**:
- *Hard cutover now*: would break any external caller relying on the
  old kwarg name. Even unlikely-but-possible cases (e.g.,
  `attune-author` or `attune-rag` calling into `health-check` directly)
  shouldn't bite the user on a minor bump.
- *Forever-dual-accept*: defeats the purpose of the cleanup.

### D2 — Keep old internal variable names for code clarity

**Decision**: Function signature uses `path`; internal variable names
in the body can stay as `project_root` / `src_path` / `cwd` if those
names are more descriptive for the local logic.

**Why**: Public API change is the goal. Internal variable naming is
a code-style choice that the workflow author should pick. Forcing
internal renames bloats the diff and risks introducing bugs.

### D3 — `rag-code-gen` keeps `cwd` semantics distinct from `path`

**Decision**: For `rag-code-gen`, `path` becomes a user-facing alias
for the SDK working directory (`cwd=` in `claude_agent_sdk`). The
internal `cwd` parameter stays for the SDK call.

**Why**: `cwd` is a real SDK concept (where the agent's tools run). For
this workflow, "scope path" and "SDK working directory" happen to be
the same thing. Users want `path` as the consistent kwarg name; the
SDK's internal needs are separate.

**Pre-flight check needed (Phase 0 task 0.2)**: Confirm `cwd` is the
SDK working directory, not a scope target. If they're semantically the
same in this workflow's context, the alias is straightforward.

### D4 — Drop the `required` flag from the registry post-migration

**Decision**: Once `test-audit` accepts `path`, the registry no longer
needs `required=True`. The workflow's own `execute()` body still
validates non-empty path and returns `_error_result` — that's where
the required-ness lives.

**Why**: The `required` flag in `PATH_ARG_REGISTRY` was a hint to the
ops runner (so the picker could enforce non-empty submission). After
migration, the workflow's internal validation is the single source of
truth.

### D5 — `PATH_ARG_REGISTRY` collapses to `frozenset[str]`, not deleted

**Decision**: Post-migration, the registry stays as a flat
`frozenset[str]` of workflow names that accept `path`. The
drift-guard test continues to assert every workflow is in the set.

**Why**: Drop-entirely would lose the "every workflow has been
migrated" guarantee. A `frozenset` is one line of code and gives the
drift-guard test something to assert against. If the BaseWorkflow ever
gets a `path: str` parameter at the class level, the registry can be
deleted then.

---

## Pre-flight findings

*(to be filled in by Phase 0 task 0.1 — sibling-package grep — and
0.2 — `rag-code-gen` cwd semantics confirmation)*

---

## Per-PR decisions

*(appended as PRs 1–5 land)*
