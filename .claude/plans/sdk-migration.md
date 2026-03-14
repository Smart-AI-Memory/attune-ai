# SDK-First Migration: Attune AI as Agents SDK Reference

**Created:** 2026-03-12
**Source:** /brainstorm session
**Status:** Planning

## Problem

Attune AI uses the Agents SDK superficially — calling
`query()` in 13 workflow variants while maintaining unused
custom scaffolding (`SDKAgent`, `SDKAgentTeam`). The SDK's
best features (subagents, hooks, sessions, resume) go
unused. Dual implementations (base + SDK variant) create
maintenance burden.

## Goals

- **Must-have:** All 18 workflows run on native SDK
  execution with no custom agent scaffolding
- **Must-have:** `claude-agent-sdk` becomes a core
  dependency (not optional extra)
- **Must-have:** Orchestration layer preserved (cost
  routing, quality gates, state, coordination)
- **Must-have:** Developed on dedicated fork(s), nothing
  breaks on `main`
- **Must-have:** Each phase produces a publishable
  tutorial for the Claude developer community
- **Nice-to-have:** Unlock new SDK features (sessions,
  hooks, subagent delegation) that improve UX
- **Nice-to-have:** Reduce total workflow file count
  (merge dual implementations)

## End State

Attune AI is both a production developer tool AND a
reference implementation that teaches the Claude developer
community how to build with the Agents SDK. Every workflow
uses the SDK natively. The custom scaffolding is gone. New
SDK features (sessions, hooks, subagents) are used where
they genuinely improve the experience.

## Approach

### Phase 0: Foundation (Fork + Dependency)

**Branch:** `feature/sdk-migration-foundation`

1. Create GitHub fork for development
2. Move `claude-agent-sdk` from optional extra to core
   dependency in `pyproject.toml`
3. Remove `[agent-sdk]` extra from all docs, README,
   install instructions
4. Remove all `_SDK_AVAILABLE` runtime guards and
   `try/except ImportError` patterns across the codebase
5. Remove the auto-routing system (`_SDK_WORKFLOW_MAP`,
   `_SDK_REVERSE_MAP`) — no more base-vs-SDK switching
6. Run full test suite, fix any breakage
7. Update CI to always install `claude-agent-sdk`

**Tutorial:** "Setting Up the Agents SDK as a Core
Dependency" — how to structure a project that builds on
the SDK from day one.

**Prune list:**
- `src/attune/agents/sdk/sdk_agent.py` (unused class)
- `src/attune/agents/sdk/sdk_team.py` (unused class)
- `src/attune/agents/sdk/adapters.py` (SDKToolsMixin,
  unused)
- All `_SDK_AVAILABLE` guard blocks across 13+ files
- `_SDK_WORKFLOW_MAP` and `_SDK_REVERSE_MAP` in
  `workflows/__init__.py`
- The `[agent-sdk]` optional extra in `pyproject.toml`

---

### Phase 1: Single Workflow Migration (Proof of Pattern)

**Branch:** `feature/sdk-migration-code-review`

Pick `code-review` as the pilot — it has 4 subagents
(security, quality, perf, architect) which maps perfectly
to SDK subagent delegation.

1. Merge `code_review.py` and `code_review_agent_sdk.py`
   into a single `code_review.py` that uses SDK natively
2. Replace manual `query()` calls with proper SDK
   subagent definitions (`AgentDefinition`)
3. Wire in SDK hooks for quality gate checks
   (`PostToolUse` to validate outputs)
4. Preserve the orchestration layer on top (cost routing
   via model selection per subagent, quality gate
   thresholds)
5. Add SDK session support — allow resuming a review
6. Full test coverage for the new implementation
7. Delete `code_review_agent_sdk.py`

**Tutorial:** "Building a Multi-Agent Code Review with
the Claude Agents SDK" — subagent delegation, specialized
roles, combining results.

**SDK features demonstrated:**
- `query()` with subagents
- `AgentDefinition` for specialized agents
- Model selection per subagent (cost routing)
- Streaming results

---

### Phase 2: Hooks & Lifecycle (3 workflows)

**Branch:** `feature/sdk-migration-hooks`

Migrate `security-audit`, `bug-predict`, and `perf-audit`
— these benefit most from SDK hooks.

1. Merge each base + SDK variant into single
   implementation
2. Use `PreToolUse` hooks for input validation (e.g.,
   block `eval()` in generated code)
3. Use `PostToolUse` hooks for output quality checks
   (severity scoring, false positive filtering)
4. Use `Stop` hooks for final report generation
5. Wire orchestration layer for tier escalation
6. Delete 3 `*_agent_sdk.py` files

**Tutorial:** "Agent Lifecycle Hooks — Validation,
Quality Gates, and Safety" — how hooks replace custom
middleware.

**SDK features demonstrated:**
- `PreToolUse` / `PostToolUse` hooks
- `HookMatcher` for pattern-based tool filtering
- Stop hooks for cleanup/reporting

---

### Phase 3: Sessions & Resume (3 workflows)

**Branch:** `feature/sdk-migration-sessions`

Migrate `test-gen`, `doc-gen`, and `doc-audit` — these
benefit from session continuity (generate tests, review
results, iterate).

1. Merge each base + SDK variant
2. Implement session capture (`session_id` from init
   message)
3. Add resume capability — user can continue a test
   generation session where they left off
4. Store session IDs in `AgentStateStore` for recovery
5. Delete 3 `*_agent_sdk.py` files

**Tutorial:** "Persistent Agent Sessions — Resume Where
You Left Off" — session management, state recovery,
iterative workflows.

