# Discovery-Sweep Access — Tasks

XML-enhanced task blocks (per
`.claude/rules/attune/xml-enhanced-prompts.md`). Three production tasks
+ one verification task. T1→T2 are sequential (handler needs the schema);
T3 is independent; T4 gates the PR.

---

## T1 — MCP tool schema

```xml
<task id="1" name="discovery-sweep-schema">
  <objective>
    Register the discovery_sweep tool schema so it appears in the MCP
    tool list and Claude can call it.
  </objective>
  <context>
    <existing-code path="src/attune/mcp/tool_schemas.py">
      get_workflow_tools() returns a dict of tool-name -> schema. Tools
      with options use an explicit input_schema (see test_generation,
      doc_gen); path-only tools use the _pt/_path_tool helper.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/mcp/tool_schemas.py">
      <change location="get_workflow_tools() return dict">
        Add "discovery_sweep" with explicit input_schema:
        required path (string); optional budget_usd (number, default
        10.0) and no_llm (boolean, default false). Description per
        design.md §1 — name the three buckets, point single-audit
        intent at the dedicated tools.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>get_workflow_tools()["discovery_sweep"]["input_schema"]["required"] == ["path"]</check>
    <check>EmpathyMCPServer()._build_dispatch_table() length increases by 1 once T2 lands</check>
  </validation>
</task>
```

## T2 — Handler + dispatch

```xml
<task id="2" name="discovery-sweep-handler">
  <objective>
    Add the _run_discovery_sweep handler and wire it into the dispatch
    table, forcing JSON output so the three buckets return structured.
  </objective>
  <context>
    <existing-code path="src/attune/mcp/server.py">
      _run_bug_predict (line ~391) is the pattern: validate path with
      _validate_file_path(..., allowed_dir=self._workspace_root), import
      the workflow lazily, await workflow.execute(...), return
      _workflow_response(result, ...). Dispatch entries live in
      _build_dispatch_table() (line ~270).
    </existing-code>
    <existing-code path="src/attune/workflows/discovery_sweep/workflow.py">
      DiscoverySweepWorkflow.execute(**kwargs) accepts path, budget_usd,
      no_llm, output_format ("markdown"|"json"); sources defaults to
      default_sources(). VERIFY the exact result keys for the buckets on
      the json return path before writing _workflow_response extractors.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="new method near _run_bug_predict">
        Add async _run_discovery_sweep(self, args) per design.md §2.
      </change>
      <change location="_build_dispatch_table()">
        Add "discovery_sweep": self._run_discovery_sweep.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>await _run_discovery_sweep({"path": "src/attune/security"}) returns dict with queue/questions/rejected keys</check>
    <check>a deliberately-crashing source surfaces as a questions entry, not an exception</check>
    <check>path traversal (../../etc) is rejected by _validate_file_path</check>
  </validation>
  <risks>
    <risk severity="medium">Bucket key names guessed instead of read from the json return path — yields empty buckets. Read workflow.py first.</risk>
  </risks>
</task>
```

## T3 — Thin skill

```xml
<task id="3" name="discovery-sweep-skill">
  <objective>
    Add a discovery-sweep skill so the workflow is discoverable in the
    catalog and auto-triggers on aggregate-audit intent.
  </objective>
  <context>
    <existing-code path="plugin/skills/bug-predict/SKILL.md">
      Thin-skill template: frontmatter (name, description with trigger
      phrases) + a short body that instructs calling the MCP tool.
    </existing-code>
  </context>
  <files-to-create>
    <file path="plugin/skills/discovery-sweep/SKILL.md">
      Frontmatter description with disambiguated triggers per design.md
      §4 / decisions D4. Body: what-it-is, the three buckets, and the
      single instruction to call the discovery_sweep MCP tool with path
      (+ optional budget_usd / no_llm). Reference only the real tool name.
    </file>
  </files-to-create>
  <validation>
    <check>ls plugin/skills/discovery-sweep/SKILL.md</check>
    <check>grep -w discovery_sweep src/attune/mcp/tool_schemas.py (the skill's named tool resolves)</check>
    <check>markdown lints clean; skill frontmatter matches the IDE linter (ground truth, not docs)</check>
  </validation>
</task>
```

## T4 — Tests, counts, README (PR gate)

```xml
<task id="4" name="discovery-sweep-tests-counts">
  <objective>
    Update tool-count assertions and the README MCP-tool-count claim, add
    a schema test, and run the reference-validation + MCP suites green.
  </objective>
  <context>
    <existing-code path="tests/unit/test_mcp_memory_tools.py">
      Line ~35 asserts len(tools) >= 41 (still holds). Line ~46 asserts
      == 46 with the redis plugin -> becomes 47.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="tests/unit/test_mcp_memory_tools.py">
      <change location="redis-plugin count assertion">46 -> 47</change>
    </file>
    <file path="tests/unit/mcp/test_tool_schemas.py">
      <change location="schema assertions">Add discovery_sweep present + required path</change>
    </file>
    <file path="README.md">
      <change location="MCP tool count claim, if present">bump by 1 (doc-audit checks this)</change>
    </file>
  </files-to-modify>
  <validation>
    <check>pytest tests/unit/test_mcp_memory_tools.py tests/unit/mcp/test_tool_schemas.py -q  (green)</check>
    <check>pytest tests/unit/plugins/test_plugin_reference_validation.py -q  (green)</check>
    <check>grep -rn "MCP tool" README.md  — claimed count matches live tool count</check>
  </validation>
  <risks>
    <risk severity="low">Other count sites (docs, website) drift. Out of scope here; note any found for a follow-up.</risk>
  </risks>
</task>
```

---

## Sequencing

- **T1 → T2** (handler references the schema's params).
- **T3** independent (can run in parallel with T1/T2).
- **T4** last — gates the PR; depends on T1–T3.

One PR. Concerns: `impl` (T1–T3) + `test` (T4) + `release-notes`
(README count + CHANGELOG entry). No `regression-guard` (feature add, not
a bug fix); no `migration` (additive).
