# MCP Server Refactor Plan

**Version:** 1.0
**Created:** 2026-03-05
**Completed:** 2026-03-04
**Owner:** Patrick Roebuck
**Status:** COMPLETE (all 5 phases executed)
**Scope:** Items 1-16 from simplify review of `src/attune/mcp/`
**Branch:** `fix/stale-slash-command-references`

---

## Architecture Context

Before refactoring, key discoveries from exploration:

- `handlers/` directory is NOT dead code — it has 5 test
  files. It duplicates the mixin logic but tests import it
  directly. Strategy: consolidate into one architecture and
  update tests.
- `request_handler.py` IS dead code — duplicates
  `handle_request()` in server.py. One test file imports it.
- Three workflows return custom result types (not
  `WorkflowResult`): `DocumentationOrchestrator`,
  `SecureReleasePipeline`, `OrchestratedHealthCheckWorkflow`.
  This is why some handlers use `getattr()`.
- Tool count assertion in
  `tests/unit/test_mcp_memory_tools.py:32` is `== 33`
  (28 core + 6 redis). Must update if tools change.

---

## Phase 1: Dead Code Removal (Items 1-2)

Low risk, high impact. Remove code that is duplicated
and never used by the live server.

### Task 1.1 — Consolidate `handlers/` into mixins

```xml
<task id="1.1" name="consolidate-handlers-dir">
  <objective>
    Eliminate the duplicate handlers/ directory by making
    its 5 test files import from the mixin modules instead.
    Delete the handlers/ source files after.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/handlers/">
      5 modules with standalone functions (take server as
      first arg). Duplicates logic in memory_handlers.py
      and workflow_handlers.py mixins, plus server.py
      inline methods for auth/context/telemetry.
    </existing-code>
    <existing-code path="tests/unit/mcp/handlers/">
      5 test files that import from attune.mcp.handlers.*
      Test the standalone function variants.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="tests/unit/mcp/handlers/test_memory_handlers.py">
      <change location="imports and test bodies">
        BEFORE: from attune.mcp.handlers.memory_handlers
                import handle_memory_store
        AFTER:  Create an EmpathyMCPServer instance (or mock)
                and call self._handle_memory_store() on it.
                Alternatively, keep tests as thin wrappers that
                instantiate the mixin.
      </change>
    </file>
    <file path="tests/unit/mcp/handlers/test_auth_handlers.py">
      <change location="imports">
        Rewrite to test server._get_auth_status() and
        server._get_auth_recommend() directly.
      </change>
    </file>
    <file path="tests/unit/mcp/handlers/test_context_handlers.py">
      <change location="imports">
        Rewrite to test server._handle_context_get/set()
        and server._handle_attune_get/set_level().
      </change>
    </file>
    <file path="tests/unit/mcp/handlers/test_telemetry_handlers.py">
      <change location="imports">
        Rewrite to test server._get_telemetry_stats().
      </change>
    </file>
    <file path="tests/unit/mcp/handlers/test_workflow_handlers.py">
      <change location="imports">
        Rewrite to test WorkflowHandlersMixin methods via
        server instance.
      </change>
    </file>
  </files-to-modify>

  <files-to-delete>
    <file path="src/attune/mcp/handlers/__init__.py" />
    <file path="src/attune/mcp/handlers/auth_handlers.py" />
    <file path="src/attune/mcp/handlers/context_handlers.py" />
    <file path="src/attune/mcp/handlers/memory_handlers.py" />
    <file path="src/attune/mcp/handlers/telemetry_handlers.py" />
    <file path="src/attune/mcp/handlers/workflow_handlers.py" />
  </files-to-delete>

  <validation>
    <check>pytest tests/unit/mcp/handlers/ passes</check>
    <check>No imports of attune.mcp.handlers remain in src/</check>
    <check>grep -r "from attune.mcp.handlers" src/ returns 0</check>
  </validation>

  <risks>
    <risk severity="medium">
      Test rewrites may miss edge cases covered by the
      standalone function tests. Diff old vs new test
      coverage to verify.
    </risk>
  </risks>
</task>
```

