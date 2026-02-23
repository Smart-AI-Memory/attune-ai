# XML-Enhanced Implementation Prompts

Detailed prompts for implementing the Claude Code integration tasks.
Each prompt is self-contained and can be given to Claude Code to execute.

**Priority Order:**

1. Task 1.1 — Hub command skills
2. Task 1.2 — Hook wiring
3. Task 2.1 — Security guard
4. Task 1.3 — CLAUDE.md update
5. Task 4.3 — Learning pipeline

---

## Task 1.1: Create Hub Command Skills

```xml
<task id="1.1" name="create-hub-command-skills">
  <objective>
    Create 7 hub command markdown files that make /dev, /testing, /workflows,
    /plan, /docs, /release, and /agent usable as Claude Code slash commands.
  </objective>

  <context>
    <existing-template path="src/attune/commands/attune.md">
      Uses YAML frontmatter with: name, description, category, aliases, tags,
      version, and a question block with header/question/options.
      Body has markdown docs, a shortcuts table, and a CRITICAL section with
      routing tables that map inputs to CLI commands.
    </existing-template>
    <setup-mechanism>
      cmd_setup() in src/attune/cli_minimal.py iterates all .md files in
      src/attune/commands/ via source_dir.iterdir() and copies them to
      ~/.claude/commands/. No code changes needed — just add .md files.
    </setup-mechanism>
    <cli-reference>
      uv run attune workflow run security-audit --path &lt;target&gt;
      uv run attune workflow run perf-audit --path &lt;target&gt;
      uv run attune workflow run bug-predict --path &lt;target&gt;
      uv run attune workflow run code-review --path &lt;target&gt;
      uv run attune workflow run test-gen --path &lt;target&gt;
      uv run attune workflow run test-gen-behavioral --path &lt;target&gt;
      uv run attune workflow run release-prep
      uv run pytest
      uv run pytest --cov=src --cov-report=term-missing
    </cli-reference>
  </context>

  <files-to-create>
    <file path="src/attune/commands/dev.md">
      <frontmatter>
        name: dev
        description: Developer tools — debug, commit, PR, code review, refactoring
        category: hub
        aliases: [developer, d]
        tags: [development, debug, commit, review, refactor]
        version: "1.0.0"
        question:
          header: "Developer Tools"
          question: "What do you need to do?"
          options:
            - label: "Debug an issue"
              description: "Investigate errors, trace execution, find root causes"
            - label: "Review code"
              description: "Quality analysis, security review, performance review"
            - label: "Commit changes"
              description: "Stage, commit with conventional commit message"
            - label: "Create a PR"
              description: "Push branch, create pull request with description"
      </frontmatter>
      <routing-table>
        /dev debug     → Start interactive debugging: read error, trace code, identify root cause
        /dev review    → uv run attune workflow run code-review --path &lt;target&gt;
        /dev commit    → Use git to stage and commit with conventional commit format
        /dev pr        → Use gh to create a pull request with summary and test plan
        /dev refactor  → Analyze code structure, suggest and apply refactoring
        /dev quality   → uv run attune workflow run bug-predict --path &lt;target&gt;
      </routing-table>
      <natural-language-routing>
        "debug", "fix", "error", "bug", "trace"   → debugging session
        "review", "quality", "analyze"             → code-review workflow
        "commit", "save", "stage"                  → git commit flow
        "pr", "pull request", "merge"              → gh pr create flow
        "refactor", "clean up", "simplify"         → refactoring session
      </natural-language-routing>
    </file>

    <file path="src/attune/commands/testing.md">
      <frontmatter>
        name: testing
        description: Test runner, coverage analysis, and test generation
        category: hub
        aliases: [test, t]
        tags: [testing, coverage, generation, pytest]
        version: "1.0.0"
        question:
          header: "Testing Hub"
          question: "What testing task do you need?"
          options:
            - label: "Run tests"
              description: "Execute pytest test suite"
            - label: "Check coverage"
              description: "Run tests with coverage report"
            - label: "Generate tests"
              description: "Auto-generate behavioral tests for a module"
      </frontmatter>
      <routing-table>
        /testing run              → uv run pytest -v
        /testing run &lt;path&gt;      → uv run pytest &lt;path&gt; -v
        /testing coverage         → uv run pytest --cov=src --cov-report=term-missing
        /testing coverage &lt;tgt&gt;  → uv run pytest --cov=&lt;tgt&gt; --cov-report=term-missing
        /testing generate &lt;mod&gt;  → uv run attune workflow run test-gen-behavioral --path &lt;mod&gt;
        /testing generate batch   → uv run attune workflow run test-gen-behavioral --batch
      </routing-table>
      <natural-language-routing>
        "run tests", "pytest", "test suite"      → pytest execution
        "coverage", "how much is covered"        → pytest --cov
        "generate tests", "write tests for"      → test-gen-behavioral workflow
      </natural-language-routing>
    </file>

    <file path="src/attune/commands/workflows.md">
      <frontmatter>
        name: workflows
        description: Automated analysis — security audit, bug prediction, performance
        category: hub
        aliases: [wf, workflow]
        tags: [security, bugs, performance, audit, analysis]
        version: "1.0.0"
        question:
          header: "Analysis Workflows"
          question: "What would you like to analyze?"
          options:
            - label: "Security audit"
              description: "Scan for vulnerabilities: eval, path traversal, secrets"
            - label: "Bug prediction"
              description: "Detect patterns likely to produce bugs"
            - label: "Performance audit"
              description: "Find bottlenecks and optimization opportunities"
            - label: "Code review"
              description: "Comprehensive quality and style analysis"
      </frontmatter>
      <routing-table>
        /workflows security       → uv run attune workflow run security-audit
        /workflows security &lt;p&gt; → uv run attune workflow run security-audit --path &lt;p&gt;
        /workflows bugs           → uv run attune workflow run bug-predict
        /workflows bugs &lt;path&gt;  → uv run attune workflow run bug-predict --path &lt;path&gt;
        /workflows perf           → uv run attune workflow run perf-audit
        /workflows perf &lt;path&gt;  → uv run attune workflow run perf-audit --path &lt;path&gt;
        /workflows review &lt;p&gt;   → uv run attune workflow run code-review --path &lt;p&gt;
        /workflows list           → uv run attune workflow list
      </routing-table>
      <natural-language-routing>
        "security", "vulnerabilities", "cwe"      → security-audit
        "bugs", "predict", "risky code"           → bug-predict
        "performance", "slow", "bottleneck"       → perf-audit
        "review", "quality"                       → code-review
        "list", "available", "what workflows"     → workflow list
      </natural-language-routing>
    </file>

    <file path="src/attune/commands/plan.md">
      <frontmatter>
        name: plan
        description: Planning, architecture, and refactoring strategies
        category: hub
        aliases: [planning, p]
        tags: [planning, architecture, strategy, refactoring]
        version: "1.0.0"
        question:
          header: "Planning Hub"
          question: "What do you need to plan?"
          options:
            - label: "Plan a feature"
              description: "Break down a feature into implementation steps"
            - label: "Refactoring strategy"
              description: "Plan safe incremental refactoring steps"
            - label: "Architecture review"
              description: "Evaluate and plan architectural changes"
      </frontmatter>
      <instructions>
        This hub is ADVISORY — it helps the user think through plans
        before executing. Use extended thinking for complex analysis.
        Output structured plans with numbered steps, file lists,
        risk assessments, and dependency graphs.
      </instructions>
      <routing-table>
        /plan feature &lt;desc&gt;   → Break feature into tasks with files, deps, risks
        /plan refactor &lt;path&gt;  → Analyze code, plan incremental refactoring steps
        /plan architecture     → Evaluate current architecture, propose improvements
        /plan review &lt;path&gt;    → uv run attune workflow run code-review --path &lt;path&gt;
      </routing-table>
    </file>

    <file path="src/attune/commands/docs.md">
      <frontmatter>
        name: docs
        description: Documentation generation and management
        category: hub
        aliases: [doc, documentation]
        tags: [documentation, readme, api-docs, changelog]
        version: "1.0.0"
        question:
          header: "Documentation Hub"
          question: "What documentation do you need?"
          options:
            - label: "Generate API docs"
              description: "Create docstrings and API reference for a module"
            - label: "Update README"
              description: "Update or generate README.md"
            - label: "Update CHANGELOG"
              description: "Add entries to CHANGELOG.md for recent changes"
            - label: "Explain code"
              description: "Generate human-readable explanation of code"
      </frontmatter>
      <routing-table>
        /docs generate &lt;path&gt;  → Generate/update docstrings for module at path
        /docs readme            → Read current README.md, suggest improvements
        /docs changelog         → Read recent git log, draft CHANGELOG entries
        /docs explain &lt;path&gt;   → Read code at path and produce explanation
        /docs architecture      → Generate architecture overview from codebase
      </routing-table>
    </file>

    <file path="src/attune/commands/release.md">
      <frontmatter>
        name: release
        description: Release preparation, security scanning, and publishing
        category: hub
        aliases: [ship, publish]
        tags: [release, publish, version, changelog, security]
        version: "1.0.0"
        question:
          header: "Release Hub"
          question: "What release task do you need?"
          options:
            - label: "Prepare release"
              description: "Version bump, changelog, pre-flight checks"
            - label: "Security scan"
              description: "Pre-release security audit"
            - label: "Health check"
              description: "Test suite, coverage, lint — full project health"
            - label: "Publish"
              description: "Build and publish to PyPI"
      </frontmatter>
      <routing-table>
        /release prep           → uv run attune workflow run release-prep
        /release security       → uv run attune workflow run security-audit
        /release health         → Run pytest + coverage + ruff + bandit, report results
        /release publish        → uv run python -m build &amp;&amp; uv run twine upload dist/*
        /release version &lt;v&gt;   → Update version in pyproject.toml and __init__.py
      </routing-table>
      <pre-release-checklist>
        1. All tests passing (pytest)
        2. Coverage above 80% (pytest --cov)
        3. No security issues (security-audit)
        4. No lint warnings (ruff check src/)
        5. CHANGELOG.md updated
        6. Version bumped in pyproject.toml
      </pre-release-checklist>
    </file>

    <file path="src/attune/commands/agent.md">
      <frontmatter>
        name: agent
        description: Create and manage custom AI agents
        category: hub
        aliases: [agents]
        tags: [agent, custom, multi-agent, orchestration]
        version: "1.0.0"
        question:
          header: "Agent Hub"
          question: "What would you like to do with agents?"
          options:
            - label: "Create a new agent"
              description: "Define a new specialized agent with role and tools"
            - label: "List agents"
              description: "Show all available agents and their capabilities"
            - label: "Run agent team"
              description: "Execute a multi-agent collaboration"
            - label: "Healthcare CDS"
              description: "Run the clinical decision support agent team"
      </frontmatter>
      <routing-table>
        /agent create &lt;name&gt;   → Guide user through agent definition (role, tools, model)
        /agent list             → List agents in src/attune/agents/ with descriptions
        /agent run &lt;name&gt;      → Execute agent or agent team
        /agent cds              → Run healthcare CDS multi-agent system
      </routing-table>
    </file>
  </files-to-create>

  <implementation-instructions>
    For each file above:
    1. Create the YAML frontmatter exactly as specified
    2. Write the markdown body following the attune.md template structure:
       - Title and one-line description
       - Quick Shortcuts table
       - "CRITICAL: Workflow Execution Instructions" section
       - Shortcut Routing table (Input → CLI Command)
       - Natural Language Routing table (Pattern → CLI Command)
       - IMPORTANT reminder to EXECUTE, not just display docs
    3. Ensure consistent formatting across all 7 files
    4. DO NOT modify cmd_setup — it already discovers all .md files automatically
  </implementation-instructions>

  <validation>
    <check>Each .md file has valid YAML frontmatter (parseable)</check>
    <check>Each file has a routing table with at least 4 entries</check>
    <check>Each file has the CRITICAL execution instructions section</check>
    <check>Running `attune setup` installs all 8 files to ~/.claude/commands/</check>
    <check>No duplicate aliases across command files</check>
  </validation>
</task>
```