**SDK features demonstrated:**
- Session capture and `resume` parameter
- Iterative agent workflows
- State persistence across invocations

---

### Phase 4: Batch Migration (7 remaining workflows)

**Branch:** `feature/sdk-migration-batch`

Migrate the remaining 7 workflows using the patterns
established in Phases 1-3:

- `release-prep` (subagents — 4 agents)
- `refactor-plan` (single agent + hooks)
- `simplify-code` (single agent)
- `dependency-check` (single agent)
- `research-synthesis` (subagents)
- `test-audit` (single agent + sessions)
- `health-check` (orchestrated subagents)

1. Apply the appropriate pattern from Phase 1-3 to each
2. Merge base + SDK variants
3. Delete 7 `*_agent_sdk.py` files
4. Update `workflows/__init__.py` registry (simplified,
   no more dual entries)

**Tutorial:** "Patterns for Agent Workflows — When to Use
Subagents vs Hooks vs Sessions" — decision framework for
choosing SDK patterns.

---

### Phase 5: Cleanup & New Features

**Branch:** `feature/sdk-migration-cleanup`

1. Remove `src/attune/agents/sdk/` directory entirely
   (all scaffolding gone)
2. Update all imports and references
3. Update MCP server tools if needed
4. Update CLI help text and docs
5. Explore new features enabled by full SDK adoption:
   - **MCP client integration** — connect attune's MCP
     server as a tool source for SDK agents
   - **Cross-workflow sessions** — security audit finds
     issue, code review picks up context
   - **Agent forking** — explore multiple refactoring
     approaches in parallel
6. Version bump (major or minor depending on breaking
   changes)
7. Update README, CHANGELOG, PyPI description

**Tutorial:** "Advanced Patterns — MCP Integration,
Session Forking, and Cross-Workflow Context" — the
payoff of full SDK adoption.

---

## Tutorial/Blog Series Outline

| # | Title | Phase | SDK Feature |
|---|-------|-------|-------------|
| 1 | Setting Up the Agents SDK as a Core Dependency | 0 | Project structure |
| 2 | Building a Multi-Agent Code Review | 1 | Subagents, delegation |
| 3 | Agent Lifecycle Hooks for Safety | 2 | Hooks, validation |
| 4 | Persistent Sessions — Resume Where You Left Off | 3 | Sessions, resume |
| 5 | Choosing the Right Agent Pattern | 4 | Decision framework |
| 6 | Advanced: MCP, Forking, Cross-Workflow Context | 5 | MCP client, forking |

## Risks

- **SDK version churn:** The SDK is young. Pin to a
  specific version range and test against new releases
  before upgrading.
- **Breaking change for existing users:** Anyone on
  `attune-ai` without the SDK installed will need to
  reinstall. Communicate in CHANGELOG and migration
  guide.
- **Cost routing complexity:** The SDK's per-agent model
  selection is simpler than attune's tier escalation.
  May need a thin adapter to preserve CHEAP->CAPABLE->
  PREMIUM behavior.
- **Session storage:** SDK sessions are ephemeral by
  default. Need to persist session IDs in
  `AgentStateStore` for cross-invocation resume.

## Open Questions

- What minimum `claude-agent-sdk` version to pin to?
- Should the tutorials live in the repo (`docs/tutorials/`)
  or on the website?
- Do we need a migration guide for users upgrading from
  the dual-implementation version?
- Should Phase 1 tutorial be published before Phase 2
  starts (get community feedback early)?

## Next Steps

- [ ] Create the development fork on GitHub
- [ ] Start Phase 0: dependency + pruning
- [ ] Draft Tutorial #1 outline

---

## XML Task Specifications

### Phase 0: Foundation