### Task 1.2 — Delete `request_handler.py`

```xml
<task id="1.2" name="delete-request-handler">
  <objective>
    Remove the duplicate request_handler.py and update
    its test to import from server.py instead.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/request_handler.py">
      Single function handle_request() — identical to
      server.py:987-1021.
    </existing-code>
    <existing-code path="tests/unit/mcp/test_request_handler.py">
      Imports from attune.mcp.request_handler.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="tests/unit/mcp/test_request_handler.py">
      <change location="imports">
        BEFORE: from attune.mcp.request_handler import
                handle_request
        AFTER:  from attune.mcp.server import handle_request
      </change>
    </file>
  </files-to-modify>

  <files-to-delete>
    <file path="src/attune/mcp/request_handler.py" />
  </files-to-delete>

  <validation>
    <check>pytest tests/unit/mcp/test_request_handler.py passes</check>
    <check>grep -r "request_handler" src/attune/ returns 0</check>
  </validation>

  <risks>
    <risk severity="low">
      Trivial change — just an import path update.
    </risk>
  </risks>
</task>
```

---

## Phase 2: Constants and Annotations (Items 4, 5, 9, 12)

Safe, mechanical changes. No logic changes.

### Task 2.1 — Extract `level_names` to module constant

```xml
<task id="2.1" name="extract-level-names">
  <objective>
    Define ATTUNE_LEVEL_NAMES and ATTUNE_LEVEL_DESCRIPTIONS
    as module-level constants in server.py. Replace all 4
    inline definitions.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      level_names dict at lines 884 and 921.
      level descriptions dict at lines 896-901.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="after line 16 (module-level)">
        Add:
        ATTUNE_LEVEL_NAMES: dict[int, str] = {
            1: "Reactive",
            2: "Guided",
            3: "Proactive",
            4: "Anticipatory",
            5: "Systems",
        }

        ATTUNE_LEVEL_DESCRIPTIONS: dict[int, str] = {
            1: "Respond when asked. Minimal proactive guidance.",
            2: "Collaborative exploration with clarifying questions.",
            3: "Act before being asked. Suggest improvements.",
            4: "Predict future needs. Prepare for likely next steps.",
            5: "Build structures that help at scale.",
        }
      </change>
      <change location="_handle_attune_get_level (line 884)">
        BEFORE: level_names = {1: "Reactive", ...}
        AFTER:  (use ATTUNE_LEVEL_NAMES constant)
      </change>
      <change location="_handle_attune_set_level (line 921)">
        BEFORE: level_names = {1: "Reactive", ...}
        AFTER:  (use ATTUNE_LEVEL_NAMES constant)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/test_mcp_memory_tools.py passes</check>
    <check>grep -c "level_names" server.py returns 0 (no local defs)</check>
  </validation>

  <risks>
    <risk severity="low">Pure refactor, no behavior change.</risk>
  </risks>
</task>
```

### Task 2.2 — Inject `name` field from dict key

```xml
<task id="2.2" name="deduplicate-tool-name-field">
  <objective>
    Remove the redundant "name" field from all 27+ tool
    definitions in _register_tools(). Inject it
    automatically from the dict key in get_tool_list().
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Every tool dict has "name": "tool_name" that duplicates
      the dict key. get_tool_list() returns
      list(self.tools.values()).
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="_register_tools (lines 84-493)">
        Remove "name": "..." from every tool dict.
      </change>
      <change location="get_tool_list (line 968)">
        BEFORE: return list(self.tools.values())
        AFTER:  return [
                    {"name": name, **defn}
                    for name, defn in self.tools.items()
                ]
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/test_mcp_memory_tools.py passes</check>
    <check>Every tool in get_tool_list() still has a "name" field</check>
    <check>grep -c '"name":' in _register_tools block is 0</check>
  </validation>

  <risks>
    <risk severity="medium">
      If any code accesses self.tools["x"]["name"] directly
      (not via get_tool_list), it will break. Grep for this
      pattern before applying.
    </risk>
  </risks>
</task>
```