---

## Task 1.2: Wire Hook Scripts to Claude Code

```xml
<task id="1.2" name="wire-hook-scripts">
  <objective>
    Register existing hook scripts as Claude Code lifecycle hooks by creating
    .claude/settings.json with hook definitions, and adapt the scripts to
    read context from stdin (Claude Code's hook protocol).
  </objective>

  <context>
    <existing-scripts location="attune_llm/hooks/scripts/">
      session_start.py  — Loads previous context and learned patterns
      session_end.py    — Saves session state
      pre_compact.py    — Prepares for context compaction
      evaluate_session.py — Evaluates session learning value
      suggest_compact.py  — Suggests memory compaction
      first_time_init.py  — Initial setup on first run
    </existing-scripts>
    <current-interface>
      Each script has: def main(**context) -> dict[str, Any]
      And a __main__ block that calls main() with no args and prints JSON.
      They do NOT currently read from stdin.
    </current-interface>
    <claude-code-hook-protocol>
      Claude Code passes hook context as JSON on stdin.
      Hook scripts must:
        - Read JSON from stdin (may be empty/absent)
        - Perform their work
        - Print JSON result to stdout
        - Exit 0 (success), 1 (error), or 2 (block tool call, PreToolUse only)
      Hook types: SessionStart, Stop, PreToolUse, PostToolUse, PreCompact
    </claude-code-hook-protocol>
    <existing-settings path=".claude/settings.local.json">
      Contains only: {"permissions": {"allow": ["Bash(uv run pytest:*)","Bash(pytest:*)"]}}
      There is NO .claude/settings.json yet (project-level).
    </existing-settings>
  </context>

  <approach>
    PROTOTYPE FIRST: Start with session_start.py only.
    Validate the stdin contract works with Claude Code before adapting all 6.
  </approach>

  <files-to-create>
    <file path=".claude/settings.json">
      <content-spec>
        JSON file with "hooks" key. Start with ONE hook (SessionStart) to
        validate the integration pattern. Add more after confirming it works.
      </content-spec>
      <structure>
        {
          "hooks": {
            "SessionStart": [
              {
                "type": "command",
                "command": "python -m attune_llm.hooks.scripts.session_start",
                "timeout": 10000
              }
            ]
          }
        }
      </structure>
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="attune_llm/hooks/scripts/session_start.py">
      <change location="__main__ block (line 158-163)">
        Replace the current __main__ block with one that reads JSON from
        stdin when available, passing it as context to main().

        BEFORE:
          if __name__ == "__main__":
              logging.basicConfig(level=logging.INFO, format="%(message)s")
              result = main()
              print(json.dumps(result, indent=2))

        AFTER:
          if __name__ == "__main__":
              import sys
              logging.basicConfig(level=logging.INFO, format="%(message)s")
              context = {}
              if not sys.stdin.isatty():
                  try:
                      raw = sys.stdin.read().strip()
                      if raw:
                          context = json.loads(raw)
                  except (json.JSONDecodeError, ValueError):
                      pass
              result = main(**context)
              print(json.dumps(result, indent=2))
      </change>
    </file>
  </files-to-modify>

  <implementation-instructions>
    1. Create .claude/settings.json with ONLY the SessionStart hook
    2. Modify session_start.py __main__ block to read stdin
    3. Test manually:
       echo '{"session_id":"test123"}' | python -m attune_llm.hooks.scripts.session_start
       python -m attune_llm.hooks.scripts.session_start < /dev/null
    4. Both should exit 0 and print valid JSON
    5. ONLY after confirming this works, add remaining hooks:
       - Stop → session_end.py
       - PreCompact → pre_compact.py
    6. Apply the same stdin-reading pattern to each adapted script
  </implementation-instructions>

  <validation>
    <check>echo '{}' | python -m attune_llm.hooks.scripts.session_start exits 0</check>
    <check>python -m attune_llm.hooks.scripts.session_start &lt; /dev/null exits 0</check>
    <check>Output is valid JSON with "initialized": true</check>
    <check>.claude/settings.json is valid JSON</check>
    <check>.claude/settings.local.json is NOT modified (separate file)</check>
  </validation>

  <risks>
    <risk severity="medium">
      Claude Code may pass different JSON shapes for different hook types.
      The stdin reading must be defensive — never crash on unexpected input.
    </risk>
    <risk severity="low">
      Hook timeout of 10s may be tight if loading many pattern files.
      Monitor and increase if needed.
    </risk>
  </risks>
</task>
```