```xml
<task id="0.1" name="sdk-core-dependency">
  <objective>
    Move claude-agent-sdk from optional extra to core
    dependency so all users get it on install.
  </objective>

  <context>
    <existing-code path="pyproject.toml">
      Core deps at lines 60-71. Optional agent-sdk extra
      at lines 119-122:
      agent-sdk = ["claude-agent-sdk>=0.1.0"]
    </existing-code>
  </context>

  <files-to-modify>
    <file path="pyproject.toml">
      <change location="dependencies list (line ~71)">
        BEFORE:
        "anthropic>=0.40.0,<1.0.0",
        ]

        AFTER:
        "anthropic>=0.40.0,<1.0.0",
        "claude-agent-sdk>=0.1.0",
        ]
      </change>
      <change location="optional-dependencies (lines 119-122)">
        BEFORE:
        # Anthropic Agent SDK
        agent-sdk = [
            "claude-agent-sdk>=0.1.0",
        ]

        AFTER:
        (delete entire agent-sdk extra block)
      </change>
    </file>
    <file path="README.md">
      <change location="all references to [agent-sdk] extra">
        BEFORE: pip install 'attune-ai[agent-sdk]'
        AFTER: (remove — SDK included by default)
      </change>
    </file>
    <file path=".claude/CLAUDE.md">
      <change location="any [agent-sdk] install references">
        BEFORE: attune-ai[agent-sdk]
        AFTER: attune-ai (SDK included by default)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pip install -e . installs claude-agent-sdk</check>
    <check>python -c "import claude_agent_sdk" succeeds
      without [agent-sdk] extra</check>
    <check>grep -r "agent-sdk" pyproject.toml returns no
      optional extra section</check>
  </validation>

  <risks>
    <risk severity="low">
      Users on constrained environments may not want the
      extra dep. Acceptable — SDK is small.
    </risk>
  </risks>

  <tutorial-notes>
    Blog: "Setting Up the Agents SDK as a Core Dependency"
    Key point: Why make it core vs optional. Show
    pyproject.toml before/after. Explain that building on
    the SDK means it's not optional infrastructure.
  </tutorial-notes>
</task>

<task id="0.2" name="remove-availability-guards">
  <objective>
    Remove all _SDK_AVAILABLE runtime guards and
    try/except ImportError patterns — the SDK is now
    always present.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/*_agent_sdk.py">
      All 15 SDK workflow files have identical guard at
      lines 24-31:

      _SDK_AVAILABLE = False
      try:
          import claude_agent_sdk
          _SDK_AVAILABLE = True
      except ImportError:
          claude_agent_sdk = None

      And in execute():
      if not _SDK_AVAILABLE:
          return self._error_result(
              "claude-agent-sdk not installed...")
    </existing-code>
    <existing-code path="src/attune/agents/sdk/sdk_models.py">
      SDK_AVAILABLE guard at lines 20-26
    </existing-code>
    <existing-code path="src/attune/workflows/__init__.py">
      _is_sdk_available() function at lines 510-517
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/*_agent_sdk.py">
      <change location="lines 24-31 in all 15 files">
        BEFORE:
        _SDK_AVAILABLE = False
        try:
            import claude_agent_sdk
            _SDK_AVAILABLE = True
        except ImportError:
            claude_agent_sdk = None

        AFTER:
        import claude_agent_sdk
      </change>
      <change location="execute() availability check">
        BEFORE:
        if not _SDK_AVAILABLE:
            return self._error_result(...)

        AFTER:
        (delete this block entirely)
      </change>
    </file>
    <file path="src/attune/agents/sdk/sdk_models.py">
      <change location="lines 20-26">
        BEFORE: SDK_AVAILABLE guard block
        AFTER: import claude_agent_sdk (direct)
      </change>
    </file>
    <file path="src/attune/workflows/__init__.py">
      <change location="_is_sdk_available() function">
        BEFORE: def _is_sdk_available(): ...
        AFTER: (delete function entirely)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep -r "_SDK_AVAILABLE" src/ returns no
      matches</check>
    <check>grep -r "SDK_AVAILABLE" src/ returns no
      matches</check>
    <check>uv run pytest tests/ -x passes</check>
  </validation>

  <risks>
    <risk severity="medium">
      Tests that mock _SDK_AVAILABLE will break. Grep
      tests/ for _SDK_AVAILABLE and update or remove
      those test cases.
    </risk>
  </risks>
</task>

<task id="0.3" name="remove-routing-layer">
  <objective>
    Remove the dual-routing system that auto-switches
    between base and SDK workflow variants. After this,
    each workflow has one implementation.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/__init__.py">
      _SDK_WORKFLOW_MAP (lines 364-378): maps 13 base
      names to SDK variant names.

      _SDK_REVERSE_MAP (lines 380-381): reverse mapping.

      get_workflow() (lines 540-545): auto-resolves to
      SDK variant when available.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/__init__.py">
      <change location="lines 364-381">
        BEFORE:
        _SDK_WORKFLOW_MAP: dict[str, str] = {
            "code-review": "code-review-sdk",
            ...13 entries...
        }
        _SDK_REVERSE_MAP = {v: k for k, v in ...}

        AFTER:
        (delete both dicts entirely)
      </change>
      <change location="get_workflow() lines 540-545">
        BEFORE:
        sdk_variant = _SDK_WORKFLOW_MAP.get(name)
        if sdk_variant and sdk_variant in WORKFLOW_REGISTRY
            and _is_sdk_available():
            ...
            return WORKFLOW_REGISTRY[sdk_variant]

        AFTER:
        (delete this auto-routing block)
      </change>
      <change location="list_workflows() SDK dedup logic">
        BEFORE: logic to hide -sdk suffixed entries
        AFTER: (delete — no more dual entries to hide)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep -r "_SDK_WORKFLOW_MAP" src/ returns no
      matches</check>
    <check>grep -r "_SDK_REVERSE_MAP" src/ returns no
      matches</check>
    <check>python -c "from attune.workflows import
      list_workflows; print(len(list_workflows()))"
      returns expected count</check>
  </validation>

  <risks>
    <risk severity="medium">
      Any code that references _SDK_WORKFLOW_MAP or
      _SDK_REVERSE_MAP will break. Grep the full codebase
      including tests.
    </risk>
  </risks>
</task>

<task id="0.4" name="prune-unused-scaffolding">
  <objective>
    Delete the unused SDKAgent, SDKAgentTeam, and
    SDKToolsMixin classes that were never instantiated
    in production code.
  </objective>

  <context>
    <existing-code path="src/attune/agents/sdk/">
      sdk_agent.py — SDKAgent class (11K, never used)
      sdk_team.py — SDKAgentTeam, QualityGate (7.3K,
        never used)
      adapters.py — SDKToolsMixin (4.4K, never used)
      sdk_models.py — SDKExecutionMode, SDKAgentResult
        (4.5K, SDKExecutionMode unused)
      __init__.py — exports all of the above (736 bytes)
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/agents/sdk/sdk_agent.py">
      DELETE entire file
    </file>
    <file path="src/attune/agents/sdk/sdk_team.py">
      DELETE entire file
    </file>
    <file path="src/attune/agents/sdk/adapters.py">
      DELETE entire file
    </file>
    <file path="src/attune/agents/sdk/__init__.py">
      <change location="entire file">
        BEFORE: exports SDKAgent, SDKAgentTeam,
          SDKToolsMixin, SDKExecutionMode, etc.
        AFTER: export only AgentSDKResultAdapter and
          SDKAgentResult (still used by workflows)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.agents.sdk import
      AgentSDKResultAdapter" succeeds</check>
    <check>grep -r "SDKAgent\b" src/ returns no matches
      (except agent_sdk workflow class names)</check>
    <check>grep -r "SDKAgentTeam" src/ returns no
      matches</check>
    <check>grep -r "SDKToolsMixin" src/ returns no
      matches</check>
    <check>uv run pytest tests/ -x passes</check>
  </validation>

  <risks>
    <risk severity="low">
      Tests importing these classes will break. Grep
      tests/ for SDKAgent, SDKAgentTeam, SDKToolsMixin
      and delete those test files.
    </risk>
  </risks>
</task>

<task id="0.5" name="update-ci">
  <objective>
    Update CI workflows to install claude-agent-sdk as
    part of standard install (no longer optional).
  </objective>

  <context>
    <existing-code path=".github/workflows/">
      CI may have separate steps for optional deps or
      skip SDK tests. These need to be normalized.
    </existing-code>
  </context>

  <files-to-modify>
    <file path=".github/workflows/*.yml">
      <change location="install steps">
        BEFORE: pip install 'attune-ai[agent-sdk]' or
          separate SDK install step
        AFTER: pip install attune-ai (SDK included)
      </change>
      <change location="test skip conditions">
        BEFORE: @pytest.mark.skipif for SDK tests
        AFTER: (remove skip conditions — SDK always
          available)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>CI passes on all platforms</check>
    <check>No tests skipped due to missing SDK</check>
  </validation>
</task>
```