### Task 2.3 — Add `# noqa: BLE001` annotations

```xml
<task id="2.3" name="add-ble001-annotations">
  <objective>
    Add # noqa: BLE001 and # INTENTIONAL: comments to all
    broad except Exception catches in server.py that lack
    them, per project coding standards.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Lines 41, 73, 744, 1048 have unannotated broad catches.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="line 41">
        BEFORE: except Exception:
        AFTER:  except Exception:  # noqa: BLE001
                    # INTENTIONAL: Version check is best-effort
      </change>
      <change location="line 73">
        BEFORE: except Exception as e:
        AFTER:  except Exception as e:  # noqa: BLE001
      </change>
      <change location="line 744">
        BEFORE: except Exception as e:
        AFTER:  except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Top-level MCP handler must
                    # not crash the server
      </change>
      <change location="line 1048">
        BEFORE: except Exception as e:
        AFTER:  except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Server loop must not crash
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>ruff check src/attune/mcp/server.py --select BLE
           returns 0 errors</check>
  </validation>

  <risks>
    <risk severity="low">Annotation-only, no logic change.</risk>
  </risks>
</task>
```

### Task 2.4 — Extract memory error message constant

```xml
<task id="2.4" name="extract-memory-error-msg">
  <objective>
    Replace the 4 identical "attune-ai memory module not
    installed" strings in memory_handlers.py with a
    module-level constant.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/memory_handlers.py">
      String appears at lines 97, 139, 182, 232.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/memory_handlers.py">
      <change location="after line 11 (module-level)">
        Add:
        _MEMORY_NOT_INSTALLED = (
            "attune-ai memory module not installed. "
            "Run: pip install attune-ai"
        )
      </change>
      <change location="lines 97, 139, 182, 232">
        BEFORE: "error": "attune-ai memory module not
                installed. Run: pip install attune-ai"
        AFTER:  "error": _MEMORY_NOT_INSTALLED
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/mcp/handlers/test_memory_handlers.py
           passes</check>
    <check>grep -c "not installed" memory_handlers.py returns 1
           (the constant definition only)</check>
  </validation>

  <risks>
    <risk severity="low">String extraction, no logic change.</risk>
  </risks>
</task>
```

---

## Phase 3: Structural Refactoring (Items 3, 6, 7)

Higher complexity. Changes dispatch and schema patterns.

### Task 3.1 — Replace if/elif dispatch with dict

```xml
<task id="3.1" name="dict-dispatch-call-tool">
  <objective>
    Replace the 70-line if/elif chain in call_tool() with
    a dict mapping tool names to handler callables. Merge
    plugin handlers into the same dispatch table.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      call_tool() at lines 672-746 has 28 if/elif branches.
      Plugin handlers already use dict dispatch at line 740:
      self._plugin_handlers[tool_name].
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="__init__ (after line 34)">
        Build dispatch table:
        self._tool_handlers: dict[str, Callable] = {
            "security_audit": self._run_security_audit,
            "bug_predict": self._run_bug_predict,
            ...all 28 tools...
        }
      </change>
      <change location="call_tool (lines 672-746)">
        BEFORE: 70-line if/elif chain
        AFTER:
        async def call_tool(self, tool_name, arguments):
            try:
                handler = self._tool_handlers.get(tool_name)
                if handler is None:
                    handler = self._plugin_handlers.get(
                        tool_name
                    )
                if handler is None:
                    return {"success": False,
                            "error": f"Unknown tool: {tool_name}"}
                return await handler(arguments)
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Top-level MCP handler
                logger.exception(f"Tool failed: {tool_name}")
                return {"success": False, "error": str(e)}
      </change>
      <change location="_register_plugin_tools">
        Plugin tools go into self._plugin_handlers (already
        works). call_tool checks both dicts.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/test_mcp_memory_tools.py passes</check>
    <check>pytest tests/unit/mcp/ passes</check>
    <check>All 28 tool names in _tool_handlers match keys in
           self.tools (write a test for this)</check>
    <check>set(self._tool_handlers) == set(self.tools)</check>
  </validation>

  <risks>
    <risk severity="medium">
      Handler methods that take no args (auth_status,
      attune_get_level) have different signatures. Need
      wrapper or normalize all handlers to accept args dict.
    </risk>
    <risk severity="low">
      Plugin handlers take (self, arguments) while core
      handlers take (arguments). Verify signatures match.
    </risk>
  </risks>
</task>
```