---

## Task 2.1: PreToolUse Security Guard

```xml
<task id="2.1" name="pretooluse-security-guard">
  <objective>
    Create a PreToolUse hook that intercepts Bash, Edit, and Write tool calls
    to enforce the project's security policies at runtime — blocking eval/exec
    in commands and writes to system directories BEFORE they execute.
  </objective>

  <context>
    <security-policies source=".claude/rules/attune/coding-standards-index.md">
      CRITICAL rules to enforce:
      1. NEVER use eval() or exec() — CWE-95
      2. NEVER write to /etc, /sys, /proc, /dev — CWE-22
      3. No null bytes in file paths
      4. No shell=True with user-controlled input — B602
    </security-policies>
    <claude-code-pretooluse-protocol>
      PreToolUse hooks receive JSON on stdin:
        {"tool_name": "Bash", "tool_input": {"command": "..."}}
        {"tool_name": "Edit", "tool_input": {"file_path": "...", ...}}
        {"tool_name": "Write", "tool_input": {"file_path": "...", ...}}

      Exit codes:
        0 = allow the tool call to proceed
        2 = BLOCK the tool call (Claude Code will not execute it)

      Blocked message: print reason to stderr before exit(2)
    </claude-code-pretooluse-protocol>
  </context>

  <file-to-create path="attune_llm/hooks/scripts/security_guard.py">
    <module-docstring>
      PreToolUse Security Validation Hook.

      Intercepts tool calls to enforce coding standards:
      1. Blocks eval()/exec() in Bash commands
      2. Validates file paths in Edit/Write operations
      3. Prevents writes to system directories
      4. Blocks null byte injection in paths

      Exit codes:
        0 = allow tool call
        2 = block tool call (Claude Code convention)
    </module-docstring>

    <dangerous-bash-patterns>
      \beval\s*\(          — Python eval() call
      \bexec\s*\(          — Python exec() call
      __import__\s*\(      — Dynamic import (code injection vector)
      subprocess\.call.*shell\s*=\s*True  — Shell injection risk
      rm\s+-rf\s+/         — Recursive delete from root
    </dangerous-bash-patterns>

    <allowlist-for-bash>
      Patterns that look dangerous but are safe:
      - "eval" appearing inside grep/rg patterns (searching for violations)
      - "eval" in string literals being written to test files
      - "exec" as part of ".exec()" (JavaScript regex method)
      Detection: if the command is grep/rg/Grep searching FOR eval, allow it
    </allowlist-for-bash>

    <system-directories>
      /etc, /sys, /proc, /dev, /boot, /sbin, /usr/sbin
    </system-directories>

    <functions>
      <function name="validate_bash_command" args="command: str" returns="tuple[bool, str]">
        Check command string against dangerous patterns.
        Apply allowlist for grep/search commands.
        Return (True, "") if safe, (False, "reason") if blocked.
      </function>

      <function name="validate_file_path" args="path: str" returns="tuple[bool, str]">
        Check for null bytes.
        Resolve path and check against system directories.
        Return (True, "") if safe, (False, "reason") if blocked.
      </function>

      <function name="main" args="context: dict" returns="dict">
        Read tool_name and tool_input from context.
        Dispatch to validate_bash_command or validate_file_path.
        Return {"allowed": True} or {"allowed": False, "reason": "..."}.
      </function>
    </functions>

    <main-block>
      Read JSON from stdin (same pattern as Task 1.2).
      Call main(context).
      If not allowed: print reason to stderr, exit(2).
      If allowed: exit(0).
    </main-block>

    <user-facing-messages>
      DO NOT show raw regex in block messages. Use clear English:
        "Blocked: eval() is prohibited — use ast.literal_eval() instead (CWE-95)"
        "Blocked: exec() is prohibited — use safe alternatives (CWE-95)"
        "Blocked: cannot write to system directory /etc (CWE-22)"
        "Blocked: file path contains null bytes (CWE-22)"
        "Blocked: rm -rf / is not allowed"
    </user-facing-messages>
  </file-to-create>

  <settings-update path=".claude/settings.json">
    Add PreToolUse entry to the hooks section:
    {
      "hooks": {
        "SessionStart": [ ... existing ... ],
        "PreToolUse": [
          {
            "matcher": {"tool_name": "Bash|Edit|Write"},
            "type": "command",
            "command": "python -m attune_llm.hooks.scripts.security_guard",
            "timeout": 3000
          }
        ]
      }
    }
  </settings-update>

  <tests>
    <test name="test_blocks_eval_in_bash_command">
      Input: {"tool_name": "Bash", "tool_input": {"command": "python -c 'eval(input())'"}}
      Expected: exit code 2, stderr contains "eval()"
    </test>
    <test name="test_blocks_exec_in_bash_command">
      Input: {"tool_name": "Bash", "tool_input": {"command": "python -c 'exec(code)'"}}
      Expected: exit code 2, stderr contains "exec()"
    </test>
    <test name="test_allows_grep_for_eval">
      Input: {"tool_name": "Bash", "tool_input": {"command": "grep -r 'eval(' src/"}}
      Expected: exit code 0 (searching FOR eval is safe)
    </test>
    <test name="test_allows_safe_bash_commands">
      Input: {"tool_name": "Bash", "tool_input": {"command": "uv run pytest tests/ -v"}}
      Expected: exit code 0
    </test>
    <test name="test_blocks_system_directory_write">
      Input: {"tool_name": "Write", "tool_input": {"file_path": "/etc/passwd"}}
      Expected: exit code 2, stderr contains "/etc"
    </test>
    <test name="test_blocks_null_byte_path">
      Input: {"tool_name": "Edit", "tool_input": {"file_path": "config\x00.json"}}
      Expected: exit code 2, stderr contains "null"
    </test>
    <test name="test_allows_valid_project_file">
      Input: {"tool_name": "Write", "tool_input": {"file_path": "src/attune/config.py"}}
      Expected: exit code 0
    </test>
    <test name="test_handles_empty_stdin">
      Input: (empty stdin)
      Expected: exit code 0 (no tool info = allow by default)
    </test>
  </tests>
</task>
```