### Phase 1: Code Review Migration (Proof of Pattern)

```xml
<task id="1.1" name="merge-code-review-implementations">
  <objective>
    Merge code_review.py (mixin-based, multi-stage) and
    code_review_agent_sdk.py (SDK query, 4 subagents)
    into a single SDK-native code_review.py.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/code_review.py">
      CodeReviewWorkflow — uses mixin composition:
      ClassifyMixin, ScanMixin, ArchitectMixin,
      CrewMixin, CodeReviewAnalysisMixin.
      Multi-stage: classify, scan, architect, crew.
      This is the base (non-SDK) implementation.
    </existing-code>
    <existing-code path="src/attune/workflows/code_review_agent_sdk.py">
      AgentCodeReviewWorkflow — single stage "agent-review"
      4 subagents: security-reviewer, quality-reviewer,
        perf-reviewer, architect-reviewer
      Uses claude_agent_sdk.query() with ClaudeAgentOptions
      Prompt template synthesizes 4 subagent reports into
        one structured report.
    </existing-code>
    <existing-code path="src/attune/mcp/server.py">
      MCP server imports CodeReviewWorkflow directly from
      code_review module (lines 774-778). Must still work
      after merge.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/code_review.py">
      <change location="entire class">
        BEFORE: Mixin-based CodeReviewWorkflow with
          multi-stage execution

        AFTER: SDK-native CodeReviewWorkflow that:
        1. Keeps class name "CodeReviewWorkflow" (for MCP
           and registry compatibility)
        2. Keeps name = "code-review" (user-facing name)
        3. Uses claude_agent_sdk.query() with 4 subagents
           defined via AgentDefinition
        4. Preserves tier_map for cost routing (model
           selection per subagent role)
        5. Uses AgentSDKResultAdapter for result conversion
        6. Single stage: "review"
      </change>
    </file>
    <file path="src/attune/workflows/code_review_agent_sdk.py">
      DELETE entire file
    </file>
    <file path="src/attune/workflows/__init__.py">
      <change location="registry entries">
        BEFORE: separate entries for "code-review" and
          "code-review-sdk"
        AFTER: single entry for "code-review" pointing to
          the merged CodeReviewWorkflow
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>attune workflow run code-review --path src/
      executes successfully using SDK</check>
    <check>MCP code_review tool still works (imports
      CodeReviewWorkflow from code_review module)</check>
    <check>attune workflow list shows "code-review" once
      (not twice)</check>
    <check>uv run pytest tests/ -k "code_review" passes
      </check>
  </validation>

  <risks>
    <risk severity="high">
      The mixin-based workflow has different stage
      semantics than the SDK single-stage approach.
      Tests that assert specific stage names or stage
      counts will break. Audit all code_review tests.
    </risk>
    <risk severity="medium">
      MCP server imports CodeReviewWorkflow by name.
      The class name must stay the same.
    </risk>
  </risks>

  <tutorial-notes>
    Blog: "Building a Multi-Agent Code Review with the
    Claude Agents SDK"

    Structure:
    1. The problem: why code review needs multiple
       perspectives (security, quality, perf, architecture)
    2. Defining subagents with AgentDefinition — one agent
       per review domain
    3. The orchestrator prompt — how to synthesize findings
    4. Model selection per subagent — cheap for scanning,
       capable for analysis
    5. Streaming results — showing progress to the user
    6. Result adaptation — converting unstructured agent
       output to structured reports

    Code examples: show the subagent definitions, the
    orchestrator prompt template, the query() call with
    ClaudeAgentOptions, and the result adapter.
  </tutorial-notes>
</task>

<task id="1.2" name="sdk-subagent-definitions">
  <objective>
    Replace the flat subagent name list with proper SDK
    AgentDefinition objects that include specialized
    system prompts, tool permissions, and model selection.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/code_review_agent_sdk.py">
      Current pattern — subagents defined as strings in
      _SUBAGENT_NAMES list and referenced in the main
      prompt. No per-agent tool restrictions or model
      overrides.

      _SUBAGENT_NAMES = [
          "security-reviewer",
          "quality-reviewer",
          "perf-reviewer",
          "architect-reviewer",
      ]
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/code_review.py">
      <change location="subagent definitions">
        BEFORE: flat list of subagent name strings

        AFTER: dict of AgentDefinition objects:
        agents={
            "security-reviewer": AgentDefinition(
                description="CWE-focused vulnerability
                  scanner",
                prompt="Analyze code for security
                  vulnerabilities...",
                tools=["Read", "Glob", "Grep"],
                model="claude-haiku-4-5-20251001",
            ),
            "quality-reviewer": AgentDefinition(
                description="Code quality and style
                  analyzer",
                prompt="Review code quality...",
                tools=["Read", "Glob", "Grep"],
                model="claude-haiku-4-5-20251001",
            ),
            "perf-reviewer": AgentDefinition(
                description="Performance bottleneck
                  detector",
                prompt="Identify performance issues...",
                tools=["Read", "Glob", "Grep"],
            ),
            "architect-reviewer": AgentDefinition(
                description="Architecture and design
                  reviewer",
                prompt="Evaluate architecture...",
                tools=["Read", "Glob", "Grep"],
                model="claude-sonnet-4-6",
            ),
        }
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Each subagent has description, prompt, tools,
      and optional model override</check>
    <check>Cost routing preserved: scanning agents use
      haiku, architecture uses sonnet</check>
    <check>Workflow executes with all 4 subagents
      producing output</check>
  </validation>

  <tutorial-notes>
    This is the core of Tutorial #2. Show how
    AgentDefinition maps to the SDK's subagent system.
    Emphasize: description for agent selection, tools
    for least-privilege, model for cost routing.
  </tutorial-notes>
</task>

<task id="1.3" name="streaming-progress">
  <objective>
    Add streaming progress reporting so users see which
    subagent is working and what it's finding in
    real-time, rather than waiting for the full result.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/code_review_agent_sdk.py">
      Current pattern collects all results silently:
      async for message in claude_agent_sdk.query(...):
          if isinstance(message, claude_agent_sdk.ResultMessage):
              result_parts.append(message.result)
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/code_review.py">
      <change location="query iteration loop">
        BEFORE: silently collect result_parts

        AFTER: log progress per subagent using
        message.parent_tool_use_id to identify which
        subagent is active:

        async for message in claude_agent_sdk.query(...):
            if hasattr(message, "parent_tool_use_id"):
                logger.info("Subagent working: %s",
                    message.parent_tool_use_id)
            if isinstance(message,
                claude_agent_sdk.ResultMessage):
                result_parts.append(message.result)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Running code-review produces log lines
      showing subagent activity</check>
    <check>Final result is unchanged</check>
  </validation>

  <tutorial-notes>
    Tutorial #2 section: "Showing Progress to Users"
    Explain message types, parent_tool_use_id for
    subagent tracking, streaming vs batch collection.
  </tutorial-notes>
</task>
```