### Task 3.2 — Tool definition factory for path-only tools

```xml
<task id="3.2" name="tool-schema-factory">
  <objective>
    Create a _path_tool() factory function to generate the
    10+ tool definitions that share the identical
    single-path-param schema. Reduce ~150 lines of
    boilerplate.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Tools like release_prep, doc_audit, refactor_plan,
      dependency_check, simplify_code, secure_release all
      have: one "path" string param with a default of ".".
      Some have required=True (security_audit, bug_predict,
      code_review, performance_audit).
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="before _register_tools">
        Add helper:
        def _path_tool(
            description: str,
            *,
            param_name: str = "path",
            param_desc: str = "Path to directory or file",
            required: bool = False,
            default: str = ".",
        ) -> dict[str, Any]:
            schema: dict[str, Any] = {
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        param_name: {
                            "type": "string",
                            "description": param_desc,
                        },
                    },
                },
            }
            if required:
                schema["input_schema"]["required"] = [param_name]
            else:
                schema["input_schema"]["properties"][param_name][
                    "default"
                ] = default
            return schema
      </change>
      <change location="_register_tools">
        Replace verbose dicts with factory calls:
        "security_audit": _path_tool(
            "Run security audit workflow...",
            param_desc="Path to directory or file to audit",
            required=True,
        ),
        "release_prep": _path_tool(
            "Run release preparation workflow...",
            param_desc="Path to project root",
        ),
        ...etc for all path-only tools...
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/test_mcp_memory_tools.py passes</check>
    <check>get_tool_list() output is identical before/after
           (write a snapshot test or compare JSON)</check>
  </validation>

  <risks>
    <risk severity="medium">
      Must preserve exact schema structure including
      "required" arrays and "default" values. Diff the
      JSON output of get_tool_list() before and after.
    </risk>
  </risks>
</task>
```

### Task 3.3 — Normalize workflow result extraction

```xml
<task id="3.3" name="normalize-result-extraction">
  <objective>
    Create a shared utility to extract standard fields
    from both WorkflowResult and custom result types.
    Unify the two access patterns across all handlers.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Pattern A: result.final_output.get("findings", [])
      Pattern B: getattr(result, "success", False)
      Used because DocumentationOrchestrator,
      SecureReleasePipeline, OrchestratedHealthCheckWorkflow
      return custom result types, not WorkflowResult.
    </existing-code>
    <existing-code path="src/attune/orchestration/workflow_agent_adapter.py">
      _extract_findings() already handles both patterns
      using getattr with fallbacks.
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/mcp/result_utils.py">
      Module with:
      def extract_base_result(result: Any) -> dict[str, Any]:
          """Extract common fields from any workflow result.
          Handles WorkflowResult and custom result types."""
          base = {
              "success": getattr(result, "success", False),
          }
          cost_report = getattr(result, "cost_report", None)
          if cost_report:
              base["cost"] = getattr(
                  cost_report, "total_cost", 0.0
              )
          else:
              base["cost"] = getattr(
                  result, "total_cost", 0.0
              )
          return base
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/mcp/workflow_handlers.py">
      <change location="_run_doc_orchestrator (line 95)">
        Use extract_base_result() for common fields,
        then add custom fields with getattr().
      </change>
      <change location="_run_secure_release (line 260)">
        Same pattern.
      </change>
      <change location="_run_health_check (line 288)">
        Same pattern.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/mcp/ passes</check>
    <check>All handlers return dicts with "success" and "cost"</check>
  </validation>

  <risks>
    <risk severity="medium">
      Custom result types may not have cost_report. The
      utility must gracefully fall back.
    </risk>
  </risks>
</task>
```

