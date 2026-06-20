# Design: Workflow `path` Kwarg Unification

**Status**: complete — all 5 target workflows accept `path` (doc-orchestrator closed in #685) — verified 2026-06-08 spec triage

---

## Phase 2: Design

### Architecture

Five independent per-workflow migrations + one cleanup PR, each
shippable in isolation:

```
PR-1: health-check + orchestrated-health-check       ← shared source file, do together
PR-2: doc-orchestrator                               ← same pattern as PR-1
PR-3: test-audit (path replaces required src_path)   ← deprecation warning
PR-4: rag-code-gen (path → cwd internally)           ← semantic clarification
PR-5: PATH_ARG_REGISTRY simplification               ← after PR-1..4 all merged
```

Each per-workflow PR is small (~30–50 LoC). The drift-guard test in
`tests/unit/ops/test_path_support_registry.py` catches missing entries
during the migration window — if a workflow's source kwarg changes to
`path` but the registry isn't updated, the test fires.

### The migration pattern

Each Category C workflow follows the same three-step pattern in its
`execute()` method:

```python
async def execute(self, **kwargs: Any) -> WorkflowResult:
    # 1. Accept BOTH the new name and the legacy name.
    path_arg: str = kwargs.get("path", "")
    legacy_arg: str = kwargs.get("<old_name>", "")  # project_root / src_path / cwd

    # 2. If only the legacy name is set, warn and forward.
    if legacy_arg and not path_arg:
        import warnings
        warnings.warn(
            f"Passing `{old_name}=` to {workflow_name} is deprecated; "
            f"use `path=` instead. Will be removed in v8.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        path_arg = legacy_arg

    # 3. Internal variable name stays as it was for code clarity.
    # ... rest of execute() unchanged
```

The two-kwarg-accept window lasts one minor version (v6.8 → v6.9). In
v7.0 (next major), the legacy kwargs become hard errors with a clear
migration message.

### Per-workflow specifics

**`health-check` / `orchestrated-health-check` (same source file)**

Current signature:
```python
async def execute(
    self,
    project_root: str | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> WorkflowResult:
```

New signature:
```python
async def execute(
    self,
    path: str | None = None,
    *,
    project_root: str | None = None,   # deprecated alias
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> WorkflowResult:
    if project_root and not path:
        warnings.warn(...)
        path = project_root
    # body uses path; existing `self.project_root = Path(path).resolve()` line uses
    # path-the-local-variable, no rename needed
```

The "Map 'target' to 'project_root' for VSCode compat" block at lines
24-26 of the source file becomes "Map 'target' to 'path'." Backward
compat for `target=` stays.

**`doc-orchestrator`**

Current signature:
```python
async def execute(
    self,
    context: dict | None = None,
    **kwargs: Any,
) -> WorkflowResult:
```

Body uses `kwargs.get("project_root")`. New body:
```python
async def execute(
    self,
    context: dict | None = None,
    **kwargs: Any,
) -> WorkflowResult:
    path = kwargs.get("path") or kwargs.get("project_root")
    if kwargs.get("project_root") and not kwargs.get("path"):
        warnings.warn(...)
    # ... rest unchanged
```

**`test-audit`**

This is the only `required=True` case. Current:
```python
async def execute(self, **kwargs: Any) -> WorkflowResult:
    src_path_arg: str = kwargs.get("src_path", "")
    if not src_path_arg:
        return self._error_result("src_path argument is required")
```

New:
```python
async def execute(self, **kwargs: Any) -> WorkflowResult:
    # Accept both names; prefer `path` if both are set.
    path_arg: str = kwargs.get("path") or kwargs.get("src_path", "")
    if kwargs.get("src_path") and not kwargs.get("path"):
        warnings.warn("src_path= is deprecated; use path=", DeprecationWarning)
    if not path_arg:
        return self._error_result("path argument is required (was: src_path)")
    # Internal variable can stay as src_path for clarity:
    src_path = path_arg
    # ... rest unchanged
```

Error message updates so users see "path argument is required" rather
than the deprecated name.

**`rag-code-gen`**

Two-kwarg semantic merge. Current uses `cwd` to mean "SDK working
directory." After the migration, `path` becomes the public name and
internal usage stays as `cwd`:

```python
async def execute(self, **kwargs: Any) -> WorkflowResult:
    path_arg = kwargs.get("path") or kwargs.get("cwd")
    if kwargs.get("cwd") and not kwargs.get("path"):
        warnings.warn("cwd= is deprecated; use path=", DeprecationWarning)
    # Forward to the SDK's cwd parameter, semantics unchanged:
    cwd_for_sdk = path_arg or os.getcwd()
    # ... rest unchanged
```

### PR-5: registry simplification

After PRs 1–4 land, `PATH_ARG_REGISTRY` is collapsed:

```python
# Before:
PATH_ARG_REGISTRY: dict[str, PathArgSpec] = {
    "bug-predict": PathArgSpec(kwarg="path"),
    "code-review": PathArgSpec(kwarg="path"),
    ...
    "health-check": PathArgSpec(kwarg="project_root"),
    "test-audit": PathArgSpec(kwarg="src_path", required=True),
    ...
}

# After:
WORKFLOWS_ACCEPTING_PATH: frozenset[str] = frozenset({
    "bug-predict", "code-review", "deep-review", "dependency-check",
    "doc-audit", "doc-gen", "doc-orchestrator", "health-check",
    "orchestrated-health-check", "perf-audit", "rag-code-gen",
    "refactor-plan", "release-prep", "research-synthesis",
    "secure-release", "security-audit", "simplify-code",
    "test-audit", "test-gen",
})

# Or: drop the registry entirely and treat "accepts path" as the contract
# that the drift-guard test enforces against EVERY workflow.
```

The `PathArgSpec` dataclass and the ops-runner kwarg-remap logic
become deletable. Drift-guard tests in
`tests/unit/ops/test_path_support_registry.py` simplify too:

```python
# Before — parametrized per workflow checking source kwarg name
# After — assert every workflow has `path` in its execute() signature
```

### Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Downstream caller passes `project_root=path` after the deprecation window | One-major-release deprecation period (v6.8 → v7.0); CHANGELOG calls it out; the DeprecationWarning is informative |
| 2 | Internal code in attune-* sibling packages uses old kwarg names | Pre-PR grep across `attune-author`, `attune-help`, `attune-rag`, `attune-software` for `project_root=`, `src_path=`, `cwd=` keyword usage on these workflows |
| 3 | Workflow body keeps using the old variable name and forgets to plumb new `path` arg | Test that calls `execute(path="src/foo")` and asserts the internal path actually scopes the run |
| 4 | `PathArgSpec.required=True` semantics get lost for test-audit | The new body still returns `_error_result` if neither `path` nor `src_path` is set; drift-guard test verifies test-audit's signature requires non-empty path |
| 5 | Mutual exclusion: user passes BOTH `path=` and old kwarg | Document in DeprecationWarning that `path=` wins when both are set; verify in tests |

### Decision points at execution time

- **D1.** Should `path` be positional-or-keyword (like `release-prep`'s current `path: str = "."`) or keyword-only? Keyword-only is safer (no risk of confusing with `context`); positional-or-keyword matches the existing convention. Recommend keyword-only for all 5.
- **D2.** Drop `PATH_ARG_REGISTRY` entirely or keep as a `frozenset` post-migration? `frozenset` preserves the drift-guard's "every workflow has an entry" check. Drop entirely if every workflow is path-accepting by construction (e.g., a BaseWorkflow assertion). Recommend `frozenset` for now.
- **D3.** Should the deprecation period be one minor or one major? One major is more conservative; one minor matches the spec's intent and the actual blast radius (we control most callers). Recommend one major (v6.8 → v7.0).

### Out-of-scope cross-references

- **ops-runner-tier2 Phase 2+**: The scope picker uses `PATH_ARG_REGISTRY` today. After this spec's PR-5 lands, the picker can read from the simpler `frozenset`. No coordination needed — ops-runner-tier2 can stay on the current registry shape while this spec migrates.
- **`attune-author` / `attune-rag` / sibling packages**: If they call any of these 5 workflows by name (unlikely but possible), they need their own minor-version bumps to switch to `path=`. Pre-PR grep flags any such call sites.
- **MCP tool schemas**: The MCP `*` tools that wrap these workflows already pass through `path=` from their JSON schema. No MCP schema change needed.

### Failure-to-deliver fallback

If a Category C workflow turns out to have internal-variable-naming or sibling-package coupling that makes the migration costly:

1. **Mark that workflow's PR as `deferred`** in this spec's `tasks.md`.
2. **Keep its entry in `PATH_ARG_REGISTRY`** (the bridge stays in place for that one workflow).
3. **PR-5 simplification is `partial`** — registry shrinks but doesn't collapse to a flat frozenset.
4. **Document the holdout** in `decisions.md` with a follow-up note.

The spec is **done** when at least 4 of the 5 workflows accept `path` AND `PATH_ARG_REGISTRY` is either flat or contains ≤1 entry.