---

## Task 1.3: Update CLAUDE.md

```xml
<task id="1.3" name="update-claude-md">
  <objective>
    Update .claude/CLAUDE.md so the "Command Hubs" section accurately reflects
    the 7 hub commands created in Task 1.1, and add a "Hooks" section documenting
    the registered lifecycle hooks from Task 1.2.
  </objective>

  <dependencies>
    <dependency task="1.1">Hub command files must exist</dependency>
    <dependency task="1.2">Hook wiring must be done</dependency>
  </dependencies>

  <file-to-modify path=".claude/CLAUDE.md">
    <section name="Command Hubs" action="verify-and-update">
      Ensure the hub table lists all 8 commands (attune + 7 hubs) with
      accurate route descriptions matching the actual routing tables in
      each .md file. Remove any routes that don't exist.

      Expected table:
      | Hub | Key Routes |
      |-----|------------|
      | /attune   | Socratic discovery, natural language routing to all workflows |
      | /dev      | debug, review, commit, pr, refactor, quality |
      | /testing  | run, coverage, generate |
      | /workflows| security, bugs, perf, review, list |
      | /plan     | feature, refactor, architecture |
      | /docs     | generate, readme, changelog, explain |
      | /release  | prep, security, health, publish |
      | /agent    | create, list, run, cds |
    </section>

    <section name="Hooks" action="add-new">
      Add a new section after Command Hubs documenting the lifecycle hooks:

      ## Lifecycle Hooks

      Hooks run automatically during Claude Code lifecycle events:

      | Event | Script | Purpose |
      |-------|--------|---------|
      | SessionStart | session_start.py | Load previous patterns and session state |
      | Stop | session_end.py | Save session state for next session |
      | PreCompact | pre_compact.py | Prepare context before compaction |
      | PreToolUse | security_guard.py | Block eval/exec and system dir writes |
    </section>
  </file-to-modify>

  <validation>
    <check>Every hub listed in CLAUDE.md has a corresponding .md file in src/attune/commands/</check>
    <check>Every route listed in CLAUDE.md exists in the corresponding command file's routing table</check>
    <check>No markdown linting warnings (MD031, MD032, MD040)</check>
  </validation>
</task>
```