---

## Phase 4: Functional Fixes (Items 8, 10, 13, 14)

Fix stubs, deprecations, and standards violations.

### Task 4.1 — Fix or remove telemetry stub

```xml
<task id="4.1" name="fix-telemetry-stub">
  <objective>
    Either wire _get_telemetry_stats() to the real
    telemetry system or remove the tool registration
    until it's functional. Currently returns hardcoded
    zeros and misleads users.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      _get_telemetry_stats (lines 871-880) returns
      hardcoded zeros. The tool description promises
      "cost savings, cache hit rates, and workflow
      performance."
    </existing-code>
    <existing-code path="src/attune/telemetry/">
      Check if UsageTracker or FeedbackLoop has real
      data to expose.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="_get_telemetry_stats">
        Option A: Wire to real telemetry:
          from attune.telemetry import UsageTracker
          tracker = UsageTracker()
          return tracker.get_stats(days=args.get("days", 30))

        Option B: If no real data available, remove tool
        from _register_tools and _tool_handlers. Update
        tool count test.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>If kept: returned data is non-zero for a project
           with usage history</check>
    <check>If removed: tool count test updated, grep for
           "telemetry_stats" in _register_tools returns 0</check>
  </validation>

  <risks>
    <risk severity="low">
      If wiring to real telemetry, ensure the tracker
      handles missing data gracefully.
    </risk>
  </risks>
</task>
```

### Task 4.2 — Replace deprecated `get_event_loop()`

```xml
<task id="4.2" name="fix-get-event-loop">
  <objective>
    Replace asyncio.get_event_loop() with
    asyncio.get_running_loop() and hoist the loop
    reference out of the while loop.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Line 1034:
      line = await asyncio.get_event_loop().run_in_executor(
          None, sys.stdin.readline
      )
      Called on every iteration of the while True loop.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="main_loop (line 1024-1051)">
        BEFORE:
        async def main_loop():
            server = EmpathyMCPServer()
            while True:
                line = await asyncio.get_event_loop(
                ).run_in_executor(None, sys.stdin.readline)

        AFTER:
        async def main_loop():
            server = EmpathyMCPServer()
            loop = asyncio.get_running_loop()
            while True:
                line = await loop.run_in_executor(
                    None, sys.stdin.readline
                )
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "import ast; ast.parse(open(
           'src/attune/mcp/server.py').read())" succeeds</check>
    <check>grep "get_event_loop" server.py returns 0</check>
  </validation>

  <risks>
    <risk severity="low">
      get_running_loop() raises RuntimeError if no loop
      is running. Since main_loop() is called via
      asyncio.run(), a loop is always running.
    </risk>
  </risks>
</task>
```

### Task 4.3 — Replace hardcoded `/tmp` path

```xml
<task id="4.3" name="fix-tmp-path">
  <objective>
    Replace hardcoded /tmp/attune-mcp.log with a path
    derived from tempfile.gettempdir(), per the project's
    own CLAUDE.md lesson about Bandit B108.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Line 1069:
      handlers=[logging.FileHandler(
          "/tmp/attune-mcp.log"
      )],  # nosec B108
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="main (line 1064-1070)">
        BEFORE:
        handlers=[logging.FileHandler(
            "/tmp/attune-mcp.log"
        )],  # nosec B108

        AFTER:
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / "attune"
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / "attune-mcp.log"
        ...
        handlers=[logging.FileHandler(str(log_path))],
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep "nosec B108" server.py returns 0</check>
    <check>bandit -r src/attune/mcp/server.py reports no
           B108 findings</check>
  </validation>

  <risks>
    <risk severity="low">
      tempfile.gettempdir() returns platform-appropriate
      temp dir. mkdir(exist_ok=True) is safe.
    </risk>
  </risks>
</task>
```