### Phase 2: Hooks & Lifecycle

```xml
<task id="2.1" name="security-audit-with-hooks">
  <objective>
    Migrate security-audit to SDK-native with PreToolUse
    hooks for input safety and PostToolUse hooks for
    output quality validation.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/security_audit_agent_sdk.py">
      4 subagents: vuln-scanner, secret-detector,
      auth-reviewer, remediation-planner.
      No hooks — all validation is post-hoc.
    </existing-code>
    <existing-code path="src/attune/workflows/security_audit.py">
      Base SecurityAuditWorkflow — mixin-based.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/security_audit.py">
      <change location="entire class">
        BEFORE: mixin-based SecurityAuditWorkflow

        AFTER: SDK-native SecurityAuditWorkflow with:
        1. 4 subagents via AgentDefinition
        2. PreToolUse hook: block Bash commands containing
           eval(), exec(), or curl to internal IPs
        3. PostToolUse hook: validate that Read tool
           results don't contain secrets (API keys,
           passwords) before passing to agent context
        4. Stop hook: generate structured severity report
        5. Keep class name SecurityAuditWorkflow for MCP
      </change>
    </file>
    <file path="src/attune/workflows/security_audit_agent_sdk.py">
      DELETE entire file
    </file>
  </files-to-modify>

  <validation>
    <check>Workflow blocks eval() in Bash tool via
      PreToolUse hook</check>
    <check>Workflow produces structured severity report
      via Stop hook</check>
    <check>MCP security_audit tool still works</check>
    <check>uv run pytest tests/ -k "security_audit"
      passes</check>
  </validation>

  <tutorial-notes>
    Blog: "Agent Lifecycle Hooks — Validation, Quality
    Gates, and Safety"

    Structure:
    1. The problem: agents can run dangerous commands or
       leak secrets during analysis
    2. PreToolUse hooks — intercepting tool calls before
       execution (show eval/exec blocker)
    3. PostToolUse hooks — validating tool results before
       they enter agent context (show secret detector)
    4. Stop hooks — structured output generation (show
       severity report builder)
    5. HookMatcher — targeting hooks to specific tools
    6. Composing hooks — stacking multiple validators
  </tutorial-notes>
</task>

<task id="2.2" name="bug-predict-with-hooks">
  <objective>
    Migrate bug-predict to SDK-native with PostToolUse
    hooks for false positive filtering.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/bug_predict_agent_sdk.py">
      3 subagents: pattern-scanner, risk-correlator,
      prevention-advisor. No hooks.
    </existing-code>
    <existing-code path="src/attune/workflows/bug_predict.py">
      Base BugPredictionWorkflow.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/bug_predict.py">
      <change location="entire class">
        BEFORE: base BugPredictionWorkflow

        AFTER: SDK-native BugPredictionWorkflow with:
        1. 3 subagents via AgentDefinition
        2. PostToolUse hook on Grep results: apply false
           positive filters (test fixtures, scanner test
           files, JavaScript regex.exec())
        3. Keep class name BugPredictionWorkflow
      </change>
    </file>
    <file path="src/attune/workflows/bug_predict_agent_sdk.py">
      DELETE entire file
    </file>
  </files-to-modify>

  <validation>
    <check>Known false positives (test fixtures, .exec())
      are filtered by PostToolUse hook</check>
    <check>MCP bug_predict tool still works</check>
  </validation>
</task>

<task id="2.3" name="perf-audit-with-hooks">
  <objective>
    Migrate perf-audit to SDK-native with hooks for
    benchmarking validation.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/perf_audit_agent_sdk.py">
      3 subagents: complexity-analyzer, bottleneck-finder,
      optimization-advisor. No hooks.
    </existing-code>
    <existing-code path="src/attune/workflows/perf_audit.py">
      Base PerformanceAuditWorkflow.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/perf_audit.py">
      <change location="entire class">
        BEFORE: base PerformanceAuditWorkflow

        AFTER: SDK-native PerformanceAuditWorkflow with:
        1. 3 subagents via AgentDefinition
        2. PostToolUse hook: validate os.walk dirs[:]
           pattern is not flagged as false positive
           (lesson learned from scanner-patterns.md)
        3. Keep class name PerformanceAuditWorkflow
      </change>
    </file>
    <file path="src/attune/workflows/perf_audit_agent_sdk.py">
      DELETE entire file
    </file>
  </files-to-modify>

  <validation>
    <check>dirs[:] pattern correctly identified as
      non-issue by PostToolUse hook</check>
    <check>MCP performance_audit tool still works</check>
  </validation>
</task>
```