---

## Task 4.3: Learning Pipeline Integration

```xml
<task id="4.3" name="learning-pipeline">
  <objective>
    Wire the session evaluation into the Stop hook and inject learned patterns
    on SessionStart, creating a self-improving feedback loop where each session
    builds on previous learnings.
  </objective>

  <context>
    <existing-scripts>
      evaluate_session.py — Evaluates a session and extracts learnings:
        - Patterns detected (debugging strategies, code review techniques)
        - Skills demonstrated (refactoring, test writing)
        - Confidence levels per pattern
        Writes results to ~/.empathy/patterns/ and ~/.empathy/skills/learned/

      session_start.py — Already loads from:
        - ~/.empathy/sessions/*.json (session state)
        - ~/.empathy/patterns/*.json (pattern files)
        - ~/.empathy/skills/learned/*.md (learned skills)
        Returns counts but does NOT inject pattern content into session.
    </existing-scripts>
    <learning-flow>
      Session N ends:
        1. Stop hook fires → session_end.py saves state
        2. evaluate_session.py analyzes session, extracts patterns
        3. Patterns written to ~/.empathy/patterns/

      Session N+1 starts:
        1. SessionStart hook fires → session_start.py loads patterns
        2. Relevant patterns injected as context for new session
        3. Agent starts with accumulated knowledge
    </learning-flow>
  </context>

  <files-to-modify>
    <file path="attune_llm/hooks/scripts/session_end.py">
      <change>
        After saving session state, call evaluate_session.main() to extract
        learnings from the session. This chains evaluation into the Stop hook
        so it happens automatically.

        Add to the end of main():
          # Evaluate session for learning value
          try:
              from attune_llm.hooks.scripts.evaluate_session import main as evaluate
              eval_result = evaluate(**context)
              result["evaluation"] = eval_result
              if eval_result.get("patterns_extracted", 0) > 0:
                  result["messages"].append(
                      f"[Learning] Extracted {eval_result['patterns_extracted']} pattern(s)"
                  )
          except ImportError:
              logger.debug("evaluate_session not available")
          except Exception as e:
              logger.warning("Session evaluation failed: %s", e)
      </change>
    </file>

    <file path="attune_llm/hooks/scripts/session_start.py">
      <change>
        After counting patterns, actually READ and include the most relevant
        pattern content so it's available as session context.

        Add after the patterns counting block (around line 148):
          # Load recent pattern content for injection
          if pattern_files:
              injected_patterns = []
              for pf in pattern_files[:5]:  # Cap at 5 most recent
                  try:
                      with open(pf) as f:
                          pattern_data = json.load(f)
                      injected_patterns.append({
                          "source": pf.stem,
                          "patterns": pattern_data.get("patterns", []),
                          "confidence": pattern_data.get("confidence", 0.0),
                      })
                  except (json.JSONDecodeError, OSError) as e:
                      logger.debug("Skipping pattern file %s: %s", pf, e)
              if injected_patterns:
                  result["injected_patterns"] = injected_patterns
                  result["messages"].append(
                      f"[Learning] Injected {len(injected_patterns)} pattern set(s) from previous sessions"
                  )

          # Load learned skill summaries
          if learned_skills:
              skill_summaries = []
              for sf in learned_skills[:10]:  # Cap at 10
                  try:
                      content = sf.read_text()
                      # Extract just the first line (title/summary)
                      first_line = content.strip().split('\n')[0].lstrip('# ')
                      skill_summaries.append({"name": sf.stem, "summary": first_line})
                  except OSError:
                      pass
              if skill_summaries:
                  result["learned_skills"] = skill_summaries
      </change>
    </file>
  </files-to-modify>

  <settings-update path=".claude/settings.json">
    Add Stop hook alongside existing SessionStart:
    {
      "hooks": {
        "SessionStart": [ ... existing ... ],
        "Stop": [
          {
            "type": "command",
            "command": "python -m attune_llm.hooks.scripts.session_end",
            "timeout": 15000
          }
        ],
        "PreToolUse": [ ... existing ... ]
      }
    }
  </settings-update>

  <quality-control>
    <concern name="bad-pattern-accumulation">
      Without quality control, incorrect patterns could accumulate and degrade
      future sessions. Mitigations:
      1. evaluate_session.py should assign confidence scores (0.0-1.0)
      2. session_start.py should only inject patterns with confidence >= 0.7
      3. Patterns older than 30 days should be ignored
      4. Cap at 5 pattern files to prevent context bloat
    </concern>
    <concern name="storage-growth">
      Pattern files accumulate over time. Add cleanup:
      - Delete pattern files older than 90 days
      - Run cleanup in session_start.py (good time, runs once per session)
    </concern>
  </quality-control>

  <validation>
    <check>session_end.py calls evaluate_session and includes results</check>
    <check>session_start.py reads pattern content, not just counts</check>
    <check>Pattern injection is capped (max 5 files, max confidence threshold)</check>
    <check>Both scripts handle missing/corrupt files gracefully</check>
    <check>Stop hook is registered in .claude/settings.json</check>
    <check>Manual test: run session_end then session_start, verify patterns flow through</check>
  </validation>

  <test-sequence>
    <step>
      1. Run session_end with mock context:
         echo '{"session_id":"test1"}' | python -m attune_llm.hooks.scripts.session_end
         Verify: exits 0, output JSON has "evaluation" key
    </step>
    <step>
      2. Check that pattern file was created:
         ls ~/.empathy/patterns/
         Verify: at least one .json file exists
    </step>
    <step>
      3. Run session_start:
         echo '{}' | python -m attune_llm.hooks.scripts.session_start
         Verify: output JSON has "injected_patterns" key with content
    </step>
    <step>
      4. Verify the feedback loop:
         Patterns extracted in step 1 appear in step 3's output
    </step>
  </test-sequence>
</task>
```