### Task 4.4 — Remove redundant `auto_discover()` call

```xml
<task id="4.4" name="remove-redundant-autodiscover">
  <objective>
    Remove the redundant registry.auto_discover() call
    in _register_plugin_tools() since get_global_registry()
    already calls it.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Line 57-58:
      registry = get_global_registry()  # calls auto_discover
      registry.auto_discover()          # redundant
    </existing-code>
    <existing-code path="src/attune/plugins/registry.py">
      get_global_registry() at line 293 calls
      registry.auto_discover() before returning.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="line 58">
        BEFORE: registry.auto_discover()
        AFTER:  (delete line)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/test_mcp_memory_tools.py passes</check>
    <check>Plugin tools still register correctly</check>
  </validation>

  <risks>
    <risk severity="low">
      No-op removal. auto_discover is idempotent anyway.
    </risk>
  </risks>
</task>
```

---

## Phase 5: Quality Improvements (Items 11, 15, 16)

Lower priority, targeted improvements.

### Task 5.1 — Improve memory search fallback

```xml
<task id="5.1" name="fix-memory-search-fallback">
  <objective>
    Improve the search fallback in memory_handlers.py to
    search specific fields instead of str(p), and cache
    query.lower() outside the comprehension.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/memory_handlers.py">
      Lines 164-174: Falls back to list_patterns() with
      str(p).lower() matching — crude and slow.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/memory_handlers.py">
      <change location="lines 164-174">
        BEFORE:
        results = [
            p for p in all_patterns
            if query.lower() in str(p).lower()
            and (pattern_type is None
                 or p.get("pattern_type") == pattern_type)
        ]

        AFTER:
        query_lower = query.lower()
        results = [
            p for p in all_patterns
            if (
                query_lower in p.get("content", "").lower()
                or query_lower in p.get("pattern_type", "").lower()
                or query_lower in p.get("key", "").lower()
            )
            and (pattern_type is None
                 or p.get("pattern_type") == pattern_type)
        ]
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/mcp/handlers/test_memory_handlers.py
           passes</check>
    <check>Search still finds patterns by content, type, key</check>
  </validation>

  <risks>
    <risk severity="medium">
      If patterns have fields not covered by content/
      pattern_type/key, searches may miss them. Check
      actual pattern schema before finalizing field list.
    </risk>
  </risks>
</task>
```

### Task 5.2 — Move version check to background

```xml
<task id="5.2" name="background-version-check">
  <objective>
    Move the synchronous PyPI version check out of
    __init__ so it doesn't block server startup by up
    to 2 seconds on cold start.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Lines 37-42: check_for_updates() is called
      synchronously in __init__. It uses
      urllib.request.urlopen with a 2s timeout.
    </existing-code>
    <existing-code path="src/attune/mcp/version_check.py">
      check_for_updates() is synchronous. Has module-level
      _cached_status so it only runs once per process.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      <change location="__init__ lines 37-42">
        BEFORE:
        try:
            from .version_check import check_for_updates
            check_for_updates()
        except Exception:
            pass

        AFTER:
        # Defer version check to avoid blocking init
        # It will run on first call or in background
        try:
            import threading
            from .version_check import check_for_updates
            threading.Thread(
                target=check_for_updates,
                daemon=True,
            ).start()
        except Exception:  # noqa: BLE001
            pass  # INTENTIONAL: Version check is best-effort
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Server starts without delay even when PyPI
           is unreachable</check>
    <check>get_update_status() still returns cached result
           after thread completes</check>
  </validation>

  <risks>
    <risk severity="low">
      Thread is daemon=True so it won't prevent exit.
      Module-level _cached_status is thread-safe for
      simple assignment.
    </risk>
  </risks>
</task>
```