### Phase 3: Sessions & Resume

```xml
<task id="3.1" name="test-gen-with-sessions">
  <objective>
    Migrate test-gen to SDK-native with session support
    so users can generate tests, review results, and
    iterate without losing context.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/test_gen_agent_sdk.py">
      3 subagents: function-identifier, test-designer,
      test-writer. Stateless — every run starts fresh.
    </existing-code>
    <existing-code path="src/attune/workflows/test_gen/">
      Base TestGenerationWorkflow — multi-stage with
      parallel generation support.
    </existing-code>
    <existing-code path="src/attune/agents/state/">
      AgentStateStore — existing state persistence
      infrastructure for storing session IDs.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/test_gen/workflow.py">
      <change location="entire class">
        BEFORE: mixin-based TestGenerationWorkflow

        AFTER: SDK-native TestGenerationWorkflow with:
        1. 3 subagents via AgentDefinition
        2. Session capture: extract session_id from init
           message during query() iteration
        3. Session storage: persist session_id in
           AgentStateStore keyed by workflow + path
        4. Resume support: accept optional session_id
           kwarg in execute() to resume previous session
           via claude_agent_sdk.query(resume=session_id)
        5. Keep class name TestGenerationWorkflow
      </change>
    </file>
    <file path="src/attune/workflows/test_gen_agent_sdk.py">
      DELETE entire file
    </file>
  </files-to-modify>

  <validation>
    <check>First run captures and stores session_id</check>
    <check>Second run with same path resumes previous
      session (agent has context of prior analysis)</check>
    <check>MCP test_generation tool still works</check>
    <check>Session ID persisted in AgentStateStore</check>
  </validation>

  <tutorial-notes>
    Blog: "Persistent Agent Sessions — Resume Where You
    Left Off"

    Structure:
    1. The problem: iterative workflows lose context
       between runs (generate tests, review, regenerate)
    2. Session capture — extracting session_id from the
       SDK's init message
    3. Session storage — using AgentStateStore (or any
       key-value store) to persist session IDs
    4. Resuming sessions — passing resume=session_id to
       query() so the agent picks up where it left off
    5. Session lifecycle — when to create new vs resume
    6. Cross-invocation state — what the agent remembers
       (files read, analysis done, conversation history)
    7. Error recovery — what happens when a session
       expires or the agent crashes mid-session
  </tutorial-notes>
</task>

<task id="3.2" name="doc-gen-with-sessions">
  <objective>
    Migrate doc-gen to SDK-native with session support
    for iterative documentation authoring.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/doc_gen_agent_sdk.py">
      3 subagents: outline-planner, content-writer,
      polish-reviewer. Stateless.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/doc_gen.py">
      <change location="entire class">
        Merge SDK variant into base. Add session capture
        and resume support (same pattern as task 3.1).
      </change>
    </file>
    <file path="src/attune/workflows/doc_gen_agent_sdk.py">
      DELETE entire file
    </file>
  </files-to-modify>

  <validation>
    <check>Session resume works for iterative doc
      authoring (outline → draft → polish)</check>
    <check>MCP doc_gen tool still works</check>
  </validation>
</task>

<task id="3.3" name="doc-audit-with-sessions">
  <objective>
    Migrate doc-audit to SDK-native with session support
    for tracking audit progress across runs.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/doc_audit_agent_sdk.py">
      3 subagents: staleness-checker, accuracy-reviewer,
      gap-finder. Stateless.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/doc_audit.py">
      <change location="entire class">
        Merge SDK variant into base. Add session support
        so re-audits can see what was flagged previously.
      </change>
    </file>
    <file path="src/attune/workflows/doc_audit_agent_sdk.py">
      DELETE entire file
    </file>
  </files-to-modify>

  <validation>
    <check>Re-audit resumes session and references prior
      findings</check>
    <check>MCP doc_audit tool still works</check>
  </validation>
</task>
```

