# Claude Code Integration Enhancement Plan

**Version:** 1.0
**Date:** 2026-02-06
**Status:** Ready for Implementation

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Phase 1: Quick Wins (Hours)](#phase-1-quick-wins)
3. [Phase 2: Core Enhancements (1-2 Days)](#phase-2-core-enhancements)
4. [Phase 3: Plugin Packaging (2-3 Days)](#phase-3-plugin-packaging)
5. [Phase 4: Advanced Features (1 Week)](#phase-4-advanced-features)
6. [Dependency Graph](#dependency-graph)
7. [Testing Strategy](#testing-strategy)

---

## Current State Analysis

### What Exists

| Integration | Status | Location |
|-------------|--------|----------|
| `/attune` slash command | Implemented | `.claude/commands/attune.md` |
| MCP server (10 tools) | Implemented | `src/attune/mcp/server.py` |
| Session hook scripts | Implemented (not wired) | `attune_llm/hooks/scripts/` |
| Git post-commit hook | Implemented | `scripts/hooks/post-commit` |
| Plugin infrastructure | Partial (no manifest) | `src/attune/plugins/` |

### What Is Missing

| Feature | Impact | Phase |
|---------|--------|-------|
| Hub command skills (`/dev`, `/testing`, etc.) | High - documented but unusable | 1 |
| Claude Code hooks registration | High - scripts exist but don't run | 1 |
| PreToolUse security validation | High - enforces coding standards | 2 |
| Custom subagent definitions | Medium - enables workflow composition | 2 |
| Enhanced setup command | Medium - reduces friction | 2 |
| Plugin packaging | High - enables distribution | 3 |
| MCP prompts | Medium - auto-discovered commands | 4 |
| Learning pipeline integration | Medium - self-improving system | 4 |

---

## Phase 1: Quick Wins

**Estimated time:** 3-5 hours
**Dependencies:** None -- all can be done independently

### Task 1.1: Create Hub Command Skills

**What:** Create 7 hub command markdown files in `src/attune/commands/`.

**Why:** Users see `/dev`, `/testing`, `/workflows`, `/plan`, `/docs`, `/release`, `/agent` documented in CLAUDE.md but cannot actually use them. This is the most visible gap.

**Files to create:**

1. `src/attune/commands/dev.md`
2. `src/attune/commands/testing.md`
3. `src/attune/commands/workflows.md`
4. `src/attune/commands/plan.md`
5. `src/attune/commands/docs.md`
6. `src/attune/commands/release.md`
7. `src/attune/commands/agent.md`

**Template (using `dev.md` as example):**

```yaml
---
name: dev
description: Developer tools - debug, commit, PR, code review, quality
category: hub
aliases: [developer]
tags: [development, debug, commit, review]
version: "1.0.0"
question:
  header: "Developer Tools"
  question: "What do you need to do?"
  multiSelect: false
  options:
    - label: "Debug an issue"
      description: "Investigate errors, trace execution, find root causes"
    - label: "Review code"
      description: "Quality analysis, security review, performance review"
    - label: "Commit changes"
      description: "Stage, commit with conventional commit message"
    - label: "Create a PR"
      description: "Push branch, create pull request with description"
    - label: "Refactor code"
      description: "Improve structure, extract functions, simplify"
---

# Developer Hub

Developer tools for debugging, committing, reviewing, and improving code.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/dev debug` | Start debugging session |
| `/dev review` | Code review |
| `/dev commit` | Stage and commit changes |
| `/dev pr` | Create pull request |
| `/dev refactor` | Refactoring session |
| `/dev quality` | Code quality analysis |

## CRITICAL: Execution Instructions

When invoked with arguments, EXECUTE the corresponding action:

| Input | Action |
| ----- | ------ |
| `/dev debug` | Start interactive debugging: read error context, trace code, identify root cause |
| `/dev review` | `uv run attune workflow run code-review --path <target>` |
| `/dev commit` | Use git to stage and commit with conventional commit format |
| `/dev pr` | Use gh to create a pull request |
| `/dev refactor` | Analyze code and suggest/apply refactoring |
| `/dev quality` | `uv run attune workflow run bug-predict --path <target>` |

## Natural Language Routing

| Pattern | Action |
| ------- | ------ |
| "debug", "fix", "error", "bug" | Start debugging session |
| "review", "quality" | Run code review workflow |
| "commit", "save" | Stage and commit |
| "pr", "pull request", "merge" | Create pull request |
| "refactor", "clean up", "simplify" | Start refactoring |
```

**Hub routing summary:**

| Hub | Key Routes |
|-----|------------|
| `/testing` | `run` -> pytest, `coverage` -> pytest --cov, `generate` -> test-gen workflow |
| `/workflows` | `security` -> security-audit, `bugs` -> bug-predict, `perf` -> perf-audit |
| `/plan` | `feature` -> feature breakdown, `review` -> code-review-pipeline, `refactor` -> refactor-plan |
| `/docs` | `generate` -> doc-gen, `manage` -> manage-documentation, `readme` -> README generation |
| `/release` | `prep` -> release-prep-crew, `security` -> secure-release, `health` -> health-check-crew |
| `/agent` | `create` -> agent creator, `list` -> show agents |

**No code changes needed for setup:** `cmd_setup` already iterates all `.md` files via `source_dir.iterdir()`.

**Testing:**

- Verify each `.md` file has valid YAML frontmatter
- Verify routing tables are complete
- Integration test: `attune setup` installs all 8 files to `~/.claude/commands/`

---

### Task 1.2: Wire Hook Scripts to Claude Code

**What:** Create `.claude/settings.json` that registers existing hook scripts as Claude Code lifecycle hooks.

**Why:** The 6 hook scripts already implement session state persistence, learning evaluation, and compaction management. They just need to be registered.

**File to create:** `.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "python -m attune_llm.hooks.scripts.session_start",
        "timeout": 10000
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "python -m attune_llm.hooks.scripts.session_end",
        "timeout": 10000
      }
    ],
    "PreCompact": [
      {
        "type": "command",
        "command": "python -m attune_llm.hooks.scripts.pre_compact",
        "timeout": 10000
      }
    ]
  }
}
```

**Required adaptation to hook scripts:**

Each script's `__main__` block needs to read context from stdin (Claude Code passes JSON on stdin):

```python
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    context = {}
    if not sys.stdin.isatty():
        try:
            context = json.load(sys.stdin)
        except json.JSONDecodeError:
            pass
    result = main(**context)
    print(json.dumps(result, indent=2))
```

Apply this pattern to all 6 scripts in `attune_llm/hooks/scripts/`.

**Testing:**

- Verify each script runs: `python -m attune_llm.hooks.scripts.<name>` (exit code 0)
- Verify scripts handle empty context gracefully
- Verify `.claude/settings.json` is valid JSON

---

### Task 1.3: Update CLAUDE.md

**What:** Ensure the hub table matches the actual installed commands after Task 1.1.

**Dependencies:** Task 1.1

---

## Phase 2: Core Enhancements

**Estimated time:** 1-2 days
**Dependencies:** Phase 1 should be complete

### Task 2.1: PreToolUse Security Validation Hook

**What:** Create a hook that intercepts Bash/Edit/Write tool calls to enforce security policies.

**Why:** The coding standards mandate never using `eval()`/`exec()` and always validating file paths. A PreToolUse hook catches violations before they reach disk.

**File to create:** `attune_llm/hooks/scripts/security_guard.py`

```python
"""PreToolUse Security Validation Hook.

Intercepts tool calls to enforce security policies:
1. Blocks eval()/exec() in Bash commands
2. Validates file paths in Edit/Write operations
3. Prevents writes to system directories

Exit codes:
  0 = allow tool call
  2 = block tool call (Claude Code convention)
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DANGEROUS_PATTERNS = [
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'__import__\s*\(',
    r'subprocess\.call\s*\(.+shell\s*=\s*True',
]

SYSTEM_DIRS = ["/etc", "/sys", "/proc", "/dev", "/boot", "/sbin"]


def validate_bash_command(command: str) -> tuple[bool, str]:
    """Check a bash command for dangerous patterns."""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return False, f"Blocked: dangerous pattern detected ({pattern})"
    return True, ""


def validate_file_path(path: str) -> tuple[bool, str]:
    """Check a file path against security rules."""
    if "\x00" in path:
        return False, "Blocked: null byte in file path"
    try:
        resolved = str(Path(path).resolve())
    except (OSError, RuntimeError):
        return False, "Blocked: unresolvable path"
    for sys_dir in SYSTEM_DIRS:
        if resolved.startswith(sys_dir):
            return False, f"Blocked: write to system directory {sys_dir}"
    return True, ""


def main(context: dict[str, Any]) -> dict[str, Any]:
    """Validate a tool call before execution."""
    tool_name = context.get("tool_name", "")
    tool_input = context.get("tool_input", {})

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        allowed, reason = validate_bash_command(command)
        if not allowed:
            return {"allowed": False, "reason": reason}

    elif tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        if file_path:
            allowed, reason = validate_file_path(file_path)
            if not allowed:
                return {"allowed": False, "reason": reason}

    return {"allowed": True}


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    context = {}
    if not sys.stdin.isatty():
        try:
            context = json.load(sys.stdin)
        except json.JSONDecodeError:
            pass
    result = main(context)
    if not result.get("allowed", True):
        print(result["reason"], file=sys.stderr)
        sys.exit(2)
    sys.exit(0)
```

**Add to `.claude/settings.json`:**

```json
"PreToolUse": [
  {
    "matcher": {
      "tool_name": "Bash|Edit|Write"
    },
    "type": "command",
    "command": "python -m attune_llm.hooks.scripts.security_guard",
    "timeout": 3000
  }
]
```

**Testing:**

- `test_blocks_eval_in_bash_command`
- `test_blocks_exec_in_bash_command`
- `test_allows_safe_bash_commands`
- `test_blocks_system_directory_writes`
- `test_blocks_null_byte_paths`
- `test_allows_valid_file_paths`

---

### Task 2.2: Custom Subagent Definitions

**What:** Create subagent definition files for specialized tasks.

**Why:** Subagents decompose large workflows into focused agents with restricted tools and persistent memory.

**Files to create:**

- `src/attune/commands/agents/security-reviewer.md` - Read-only security analysis
- `src/attune/commands/agents/test-writer.md` - Test generation (write to `tests/` only)
- `src/attune/commands/agents/doc-generator.md` - Documentation generation

**Example (`security-reviewer.md`):**

```yaml
---
name: security-reviewer
description: Specialized security analysis subagent
model: sonnet
---

# Security Reviewer Agent

You are a specialized security analysis agent for the Attune AI project.

## Your Role

Perform thorough security analysis focusing on:

1. **Path traversal** (CWE-22) - Check all open(), write_text(), write_bytes()
2. **Code injection** (CWE-95) - Find eval(), exec() usage
3. **Exception handling** - Find bare except: clauses
4. **Secrets detection** - Hardcoded API keys or passwords

## Output Format

| Severity | File | Line | Finding | CWE |
|----------|------|------|---------|-----|
| CRITICAL | ... | ... | ... | ... |

## Project Security Rules

!cat .claude/rules/attune/coding-standards-index.md
```

**Hub skills reference subagents via Task tool:** The `/dev review` command would include instructions like "Use the Task tool to spawn a security-reviewer subagent for security-focused analysis."

---

### Task 2.3: Enhanced Setup Command

**What:** Extend `attune setup` to also install hooks config and MCP config.

**Why:** Users must currently configure hooks and MCP manually. Setup should handle everything.

**File to modify:** `src/attune/cli_minimal.py` (the `cmd_setup` function at line 850)

**Key behavior:**

- Install command `.md` files (existing)
- Copy `.claude/settings.json` to `~/.claude/settings.json` if not present
- Copy `.claude/mcp.json` to `~/.claude/mcp.json` if not present
- **Never overwrite** existing config files (suggest manual merge instead)

**Output:**

```text
Attune AI Setup
  Commands installed: 8 (attune, dev, testing, workflows, plan, docs, release, agent)
  Hooks installed: settings.json (SessionStart, Stop, PreCompact, PreToolUse)
  MCP server configured: mcp.json (10 tools)
  Skipped: settings.json already exists (merge manually)
```

---

### Task 2.4: Extended Thinking in Security and Architecture Skills

**What:** Add extended thinking directives to skills that benefit from deep reasoning.

**Files to modify:** `workflows.md`, `plan.md`, `release.md`

**Implementation:** Add reasoning instructions to skill preambles for security audits, architecture planning, and release readiness assessments. Include explicit "think step by step" directives for complex analysis tasks.

---

## Phase 3: Plugin Packaging

**Estimated time:** 2-3 days
**Dependencies:** Phase 1 and 2 substantially complete

### Task 3.1: Create Plugin Manifest

**What:** Create `plugin/manifest.json` following Claude Code's plugin specification.

**Why:** Plugins are the distributable packaging format. This makes attune-ai installable via `claude plugin install`.

**File to create:** `plugin/manifest.json`

```json
{
  "name": "attune-ai",
  "version": "2.3.3",
  "description": "AI-powered developer workflows with cost optimization and intelligent routing",
  "author": {
    "name": "Smart AI Memory, LLC"
  },
  "license": "Apache-2.0",
  "homepage": "https://github.com/Smart-AI-Memory/attune-ai",
  "repository": "https://github.com/Smart-AI-Memory/attune-ai",
  "skills": {
    "attune": "commands/attune.md",
    "dev": "commands/dev.md",
    "testing": "commands/testing.md",
    "workflows": "commands/workflows.md",
    "plan": "commands/plan.md",
    "docs": "commands/docs.md",
    "release": "commands/release.md",
    "agent": "commands/agent.md"
  },
  "hooks": "hooks/hooks.json",
  "mcp_servers": {
    "attune": {
      "command": "python",
      "args": ["-m", "attune.mcp.server"]
    }
  }
}
```

---

### Task 3.2: Plugin Build and Install Commands

**What:** Add `attune plugin build`, `attune plugin install`, `attune plugin validate` CLI commands.

**File to modify:** `src/attune/cli_minimal.py`

**File to create:** `src/attune/cli/commands/plugin_commands.py`

**`plugin build`** reads manifest, verifies all referenced files exist, creates distributable archive.

**`plugin install`** reads manifest, copies skills, merges hooks, merges MCP config.

**`plugin validate`** checks manifest schema and file references.

---

### Task 3.3: Refactor Setup to Use Plugin Manifest

**What:** Make `cmd_setup` read from `plugin/manifest.json` as single source of truth.

**Why:** Ensures consistency between `attune setup` and `attune plugin install`.

**Fallback:** If no manifest exists, fall back to current file-globbing behavior.

---

## Phase 4: Advanced Features

**Estimated time:** 1 week
**Dependencies:** Phase 1-3 substantially complete

### Task 4.1: MCP Prompts as Slash Commands

**What:** Add MCP prompts to `src/attune/mcp/server.py` so they appear as slash commands.

**Why:** MCP prompts are auto-discovered by Claude Code without needing separate `.md` files.

**Prompts to add:**

| Prompt | Description | Arguments |
|--------|-------------|-----------|
| `security-scan` | Security vulnerability scan | `path` (required) |
| `test-gen` | Generate tests for a module | `module` (required), `style` (optional) |
| `cost-report` | Show cost savings report | `days` (optional) |

**Prerequisite:** Consider migrating from custom stdio protocol to official `mcp` Python SDK.

---

### Task 4.2: Agent Team Orchestration

**What:** Create a `/deep-review` skill that orchestrates multiple subagents in parallel.

**Why:** Enables comprehensive analysis (security + quality + test gaps) in a single command.

**Process:**

1. **Security Pass** - Spawn security-reviewer subagent (read-only)
2. **Quality Pass** - Run code-review workflow
3. **Test Gap Analysis** - Run pytest --cov and identify uncovered paths
4. **Synthesis** - Combine findings into prioritized report

---

### Task 4.3: Learning Pipeline Integration

**What:** Wire evaluate_session into Stop hook; inject learned patterns on SessionStart.

**Why:** Creates a self-improving system where each session builds on previous learnings.

**Changes:**

- Add `evaluate_session` to Stop hooks in `.claude/settings.json`
- Modify `session_start.py` to call `apply_learned_patterns()` and include results
- Patterns persist in `~/.empathy/patterns/` and `.attune/learned_skills/`

---

### Task 4.4: Dynamic Context in Skills

**What:** Add `!command` syntax to hub skills for fresh project state injection.

**Why:** Skills always show current context (git status, test results, version info).

| Skill | Dynamic Context |
|-------|----------------|
| `/dev` | `!git status --short`, `!git log --oneline -5`, `!git branch --show-current` |
| `/testing` | Last test results, coverage percentage |
| `/release` | Current version, changelog preview (`!head -20 CHANGELOG.md`) |
| `/workflows` | Available workflow list (`!uv run attune workflow list`) |

---

## Dependency Graph

```text
Phase 1 (Parallel - no dependencies):
  1.1 Hub Commands ─────┐
  1.2 Hook Wiring  ─────┼──> Phase 2
  1.3 CLAUDE.md    ─────┘

Phase 2 (Independent tasks):
  2.1 Security Hook ────────> Phase 3
  2.2 Subagent Definitions ─> Phase 3
  2.3 Enhanced Setup ───────> Phase 3
  2.4 Extended Thinking ────> (Independent)

Phase 3 (Sequential):
  3.1 Plugin Manifest ──> 3.2 Build/Install CLI ──> 3.3 Setup Refactor

Phase 4 (Independent, after prerequisites):
  4.1 MCP Prompts ──────────> (Independent)
  4.2 Agent Teams ──────────> (Requires 2.2)
  4.3 Learning Pipeline ───> (Requires 1.2)
  4.4 Dynamic Context ─────> (Requires 1.1)
```

---

## Testing Strategy

### Unit Tests Per Task

Each task includes specific test cases. All follow naming convention:
`test_{function_name}_{scenario}_{expected_outcome}`

### Integration Test Suite

Create `tests/integration/test_claude_code_integration.py`:

```python
"""Integration tests for Claude Code features."""

class TestSetupCommand:
    def test_setup_installs_all_hub_commands(self, tmp_path): ...
    def test_setup_installs_hooks_configuration(self, tmp_path): ...
    def test_setup_preserves_existing_settings(self, tmp_path): ...

class TestHookScripts:
    def test_session_start_runs_standalone(self): ...
    def test_session_end_runs_standalone(self): ...
    def test_security_guard_blocks_eval(self): ...
    def test_security_guard_allows_safe_commands(self): ...

class TestPluginManifest:
    def test_manifest_is_valid_json(self): ...
    def test_manifest_references_exist(self): ...
```

### Manual Testing Checklist

After implementation, verify in Claude Code:

- [ ] `/attune` launches Socratic discovery
- [ ] `/dev debug` starts debugging session
- [ ] `/testing coverage` runs pytest with coverage
- [ ] `/workflows security` runs security-audit workflow
- [ ] `/release prep` runs release-prep workflow
- [ ] SessionStart hook outputs loaded patterns
- [ ] PreToolUse hook blocks `eval()` in Bash commands
- [ ] MCP tools are available in Claude Code tool list
- [ ] `attune setup` installs all commands, hooks, and MCP config
- [ ] `attune plugin validate` passes with no errors

---

## Summary

| Phase | Tasks | Effort | Key Deliverable |
|-------|-------|--------|-----------------|
| 1 | 3 | 3-5 hours | Hub commands work, hooks run |
| 2 | 4 | 1-2 days | Security guard, subagents, enhanced setup |
| 3 | 3 | 2-3 days | Distributable Claude Code plugin |
| 4 | 4 | 1 week | MCP prompts, agent teams, learning, dynamic context |

**Total estimated effort:** ~2 weeks

**Highest impact tasks:** 1.1 (hub commands), 1.2 (hook wiring), 2.1 (security guard), 3.1 (plugin manifest)

---

## Critical Files Reference

| File | Purpose |
|------|---------|
| `src/attune/commands/attune.md` | Template for hub command skills |
| `attune_llm/hooks/scripts/session_start.py` | Needs `__main__` adaptation for Claude Code |
| `src/attune/mcp/server.py` | Extend with MCP prompts |
| `src/attune/cli_minimal.py:850` | `cmd_setup` to enhance |
| `attune_llm/hooks/config.py` | Internal hook models to align with Claude Code format |
