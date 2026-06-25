# Discovery-Sweep Access — Design

Grounded in the existing `bug_predict` MCP-tool wiring (the canonical
workflow-tool pattern). Reference chain per
`.claude/rules/attune/plugin-reference-validation.md`:
**Command/Skill → MCP tool schema → dispatch → handler → workflow class.**

---

## Touch points

| Layer | File | Change |
|-------|------|--------|
| Schema | `src/attune/mcp/tool_schemas.py` | add `discovery_sweep` to `get_workflow_tools()` |
| Dispatch | `src/attune/mcp/server.py` `_build_dispatch_table()` | add `"discovery_sweep": self._run_discovery_sweep` |
| Handler | `src/attune/mcp/server.py` | add `_run_discovery_sweep()` |
| Skill | `plugin/skills/discovery-sweep/SKILL.md` | new thin skill |
| Tests | `tests/unit/test_mcp_memory_tools.py`, `tests/unit/mcp/test_tool_schemas.py` | bump counts, add schema assertion |
| Docs | `README.md` (+ any MCP-tool-count claim) | bump count (doc-audit checks it) |

No change to `workflows/discovery_sweep/`.

---

## 1. Tool schema (`get_workflow_tools()`)

`discovery_sweep` needs more than the `_path_tool` helper (it has knobs),
so it uses an explicit `input_schema` like `test_generation`/`doc_gen`:

```python
"discovery_sweep": {
    "description": (
        "Run the discovery-sweep meta-workflow: fans out across all "
        "audit sources (pattern scan, bug-predict, security, deps, "
        "perf, docs, tests), dedups, and triages findings into "
        "queue / questions / rejected buckets. Use for a full "
        "'what should I fix' pass; single-purpose audits have their "
        "own tools."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory or file to sweep",
            },
            "budget_usd": {
                "type": "number",
                "description": "Total LLM spend cap (default 10.00)",
                "default": 10.0,
            },
            "no_llm": {
                "type": "boolean",
                "description": "Fast pattern-only sweep (skip LLM sources)",
                "default": False,
            },
        },
        "required": ["path"],
    },
},
```

`min_severity` is intentionally **not** exposed — the triage threshold
lives in `verification.py`, not an `execute()` kwarg. Keep the surface to
what the engine actually accepts.

---

## 2. Handler (`server.py`)

Mirrors `_run_bug_predict`, forcing `output_format="json"` so the buckets
return structured (FR-4). `sources` defaults to `default_sources()`
inside `execute()`, so the handler doesn't assemble them:

```python
async def _run_discovery_sweep(self, args: dict[str, Any]) -> dict[str, Any]:
    """Run the discovery-sweep triage meta-workflow."""
    from attune.security.path_validation import _validate_file_path
    from attune.workflows.discovery_sweep import DiscoverySweepWorkflow

    validated_path = str(
        _validate_file_path(args["path"], allowed_dir=self._workspace_root)
    )
    workflow = DiscoverySweepWorkflow()
    result = await workflow.execute(
        path=validated_path,
        budget_usd=float(args.get("budget_usd", 10.0)),
        no_llm=bool(args.get("no_llm", False)),
        output_format="json",
    )
    return _workflow_response(
        result,
        queue=("queue", []),
        questions=("questions", []),
        rejected=("rejected", []),
    )
```

**Verify during implementation:** the exact keys `execute()` puts on
`WorkflowResult` for the three buckets (read the `output_format="json"`
return path in `workflow.py` around the `WorkflowResult(...)` build — the
`_workflow_response` extractor keys must match). Do not assume.

---

## 3. Dispatch entry

In `_build_dispatch_table()`, beside the other workflow entries:

```python
"discovery_sweep": self._run_discovery_sweep,
```

---

## 4. Skill (`plugin/skills/discovery-sweep/SKILL.md`)

Thin skill modeled on `bug-predict/SKILL.md`. Frontmatter `description`
carries the auto-triggers, **disambiguated** (NFR-2):

- **Fires on:** "run all audits", "full sweep", "audit everything",
  "what should I fix", "triage findings", "discovery sweep",
  "sweep the codebase".
- **Does NOT claim:** bare "security" / "find bugs" / "review" / "predict
  bugs" (those belong to `security-audit` / `bug-predict` /
  `code-quality` / `deep-review`); nor "run multiple workflows" (that is
  `workflow-orchestration`, which is explicit-only).

Body: one-paragraph what-it-is, the three-bucket explanation, and a
single instruction to call the `discovery_sweep` MCP tool with `path`
(+ optional `budget_usd` / `no_llm`). It must reference only the real
tool name `discovery_sweep`.

---

## 5. Tests & counts

- `tests/unit/test_mcp_memory_tools.py:35` `>= 41` still holds; **line 46
  `== 46` (with redis) → `== 47`**.
- `tests/unit/mcp/test_tool_schemas.py` — add a `discovery_sweep` schema
  assertion (present, has required `path`).
- `tests/unit/plugins/test_plugin_reference_validation.py` — passes
  automatically once the skill references a real tool; run it.
- `README.md` — if it states an MCP-tool count, bump it (the `doc-audit`
  workflow's README-claim check fails otherwise).

---

## Risks

- **R1 (medium):** wrong bucket keys in `_workflow_response` → empty
  buckets in the response. Mitigation: read the json return path; assert
  on a real sweep in the handler test.
- **R2 (low):** auto-trigger shadowing regresses sibling skills.
  Mitigation: explicit-only fallback if phrasing proves greedy; the
  `skill-sync` / disambiguation test guards it.
- **R3 (low):** count drift across the 3+ count sites. Mitigation: the
  acceptance checklist enumerates every site.