### Phase 4: Batch Migration

```xml
<task id="4.1" name="release-prep-subagents">
  <objective>
    Migrate release-prep — 4 subagents (health-checker,
    security-scanner, changelog-generator,
    release-assessor) using subagent pattern from Phase 1.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/release_prep_agent_sdk.py">
      ReleasePrepAgentSDKWorkflow with 4 subagents.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/release_prep.py">
      Merge SDK variant. Use AgentDefinition for each of
      the 4 subagents. Keep ReleasePreparationWorkflow
      class name (MCP imports it).
    </file>
    <file path="src/attune/workflows/release_prep_agent_sdk.py">
      DELETE
    </file>
  </files-to-modify>

  <validation>
    <check>attune workflow run release-prep works</check>
    <check>MCP release_prep tool works</check>
  </validation>
</task>

<task id="4.2" name="refactor-plan-hooks">
  <objective>
    Migrate refactor-plan using hooks pattern from
    Phase 2 (PostToolUse for safety validation of
    suggested refactorings).
  </objective>

  <context>
    <existing-code path="src/attune/workflows/refactor_plan_agent_sdk.py">
      3 subagents: debt-scanner, impact-analyzer,
      plan-generator.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/refactor_plan.py">
      Merge SDK variant. Add PostToolUse hook to validate
      that suggested refactorings don't introduce
      security issues (no eval, validated paths).
    </file>
    <file path="src/attune/workflows/refactor_plan_agent_sdk.py">
      DELETE
    </file>
  </files-to-modify>
</task>

<task id="4.3" name="simplify-code-single-agent">
  <objective>
    Migrate simplify-code as a single-agent workflow
    (minimal subagents needed).
  </objective>

  <context>
    <existing-code path="src/attune/workflows/simplify_code_agent_sdk.py">
      3 subagents: complexity-scanner,
      simplification-designer, safety-reviewer.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/simplify_code.py">
      Merge SDK variant. Keep 3 subagents for thorough
      analysis.
    </file>
    <file path="src/attune/workflows/simplify_code_agent_sdk.py">
      DELETE
    </file>
  </files-to-modify>
</task>

<task id="4.4" name="dependency-check-single-agent">
  <objective>
    Migrate dependency-check (2 subagents:
    inventory-assessor, update-advisor).
  </objective>

  <context>
    <existing-code path="src/attune/workflows/dependency_check_agent_sdk.py">
      Only 2 subagents — simplest SDK workflow.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/dependency_check.py">
      Merge SDK variant.
    </file>
    <file path="src/attune/workflows/dependency_check_agent_sdk.py">
      DELETE
    </file>
  </files-to-modify>
</task>

<task id="4.5" name="research-synthesis-subagents">
  <objective>
    Migrate research-synthesis (3 subagents:
    source-summarizer, pattern-analyst,
    synthesis-writer).
  </objective>

  <context>
    <existing-code path="src/attune/workflows/research_synthesis_agent_sdk.py">
      3 subagents following standard pattern.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/research_synthesis.py">
      Merge SDK variant.
    </file>
    <file path="src/attune/workflows/research_synthesis_agent_sdk.py">
      DELETE
    </file>
  </files-to-modify>
</task>

<task id="4.6" name="test-audit-sessions">
  <objective>
    Migrate test-audit using sessions pattern from
    Phase 3 (track coverage gaps across runs).
  </objective>

  <context>
    <existing-code path="src/attune/workflows/test_audit_agent_sdk.py">
      3 subagents: coverage-auditor, gap-analyzer,
      test-planner.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/test_audit.py">
      Merge SDK variant. Add session support so
      re-audits can track which gaps were addressed.
    </file>
    <file path="src/attune/workflows/test_audit_agent_sdk.py">
      DELETE
    </file>
  </files-to-modify>
</task>

<task id="4.7" name="health-check-dynamic-subagents">
  <objective>
    Migrate health-check — unique pattern with
    mode-based dynamic subagent selection (6 possible
    subagents, selected by mode).
  </objective>

  <context>
    <existing-code path="src/attune/workflows/health_check_agent_sdk.py">
      6 subagents: test-checker, dep-checker,
      lint-checker, ci-checker, doc-checker,
      security-checker. Mode selects which subset runs.
      _MODE_SUBAGENTS dict maps mode to subagent list.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/health_check.py">
      Merge SDK variant. Preserve dynamic subagent
      selection — build AgentDefinition dict at runtime
      based on mode parameter.
    </file>
    <file path="src/attune/workflows/health_check_agent_sdk.py">
      DELETE
    </file>
  </files-to-modify>

  <validation>
    <check>mode="quick" runs subset of subagents</check>
    <check>mode="full" runs all 6 subagents</check>
  </validation>

  <tutorial-notes>
    Blog: "Patterns for Agent Workflows — When to Use
    Subagents vs Hooks vs Sessions"

    Structure:
    1. Decision framework: when each SDK pattern shines
       - Subagents: parallel specialized analysis
         (code-review, release-prep)
       - Hooks: validation, safety, quality gates
         (security-audit, bug-predict)
       - Sessions: iterative workflows that build on
         prior context (test-gen, doc-gen)
       - Dynamic subagents: configurable scope
         (health-check)
    2. Composing patterns: subagents + hooks together
    3. Anti-patterns: when NOT to use each pattern
    4. Real examples from attune-ai's migration
  </tutorial-notes>
</task>
```

### Phase 5: Cleanup & New Features