### Task 5.3 — Document mixin protocol

```xml
<task id="5.3" name="document-mixin-protocol">
  <objective>
    Add type-hinted protocol attributes to the mixin
    classes so that missing attributes are caught by
    static analysis rather than at runtime.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/memory_handlers.py">
      MemoryHandlersMixin accesses self._memory but
      only documents it in a docstring. No type hint.
    </existing-code>
    <existing-code path="src/attune/mcp/workflow_handlers.py">
      WorkflowHandlersMixin has no documented dependencies
      on host class attributes.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/memory_handlers.py">
      <change location="class MemoryHandlersMixin (line 14)">
        Add typed class-level declarations:
        class MemoryHandlersMixin:
            _memory: Any  # Set by host __init__
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>mypy src/attune/mcp/memory_handlers.py passes
           (or shows no new errors)</check>
  </validation>

  <risks>
    <risk severity="low">
      Type annotations only, no runtime behavior change.
    </risk>
  </risks>
</task>
```

---

## Execution Order

```text
Phase 1 (Items 1-2): Dead code removal
  Task 1.1  Consolidate handlers/ into mixins
  Task 1.2  Delete request_handler.py
  Commit + run full test suite

Phase 2 (Items 4, 5, 9, 12): Constants and annotations
  Task 2.1  Extract level_names constant
  Task 2.2  Deduplicate tool name field
  Task 2.3  Add BLE001 annotations
  Task 2.4  Extract memory error message constant
  Commit + run full test suite

Phase 3 (Items 3, 6, 7): Structural refactoring
  Task 3.1  Dict dispatch for call_tool
  Task 3.2  Tool schema factory
  Task 3.3  Normalize result extraction
  Commit + run full test suite

Phase 4 (Items 8, 10, 13, 14): Functional fixes
  Task 4.1  Fix or remove telemetry stub
  Task 4.2  Replace deprecated get_event_loop
  Task 4.3  Replace hardcoded /tmp path
  Task 4.4  Remove redundant auto_discover
  Commit + run full test suite

Phase 5 (Items 11, 15, 16): Quality improvements
  Task 5.1  Improve memory search fallback
  Task 5.2  Move version check to background
  Task 5.3  Document mixin protocol
  Commit + run full test suite
```

---

## Item-to-Task Mapping

| Item | Description | Task |
|------|-------------|------|
| 1 | Dead handlers/ directory | 1.1 |
| 2 | Dead request_handler.py | 1.2 |
| 3 | Stringly-typed dispatch | 3.1 |
| 4 | Duplicated level_names | 2.1 |
| 5 | Redundant name field | 2.2 |
| 6 | Tool schema boilerplate | 3.2 |
| 7 | Inconsistent result extraction | 3.3 |
| 8 | Telemetry stub | 4.1 |
| 9 | Missing BLE001 annotations | 2.3 |
| 10 | Deprecated get_event_loop | 4.2 |
| 11 | Crude memory search fallback | 5.1 |
| 12 | Repeated error message | 2.4 |
| 13 | Hardcoded /tmp path | 4.3 |
| 14 | Redundant auto_discover | 4.4 |
| 15 | Blocking version check | 5.2 |
| 16 | Mixin protocol not enforced | 5.3 |

---

## Risk Summary

| Phase | Risk Level | Mitigation |
|-------|-----------|------------|
| 1 | Medium | Test rewrites need careful coverage comparison |
| 2 | Low | Mechanical changes, no logic |
| 3 | Medium | Snapshot tool list JSON before/after; normalize handler signatures |
| 4 | Low | Targeted fixes with clear validation |
| 5 | Low-Medium | Search field list needs schema verification |
