# Phase 1 audit — `--path` support per workflow

**Date**: 2026-05-12
**Method**: three-step inspection per the spec's Phase 1 plan:
1. CLI surface check (`attune workflow run --help`) — does the CLI accept `--path`?
2. Per-workflow `execute()` signature scan
3. Per-workflow `execute()` body scan for actual `path` consumption (kwargs.get / direct kwarg)
4. Cross-check via `attune workflow info <name>` for the docstring's example invocation
**Outcome**: hypothesis H2 ("Workflow `--path` support is unevenly implemented") **confirmed and refined**. The reality is three-way, not binary.

---

## CLI surface check

```text
$ attune workflow run --help
usage: attune workflow run [-h] [--input INPUT] [--path PATH]
                           [--target TARGET] [--json]
                           name
```

`--path` is a **uniform CLI argument** for every workflow. It always
becomes a `path=...` kwarg in `workflow.execute(**input_data)` (see
`src/attune/cli_commands/workflow_commands.py:102-106`). Whether the
workflow actually CONSUMES that kwarg is the real question.

`--target` is a separate uniform CLI argument and is the documented
alternative kwarg for some workflows (notably `health-check` family
maps `target` → `project_root` at `src/attune/workflows/orchestrated_health_check.py:24-26`).

---

## Per-workflow categorization

| Workflow | execute() signature kwargs | Path arg actually consumed | Category |
|---|---|---|---|
| `bug-predict` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `code-review` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `deep-review` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `dependency-check` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `doc-audit` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `doc-gen` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `perf-audit` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `refactor-plan` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `research-synthesis` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `security-audit` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `simplify-code` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `test-gen` | `**kwargs` | `kwargs.get("path", "")` | **A — direct** |
| `release-prep` | `path: str = "."` | direct signature arg | **B — direct (signature)** |
| `secure-release` | `path: str = "."` | direct signature arg | **B — direct (signature)** |
| `health-check` | `project_root=None, **kwargs` | uses `project_root`; maps `target` → `project_root` at line 24-26 | **C — aliased** |
| `orchestrated-health-check` | `project_root=None, **kwargs` | same as health-check (same source file) | **C — aliased** |
| `doc-orchestrator` | `context, **kwargs` | uses `kwargs.get("project_root")` | **C — aliased** |
| `test-audit` | `**kwargs` | `kwargs.get("src_path", "")` — **errors if missing** | **C — aliased** |
| `rag-code-gen` | `**kwargs` | uses `kwargs.get("cwd")` for SDK working-dir | **C — aliased** |

Totals:
- **A + B (14 workflows)**: respond directly to the CLI `--path` arg with no rewiring.
- **C (5 workflows)**: ignore the `--path` kwarg as-is. They take path-shaped scoping under a different name.

No workflow in the audit is genuinely "project-wide by design" — every one of the 19 has SOME form of scoping argument. The spec's framing in H2 ("`release-prep`, `health-check`, `dependency-check` don't [take path]") is partially wrong:

- `dependency-check` **does** take `path` (Category A).
- `release-prep` **does** take `path` (Category B — signature-level).
- `health-check` takes `project_root`, not `path` (Category C).

---

## Implication for Phase 2 (scope picker)

The spec's Phase 2.3 plan was:

> "Render the `<select>` + hidden `<input type="text">` per row in
> `workflows.html`. Show `<span class="scope-na">` for workflows
> where `supports_path[w.name] is False`."

The audit suggests a **better default than scope-na**: remap Category C
in the ops runner so the picker works for all 19 workflows.

### Three implementation options for `SUPPORTS_PATH_ARG` (task 1.3)

**Option 1 — Binary registry, scope-na for Category C (spec's literal plan).**

```python
SUPPORTS_PATH_ARG: dict[str, bool] = {
    "bug-predict": True, "code-review": True, ...,  # 14 True
    "doc-orchestrator": False, "health-check": False, ...,  # 5 False
}
```

Tooltip on scope-na: "Runs project-wide by default." Inaccurate
(they're path-scoped, just under a different arg) but matches the
spec's existing prose. Simplest.

**Option 2 — Three-way registry with kwarg-name remapping.**

```python
@dataclass
class PathArgSpec:
    kwarg: str | None  # Which kwarg name the workflow expects, or None
    required: bool = False

PATH_ARG_REGISTRY: dict[str, PathArgSpec] = {
    "bug-predict": PathArgSpec(kwarg="path"),
    ...
    "health-check": PathArgSpec(kwarg="project_root"),
    "doc-orchestrator": PathArgSpec(kwarg="project_root"),
    "test-audit": PathArgSpec(kwarg="src_path", required=True),
    "rag-code-gen": PathArgSpec(kwarg="cwd"),
}
```

The ops runner reads this registry and rewrites the kwarg name before
spawning the subprocess. All 19 workflows get the picker; the user
never knows about the kwarg-name mismatch. **Recommended.**

**Option 3 — Fix the workflows to all accept `path` (consistency).**

Rewrite Category C workflows to accept `path` and forward it to their
internal `project_root` / `src_path` / `cwd`. Cleanest long-term, but
out of scope for this spec — it's a refactor of 5 workflow files. The
ops runner would then need no registry at all.

### Recommendation

**Option 2 (three-way registry with kwarg-name remapping).** Reasons:
- Captures the actual reality (Category C workflows ARE path-scoped,
  just under a different name)
- Lets the picker work for all 19 workflows without compromising UX
- Doesn't require touching 5 workflow files (Option 3)
- Forward-compatible: if a future workflow adds direct `path` support,
  registry entry simplifies; if Category C workflows are unified
  upstream, registry collapses to Category A automatically
- `required=True` for `test-audit` ensures the picker can't submit a
  scope-less run that the workflow would reject

The drift-guard test (task 1.3, third bullet) becomes more useful too —
it asserts every workflow has a registry entry AND that the entry's
`kwarg` matches the actual kwarg name in the workflow source (catches
silent renames).

---

## Suggested updates to `tasks.md`

If this audit is accepted:

- Mark task **1.1** (grep workflow source) **done**.
- Mark task **1.2** (`--help` verification) **done** with the cross-check above.
- Reframe task **1.3** from "Record findings as `SUPPORTS_PATH_ARG` dict" to "Add `PATH_ARG_REGISTRY` dict to `src/attune/ops/data.py` per Option 2 (three-way registry with kwarg-name remapping)." Drift-guard test asserts both presence and kwarg-name match.
- Tasks **2.x** Phase 2 implementation can read this registry — no scope-na branch needed.

The remaining work is concrete and unchanged from the spec; the audit
mostly **expands** what Phase 2 can deliver (all 19 workflows scoped
instead of 14).