---

## Task 2.2-2.4 and 4.1-4.4: Remaining Tasks

```xml
<task id="2.2" name="custom-subagent-definitions">
  <objective>
    Create subagent definition files for specialized tasks that can be
    spawned via the Task tool from hub commands.
  </objective>

  <files-to-create>
    <file path="src/attune/commands/agents/security-reviewer.md">
      <role>Read-only security analysis agent</role>
      <model>sonnet</model>
      <focus>
        Path traversal (CWE-22), code injection (CWE-95), bare except
        clauses, hardcoded secrets. Output as severity-sorted table.
      </focus>
      <tools>Read, Grep, Glob only — no write access</tools>
      <context-injection>
        Include content from .claude/rules/attune/coding-standards-index.md
        so the agent knows the project's specific security rules.
      </context-injection>
    </file>

    <file path="src/attune/commands/agents/test-writer.md">
      <role>Behavioral test generation agent</role>
      <model>sonnet</model>
      <focus>
        Generate pytest tests using Given/When/Then structure.
        Read source with _extract_api_surface pattern to get exact signatures.
        Write ONLY to tests/ directory.
      </focus>
      <tools>Read, Grep, Glob, Write (restricted to tests/), Bash (pytest only)</tools>
    </file>

    <file path="src/attune/commands/agents/doc-generator.md">
      <role>Documentation generation agent</role>
      <model>haiku</model>
      <focus>
        Generate and update docstrings, README sections, and API reference.
        Follow Google-style docstring format per project standards.
      </focus>
      <tools>Read, Grep, Glob, Edit, Write (restricted to docs/ and src/)</tools>
    </file>
  </files-to-create>
</task>

<task id="2.3" name="enhanced-setup-command">
  <objective>
    Extend attune setup to install hooks config and MCP config alongside
    command files, providing one-command setup for all Claude Code integration.
  </objective>

  <file-to-modify path="src/attune/cli_minimal.py" function="cmd_setup">
    <additions>
      After installing .md command files:
      1. Copy .claude/settings.json → project .claude/settings.json if not present
      2. Copy .claude/mcp.json → project .claude/mcp.json if not present
      3. NEVER overwrite existing files — print "Skipped: already exists"
      4. Print summary showing what was installed vs skipped
    </additions>
  </file-to-modify>
</task>

<task id="2.4" name="extended-thinking-in-skills">
  <objective>
    Add extended thinking directives to skills that benefit from deep
    reasoning: security audits, architecture planning, release readiness.
  </objective>

  <approach>
    Add a "## Reasoning Approach" section to workflows.md, plan.md, and
    release.md that instructs the LLM to think step-by-step for complex
    analysis. Use XML tags like &lt;analysis-steps&gt; to structure the
    thinking process.
  </approach>
</task>

<task id="4.1" name="mcp-prompts">
  <objective>
    Add MCP prompts to the MCP server so they appear as auto-discovered
    commands in Claude Code.
  </objective>

  <note>
    Only implement AFTER confirming skills (Task 1.1) don't already cover
    the use case. Use MCP prompts for PROGRAMMATIC tools (security-scan,
    test-gen, cost-report) not interactive hubs.
  </note>

  <file-to-modify path="src/attune/mcp/server.py">
    Add prompts:
      security-scan: Run security audit on a path (arg: path)
      test-gen: Generate tests for a module (arg: module, style)
      cost-report: Show cost savings report (arg: days)
  </file-to-modify>
</task>

<task id="4.2" name="agent-team-orchestration">
  <objective>
    Create /deep-review skill that orchestrates security-reviewer,
    code-review, and test-gap-analysis subagents in parallel, then
    synthesizes findings into a single prioritized report.
  </objective>

  <dependencies>
    <dependency task="2.2">Subagent definitions must exist</dependency>
  </dependencies>

  <process>
    1. Spawn security-reviewer subagent (read-only)
    2. Run code-review workflow (via CLI)
    3. Run pytest --cov and parse uncovered lines
    4. Combine all findings into severity-sorted report
  </process>
</task>

<task id="4.4" name="dynamic-context-in-skills">
  <objective>
    Inject fresh project state (git status, test results, version) into
    hub skills on invocation.
  </objective>

  <approach>
    Skills are static markdown — they cannot execute commands during expansion.
    Instead, add instructions in each skill's CRITICAL section telling the
    LLM to run context-gathering commands FIRST before proceeding:

    "Before executing any action, gather current context:
     1. Run: git status --short
     2. Run: git log --oneline -5
     3. Run: git branch --show-current
     Then proceed with the requested action using this context."
  </approach>
</task>
```