```xml
<task id="5.1" name="delete-sdk-scaffolding-dir">
  <objective>
    Remove the entire src/attune/agents/sdk/ directory
    now that all workflows use SDK directly and no
    scaffolding classes remain.
  </objective>

  <context>
    After Phase 4, the only remaining files in
    src/attune/agents/sdk/ should be:
    - __init__.py (exports AgentSDKResultAdapter)
    - sdk_models.py (SDKAgentResult dataclass)

    Move AgentSDKResultAdapter to a shared location
    (e.g., src/attune/workflows/sdk_adapter.py) then
    delete the directory.
  </context>

  <files-to-create>
    <file path="src/attune/workflows/sdk_adapter.py">
      Move AgentSDKResultAdapter class here. This is
      the shared result conversion utility used by all
      SDK-native workflows.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/*">
      Update all imports from
      "from attune.agents.sdk import AgentSDKResultAdapter"
      to
      "from attune.workflows.sdk_adapter import
        AgentSDKResultAdapter"
    </file>
    <file path="src/attune/agents/sdk/">
      DELETE entire directory
    </file>
    <file path="src/attune/agents/__init__.py">
      Remove sdk subpackage from exports
    </file>
  </files-to-modify>

  <validation>
    <check>src/attune/agents/sdk/ directory does not
      exist</check>
    <check>All workflows still import
      AgentSDKResultAdapter successfully</check>
    <check>Full test suite passes</check>
  </validation>
</task>

<task id="5.2" name="update-mcp-server">
  <objective>
    Verify and update MCP server to work with the
    merged workflow classes. The server imports base
    workflow classes directly — confirm all class names
    and import paths are correct.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Direct imports at lines 740-825:
      - SecurityAuditWorkflow from security_audit
      - BugPredictionWorkflow from bug_predict
      - CodeReviewWorkflow from code_review
      - TestGenerationWorkflow from test_gen
      - PerformanceAuditWorkflow from perf_audit
      - ReleasePreparationWorkflow from release_prep
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/server.py">
      Verify all lazy imports still resolve. Class names
      were preserved during migration, so most should
      work. Check for any that were renamed.
    </file>
  </files-to-modify>

  <validation>
    <check>All 17 MCP workflow tools execute without
      import errors</check>
    <check>MCP tool list returns correct count</check>
  </validation>
</task>

<task id="5.3" name="cross-workflow-sessions">
  <objective>
    New feature: enable cross-workflow session sharing
    so a security audit can hand off findings to a
    code review that picks up the same context.
  </objective>

  <context>
    With sessions implemented in Phases 1-4, each
    workflow stores its own session_id. This task
    creates a session registry that allows workflows
    to discover and resume sessions from other
    workflows that analyzed the same path.
  </context>

  <files-to-create>
    <file path="src/attune/workflows/session_registry.py">
      SessionRegistry class:
      - store(workflow_name, path, session_id)
      - lookup(path) -> dict of workflow->session_id
      - find_related(workflow_name, path) -> session_id
        of most recent related workflow on same path
      Backed by AgentStateStore.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/code_review.py">
      Before starting review, check SessionRegistry for
      a recent security-audit session on the same path.
      If found, resume that session to inherit the
      security context.
    </file>
  </files-to-modify>

  <validation>
    <check>Run security-audit on src/, then code-review
      on src/ — code review references security findings
      without re-scanning</check>
  </validation>

  <tutorial-notes>
    Blog: "Advanced Patterns — MCP Integration, Session
    Forking, and Cross-Workflow Context"

    Structure:
    1. The vision: workflows that build on each other's
       analysis rather than starting from scratch
    2. Session registry — a thin layer for discovering
       related sessions
    3. Cross-workflow handoff — security audit findings
       informing code review priorities
    4. Session forking — exploring multiple refactoring
       approaches in parallel branches
    5. MCP client integration — using attune's own MCP
       server as a tool source for SDK agents (agents
       that can invoke other attune workflows)
    6. The full picture: attune as a reference
       implementation for production agent systems
  </tutorial-notes>
</task>

<task id="5.4" name="version-bump-and-changelog">
  <objective>
    Bump version, update CHANGELOG and README to
    reflect the SDK-first architecture.
  </objective>

  <files-to-modify>
    <file path="pyproject.toml">
      Bump version (minor or major based on breaking
      changes assessment)
    </file>
    <file path="CHANGELOG.md">
      Document: SDK as core dependency, removed dual
      implementations, new features (hooks, sessions,
      cross-workflow context)
    </file>
    <file path="README.md">
      Update architecture section, remove [agent-sdk]
      extra references, highlight SDK-native workflows
    </file>
    <file path=".claude/CLAUDE.md">
      Update project structure, remove agents/sdk/
      references, update version
    </file>
  </files-to-modify>

  <validation>
    <check>Version string updated consistently across
      all files</check>
    <check>CHANGELOG has migration notes for users
      upgrading from dual-implementation version</check>
    <check>README accurately reflects new architecture
      </check>
  </validation>
</task>
```

### Deep Review (Phase 1 only)

```xml
<task id="1.4" name="deep-review-migration">
  <objective>
    Migrate deep-review SDK variant into the main
    deep-review workflow. This is the 15th SDK file
    not covered in the 13-workflow routing map.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/deep_review_agent_sdk.py">
      Multi-pass deep review variant using SDK. Not
      in _SDK_WORKFLOW_MAP — registered independently.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/deep_review.py">
      Merge SDK variant into base implementation.
    </file>
    <file path="src/attune/workflows/deep_review_agent_sdk.py">
      DELETE
    </file>
  </files-to-modify>

  <validation>
    <check>/deep-review command works with SDK-native
      implementation</check>
  </validation>
</task>
```
